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


def test_call_summarization_model_returns_summary():
    api_response = {
        "content": [{"type": "text", "text": "This release adds multi-chip support."}]
    }
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_response)):
        result = sr.call_summarization_model(
            repo="tenstorrent/tt-metal",
            release_name="v0.58.0",
            body="## Multi-chip support\n\nAdds routing for n300 configurations across 4 chips...\n" + "x" * 120,
            affiliation="official",
        )
    assert result == "This release adds multi-chip support."


def test_call_summarization_model_returns_empty_on_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 429, "Too Many Requests", {}, None)):
        result = sr.call_summarization_model(
            repo="tenstorrent/tt-metal",
            release_name="v0.58.0",
            body="x" * 200,
            affiliation="official",
        )
    assert result == ""


def test_main_appends_new_release_item(tmp_path, monkeypatch):
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{
                "tagName": "v1.0.0",
                "name": "v1.0.0",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0",
                "prerelease": False,
            }]
        }
    }
    feeds = []
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))

    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()
    (entry_dir / "tt-metal.json").write_text(json.dumps({
        "affiliation": "official",
        "links": [{"type": "repo", "url": "https://github.com/tenstorrent/tt-metal"}],
    }))

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",       "fake-token")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model",  return_value="A great summary."):
        sr.main([])

    result = json.loads(feeds_file.read_text())
    assert len(result) == 1
    item = result[0]
    assert item["type"] == "release"
    assert item["source"] == "github"
    assert item["approved"] is True
    assert item["affiliation"] == "official"
    assert item["description"] == "A great summary."
    assert item["url"] == "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0"


def test_main_skips_sparse_body(tmp_path, monkeypatch):
    meta = {
        "https://github.com/foo/bar": {
            "releases": [{
                "tagName": "v0.1",
                "name": "v0.1",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/foo/bar/releases/tag/v0.1",
                "prerelease": False,
            }]
        }
    }
    feeds = []
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",       "fake-token")

    with patch.object(sr, "fetch_release_body", return_value="Bug fixes."):
        sr.main([])

    result = json.loads(feeds_file.read_text())
    assert result == []


def test_main_dry_run_does_not_write(tmp_path, monkeypatch):
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{
                "tagName": "v2.0.0",
                "name": "v2.0.0",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/tenstorrent/tt-metal/releases/tag/v2.0.0",
                "prerelease": False,
            }]
        }
    }
    feeds = []
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",       "fake-token")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model",  return_value="A summary."):
        sr.main(["--dry-run"])

    result = json.loads(feeds_file.read_text())
    assert result == []


def test_main_skips_already_known_url(tmp_path, monkeypatch):
    url = "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0"
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{"tagName": "v1.0.0", "name": "v1.0.0",
                          "publishedAt": "2026-06-01T12:00:00Z",
                          "url": url, "prerelease": False}]
        }
    }
    feeds = [{"url": url, "type": "release", "approved": True}]
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",       "fake-token")

    with patch.object(sr, "fetch_release_body") as mock_body:
        sr.main([])

    mock_body.assert_not_called()


def test_main_skips_release_with_null_published_at(tmp_path, monkeypatch):
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{
                "tagName": "v1.0.0",
                "name": "v1.0.0",
                "publishedAt": None,
                "url": "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0",
                "prerelease": False,
            }]
        }
    }
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps([]))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",       "fake-token")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model",  return_value="A summary."):
        sr.main([])  # must not raise TypeError

    result = json.loads(feeds_file.read_text())
    assert len(result) == 1
    assert result[0]["date"] == "1970-01-01"


def test_main_dry_run_counts_items(tmp_path, monkeypatch):
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{
                "tagName": "v3.0.0",
                "name": "v3.0.0",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/tenstorrent/tt-metal/releases/tag/v3.0.0",
                "prerelease": False,
            }]
        }
    }
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps([]))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",       "fake-token")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model",  return_value="A summary."), \
         patch("builtins.print") as mock_print:
        sr.main(["--dry-run"])

    # The final summary line must say exactly 1 item would be added, not 0 or 2+.
    assert any(
        "1 item would be added" in str(call.args)
        for call in mock_print.call_args_list
    )
