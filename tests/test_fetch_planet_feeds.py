# tests/test_fetch_planet_feeds.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Tests for the planet feed fetcher's approval and decline bookkeeping.

Both behaviors here were broken at some point and are easy to break again:

  - The fetcher used to force ``approved = True`` onto every item it loaded,
    which silently republished posts a maintainer had deliberately left
    unapproved (see the 48 clehaxze.tw flips in PR #173).
  - Declined posts must never come back. Nothing stops a feed from serving
    the same entry forever, so a decline is only durable if the fetcher
    treats those URLs as already-known before it fetches anything.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import fetch_planet_feeds as fpf


# ── load_existing: a maintainer's approval decision is data, not a default ──

def test_load_existing_preserves_unapproved_items(tmp_path):
    """approved=False survives a load — the fetcher must not re-approve it."""
    f = tmp_path / "planet_feeds.json"
    f.write_text(json.dumps([
        {"url": "https://example.com/off-topic", "approved": False, "title": "Off topic"},
        {"url": "https://example.com/on-topic",  "approved": True,  "title": "On topic"},
    ]))

    existing = fpf.load_existing(f)

    assert existing["https://example.com/off-topic"]["approved"] is False
    assert existing["https://example.com/on-topic"]["approved"] is True


def test_load_existing_keys_by_url_and_skips_urlless_items(tmp_path):
    f = tmp_path / "planet_feeds.json"
    f.write_text(json.dumps([
        {"url": "https://example.com/a", "approved": True},
        {"approved": True, "title": "malformed — no url"},
    ]))

    existing = fpf.load_existing(f)

    assert list(existing) == ["https://example.com/a"]


def test_load_existing_returns_empty_dict_when_file_missing(tmp_path):
    assert fpf.load_existing(tmp_path / "nope.json") == {}


def test_load_existing_returns_empty_dict_on_malformed_json(tmp_path):
    f = tmp_path / "planet_feeds.json"
    f.write_text("{not json")

    assert fpf.load_existing(f) == {}


# ── load_declined_urls: the "we saw it, we said no" record ──────────────────

def test_load_declined_urls_returns_declined_urls(tmp_path):
    f = tmp_path / "planet_declined.json"
    f.write_text(json.dumps([
        {"url": "https://clehaxze.tw/gemlog/off-topic", "title": "Off topic",
         "date": "2026-07-27", "source": "clehaxze.tw", "reason": "off-topic"},
        {"url": "https://clehaxze.tw/gemlog/also-off",  "title": "Also off",
         "date": "2026-07-13", "source": "clehaxze.tw", "reason": "off-topic"},
    ]))

    assert fpf.load_declined_urls(f) == {
        "https://clehaxze.tw/gemlog/off-topic",
        "https://clehaxze.tw/gemlog/also-off",
    }


def test_load_declined_urls_returns_empty_set_when_file_missing(tmp_path):
    assert fpf.load_declined_urls(tmp_path / "nope.json") == set()


def test_load_declined_urls_returns_empty_set_on_malformed_json(tmp_path):
    f = tmp_path / "planet_declined.json"
    f.write_text("[{oops")

    assert fpf.load_declined_urls(f) == set()


# ── merge_items: declined wins over anything still sitting in the feed ──────

def test_merge_items_drops_feed_items_that_were_later_declined():
    """A URL in both files is a stale feed row — the decline is the decision."""
    existing = {
        "https://example.com/declined": {"url": "https://example.com/declined",
                                         "approved": True, "dateISO": "2026-07-27T00:00:00Z"},
        "https://example.com/kept":     {"url": "https://example.com/kept",
                                         "approved": True, "dateISO": "2026-07-28T00:00:00Z"},
    }

    merged = fpf.merge_items(existing, [], {"https://example.com/declined"})

    assert [i["url"] for i in merged] == ["https://example.com/kept"]


def test_merge_items_sorts_newest_first():
    existing = {
        "https://example.com/old": {"url": "https://example.com/old", "dateISO": "2025-01-01T00:00:00Z"},
    }
    new = [{"url": "https://example.com/new", "dateISO": "2026-08-18T00:00:00Z"}]

    merged = fpf.merge_items(existing, new, set())

    assert [i["url"] for i in merged] == ["https://example.com/new", "https://example.com/old"]
