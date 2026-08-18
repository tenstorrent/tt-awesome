# tests/test_decline_planet_item.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Tests for the decline helper — moving a planet item to the declined list."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import decline_planet_item as dpi


def _feed(*items):
    return list(items)


ITEM_OFF = {
    "type": "article", "source": "clehaxze.tw", "approved": False,
    "title": "Getting ROCm working on Arch WSL",
    "url": "https://clehaxze.tw/gemlog/rocm-arch-wsl",
    "description": "A long description that should not be carried over.",
    "date": "2026-07-13", "dateISO": "2026-07-13T00:00:00Z",
    "label": "clehaxze.tw", "projectName": "clehaxze.tw",
    "projectId": None, "affiliation": "community",
}
ITEM_ON = {
    "type": "article", "source": "clehaxze.tw", "approved": True,
    "title": "Memory on Tenstorrent",
    "url": "https://clehaxze.tw/gemlog/memory-on-tenstorrent",
    "date": "2025-03-17", "dateISO": "2025-03-17T00:00:00Z",
    "label": "clehaxze.tw", "projectName": "clehaxze.tw",
    "projectId": None, "affiliation": "community",
}


def test_decline_removes_item_from_the_feed(tmp_path):
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    feed.write_text(json.dumps(_feed(ITEM_OFF, ITEM_ON)))

    dpi.decline(feed, declined, [ITEM_OFF["url"]], "off-topic")

    remaining = json.loads(feed.read_text())
    assert [i["url"] for i in remaining] == [ITEM_ON["url"]]


def test_decline_records_a_slim_tombstone(tmp_path):
    """The record keeps identity, not the article body."""
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    feed.write_text(json.dumps(_feed(ITEM_OFF)))

    dpi.decline(feed, declined, [ITEM_OFF["url"]], "off-topic")

    assert json.loads(declined.read_text()) == [{
        "url": ITEM_OFF["url"],
        "title": ITEM_OFF["title"],
        "date": ITEM_OFF["date"],
        "source": ITEM_OFF["source"],
        "reason": "off-topic",
    }]


def test_decline_appends_to_an_existing_declined_list(tmp_path):
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    feed.write_text(json.dumps(_feed(ITEM_OFF)))
    declined.write_text(json.dumps([{
        "url": "https://clehaxze.tw/gemlog/earlier",
        "title": "Earlier", "date": "2025-01-01",
        "source": "clehaxze.tw", "reason": "off-topic",
    }]))

    dpi.decline(feed, declined, [ITEM_OFF["url"]], "off-topic")

    # Ordering is covered by test_declined_list_is_sorted_newest_first; what
    # matters here is that the pre-existing record survives the write.
    urls = {d["url"] for d in json.loads(declined.read_text())}
    assert urls == {"https://clehaxze.tw/gemlog/earlier", ITEM_OFF["url"]}


def test_decline_is_idempotent_for_an_already_declined_url(tmp_path):
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    feed.write_text(json.dumps(_feed(ITEM_OFF)))

    dpi.decline(feed, declined, [ITEM_OFF["url"]], "off-topic")
    dpi.decline(feed, declined, [ITEM_OFF["url"]], "off-topic")

    assert len(json.loads(declined.read_text())) == 1


def test_decline_rejects_a_url_that_is_in_neither_file(tmp_path):
    """A typo'd URL must fail loudly rather than write a bogus tombstone."""
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    feed.write_text(json.dumps(_feed(ITEM_OFF)))

    with pytest.raises(SystemExit):
        dpi.decline(feed, declined, ["https://clehaxze.tw/gemlog/typo"], "off-topic")

    assert not declined.exists()
    assert len(json.loads(feed.read_text())) == 1


def test_decline_writes_nothing_when_any_url_is_unknown(tmp_path):
    """All-or-nothing: one bad URL must not half-apply the batch."""
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    feed.write_text(json.dumps(_feed(ITEM_OFF, ITEM_ON)))

    with pytest.raises(SystemExit):
        dpi.decline(feed, declined, [ITEM_OFF["url"], "https://example.com/typo"], "off-topic")

    assert len(json.loads(feed.read_text())) == 2
    assert not declined.exists()


def test_declined_list_is_sorted_newest_first(tmp_path):
    feed = tmp_path / "planet_feeds.json"
    declined = tmp_path / "planet_declined.json"
    older = dict(ITEM_ON, url="https://clehaxze.tw/gemlog/older", date="2024-01-01")
    feed.write_text(json.dumps(_feed(ITEM_OFF, older)))

    dpi.decline(feed, declined, [older["url"], ITEM_OFF["url"]], "off-topic")

    assert [d["date"] for d in json.loads(declined.read_text())] == ["2026-07-13", "2024-01-01"]
