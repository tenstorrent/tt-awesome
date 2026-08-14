# tests/test_summarize_releases.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import base64
import json
import sys

import pytest
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


def _mock_raw(text):
    """A urlopen mock whose body is raw bytes (e.g. a download_url response)."""
    mock = MagicMock()
    mock.read.return_value = text.encode()
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


def test_is_sparse_boundary_at_limit():
    # Bodies at or above SPARSE_LIMIT pass; one char below is still sparse.
    assert sr.is_sparse("A" * (sr.SPARSE_LIMIT - 1)) is True
    assert sr.is_sparse("A" * sr.SPARSE_LIMIT) is False


def test_is_sparse_false_for_terse_multi_bullet_release():
    # Representative of ttsim v1.8.4: a few real bullets, ~134 chars.
    # The 120-char limit must let these through (regression guard).
    body = (
        "- Added more ARC, PCIe, and tile register functionality\n"
        "- Various minor Tensix bug fixes/features\n"
        "- Improved error message reporting"
    )
    assert len(body.strip()) >= sr.SPARSE_LIMIT
    assert sr.is_sparse(body) is False


def test_main_skips_prerelease_tags(tmp_path, monkeypatch):
    # dev: "1.3.0.dev20260609002802", "v0.73.0-dev20260610"
    # RC:  "v0.72.0-rc4", "ttkmd-2.9.0-rc1"
    # QA:  "v1.0.0-qa1"
    # alpha/beta: "v0.17.0-alpha" (tt-buda), "v1.0.0-beta2"
    # CI experiment tags: "7.67.0-strength-49763" (sfpi)
    prerelease_tags = [
        "1.3.0.dev20260609002802",
        "v0.73.0-dev20260610",
        "v0.9.5-dev.260424",
        "v0.72.0-rc4",
        "ttkmd-2.9.0-rc1",
        "v1.0.0-qa1",
        "v0.17.0-alpha",
        "v1.0.0-beta2",
        "7.67.0-strength-49763",
    ]
    releases = [
        {"tagName": t, "name": t, "publishedAt": "2026-06-01T00:00:00Z",
         "url": f"https://github.com/tenstorrent/tt-metal/releases/tag/{t}",
         "prerelease": False}
        for t in prerelease_tags
    ]
    meta = {"https://github.com/tenstorrent/tt-metal": {"releases": releases}}
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps([]))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

    with patch.object(sr, "fetch_release_body") as mock_body:
        sr.main([])

    mock_body.assert_not_called()
    assert json.loads(feeds_file.read_text()) == []


def test_call_summarization_model_returns_summary(monkeypatch):
    monkeypatch.setenv("SUMMARY_PROVIDER", "anthropic")
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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model",  return_value="A summary."):
        sr.main([])  # must not raise TypeError

    result = json.loads(feeds_file.read_text())
    assert len(result) == 1
    assert result[0]["date"] == "1970-01-01"


# ── Changelog fallback: bodies that defer to CHANGELOG.md ────────────────────
# Some repos (e.g. tt-vscode-toolkit) publish a fixed boilerplate release body
# — install instructions, prerequisites, and a "What's New → See CHANGELOG.md"
# pointer — while the actual per-version changes live in CHANGELOG.md. The
# summarizer must recognise this and summarize the matching changelog section
# instead of the boilerplate preamble.

SAMPLE_CHANGELOG = """\
# Changelog

All notable changes to the project will be documented in this file.

The format is based on Keep a Changelog.

---

## [0.0.514] - 2026-06-23
### Fixed
- **isTtsimQemuInstalled avoids grep subprocess** — pure-Node stdout check.
- **Disk space check uses correct mount point** — threshold raised to 12 GB.

## [0.0.513] - 2026-06-23
### Fixed
- **python -> python3 across all remaining lessons** — Ubuntu 24.04 fix.
"""

BOILERPLATE_BODY = """\
## tt-vscode-toolkit v0.0.514

### Installation

code --install-extension Tenstorrent.tt-vscode-toolkit

### Prerequisites

- Tenstorrent hardware (n150, n300, T3000, p100, p150, or Galaxy)
- Linux (Ubuntu 20.04+, RHEL 8+)

### What's New

See [CHANGELOG.md](https://github.com/tenstorrent/tt-vscode-toolkit/blob/v0.0.514/CHANGELOG.md)
"""


def test_extract_changelog_section_returns_matching_version():
    section = sr.extract_changelog_section(SAMPLE_CHANGELOG, "v0.0.514")
    assert section is not None
    assert "isTtsimQemuInstalled avoids grep subprocess" in section
    assert "Disk space check uses correct mount point" in section
    # Must not bleed into the previous/next version's notes.
    assert "python3 across all remaining lessons" not in section
    assert "0.0.513" not in section


def test_extract_changelog_section_strips_v_prefix():
    # Tag is "v0.0.514" but the changelog header reads "## [0.0.514]".
    assert sr.extract_changelog_section(SAMPLE_CHANGELOG, "v0.0.514") is not None
    # And a bare version tag (no leading v) also matches.
    assert sr.extract_changelog_section(SAMPLE_CHANGELOG, "0.0.514") is not None


def test_extract_changelog_section_returns_none_when_absent():
    assert sr.extract_changelog_section(SAMPLE_CHANGELOG, "v9.9.9") is None
    assert sr.extract_changelog_section("", "v0.0.514") is None


def test_extract_changelog_section_no_false_substring_match():
    # "0.0.51" must NOT match the "0.0.514" header (version boundary).
    assert sr.extract_changelog_section(SAMPLE_CHANGELOG, "v0.0.51") is None


PRERELEASE_CHANGELOG = """\
# Changelog

## [0.0.514-rc1] - 2026-06-20
### Added
- A release-candidate-only entry that is long enough to clear the sparse gate.

## [0.0.514] - 2026-06-23
### Fixed
- The actual stable entry, also long enough to clear the sparse gate easily.
"""


def test_extract_changelog_section_ignores_prerelease_suffix():
    # Requesting the stable tag must return the stable section, never a
    # pre-release heading like "[0.0.514-rc1]" that shares the version prefix —
    # even when the pre-release heading appears first in the file.
    section = sr.extract_changelog_section(PRERELEASE_CHANGELOG, "v0.0.514")
    assert "The actual stable entry" in section
    assert "release-candidate-only" not in section
    assert "rc1" not in section


def test_extract_changelog_section_no_match_for_prerelease_only():
    # If only a pre-release section exists, a stable-tag request finds nothing
    # (better to fall back than to summarize the wrong version's notes).
    only_rc = "# Changelog\n\n## [0.0.514-rc1] - 2026-06-20\n### Added\n- rc only.\n"
    assert sr.extract_changelog_section(only_rc, "v0.0.514") is None


DUP_CHANGELOG = """\
# Changelog

## [0.0.454] - 2026-05-27
### Changed
- Hardware naming normalization across lessons, pages, and docs prose/tables.

## [0.0.454] - 2026-06-05
### Fixed
- Web build GitHub-blob media links now carry the BASE_PATH prefix correctly.
"""


def test_extract_changelog_section_disambiguates_by_date():
    # The same version appears twice (an upstream duplicate). When a release
    # date is supplied, the section whose header carries that date wins.
    section = sr.extract_changelog_section(DUP_CHANGELOG, "v0.0.454", date="2026-06-05")
    assert "Web build GitHub-blob media links" in section
    assert "Hardware naming normalization" not in section


def test_extract_changelog_section_first_match_without_date():
    # With no date hint, fall back to the first matching section.
    section = sr.extract_changelog_section(DUP_CHANGELOG, "v0.0.454")
    assert "Hardware naming normalization" in section


def test_fetch_changelog_section_falls_back_to_resolved_default_branch():
    # The changelog at the release tag lags (no section yet); the section only
    # exists on the repo's default branch — which here is "develop", not main.
    # fetch must resolve the real default branch and look there.
    tagged   = {"content": base64.b64encode(SAMPLE_CHANGELOG.encode()).decode()}  # lacks 0.0.999
    repo_meta = {"default_branch": "develop"}
    on_branch = {"content": base64.b64encode(
        "# Changelog\n\n## [0.0.999] - 2026-07-01\n### Added\n"
        "- A genuinely new and sufficiently long changelog entry for testing.\n".encode()
    ).decode()}
    # Call order: changelog@tag -> /repos/{repo} (default branch) -> changelog@develop
    responses = [_mock_urlopen(tagged), _mock_urlopen(repo_meta), _mock_urlopen(on_branch)]
    with patch("urllib.request.urlopen", side_effect=responses):
        section = sr.fetch_changelog_section("tenstorrent/some-repo", "v0.0.999")
    assert section is not None
    assert "genuinely new" in section


def test_fetch_changelog_text_uses_download_url_for_large_file():
    # Files over ~1MB come back from the Contents API with empty `content` and a
    # `download_url`. The fetcher must follow that URL instead of returning "".
    contents = _mock_urlopen({"content": "", "download_url": "https://raw/CHANGELOG.md"})
    raw = _mock_raw("# Changelog\n\n## [0.0.999] - 2026-07-01\n### Added\n- A big changelog.\n")
    with patch("urllib.request.urlopen", side_effect=[contents, raw]):
        text = sr._fetch_changelog_text("tenstorrent/big-repo", "main")
    assert text is not None
    assert "0.0.999" in text


def test_fetch_changelog_text_tries_next_name_when_content_empty():
    # A candidate file that yields no usable content (empty, no download_url)
    # must not abort the search — the next CHANGELOG_NAMES candidate is tried.
    empty = _mock_urlopen({"content": "", "download_url": None})            # CHANGELOG.md
    good_text = "# Changelog\n\n## [1.0.0] - 2026-01-01\n### Added\n- Real notes here.\n"
    good = _mock_urlopen({"content": base64.b64encode(good_text.encode()).decode()})  # CHANGELOG
    with patch("urllib.request.urlopen", side_effect=[empty, good]):
        text = sr._fetch_changelog_text("tenstorrent/repo", "main")
    assert text is not None
    assert "1.0.0" in text


def test_body_defers_to_changelog_true_for_boilerplate():
    assert sr.body_defers_to_changelog(BOILERPLATE_BODY) is True


def test_body_defers_to_changelog_false_for_real_notes():
    body = (
        "## What's new\n\nAdds multi-chip routing for n300 configurations across "
        "four chips, plus assorted bug fixes in the dispatch path." + "x" * 80
    )
    assert sr.body_defers_to_changelog(body) is False


def test_main_summarizes_changelog_when_body_defers(tmp_path, monkeypatch):
    meta = {
        "https://github.com/tenstorrent/tt-vscode-toolkit": {
            "releases": [{
                "tagName": "v0.0.514",
                "name": "v0.0.514",
                "publishedAt": "2026-06-23T12:00:00Z",
                "url": "https://github.com/tenstorrent/tt-vscode-toolkit/releases/tag/v0.0.514",
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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

    with patch.object(sr, "fetch_release_body", return_value=BOILERPLATE_BODY), \
         patch.object(sr, "fetch_changelog_section", return_value=(
             "## [0.0.514]\n### Fixed\n"
             "- Real change A — isTtsimQemuInstalled now avoids the grep subprocess.\n"
             "- Real change B — disk space check uses the correct mount point."
         )) as mock_cl, \
         patch.object(sr, "call_summarization_model", return_value="A real summary.") as mock_llm:
        sr.main([])

    # The changelog section — not the boilerplate body — must be what gets summarized.
    mock_cl.assert_called_once_with("tenstorrent/tt-vscode-toolkit", "v0.0.514", date="2026-06-23")
    summarized_content = mock_llm.call_args.kwargs.get("body") or mock_llm.call_args.args[2]
    assert "Real change A" in summarized_content
    assert "Installation" not in summarized_content


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
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model",  return_value="A summary."), \
         patch("builtins.print") as mock_print:
        sr.main(["--dry-run"])

    # The final summary line must say exactly 1 item would be added, not 0 or 2+.
    assert any(
        "1 item would be added" in str(call.args)
        for call in mock_print.call_args_list
    )


def test_main_exits_nonzero_when_every_summarization_fails(tmp_path, monkeypatch, capsys):
    """A dead provider must go red, not masquerade as 'nothing new to summarize'.

    Regression test for the GitHub Models retirement: SUMMARY_PROVIDER=github
    kept passing the credential preflight (GITHUB_TOKEN is always present in
    Actions) while every inference call returned '', so the nightly job logged
    a SKIP per release and exited 0 with an empty PR.
    """
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
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps([]))

    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()
    (entry_dir / "tt-metal.json").write_text(json.dumps({
        "affiliation": "official",
        "links": [{"type": "repo", "url": "https://github.com/tenstorrent/tt-metal"}],
    }))

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)
    monkeypatch.setattr(sr, "TOKEN",         "fake-token")
    monkeypatch.setattr(sr, "FOUNDRY_KEY",   "fake-foundry-key")

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_summarization_model", return_value=""):
        with pytest.raises(SystemExit) as excinfo:
            sr.main([])

    assert excinfo.value.code == 1
    assert "all 1 summarization call(s) failed" in capsys.readouterr().err
    # The feed file must be left untouched when nothing could be summarized.
    assert json.loads(feeds_file.read_text()) == []


# ── rename-proof release dedup ───────────────────────────────────────────────

def test_release_key_normalizes_case_and_spacing():
    assert sr.release_key("  tt-bh-linux   v0.11 ") == sr.release_key("TT-BH-Linux v0.11")


def test_load_known_release_keys_only_covers_releases(tmp_path):
    feeds = [
        {"type": "release", "title": "tt-bh-linux v0.11",
         "url": "https://github.com/tenstorrent/tt-bh-linux/releases/tag/v0.11"},
        {"type": "video", "title": "Some Talk", "url": "https://youtube.com/watch?v=abc"},
        {"type": "release", "url": "https://example.com/no-title"},
    ]
    p = tmp_path / "planet_feeds.json"
    p.write_text(json.dumps(feeds))
    assert sr.load_known_release_keys(p) == {"tt-bh-linux v0.11"}


def test_renamed_repo_release_is_recognized_as_known(tmp_path):
    """The real bug: GitHub reports the new owner, so the URL check misses it.

    tt-bh-linux moved tenstorrent -> tenstorrent-riscv-software and BarraCUDA
    was renamed to Booth; both published twice on the planet.
    """
    feeds = [{"type": "release", "title": "tt-bh-linux v0.11",
              "url": "https://github.com/tenstorrent/tt-bh-linux/releases/tag/v0.11"}]
    p = tmp_path / "planet_feeds.json"
    p.write_text(json.dumps(feeds))

    known_urls = sr.load_known_urls(p)
    known_keys = sr.load_known_release_keys(p)

    # Same release, new canonical URL after the move.
    new_url = "https://github.com/tenstorrent-riscv-software/tt-bh-linux/releases/tag/v0.11"
    assert new_url not in known_urls               # URL check alone lets it through
    assert sr.release_key("tt-bh-linux v0.11") in known_keys   # identity check catches it


def test_distinct_tags_are_not_collapsed(tmp_path):
    feeds = [{"type": "release", "title": "tt-bh-linux v0.11", "url": "https://x/v0.11"}]
    p = tmp_path / "planet_feeds.json"
    p.write_text(json.dumps(feeds))
    known_keys = sr.load_known_release_keys(p)
    assert sr.release_key("tt-bh-linux v0.12") not in known_keys
    assert sr.release_key("other-proj v0.11") not in known_keys


def test_one_malformed_item_does_not_wipe_the_dedup_set(tmp_path, capsys):
    """A single bad record must not silently disable rename dedup entirely."""
    feeds = [
        {"type": "release", "title": "good-proj v1.0", "url": "https://x/1"},
        {"type": "release", "title": 123, "url": "https://x/2"},     # non-string
        {"type": "release", "title": "   ", "url": "https://x/3"},   # blank
        "not-even-a-dict",
        {"type": "release", "title": "other-proj v2.0", "url": "https://x/4"},
    ]
    p = tmp_path / "planet_feeds.json"
    p.write_text(json.dumps(feeds))

    keys = sr.load_known_release_keys(p)
    assert keys == {"good-proj v1.0", "other-proj v2.0"}

    # ...and the skipped ones are reported rather than swallowed.
    err = capsys.readouterr().err
    assert err.count("WARN") == 2
    assert "https://x/2" in err and "https://x/3" in err


def test_unreadable_file_does_not_double_warn(tmp_path, capsys):
    """load_known_urls already reports a malformed file; don't warn twice."""
    p = tmp_path / "planet_feeds.json"
    p.write_text("{not json")
    assert sr.load_known_release_keys(p) == set()
    assert "WARN" not in capsys.readouterr().err
