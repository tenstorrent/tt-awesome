# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate import validate_entry


def valid(overrides=None):
    e = {
        "id": "test-entry",
        "name": "Test Entry",
        "description": "A test entry.",
        "affiliation": "community",
        "categories": ["ai-models"],
        "links": [{"type": "repo", "url": "https://github.com/foo/bar"}],
    }
    if overrides:
        e.update(overrides)
    return e


def p(stem="test-entry"):
    return Path(f"/fake/entries/{stem}.json")


def test_valid_entry_has_no_errors():
    assert validate_entry(p(), valid()) == []


def test_id_must_match_filename():
    errors = validate_entry(p("other"), valid())
    assert any("must match filename" in e for e in errors)


def test_missing_name():
    e = valid()
    del e["name"]
    assert any("name" in err for err in validate_entry(p(), e))


def test_missing_description():
    e = valid()
    del e["description"]
    assert any("description" in err for err in validate_entry(p(), e))


def test_invalid_affiliation():
    errors = validate_entry(p(), valid({"affiliation": "partner"}))
    assert any("affiliation" in e for e in errors)


def test_empty_categories():
    errors = validate_entry(p(), valid({"categories": []}))
    assert any("categories" in e for e in errors)


def test_unknown_category():
    errors = validate_entry(p(), valid({"categories": ["unknown-cat"]}))
    assert any("unknown category" in e for e in errors)


def test_empty_links():
    errors = validate_entry(p(), valid({"links": []}))
    assert any("links" in e for e in errors)


def test_invalid_link_type():
    e = valid({"links": [{"type": "podcast", "url": "https://example.com"}]})
    assert any("type" in err for err in validate_entry(p(), e))


def test_http_url_rejected():
    e = valid({"links": [{"type": "repo", "url": "http://github.com/foo/bar"}]})
    assert any("https://" in err for err in validate_entry(p(), e))


def test_invalid_hardware():
    errors = validate_entry(p(), valid({"hardware": ["rtx4090"]}))
    assert any("hardware" in e for e in errors)


def test_valid_hardware():
    e = valid({"hardware": ["blackhole", "wormhole", "ttsim"]})
    assert validate_entry(p(), e) == []


def test_featured_must_be_bool():
    errors = validate_entry(p(), valid({"featured": "yes"}))
    assert any("featured" in e for e in errors)


def test_multiple_valid_categories_and_links():
    e = valid({
        "categories": ["ai-models", "research"],
        "links": [
            {"type": "repo", "url": "https://github.com/foo/bar"},
            {"type": "talk", "url": "https://fosdem.org/talk", "label": "FOSDEM 2026"},
        ],
    })
    assert validate_entry(p(), e) == []


# ── affiliation vs repo owner ────────────────────────────────────────────────

def test_tt_org_repo_must_be_official():
    """The tt-bh-linux class of bug: a repo in a TT-owned org labeled community."""
    e = valid({"affiliation": "community",
               "links": [{"type": "repo",
                          "url": "https://github.com/tenstorrent-riscv-software/tt-bh-linux"}]})
    errors = validate_entry(p(), e)
    assert any("must be 'official'" in x for x in errors)


def test_satellite_org_marked_official_is_valid():
    e = valid({"affiliation": "official",
               "links": [{"type": "repo", "url": "https://github.com/tenstorrent-metal/foo"}]})
    assert validate_entry(p(), e) == []


def test_official_with_non_tt_owner_is_flagged():
    e = valid({"affiliation": "official",
               "links": [{"type": "repo", "url": "https://github.com/someone/tt-thing"}]})
    errors = validate_entry(p(), e)
    assert any("not a known Tenstorrent-owned org" in x for x in errors)


def test_only_the_canonical_repo_link_is_checked():
    """An article entry citing a Tenstorrent repo must not be forced official."""
    e = valid({"affiliation": "community",
               "links": [{"type": "repo", "url": "https://github.com/marty1885/x"},
                         {"type": "article", "url": "https://github.com/tenstorrent/tt-metal"}]})
    assert validate_entry(p(), e) == []


def test_official_without_repo_link_is_valid():
    e = valid({"affiliation": "official",
               "links": [{"type": "website", "url": "https://docs.tenstorrent.com/x"}]})
    assert validate_entry(p(), e) == []


def test_non_github_repo_host_is_skipped():
    e = valid({"affiliation": "official",
               "links": [{"type": "repo", "url": "https://gitlab.com/tt/x"}]})
    assert validate_entry(p(), e) == []
