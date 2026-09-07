# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from fetch_github_meta import fetch_repo, fetch_releases


def _mock_response(data):
    """Return a context-manager mock that yields JSON-encoded data."""
    encoded = json.dumps(data).encode()
    mock = MagicMock()
    mock.read.return_value = encoded
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# ── fetch_repo fork detection ────────────────────────────────────────────────

def test_fetch_repo_non_fork_has_no_fork_fields():
    data = {
        "stargazers_count": 42,
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
        "fork": False,
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("foo/bar")
    assert result["stars"] == 42
    assert result["_is_fork"] is False
    assert result["_fork_parent_name"] == ""
    assert result["_fork_parent_url"] == ""


def test_fetch_repo_fork_captures_parent():
    data = {
        "stargazers_count": 10,
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
        "fork": True,
        "parent": {
            "full_name": "upstream/repo",
            "html_url": "https://github.com/upstream/repo",
        },
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("foo/bar")
    assert result["_is_fork"] is True
    assert result["_fork_parent_name"] == "upstream/repo"
    assert result["_fork_parent_url"] == "https://github.com/upstream/repo"


def test_fetch_repo_fork_without_parent_key():
    """fork:true but no parent key (edge case) — should not crash."""
    data = {
        "stargazers_count": 5,
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
        "fork": True,
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("foo/bar")
    assert result["_is_fork"] is True
    assert result["_fork_parent_name"] == ""


# ── fetch_releases ────────────────────────────────────────────────────────────

def test_fetch_releases_returns_non_draft_releases():
    data = [
        {
            "tag_name": "v1.1.0", "name": "v1.1.0",
            "published_at": "2026-05-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v1.1.0",
            "prerelease": False, "draft": False,
        },
        {
            "tag_name": "v1.0.0-rc1", "name": "RC1",
            "published_at": "2026-04-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v1.0.0-rc1",
            "prerelease": True, "draft": False,
        },
        {
            "tag_name": "v0.9.0", "name": "v0.9.0",
            "published_at": "2026-03-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v0.9.0",
            "prerelease": False, "draft": True,   # draft — must be excluded
        },
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_releases("foo/bar")
    assert len(result) == 2
    assert result[0]["tagName"] == "v1.1.0"
    assert result[0]["prerelease"] is False
    assert result[1]["tagName"] == "v1.0.0-rc1"
    assert result[1]["prerelease"] is True


def test_fetch_releases_empty_repo():
    with patch("urllib.request.urlopen", return_value=_mock_response([])):
        result = fetch_releases("foo/bar")
    assert result == []


def test_fetch_releases_name_falls_back_to_tag():
    data = [{
        "tag_name": "v2.0.0", "name": "",
        "published_at": "2026-05-10T00:00:00Z",
        "html_url": "https://github.com/foo/bar/releases/tag/v2.0.0",
        "prerelease": False, "draft": False,
    }]
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_releases("foo/bar")
    assert result[0]["name"] == "v2.0.0"


# ── release ordering ─────────────────────────────────────────────────────────
# src/_data/entries.js resolves latestStableRelease with releases.find(...),
# which takes the FIRST match in array order and therefore assumes the list is
# newest-first. GitHub's list-releases endpoint sorts by created_at, not
# published_at, so a release tagged from an older commit but published later
# (tt-finetune's demo-2026-08-29) arrives out of order and quietly breaks that
# assumption. Sort here so the invariant the data layer documents is actually
# guaranteed, for every repo, on every nightly run.

def test_fetch_releases_sorts_newest_published_first():
    data = [
        {   # created earlier, published LAST — the out-of-order case
            "tag_name": "v0.2.1", "name": "v0.2.1",
            "published_at": "2026-08-28T17:21:58Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v0.2.1",
            "prerelease": False, "draft": False,
        },
        {
            "tag_name": "demo-2026-08-29", "name": "Demo",
            "published_at": "2026-08-29T15:44:38Z",
            "html_url": "https://github.com/foo/bar/releases/tag/demo-2026-08-29",
            "prerelease": False, "draft": False,
        },
        {
            "tag_name": "v0.2.0", "name": "v0.2.0",
            "published_at": "2026-08-26T07:14:15Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v0.2.0",
            "prerelease": False, "draft": False,
        },
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_releases("foo/bar")
    assert [r["tagName"] for r in result] == ["demo-2026-08-29", "v0.2.1", "v0.2.0"]


def test_fetch_releases_sort_tolerates_missing_published_at():
    # A draft-turned-release can carry a null published_at; it must sort last
    # rather than raising and costing us the whole repo's release list.
    data = [
        {   "tag_name": "v1.0.0", "name": "v1.0.0", "published_at": None,
            "html_url": "https://github.com/foo/bar/releases/tag/v1.0.0",
            "prerelease": False, "draft": False },
        {   "tag_name": "v1.1.0", "name": "v1.1.0",
            "published_at": "2026-05-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v1.1.0",
            "prerelease": False, "draft": False },
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_releases("foo/bar")
    assert [r["tagName"] for r in result] == ["v1.1.0", "v1.0.0"]
