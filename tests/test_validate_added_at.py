# tests/test_validate_added_at.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate import validate_entry, validate_entry_warnings


def p(stem="test-entry"):
    return Path(f"/fake/entries/{stem}.json")


def valid(overrides=None):
    e = {
        "id": "test-entry",
        "name": "Test Entry",
        "description": "A test.",
        "affiliation": "community",
        "categories": ["ai-models"],
        "links": [{"type": "repo", "url": "https://github.com/foo/bar"}],
        "added_at": "2026-01-01",
    }
    if overrides:
        e.update(overrides)
    return e


def test_no_warning_when_added_at_present():
    warnings = validate_entry_warnings(p(), valid())
    assert not any("added_at" in w for w in warnings)


def test_warns_when_added_at_missing():
    e = valid()
    del e["added_at"]
    warnings = validate_entry_warnings(p(), e)
    assert any("added_at" in w for w in warnings)


def test_error_when_added_at_invalid_format():
    errors = validate_entry(p(), valid({"added_at": "01/01/2026"}))
    assert any("added_at" in e for e in errors)


def test_error_when_added_at_not_string():
    errors = validate_entry(p(), valid({"added_at": 20260101}))
    assert any("added_at" in e for e in errors)
