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
