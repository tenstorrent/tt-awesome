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


# ── Rename / org-move detection ──────────────────────────────────────────────
#
# GitHub answers a request for a renamed repo with a 301 that urllib follows,
# so the JSON that comes back describes the repo under its *current* name.
# fetch_repo keeps that name; main() compares it to the entry's and rewrites
# the entry when they differ.

from fetch_github_meta import rename_target, apply_rename, format_renames_md
import fetch_github_meta as fgm


def test_fetch_repo_captures_current_full_name_and_url():
    data = {
        "stargazers_count": 14, "updated_at": "2026-10-19T00:00:00Z",
        "full_name": "hedgehope/wolfpine",
        "html_url": "https://github.com/hedgehope/wolfpine",
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("mesham/tt-sim")
    assert result["_full_name"] == "hedgehope/wolfpine"
    assert result["_html_url"] == "https://github.com/hedgehope/wolfpine"


def test_rename_target_is_none_when_unchanged():
    assert rename_target("tenstorrent/tt-metal", "tenstorrent/tt-metal") is None


def test_rename_target_ignores_case_only_differences():
    # GitHub repo names are case-insensitive; "Tenstorrent/TT-Metal" in an
    # entry is the same repo as "tenstorrent/tt-metal" in the API response.
    assert rename_target("Tenstorrent/TT-Metal", "tenstorrent/tt-metal") is None


def test_rename_target_is_none_when_api_gave_no_name():
    # A fetch that failed or returned no full_name must never look like a rename.
    assert rename_target("mesham/tt-sim", "") is None


def test_rename_target_detects_rename_and_org_move():
    assert rename_target("mesham/tt-sim", "hedgehope/wolfpine") == "hedgehope/wolfpine"
    assert rename_target("tenstorrent/tt-bh-linux", "tenstorrent-riscv-software/tt-bh-linux") \
        == "tenstorrent-riscv-software/tt-bh-linux"


def _entry_file(tmp_path, **overrides):
    entry = {
        "id": "tt-sim",
        "name": "tt-sim",
        "description": "A simulator — with a dash to check UTF-8 survives.",
        "affiliation": "community",
        "categories": ["riscv-arch"],
        "links": [
            {"type": "repo", "url": "https://github.com/mesham/tt-sim"},
            {"type": "website", "url": "https://github.com/mesham/tt-sim/wiki"},
        ],
        "author": "mesham",
    }
    entry.update(overrides)
    path = tmp_path / "tt-sim.json"
    path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")
    return path


def test_apply_rename_rewrites_repo_link_and_records_previous_repo(tmp_path):
    path = _entry_file(tmp_path)
    apply_rename(path, "mesham/tt-sim", "hedgehope/wolfpine",
                 "https://github.com/hedgehope/wolfpine")
    entry = json.loads(path.read_text())
    assert entry["links"][0] == {"type": "repo", "url": "https://github.com/hedgehope/wolfpine"}
    # Only the canonical repo link moves; other links are left for a human.
    assert entry["links"][1]["url"] == "https://github.com/mesham/tt-sim/wiki"
    assert entry["previous_repos"] == ["mesham/tt-sim"]
    # Everything else, including the author, is untouched — the author did not change.
    assert entry["author"] == "mesham"
    assert entry["name"] == "tt-sim"


def test_apply_rename_preserves_key_order_utf8_and_trailing_newline(tmp_path):
    path = _entry_file(tmp_path)
    before = path.read_text()
    apply_rename(path, "mesham/tt-sim", "hedgehope/wolfpine",
                 "https://github.com/hedgehope/wolfpine")
    after = path.read_text()
    assert "—" in after                      # ensure_ascii=False
    assert after.endswith("}\n")
    # Key order is preserved so the diff is only the lines that changed.
    assert list(json.loads(before)) + ["previous_repos"] == list(json.loads(after))


def test_apply_rename_appends_to_existing_previous_repos_without_duplicates(tmp_path):
    path = _entry_file(tmp_path, previous_repos=["someone/older-name", "mesham/tt-sim"])
    apply_rename(path, "mesham/tt-sim", "hedgehope/wolfpine",
                 "https://github.com/hedgehope/wolfpine")
    entry = json.loads(path.read_text())
    assert entry["previous_repos"] == ["someone/older-name", "mesham/tt-sim"]


def test_main_rewrites_renamed_entry_and_keys_meta_by_new_url(tmp_path, monkeypatch):
    entries = tmp_path / "entries" / "riscv-arch"
    entries.mkdir(parents=True)
    path = _entry_file(entries)
    meta_out = tmp_path / "github_meta.json"
    renames_out = tmp_path / "repo-renames.md"
    monkeypatch.setattr(fgm, "ENTRIES_DIR", tmp_path / "entries")
    monkeypatch.setattr(fgm, "META_OUT", meta_out)
    monkeypatch.setattr(fgm, "RENAMES_OUT", renames_out)
    monkeypatch.setattr(fgm, "fetch_repo", lambda repo: {
        "stars": 14, "updatedAt": "2026-10-19T00:00:00Z",
        "_default_branch": "main", "_is_fork": False,
        "_fork_parent_name": "", "_fork_parent_url": "",
        "_full_name": "hedgehope/wolfpine",
        "_html_url": "https://github.com/hedgehope/wolfpine",
    })
    monkeypatch.setattr(fgm, "fetch_readme_image", lambda repo, b: None)
    monkeypatch.setattr(fgm, "fetch_releases", lambda repo: [])
    monkeypatch.setattr(fgm, "fetch_changelog", lambda repo, b: None)

    fgm.main([])

    entry = json.loads(path.read_text())
    assert entry["links"][0]["url"] == "https://github.com/hedgehope/wolfpine"
    assert entry["previous_repos"] == ["mesham/tt-sim"]
    meta = json.loads(meta_out.read_text())
    # The site looks metadata up by the entry's repo URL, so the key must be
    # the URL the entry now carries, not the one it was fetched under.
    assert list(meta) == ["https://github.com/hedgehope/wolfpine"]
    assert meta["https://github.com/hedgehope/wolfpine"]["stars"] == 14
    md = renames_out.read_text()
    assert md.startswith("### ")
    assert "mesham/tt-sim" in md and "hedgehope/wolfpine" in md
    assert "riscv-arch/tt-sim.json" in md


def test_main_dry_run_reports_rename_but_touches_nothing(tmp_path, monkeypatch):
    entries = tmp_path / "entries" / "riscv-arch"
    entries.mkdir(parents=True)
    path = _entry_file(entries)
    before = path.read_text()
    meta_out = tmp_path / "github_meta.json"
    renames_out = tmp_path / "repo-renames.md"
    monkeypatch.setattr(fgm, "ENTRIES_DIR", tmp_path / "entries")
    monkeypatch.setattr(fgm, "META_OUT", meta_out)
    monkeypatch.setattr(fgm, "RENAMES_OUT", renames_out)
    monkeypatch.setattr(fgm, "fetch_repo", lambda repo: {
        "stars": 1, "updatedAt": "", "_default_branch": "main", "_is_fork": False,
        "_fork_parent_name": "", "_fork_parent_url": "",
        "_full_name": "hedgehope/wolfpine",
        "_html_url": "https://github.com/hedgehope/wolfpine",
    })
    monkeypatch.setattr(fgm, "fetch_readme_image", lambda repo, b: None)
    monkeypatch.setattr(fgm, "fetch_releases", lambda repo: [])
    monkeypatch.setattr(fgm, "fetch_changelog", lambda repo, b: None)

    fgm.main(["--dry-run"])

    assert path.read_text() == before
    assert not renames_out.exists()
    # Metadata is still written (the workflow step always runs it) but keyed by
    # the URL the entry still has, so the site stays consistent with the entry.
    assert list(json.loads(meta_out.read_text())) == ["https://github.com/mesham/tt-sim"]


def test_main_without_rename_leaves_entry_alone_and_writes_no_renames_file(tmp_path, monkeypatch):
    entries = tmp_path / "entries" / "riscv-arch"
    entries.mkdir(parents=True)
    path = _entry_file(entries)
    before = path.read_text()
    renames_out = tmp_path / "repo-renames.md"
    renames_out.write_text("stale from a previous run\n")
    monkeypatch.setattr(fgm, "ENTRIES_DIR", tmp_path / "entries")
    monkeypatch.setattr(fgm, "META_OUT", tmp_path / "github_meta.json")
    monkeypatch.setattr(fgm, "RENAMES_OUT", renames_out)
    monkeypatch.setattr(fgm, "fetch_repo", lambda repo: {
        "stars": 1, "updatedAt": "", "_default_branch": "main", "_is_fork": False,
        "_fork_parent_name": "", "_fork_parent_url": "",
        "_full_name": "mesham/tt-sim", "_html_url": "https://github.com/mesham/tt-sim",
    })
    monkeypatch.setattr(fgm, "fetch_readme_image", lambda repo, b: None)
    monkeypatch.setattr(fgm, "fetch_releases", lambda repo: [])
    monkeypatch.setattr(fgm, "fetch_changelog", lambda repo, b: None)

    fgm.main([])

    assert path.read_text() == before
    # A leftover file from an earlier run must not be mistaken for this run's findings.
    assert not renames_out.exists()


def test_format_renames_md_lists_each_rename_with_a_checklist():
    md = format_renames_md([{
        "entry_id": "tt-sim", "entry_path": "entries/riscv-arch/tt-sim.json",
        "old_repo": "mesham/tt-sim", "new_repo": "hedgehope/wolfpine",
        "new_url": "https://github.com/hedgehope/wolfpine",
    }])
    assert md.startswith("### 🔀 1 repo rename detected")
    assert "`mesham/tt-sim` → [`hedgehope/wolfpine`](https://github.com/hedgehope/wolfpine)" in md
    assert "entries/riscv-arch/tt-sim.json" in md
    for word in ("name", "previous_ids", "description", "author", "affiliation", "packages"):
        assert word in md
