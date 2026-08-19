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

import pytest

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


def test_load_existing_skips_a_malformed_row_and_keeps_the_rest(tmp_path):
    """One bad row must not truncate the load — main() would rewrite the file
    with only the rows that came before it."""
    f = tmp_path / "planet_feeds.json"
    f.write_text(json.dumps([
        {"url": "https://example.com/a", "approved": True},
        "a stray string where an object should be",
        {"url": "https://example.com/b", "approved": False},
    ]))

    existing = fpf.load_existing(f)

    assert set(existing) == {"https://example.com/a", "https://example.com/b"}


def test_load_existing_aborts_on_an_unparseable_file(tmp_path):
    """Returning {} here would make main() rewrite the feed from scratch."""
    f = tmp_path / "planet_feeds.json"
    f.write_text("{not json")

    with pytest.raises(SystemExit):
        fpf.load_existing(f)


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


def test_load_declined_urls_skips_a_malformed_row_and_keeps_the_rest(tmp_path):
    f = tmp_path / "planet_declined.json"
    f.write_text(json.dumps([
        {"url": "https://clehaxze.tw/gemlog/off-topic", "reason": "off-topic"},
        None,
        {"no_url_key": True},
        {"url": "https://clehaxze.tw/gemlog/also-off", "reason": "off-topic"},
    ]))

    assert fpf.load_declined_urls(f) == {
        "https://clehaxze.tw/gemlog/off-topic",
        "https://clehaxze.tw/gemlog/also-off",
    }


def test_load_declined_urls_aborts_on_an_unparseable_file(tmp_path):
    """Returning an empty set would forget every decline and re-propose them
    on the next run — the exact failure this list exists to prevent."""
    f = tmp_path / "planet_declined.json"
    f.write_text("[{oops")

    with pytest.raises(SystemExit):
        fpf.load_declined_urls(f)


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


# ── fetch_community_feed: Atom descriptions survive the parse ────────────────
#
# An ElementTree element is falsy when it has no *child* elements, and a feed's
# <summary>/<content> is text (CDATA or escaped HTML), not children. The old
# `find(summary) or find(content) or find("description")` chain therefore
# skipped past the element it had just found and returned the final None, so
# every Atom item the fetcher wrote landed with description "". RSS was
# unaffected: its <description> is last in the chain, and `or` returns the last
# operand regardless of truthiness.

def _atom(body: str) -> str:
    return f'<feed xmlns="{fpf.NS_ATOM}">{body}</feed>'


def _fetch_xml(monkeypatch, xml: str, trusted: bool = True) -> list:
    monkeypatch.setattr(fpf, "_get", lambda url, timeout=12: xml.encode())
    feed = {"name": "example.com", "url": "https://example.com/atom.xml",
            "affiliation": "community", "trusted": trusted}
    return fpf.fetch_community_feed(feed, set())


def test_community_feed_keeps_an_atom_summary(monkeypatch):
    items = _fetch_xml(monkeypatch, _atom("""
      <entry>
        <title>A post</title>
        <link href="https://example.com/a" />
        <published>2026-06-23T00:00:00-07:00</published>
        <summary>What the post is about.</summary>
      </entry>"""))

    assert [i["description"] for i in items] == ["What the post is about."]


def test_community_feed_falls_back_to_atom_content(monkeypatch):
    """No <summary> at all — the post body is the only description available."""
    items = _fetch_xml(monkeypatch, _atom("""
      <entry>
        <title>A post</title>
        <link href="https://example.com/a" />
        <published>2026-06-23T00:00:00-07:00</published>
        <content type="html">&lt;p&gt;Body text.&lt;/p&gt;</content>
      </entry>"""))

    assert [i["description"] for i in items] == ["Body text."]


def test_community_feed_skips_an_empty_summary_for_content(monkeypatch):
    """An empty <summary> must not shadow a <content> that has real text."""
    items = _fetch_xml(monkeypatch, _atom("""
      <entry>
        <title>A post</title>
        <link href="https://example.com/a" />
        <published>2026-06-23T00:00:00-07:00</published>
        <summary>   </summary>
        <content type="html">&lt;p&gt;Body text.&lt;/p&gt;</content>
      </entry>"""))

    assert [i["description"] for i in items] == ["Body text."]


def test_community_feed_keeps_an_rss_description(monkeypatch):
    items = _fetch_xml(monkeypatch, """<rss><channel>
      <item>
        <title>A post</title>
        <link>https://example.com/a</link>
        <pubDate>Tue, 23 Jun 2026 00:00:00 +0000</pubDate>
        <description>What the post is about.</description>
      </item>
    </channel></rss>""")

    assert [i["description"] for i in items] == ["What the post is about."]


def test_community_feed_carries_source_date_and_approval(monkeypatch):
    """The published date is preserved, so a back-dated post files under the
    month it was written rather than the day it was fetched."""
    items = _fetch_xml(monkeypatch, _atom("""
      <entry>
        <title>A post</title>
        <link href="https://example.com/a" />
        <published>2026-06-23T00:00:00-07:00</published>
        <summary>Summary.</summary>
      </entry>"""), trusted=False)

    assert items[0]["date"] == "2026-06-23"
    assert items[0]["dateISO"] == "2026-06-23T00:00:00Z"
    assert items[0]["approved"] is False
