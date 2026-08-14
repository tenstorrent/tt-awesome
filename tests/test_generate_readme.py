# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_readme import sort_entries, render_entry, AFFILIATION_ORDER, pkg_url

COMM = {
    "id": "cool-proj", "name": "cool-proj",
    "description": "A cool community project.",
    "affiliation": "community", "categories": ["ai-models"],
    "links": [{"type": "repo", "url": "https://github.com/foo/cool-proj"}],
    "stars": 50, "featured": True,
}
AFFIL = {**COMM, "id": "affil-proj", "name": "affil-proj", "affiliation": "affiliated", "featured": False}
OFFICIAL = {**COMM, "id": "official-proj", "name": "official-proj", "affiliation": "official", "featured": True, "stars": 9999}


def test_community_always_before_official():
    result = sort_entries([OFFICIAL, COMM])
    assert result[0]["affiliation"] == "community"


def test_featured_first_within_tier():
    plain = {**COMM, "id": "plain", "name": "plain", "featured": False, "stars": 1000}
    result = sort_entries([plain, COMM])
    assert result[0]["name"] == "cool-proj"


def test_stars_desc_within_same_tier_and_featured():
    high = {**COMM, "id": "high", "name": "high", "featured": False, "stars": 200}
    low  = {**COMM, "id": "low",  "name": "low",  "featured": False, "stars": 5}
    result = sort_entries([low, high])
    assert result[0]["name"] == "high"


def test_affiliated_between_community_and_official():
    result = sort_entries([OFFICIAL, AFFIL, COMM])
    affiliations = [e["affiliation"] for e in result]
    assert affiliations == ["community", "affiliated", "official"]


def test_render_entry_contains_name_description_badge():
    md = render_entry(COMM)
    assert "cool-proj" in md
    assert "community" in md
    assert "A cool community project." in md


def test_render_entry_includes_all_links():
    entry = {**COMM, "links": [
        {"type": "repo", "url": "https://github.com/foo/cool-proj"},
        {"type": "talk", "url": "https://fosdem.org/talk", "label": "FOSDEM 2026"},
    ]}
    md = render_entry(entry)
    assert "FOSDEM 2026" in md
    assert "🎤" in md


def test_render_entry_no_repo_link():
    entry = {**COMM, "links": [{"type": "paper", "url": "https://arxiv.org/abs/1234.56789"}]}
    md = render_entry(entry)
    assert "cool-proj" in md
    assert "arxiv.org" in md


# ── pkg_url ──────────────────────────────────────────────────────────────────

def test_pkg_url_pypi_and_cargo():
    assert pkg_url({"type": "pypi", "name": "ttperf"}) == "https://pypi.org/project/ttperf/"
    assert pkg_url({"type": "cargo", "name": "luwen"}) == "https://crates.io/crates/luwen"


def test_pkg_url_conda_defaults_to_conda_forge():
    assert (pkg_url({"type": "conda", "name": "tt-metalium"})
            == "https://anaconda.org/conda-forge/tt-metalium")


def test_pkg_url_conda_honors_explicit_channel():
    assert (pkg_url({"type": "conda", "name": "pkg", "channel": "my-chan"})
            == "https://anaconda.org/my-chan/pkg")


def test_pkg_url_apt_launchpad_ppa():
    assert (pkg_url({"type": "apt", "name": "foo", "ppa": "ppa:owner/archive"})
            == "https://launchpad.net/~owner/+archive/ubuntu/archive")


def test_pkg_url_apt_plain_url():
    """Every apt entry in the list uses `url`, not a launchpad ppa: spec."""
    assert (pkg_url({"type": "apt", "name": "tt-smi", "url": "https://ppa.tenstorrent.com/"})
            == "https://ppa.tenstorrent.com/")


def test_pkg_url_apt_prefers_launchpad_over_url():
    pkg = {"type": "apt", "name": "foo", "ppa": "ppa:owner/archive", "url": "https://example.com/"}
    assert pkg_url(pkg) == "https://launchpad.net/~owner/+archive/ubuntu/archive"


def test_pkg_url_unknown_type_is_none():
    assert pkg_url({"type": "brew", "name": "foo"}) is None
    assert pkg_url({"type": "apt", "name": "foo"}) is None
