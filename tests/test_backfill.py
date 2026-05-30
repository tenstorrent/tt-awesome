# tests/test_backfill.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import backfill_added_at as baa


def test_parse_git_date_extracts_date():
    assert baa.parse_git_date("2026-05-08 16:24:50 -0700") == "2026-05-08"


def test_parse_git_date_returns_none_for_empty():
    assert baa.parse_git_date("") is None
    assert baa.parse_git_date(None) is None


def test_get_added_date_calls_git(tmp_path):
    fake_file = tmp_path / "test-entry.json"
    fake_file.write_text("{}")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="2026-03-15 10:00:00 -0800\n", returncode=0
        )
        result = baa.get_added_date(fake_file)
    assert result == "2026-03-15"
    args = mock_run.call_args[0][0]
    assert "git" in args[0]
    assert "--diff-filter=A" in args


def test_get_added_date_returns_none_when_git_empty(tmp_path):
    fake_file = tmp_path / "test-entry.json"
    fake_file.write_text("{}")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = baa.get_added_date(fake_file)
    assert result is None


def test_backfill_writes_added_at(tmp_path):
    entry = {"id": "my-entry", "name": "My Entry"}
    f = tmp_path / "my-entry.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date", return_value="2026-01-10"):
        updated, skipped = baa.backfill_entries([f])
    data = json.loads(f.read_text())
    assert data["added_at"] == "2026-01-10"
    assert updated == 1
    assert skipped == 0


def test_backfill_skips_existing_added_at(tmp_path):
    entry = {"id": "my-entry", "added_at": "2025-12-01"}
    f = tmp_path / "my-entry.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date") as mock_get:
        updated, skipped = baa.backfill_entries([f])
    mock_get.assert_not_called()
    assert updated == 0
    assert skipped == 1


def test_backfill_skips_when_git_returns_nothing(tmp_path):
    entry = {"id": "my-entry"}
    f = tmp_path / "my-entry.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date", return_value=None):
        updated, skipped = baa.backfill_entries([f])
    data = json.loads(f.read_text())
    assert "added_at" not in data
    assert updated == 0
    assert skipped == 1


def test_backfill_preserves_field_order(tmp_path):
    entry = {"id": "x", "name": "X", "description": "Desc", "affiliation": "official"}
    f = tmp_path / "x.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date", return_value="2026-02-01"):
        baa.backfill_entries([f])
    result = json.loads(f.read_text())
    keys = list(result.keys())
    assert keys == ["id", "name", "description", "affiliation", "added_at"]


def test_backfill_skips_invalid_json(tmp_path):
    f = tmp_path / "bad-entry.json"
    f.write_text("{not valid json")
    updated, skipped = baa.backfill_entries([f])
    assert updated == 0
    assert skipped == 1
