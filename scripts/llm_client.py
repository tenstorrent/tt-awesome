#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Provider-agnostic LLM client for the CI summarization scripts.

Prompts live in prompts/*.prompt.yml — GitHub Models prompt-file format — so
the exact same file drives the GitHub Models playground/evals (the repo's
Models tab) and these scripts. There is deliberately no second copy of any
prompt in Python.

Provider selection (flip via a repository Variable, no code change):

    SUMMARY_PROVIDER = anthropic  (default) — Anthropic Messages API;
                                   needs ANTHROPIC_API_KEY
                       github     — GitHub Models (models.github.ai);
                                   needs GITHUB_TOKEN with `models: read`
    SUMMARY_MODEL    = optional model override for either provider
                       (e.g. "claude-haiku-4-5-20251001" or "openai/gpt-4.1")

When SUMMARY_PROVIDER=github the model defaults to the prompt file's `model`
field; the Anthropic path keeps each caller's model default, since Anthropic
models are not in the GitHub Models catalog (and vice versa).

Free-tier GitHub Models caps requests at 8k input / 4k output tokens — well
above what these prompts need — and the built-in Actions GITHUB_TOKEN works
as the bearer token when the workflow grants `models: read`.
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

VALID_PROVIDERS = ("anthropic", "github")

# {{variable}} placeholders, GitHub Models prompt-file style.
_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def active_provider() -> str:
    """Return the provider selected by SUMMARY_PROVIDER (default: anthropic)."""
    provider = (os.environ.get("SUMMARY_PROVIDER") or "anthropic").strip().lower()
    if provider not in VALID_PROVIDERS:
        print(
            f"  WARN llm_client: unknown SUMMARY_PROVIDER '{provider}', using 'anthropic'",
            file=sys.stderr,
        )
        return "anthropic"
    return provider


def missing_credential(anthropic_api_key: str = "", github_token: str = "") -> str | None:
    """Return the name of the credential the active provider needs but lacks, or None."""
    if active_provider() == "github":
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

    if active_provider() == "github":
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
        # 401/403 usually means GitHub Models isn't enabled for the org or the
        # workflow lacks `models: read`; 404 an unknown/retired model id.
        print(f"  WARN llm_client github {model}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN llm_client github {model}: {e}", file=sys.stderr)
    return ""
