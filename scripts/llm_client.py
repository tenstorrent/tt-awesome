#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Provider-agnostic LLM client for the CI summarization scripts.

Prompts live in prompts/*.prompt.yml, kept in GitHub Models prompt-file format
even though that service is gone: it is a serviceable provider-neutral
container, and keeping it means there is still no second copy of any prompt in
Python.

Provider selection (flip via a repository Variable, no code change):

    SUMMARY_PROVIDER = foundry    (default) — Claude on Microsoft Foundry;
                                   needs FOUNDRY_API_KEY
                       anthropic  — Anthropic Messages API direct;
                                   needs ANTHROPIC_API_KEY
                       github     — GitHub Models. RETIRED, see below.
    SUMMARY_MODEL    = optional model override for any provider
    FOUNDRY_ENDPOINT = optional override for the Foundry deployment URL

Foundry serves Claude behind an Anthropic-compatible surface at
``/anthropic/v1/messages``, so it takes the same request and response shape as
the direct Anthropic path — the only differences are the host and the fact that
billing runs through Azure. Both paths therefore share _call_anthropic_api().

⚠️ The `github` provider no longer works. GitHub Models was fully retired on
2026-07-30 — the playground, catalog, and inference API are gone for every
customer, and models.github.ai now answers every request with HTTP 410
`github_models_retirement_brownout`. The path is kept only so an unconverted
SUMMARY_PROVIDER=github fails with an explanatory message instead of a bare
HTTP code. See https://github.blog/changelog/2026-07-30-github-models-is-now-retired/

Not supported: GitHub Copilot inference. api.githubcopilot.com accepts only
interactive OAuth (gho_) tokens — measured from inside Actions, it rejects a
PAT with "Personal Access Tokens are not supported for this endpoint" and the
built-in token with "GitHub App Server-To-Server Tokens are not supported for
this endpoint" — and the Copilot CLI route that does work in CI needs a node
install plus a subprocess per call. Foundry is the simpler dependency.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROMPTS_DIR = ROOT / "prompts"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"

# Microsoft Foundry, Anthropic-compatible surface. Overridable via
# FOUNDRY_ENDPOINT so a new resource does not need a code change.
FOUNDRY_URL = (
    os.environ.get("FOUNDRY_ENDPOINT")
    or "https://tsingletary-8246-resource.services.ai.azure.com/anthropic/v1/messages"
)
# Foundry catalogs Claude without the date suffix that api.anthropic.com uses.
FOUNDRY_DEFAULT_MODEL = "claude-haiku-4-5"

VALID_PROVIDERS = ("anthropic", "github", "foundry")
DEFAULT_PROVIDER = "foundry"

# {{variable}} placeholders, GitHub Models prompt-file style.
_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def active_provider() -> str:
    """Return the provider selected by SUMMARY_PROVIDER (default: foundry)."""
    provider = (os.environ.get("SUMMARY_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if provider not in VALID_PROVIDERS:
        print(
            f"  WARN llm_client: unknown SUMMARY_PROVIDER '{provider}', using '{DEFAULT_PROVIDER}'",
            file=sys.stderr,
        )
        return DEFAULT_PROVIDER
    return provider


def missing_credential(
    anthropic_api_key: str = "", github_token: str = "", foundry_api_key: str = ""
) -> str | None:
    """Return the name of the credential the active provider needs but lacks, or None."""
    provider = active_provider()
    if provider == "foundry":
        return None if foundry_api_key else "FOUNDRY_API_KEY"
    if provider == "github":
        return None if github_token else "GITHUB_TOKEN"
    return None if anthropic_api_key else "ANTHROPIC_API_KEY"


def load_prompt(name: str) -> dict:
    """Load prompts/<name>.prompt.yml. Raises on a missing or malformed file —
    a broken prompt should fail the CI step loudly, not degrade silently."""
    try:
        import yaml  # lazy: PyYAML is only required when a prompt is actually used
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "PyYAML is required to load prompts/*.prompt.yml — install it with "
            "`pip install pyyaml` (CI workflows do this in their setup step)."
        ) from e

    path = PROMPTS_DIR / f"{name}.prompt.yml"
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not data.get("messages"):
        raise ValueError(f"{path}: expected a mapping with a 'messages' list")
    return data


def render_messages(messages: list, variables: dict) -> list:
    """Substitute {{var}} placeholders; unknown placeholders are left intact."""
    rendered = []
    for msg in messages:
        content = _VAR_RE.sub(
            lambda m: str(variables.get(m.group(1), m.group(0))),
            msg.get("content") or "",
        )
        rendered.append({"role": msg["role"], "content": content})
    return rendered


def complete(
    prompt_name: str,
    variables: dict,
    *,
    anthropic_model: str,
    anthropic_api_key: str = "",
    github_token: str = "",
    foundry_api_key: str = "",
    timeout: int = 30,
) -> str:
    """Render a prompt file and run it on the active provider.

    Returns the model's text reply, or "" on any API error (matching the
    existing degrade-gracefully contract of both CI scripts). Credentials are
    passed in by the caller so tests can monkeypatch the caller's module-level
    constants, as they always have.
    """
    prompt = load_prompt(prompt_name)
    messages = render_messages(prompt.get("messages", []), variables)
    max_tokens = int((prompt.get("modelParameters") or {}).get("maxTokens") or 400)
    model_override = (os.environ.get("SUMMARY_MODEL") or "").strip()

    provider = active_provider()

    if provider == "foundry":
        model = model_override or FOUNDRY_DEFAULT_MODEL
        return _call_anthropic_api(FOUNDRY_URL, model, messages, max_tokens,
                                   foundry_api_key, timeout, label="foundry")

    if provider == "github":
        model = model_override or prompt.get("model") or "openai/gpt-4.1-mini"
        return _call_github_models(model, messages, max_tokens, github_token, timeout)

    model = model_override or anthropic_model
    return _call_anthropic_api(ANTHROPIC_URL, model, messages, max_tokens,
                               anthropic_api_key, timeout, label="anthropic")


def _error_detail(e: "urllib.error.HTTPError", limit: int = 300) -> str:
    """Best-effort human-readable detail from an HTTP error body.

    Providers disagree on error shape ({"error": {"message": ...}} vs
    {"error": "..."} vs plain text), and an unreadable body must never mask the
    status code, so every failure path here degrades to ''.
    """
    try:
        raw = e.read().decode("utf-8", "replace").strip()
    except Exception:
        return ""
    if not raw:
        return ""
    try:
        err = json.loads(raw).get("error", raw)
        detail = err.get("message", "") if isinstance(err, dict) else str(err)
    except Exception:
        detail = raw
    detail = " ".join(detail.split())
    return detail[:limit] + ("…" if len(detail) > limit else "")


def _call_anthropic_api(url, model, messages, max_tokens, api_key, timeout, *, label) -> str:
    """POST an Anthropic Messages request. Serves both Anthropic and Foundry.

    Foundry's ``/anthropic/v1/messages`` mirrors the upstream contract — same
    payload, same ``x-api-key`` auth, same ``content[0].text`` response — so the
    only per-provider state is the URL, the key, and the label in log lines.
    """
    # The Messages API takes system text as a top-level field, not a message.
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    chat = [m for m in messages if m["role"] != "system"]
    payload = {"model": model, "max_tokens": max_tokens, "messages": chat}
    if system:
        payload["system"] = system

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", ANTHROPIC_VERSION)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        # Surface the body: on Foundry a 404 usually means the model id is not
        # deployed on this resource, and a 401 means the key belongs to a
        # different one. Neither is diagnosable from the status code alone.
        print(f"  WARN llm_client {label} {model}: HTTP {e.code} {_error_detail(e)}".rstrip(),
              file=sys.stderr)
    except Exception as e:
        print(f"  WARN llm_client {label} {model}: {e}", file=sys.stderr)
    return ""


def _call_github_models(model, messages, max_tokens, token, timeout) -> str:
    # OpenAI-compatible chat completions; system prompts ride along as messages.
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}

    req = urllib.request.Request(GITHUB_MODELS_URL, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        # 410 is now the only realistic outcome: GitHub Models was retired on
        # 2026-07-30 and the endpoint answers every request with it.
        if e.code == 410:
            print(
                "  WARN llm_client github: GitHub Models was retired on 2026-07-30 and no "
                "longer serves any request — set SUMMARY_PROVIDER=foundry",
                file=sys.stderr,
            )
        else:
            print(f"  WARN llm_client github {model}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN llm_client github {model}: {e}", file=sys.stderr)
    return ""
