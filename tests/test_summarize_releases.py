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
