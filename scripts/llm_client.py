#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Provider-agnostic LLM client for the CI summarization scripts.

Prompts live in prompts/*.prompt.yml — GitHub Models prompt-file format — so
the exact same file drives the GitHub Models playground/evals (the repo's
Models tab) and these scripts. There is deliberately no second copy of any
prompt in Python.

Provider selection (flip via a repository Variable, no code change):

    SUMMARY_PROVIDER = copilot    (default) — GitHub Copilot inference;
                                   needs COPILOT_TOKEN (see below)
                       anthropic  — Anthropic Messages API;
                                   needs ANTHROPIC_API_KEY
                       github     — GitHub Models. RETIRED, see below.
    SUMMARY_MODEL    = optional model override for any provider
                       (e.g. "gpt-4o-mini" or "claude-haiku-4-5-20251001")

⚠️ The `github` provider no longer works. GitHub Models was fully retired on
2026-07-30 — the playground, catalog, and inference API are gone for every
customer, and models.github.ai now answers every request with HTTP 410
`github_models_retirement_brownout`. The path is kept only so an unconverted
SUMMARY_PROVIDER=github fails with an explanatory message instead of a bare
HTTP code. See https://github.blog/changelog/2026-07-30-github-models-is-now-retired/

The `copilot` provider is the GitHub-native replacement: an OpenAI-compatible
chat-completions endpoint whose catalog spans OpenAI, Anthropic, and Google
models. It authenticates with a token belonging to an account that holds a
Copilot seat — the Actions-issued GITHUB_TOKEN does NOT have one, so CI must
supply a PAT via the COPILOT_TOKEN secret. Note that only models exposing the
chat-completions API work here; newer responses-API-only ids (gpt-5.x) return
`unsupported_api_for_model`. GitHub's own supported route for Actions is the
Copilot CLI (`actions/ai-inference` with `provider: copilot`), which shells out
per invocation; this client calls the same service directly because these
scripts summarize in a Python loop, one call per release.
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
COPILOT_URL = "https://api.githubcopilot.com/chat/completions"

# The Copilot endpoint rejects requests without an integration id (HTTP 400).
COPILOT_INTEGRATION_ID = "vscode-chat"
# Default Copilot model. Chat-completions-capable and strong at the short,
# voice-sensitive prose these prompts ask for; override with SUMMARY_MODEL.
COPILOT_DEFAULT_MODEL = "claude-sonnet-4.5"

VALID_PROVIDERS = ("anthropic", "github", "copilot")
DEFAULT_PROVIDER = "copilot"

# {{variable}} placeholders, GitHub Models prompt-file style.
_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def active_provider() -> str:
    """Return the provider selected by SUMMARY_PROVIDER (default: copilot)."""
    provider = (os.environ.get("SUMMARY_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if provider not in VALID_PROVIDERS:
        print(
            f"  WARN llm_client: unknown SUMMARY_PROVIDER '{provider}', using '{DEFAULT_PROVIDER}'",
            file=sys.stderr,
        )
        return DEFAULT_PROVIDER
    return provider


def missing_credential(
    anthropic_api_key: str = "", github_token: str = "", copilot_token: str = ""
) -> str | None:
    """Return the name of the credential the active provider needs but lacks, or None."""
    provider = active_provider()
    if provider == "copilot":
        return None if copilot_token else "COPILOT_TOKEN"
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
    copilot_token: str = "",
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

    if provider == "copilot":
        # The prompt file's `model` field is a GitHub Models id (vendor-prefixed)
        # and means nothing to Copilot, so this path carries its own default.
        model = model_override or COPILOT_DEFAULT_MODEL
        return _call_copilot(model, messages, max_tokens, copilot_token, timeout)

    if provider == "github":
        model = model_override or prompt.get("model") or "openai/gpt-4.1-mini"
        return _call_github_models(model, messages, max_tokens, github_token, timeout)

    model = model_override or anthropic_model
    return _call_anthropic(model, messages, max_tokens, anthropic_api_key, timeout)


def _call_anthropic(model, messages, max_tokens, api_key, timeout) -> str:
    # The Messages API takes system text as a top-level field, not a message.
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    chat = [m for m in messages if m["role"] != "system"]
    payload = {"model": model, "max_tokens": max_tokens, "messages": chat}
    if system:
        payload["system"] = system

    req = urllib.request.Request(ANTHROPIC_URL, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", ANTHROPIC_VERSION)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        print(f"  WARN llm_client anthropic {model}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN llm_client anthropic {model}: {e}", file=sys.stderr)
    return ""


def _call_copilot(model, messages, max_tokens, token, timeout) -> str:
    """Call the GitHub Copilot chat-completions endpoint (OpenAI-compatible)."""
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}

    req = urllib.request.Request(COPILOT_URL, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Copilot-Integration-Id", COPILOT_INTEGRATION_ID)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        # 401/403: the token has no Copilot seat (an Actions GITHUB_TOKEN never
        # does). 400 `unsupported_api_for_model`: the id is responses-API only.
        detail = ""
        try:
            detail = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        print(f"  WARN llm_client copilot {model}: HTTP {e.code} {detail}".rstrip(), file=sys.stderr)
    except Exception as e:
        print(f"  WARN llm_client copilot {model}: {e}", file=sys.stderr)
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
                "longer serves any request — set SUMMARY_PROVIDER=copilot",
                file=sys.stderr,
            )
        else:
            print(f"  WARN llm_client github {model}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN llm_client github {model}: {e}", file=sys.stderr)
    return ""
