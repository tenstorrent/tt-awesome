# tests/test_summarize_releases.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import summarize_releases as sr


def test_load_known_urls_returns_set_of_urls(tmp_path):
    feeds = [
        {"url": "https://github.com/foo/bar/releases/tag/v1.0", "type": "release"},
        {"url": "https://youtube.com/watch?v=abc", "type": "video"},
    ]
    f = tmp_path / "planet_feeds.json"
    f.write_text(json.dumps(feeds))
    result = sr.load_known_urls(f)
    assert result == {
        "https://github.com/foo/bar/releases/tag/v1.0",
        "https://youtube.com/watch?v=abc",
    }


def test_load_known_urls_returns_empty_set_when_file_missing(tmp_path):
    result = sr.load_known_urls(tmp_path / "nonexistent.json")
    assert result == set()


def test_resolve_affiliation_finds_matching_entry(tmp_path):
    entry = {
        "affiliation": "official",
        "links": [{"type": "repo", "url": "https://github.com/tenstorrent/tt-metal"}],
    }
    f = tmp_path / "tt-metal.json"
    f.write_text(json.dumps(entry))
    result = sr.resolve_affiliation("https://github.com/tenstorrent/tt-metal", [tmp_path])
    assert result == "official"


def test_resolve_affiliation_returns_community_when_no_match(tmp_path):
    result = sr.resolve_affiliation("https://github.com/unknown/repo", [tmp_path])
    assert result == "community"


def test_resolve_affiliation_handles_trailing_slash(tmp_path):
    entry = {
        "affiliation": "community",
        "links": [{"type": "repo", "url": "https://github.com/foo/bar"}],
    }
    f = tmp_path / "bar.json"
    f.write_text(json.dumps(entry))
    # URL with trailing slash should still match
    result = sr.resolve_affiliation("https://github.com/foo/bar/", [tmp_path])
    assert result == "community"


def test_load_known_urls_returns_empty_set_on_malformed_json(tmp_path):
    f = tmp_path / "planet_feeds.json"
    f.write_text("not valid json {{{")
    result = sr.load_known_urls(f)
    assert result == set()


def _mock_urlopen(data):
    encoded = json.dumps(data).encode()
    mock = MagicMock()
    mock.read.return_value = encoded
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_fetch_release_body_returns_body():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen({"body": "## What's new\n\nAdded feature X."})):
        result = sr.fetch_release_body("tenstorrent/tt-metal", "v1.0.0")
    assert result == "## What's new\n\nAdded feature X."


def test_fetch_release_body_returns_empty_on_http_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 404, "Not Found", {}, None)):
        result = sr.fetch_release_body("tenstorrent/tt-metal", "v1.0.0")
    assert result == ""


def test_fetch_release_body_returns_empty_when_body_is_none():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen({"body": None})):
        result = sr.fetch_release_body("tenstorrent/tt-metal", "v1.0.0")
    assert result == ""


def test_is_sparse_true_for_empty():
    assert sr.is_sparse("") is True
    assert sr.is_sparse("   \n  ") is True


def test_is_sparse_true_for_short_body():
    assert sr.is_sparse("Bug fixes.") is True


def test_is_sparse_false_for_substantial_body():
    body = "A" * 151
    assert sr.is_sparse(body) is False


def test_call_github_models_returns_summary():
    api_response = {
        "choices": [{"message": {"content": "This release adds multi-chip support."}}]
    }
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_response)):
        result = sr.call_github_models(
            repo="tenstorrent/tt-metal",
            release_name="v0.58.0",
            body="## Multi-chip support\n\nAdds routing for n300 configurations across 4 chips...\n" + "x" * 120,
            affiliation="official",
        )
    assert result == "This release adds multi-chip support."


def test_call_github_models_returns_empty_on_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 429, "Too Many Requests", {}, None)):
        result = sr.call_github_models(
            repo="tenstorrent/tt-metal",
            release_name="v0.58.0",
            body="x" * 200,
            affiliation="official",
        )
    assert result == ""
