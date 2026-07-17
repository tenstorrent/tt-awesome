# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Tests for scripts/llm_client.py — prompt-file loading, {{var}} rendering,
and Anthropic ↔ GitHub Models provider dispatch.

Run with: pytest tests/test_llm_client.py
"""
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import llm_client as lc


def _mock_urlopen(response_dict):
    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _Resp(json.dumps(response_dict).encode())


# ── Prompt files ──────────────────────────────────────────────────────────────

def test_repo_prompt_files_are_valid():
    """Every prompts/*.prompt.yml parses and carries the fields both the
    GitHub Models playground and llm_client rely on."""
    import yaml

    files = sorted(lc.PROMPTS_DIR.glob("*.prompt.yml"))
    assert files, "no prompt files found in prompts/"
    for f in files:
        data = yaml.safe_load(f.read_text())
        assert data.get("name"), f"{f.name}: missing name"
        assert data.get("description"), f"{f.name}: missing description"
        # model must be a GitHub Models id ({publisher}/{model})
        assert "/" in (data.get("model") or ""), f"{f.name}: model must be publisher/name"
        roles = [m.get("role") for m in data.get("messages", [])]
        assert "user" in roles, f"{f.name}: needs a user message"


def test_load_prompt_rejects_malformed(tmp_path, monkeypatch):
    bad = tmp_path / "broken.prompt.yml"
    bad.write_text("just a string")
    monkeypatch.setattr(lc, "PROMPTS_DIR", tmp_path)
    try:
        lc.load_prompt("broken")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ── Rendering ─────────────────────────────────────────────────────────────────

def test_render_messages_substitutes_and_preserves_unknown():
    msgs = [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Repo: {{repo}} ({{ affiliation }}) {{unknown}}"},
    ]
    out = lc.render_messages(msgs, {"repo": "tenstorrent/tt-metal", "affiliation": "official"})
    assert out[0]["content"] == "Be brief."
    assert out[1]["content"] == "Repo: tenstorrent/tt-metal (official) {{unknown}}"


# ── Provider selection ────────────────────────────────────────────────────────

def test_active_provider_default_and_override(monkeypatch):
    monkeypatch.delenv("SUMMARY_PROVIDER", raising=False)
    assert lc.active_provider() == "anthropic"
    monkeypatch.setenv("SUMMARY_PROVIDER", "GitHub")
    assert lc.active_provider() == "github"
    monkeypatch.setenv("SUMMARY_PROVIDER", "gemini")
    assert lc.active_provider() == "anthropic"  # unknown → warn + default


def test_missing_credential(monkeypatch):
    monkeypatch.delenv("SUMMARY_PROVIDER", raising=False)
    assert lc.missing_credential(anthropic_api_key="", github_token="x") == "ANTHROPIC_API_KEY"
    assert lc.missing_credential(anthropic_api_key="k") is None
    monkeypatch.setenv("SUMMARY_PROVIDER", "github")
    assert lc.missing_credential(anthropic_api_key="k", github_token="") == "GITHUB_TOKEN"
    assert lc.missing_credential(github_token="t") is None


# ── Dispatch ──────────────────────────────────────────────────────────────────

def test_complete_anthropic_path(monkeypatch):
    monkeypatch.delenv("SUMMARY_PROVIDER", raising=False)
    monkeypatch.delenv("SUMMARY_MODEL", raising=False)
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data)
        captured["headers"] = dict(req.header_items())
        return _mock_urlopen({"content": [{"type": "text", "text": "A summary."}]})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        out = lc.complete(
            "summarize-release",
            {"repo": "t/r", "affiliation": "official", "release_name": "v1", "notes": "n"},
            anthropic_model="claude-test-model",
            anthropic_api_key="secret-key",
        )
    assert out == "A summary."
    assert captured["url"] == lc.ANTHROPIC_URL
    assert captured["payload"]["model"] == "claude-test-model"
    assert captured["payload"]["system"]  # system prompt lifted to top level
    assert captured["payload"]["messages"][0]["role"] == "user"
    assert "t/r (official)" in captured["payload"]["messages"][0]["content"]
    assert captured["headers"].get("X-api-key") == "secret-key"


def test_complete_github_path_uses_prompt_model(monkeypatch):
    monkeypatch.setenv("SUMMARY_PROVIDER", "github")
    monkeypatch.delenv("SUMMARY_MODEL", raising=False)
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data)
        captured["headers"] = dict(req.header_items())
        return _mock_urlopen({"choices": [{"message": {"content": "GH summary."}}]})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        out = lc.complete(
            "summarize-release",
            {"repo": "t/r", "affiliation": "official", "release_name": "v1", "notes": "n"},
            anthropic_model="claude-test-model",
            github_token="gh-token",
        )
    assert out == "GH summary."
    assert captured["url"] == lc.GITHUB_MODELS_URL
    # model comes from the prompt file when SUMMARY_MODEL is unset
    assert captured["payload"]["model"] == "openai/gpt-4.1-mini"
    # system prompt stays a chat message on the OpenAI-compatible API
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert captured["headers"].get("Authorization") == "Bearer gh-token"


def test_complete_summary_model_env_overrides(monkeypatch):
    monkeypatch.setenv("SUMMARY_PROVIDER", "github")
    monkeypatch.setenv("SUMMARY_MODEL", "openai/gpt-4.1")
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["payload"] = json.loads(req.data)
        return _mock_urlopen({"choices": [{"message": {"content": "x"}}]})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        lc.complete(
            "summarize-release",
            {"repo": "t/r", "affiliation": "official", "release_name": "v1", "notes": "n"},
            anthropic_model="claude-test-model",
            github_token="gh-token",
        )
    assert captured["payload"]["model"] == "openai/gpt-4.1"


def test_complete_returns_empty_on_http_error(monkeypatch):
    import urllib.error

    monkeypatch.setenv("SUMMARY_PROVIDER", "github")
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(None, 403, "models disabled", {}, None),
    ):
        out = lc.complete(
            "summarize-release",
            {"repo": "t/r", "affiliation": "official", "release_name": "v1", "notes": "n"},
            anthropic_model="m",
            github_token="t",
        )
    assert out == ""
