import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_readme import sort_entries, render_entry, AFFILIATION_ORDER

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
