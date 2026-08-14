#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Fetch external planet feed items for Planet Tenstorrent.

Sources:
  - YouTube @tenstorrentinc (trusted — auto-approved)
  - arXiv papers mentioning Tenstorrent (trusted — auto-approved, skips entries already curated)
  - r/tenstorrent subreddit (reviewed — auto-approved)
  - Community blogs (reviewed — auto-approved)
  - Connpass events — Tenstorrent Japan Tech Talk series (trusted — auto-approved).
    Descriptions are condensed into a bilingual EN + JA summary (~200 chars each)
    via the active summarization provider (GitHub Copilot by default, see
    scripts/llm_client.py); Japanese-only when its credential is absent.

Items are appended to src/_data/planet_feeds.json. All items (new and
existing) are written with approved=True so they appear on the Planet
feed immediately.

Usage:
    python3 scripts/fetch_planet_feeds.py [--dry-run]
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT     = Path(__file__).parent.parent
ENTRIES  = ROOT / "entries"
OUT      = ROOT / "src" / "_data" / "planet_feeds.json"

YOUTUBE_CHANNELS = [
    {"id": "UC7041p6DlAh0r4_Fnlk10pQ", "name": "Tenstorrent",  "affiliation": "official"},
    {"id": "UC2AWMRWukuukkLf52phMdjw",  "name": "tt-tinkering", "affiliation": "affiliated"},
]
REDDIT_URL = "https://www.reddit.com/r/tenstorrent/.rss?limit=25&sort=new"
ARXIV_URL  = ("https://export.arxiv.org/api/query"
              "?search_query=all:tenstorrent"
              "&sortBy=submittedDate&sortOrder=descending&max_results=20")

# NOTE: fetch_community_feed() does no topic filtering — every item in these
# feeds becomes a planet item. Only list feeds whose whole output is on-topic,
# and set trusted=False for anything broader so items land unapproved and get
# reviewed before publishing.
COMMUNITY_FEEDS = [
    # /gemlog/atom.xml started 404ing; only the site-wide feed remains. That feed
    # is much broader than the old gemlog subset (Arch/ROCm/search-engine posts
    # alongside the Tenstorrent ones), so items land unapproved for review.
    {"name": "clehaxze.tw",    "url": "https://clehaxze.tw/atom.xml",             "affiliation": "community", "trusted": False},
    {"name": "jasondavies.com","url": "https://www.jasondavies.com/atom.xml",      "affiliation": "community", "trusted": True},
    {"name": "anuraagw.me",    "url": "https://anuraagw.me/atom.xml",              "affiliation": "community", "trusted": True},
    # Eric Zietlow (DevRel) — dev.to serves per-author RSS at /feed/<user>.
    {"name": "dev.to/mando222","url": "https://dev.to/feed/mando222",              "affiliation": "affiliated", "trusted": True},
]
CONNPASS_FEEDS = [
    # Connpass serves group feeds at /ja.atom (there is no /feed.atom — it 404s).
    {"name": "Tenstorrent Japan", "url": "https://tenstorrent.connpass.com/ja.atom", "affiliation": "official", "trusted": True},
]

USER_AGENT = "tt-awesome-planet/1.0 (github.com/tenstorrent/tt-awesome)"

# LLM summarization — condenses Japanese connpass event descriptions into a
# short bilingual (EN + JA) summary. Optional: when the active provider's
# credential is unset (e.g. local runs, forks) the fetcher keeps the plain
# Japanese text. The prompt lives in prompts/connpass-bilingual.prompt.yml;
# the provider flips via SUMMARY_PROVIDER (see scripts/llm_client.py).
import llm_client

TRANSLATE_MODEL = "claude-haiku-4-5-20251001"  # Anthropic-direct default
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
GH_TOKEN        = os.environ.get("GITHUB_TOKEN", "")
FOUNDRY_KEY     = os.environ.get("FOUNDRY_API_KEY", "")  # default foundry provider

NS_ATOM  = "http://www.w3.org/2005/Atom"
NS_MEDIA = "http://search.yahoo.com/mrss/"
NS_YT    = "http://www.youtube.com/xml/schemas/2015"


def _get(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(html: str) -> str:
    """Remove HTML tags and decode basic entities."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    # Decode named entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Decode numeric entities; clamp to valid Unicode to survive malformed feeds
    def _decode_dec(m):
        cp = int(m.group(1))
        return chr(cp) if cp <= 0x10FFFF else ""
    def _decode_hex(m):
        cp = int(m.group(1), 16)
        return chr(cp) if cp <= 0x10FFFF else ""
    text = re.sub(r"&#(\d+);", _decode_dec, text)
    text = re.sub(r"&#x([0-9a-fA-F]+);", _decode_hex, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, limit: int = 800) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def iso_to_date(date_str: str) -> str:
    """Return YYYY-MM-DD from an ISO 8601 or RFC 2822 date string."""
    if not date_str:
        return "1970-01-01"
    # ISO 8601: "2026-06-02T..." or "2026-06-02 ..."
    m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)
    # RFC 2822: "Mon, 02 Jun 2026 12:00:00 +0000"
    try:
        from email.utils import parsedate
        t = parsedate(date_str)
        if t:
            return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}"
    except Exception:
        pass
    return "1970-01-01"


def load_known_arxiv_ids() -> set:
    """Scan all entry JSONs for arXiv IDs already curated."""
    ids = set()
    for f in ENTRIES.rglob("*.json"):
        try:
            data = json.loads(f.read_text())
            for link in data.get("links", []):
                url = link.get("url", "")
                m = re.search(r"arxiv\.org/abs/(\d+\.\d+)", url)
                if m:
                    ids.add(m.group(1))
        except Exception:
            pass
    return ids


def fetch_youtube(known_urls: set) -> list:
    all_items = []
    for channel in YOUTUBE_CHANNELS:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['id']}"
        try:
            root = ET.fromstring(_get(url))
        except Exception as e:
            print(f"  WARN youtube ({channel['name']}): {e}", file=sys.stderr)
            continue
        for entry in root.findall(f"{{{NS_ATOM}}}entry"):
            title     = (entry.findtext(f"{{{NS_ATOM}}}title") or "").strip()
            published = entry.findtext(f"{{{NS_ATOM}}}published") or ""
            vid_el    = entry.find(f"{{{NS_YT}}}videoId")
            vid_id    = vid_el.text if vid_el is not None else None
            if not vid_id:
                continue
            video_url = f"https://www.youtube.com/watch?v={vid_id}"
            if video_url in known_urls:
                continue
            desc_el   = entry.find(f".//{{{NS_MEDIA}}}description")
            desc      = truncate(strip_html(desc_el.text if desc_el is not None else ""))
            date_str  = iso_to_date(published)
            all_items.append({
                "type":        "video",
                "source":      "youtube",
                "approved":    True,
                "title":       title,
                "url":         video_url,
                "description": desc,
                "date":        date_str,
                "dateISO":     published or f"{date_str}T00:00:00Z",
                "label":       f"{channel['name']} — YouTube",
                "projectName": channel["name"],
                "projectId":   None,
                "affiliation": channel["affiliation"],
            })
    return all_items


def fetch_arxiv(known_arxiv_ids: set, known_urls: set) -> list:
    try:
        root = ET.fromstring(_get(ARXIV_URL, timeout=20))
    except Exception as e:
        print(f"  WARN arxiv: {e}", file=sys.stderr)
        return []

    items = []
    for entry in root.findall(f"{{{NS_ATOM}}}entry"):
        title     = re.sub(r"\s+", " ", (entry.findtext(f"{{{NS_ATOM}}}title") or "").strip())
        published = entry.findtext(f"{{{NS_ATOM}}}published") or ""
        summary   = re.sub(r"\s+", " ", (entry.findtext(f"{{{NS_ATOM}}}summary") or "").strip())
        # Prefer the HTML link over the raw atom ID
        link_el = entry.find(f"{{{NS_ATOM}}}link[@type='text/html']")
        if link_el is None:
            link_el = entry.find(f"{{{NS_ATOM}}}link")
        url = (link_el.get("href") if link_el is not None else "").strip()
        if not url:
            continue
        # Dedup: skip if URL already in file or arXiv ID already in entries
        if url in known_urls:
            continue
        m = re.search(r"arxiv\.org/abs/(\d+\.\d+)", url)
        if m and m.group(1) in known_arxiv_ids:
            continue
        arxiv_id = m.group(1) if m else ""
        date_str = iso_to_date(published)
        items.append({
            "type":        "paper",
            "source":      "arxiv",
            "approved":    True,
            "title":       title,
            "url":         url,
            "description": truncate(summary, 800),
            "date":        date_str,
            "dateISO":     published or f"{date_str}T00:00:00Z",
            "label":       f"arXiv:{arxiv_id}" if arxiv_id else "arXiv",
            "projectName": "arXiv",
            "projectId":   None,
            "affiliation": "community",
        })
    return items


def fetch_reddit(known_urls: set) -> list:
    try:
        root = ET.fromstring(_get(REDDIT_URL))
    except Exception as e:
        print(f"  WARN reddit: {e}", file=sys.stderr)
        return []

    items = []
    for entry in root.findall(f"{{{NS_ATOM}}}entry"):
        title     = (entry.findtext(f"{{{NS_ATOM}}}title") or "").strip()
        published = entry.findtext(f"{{{NS_ATOM}}}published") or ""
        link_el   = entry.find(f"{{{NS_ATOM}}}link")
        url       = (link_el.get("href") if link_el is not None else "").strip()
        if not url or url in known_urls:
            continue
        content_el = entry.find(f"{{{NS_ATOM}}}content")
        raw_html   = content_el.text if content_el is not None else ""
        desc       = truncate(strip_html(raw_html))
        date_str   = iso_to_date(published)
        items.append({
            "type":        "article",
            "source":      "reddit",
            "approved":    False,
            "title":       title,
            "url":         url,
            "description": desc,
            "date":        date_str,
            "dateISO":     published or f"{date_str}T00:00:00Z",
            "label":       "r/tenstorrent",
            "projectName": "r/tenstorrent",
            "projectId":   None,
            "affiliation": "community",
        })
    return items


def fetch_community_feed(feed: dict, known_urls: set) -> list:
    try:
        root = ET.fromstring(_get(feed["url"]))
    except Exception as e:
        print(f"  WARN {feed['name']}: {e}", file=sys.stderr)
        return []

    items = []
    # Try Atom entries first, fall back to RSS items
    entries = root.findall(f"{{{NS_ATOM}}}entry") or root.findall(".//item")
    for entry in entries:
        # Atom
        title     = (entry.findtext(f"{{{NS_ATOM}}}title") or entry.findtext("title") or "").strip()
        published = (entry.findtext(f"{{{NS_ATOM}}}published") or
                     entry.findtext(f"{{{NS_ATOM}}}updated") or
                     entry.findtext("pubDate") or "")
        link_el   = entry.find(f"{{{NS_ATOM}}}link")
        url       = ""
        if link_el is not None:
            url = link_el.get("href") or link_el.text or ""
        if not url:
            url = entry.findtext("link") or ""
        url = url.strip()
        if not url or url in known_urls:
            continue
        summary_el = (entry.find(f"{{{NS_ATOM}}}summary") or
                      entry.find(f"{{{NS_ATOM}}}content") or
                      entry.find("description"))
        raw = summary_el.text if summary_el is not None else ""
        desc = truncate(strip_html(raw))
        date_str = iso_to_date(published)
        items.append({
            "type":        "article",
            "source":      feed["name"],
            "approved":    feed.get("trusted", False),
            "title":       title,
            "url":         url,
            "description": desc,
            "date":        date_str,
            "dateISO":     f"{date_str}T00:00:00Z",
            "label":       feed["name"],
            "projectName": feed["name"],
            "projectId":   None,
            "affiliation": feed.get("affiliation", "community"),
        })
    return items


def bilingual_description(text: str) -> str:
    """Condense a Japanese event description into "≤200-char EN — ≤200-char JA".

    Returns "" when the active provider's credential is unset or the call
    fails, so callers can fall back to the untranslated text.
    """
    if not text:
        return ""
    if llm_client.missing_credential(
        anthropic_api_key=ANTHROPIC_KEY, github_token=GH_TOKEN, foundry_api_key=FOUNDRY_KEY
    ):
        return ""
    try:
        reply = llm_client.complete(
            "connpass-bilingual",
            {"event_text": text},
            anthropic_model=TRANSLATE_MODEL,
            anthropic_api_key=ANTHROPIC_KEY,
            github_token=GH_TOKEN,
            foundry_api_key=FOUNDRY_KEY,
        )
        if not reply:
            return ""
        parts = json.loads(reply)
        en = str(parts.get("en", "")).strip()
        ja = str(parts.get("ja", "")).strip()
        if en and ja:
            # Hard-clamp to the promised 200 chars per language — the prompt
            # asks for it, but the contract shouldn't depend on model behavior.
            return f"{truncate(en, 200)} — {truncate(ja, 200)}"
        print("  WARN bilingual_description: model reply missing en/ja", file=sys.stderr)
    except Exception as e:
        # llm_client returns "" on API errors; anything caught here is a
        # malformed reply (e.g. non-JSON text) rather than a transport failure.
        print(f"  WARN bilingual_description: {e}", file=sys.stderr)
    return ""


def fetch_connpass(known_urls: set) -> list:
    items = []
    for feed in CONNPASS_FEEDS:
        try:
            root = ET.fromstring(_get(feed["url"]))
        except Exception as e:
            print(f"  WARN {feed['name']}: {e}", file=sys.stderr)
            continue

        for entry in root.findall(f"{{{NS_ATOM}}}entry"):
            title     = (entry.findtext(f"{{{NS_ATOM}}}title") or "").strip()
            published = (entry.findtext(f"{{{NS_ATOM}}}published") or
                         entry.findtext(f"{{{NS_ATOM}}}updated") or "")
            # NB: pick the first non-None match explicitly — `or`-chaining
            # Elements doesn't work (childless ones are falsy), which would
            # defeat this preference order and always take the last fallback.
            link_el = None
            for path in (f"{{{NS_ATOM}}}link[@rel='alternate'][@type='text/html']",
                         f"{{{NS_ATOM}}}link[@rel='alternate']",
                         f"{{{NS_ATOM}}}link[@type='text/html']",
                         f"{{{NS_ATOM}}}link"):
                link_el = entry.find(path)
                if link_el is not None:
                    break
            url       = ""
            if link_el is not None:
                url = link_el.get("href") or link_el.text or ""
            url = url.strip()
            # The feed appends utm_* tracking params to every event link;
            # drop them so stored URLs are clean and dedup stays stable.
            if "?" in url:
                base, _, query = url.partition("?")
                kept = [p for p in query.split("&") if p and not p.startswith("utm_")]
                url = base + ("?" + "&".join(kept) if kept else "")
            if not url or url in known_urls:
                continue
            known_urls.add(url)
            # NB: use `is None`, not `or` — ElementTree Elements with no
            # children are falsy even when they carry text.
            summary_el = entry.find(f"{{{NS_ATOM}}}summary")
            if summary_el is None:
                summary_el = entry.find(f"{{{NS_ATOM}}}content")
            raw  = summary_el.text if summary_el is not None else ""
            desc = truncate(strip_html(raw))
            # Connpass descriptions are Japanese; offer readers a bilingual
            # summary when the API key is available (JA-only fallback otherwise).
            desc = bilingual_description(desc) or desc
            date_str = iso_to_date(published)
            items.append({
                "type":        "talk",
                "source":      "connpass",
                "approved":    feed.get("trusted", False),
                "title":       title,
                "url":         url,
                "description": desc,
                "date":        date_str,
                "dateISO":     published or f"{date_str}T00:00:00Z",
                "label":       f"{feed['name']} — connpass",
                "projectName": feed["name"],
                "projectId":   None,
                "affiliation": feed.get("affiliation", "official"),
            })
    return items


def main():
    dry_run = "--dry-run" in sys.argv

    # Load existing items — force approved=True on all (auto-approve policy)
    existing: dict = {}
    if OUT.exists():
        try:
            for item in json.loads(OUT.read_text()):
                if item.get("url"):
                    item["approved"] = True
                    existing[item["url"]] = item
        except Exception as e:
            print(f"  WARN: could not read {OUT}: {e}", file=sys.stderr)

    known_arxiv = load_known_arxiv_ids()
    known_urls  = set(existing.keys())

    # known_urls grows as each source is fetched to prevent cross-source dupes
    print(f"Fetching YouTube ({len(YOUTUBE_CHANNELS)} channels)…")
    yt = fetch_youtube(known_urls)
    print(f"  {len(yt)} new videos")
    new_items = yt
    known_urls.update(i["url"] for i in yt)

    print("Fetching arXiv…")
    ax = fetch_arxiv(known_arxiv, known_urls)
    print(f"  {len(ax)} new papers")
    new_items += ax
    known_urls.update(i["url"] for i in ax)

    print("Fetching Reddit…")
    rd = fetch_reddit(known_urls)
    print(f"  {len(rd)} posts")
    new_items += rd
    known_urls.update(i["url"] for i in rd)

    for feed in COMMUNITY_FEEDS:
        print(f"Fetching {feed['name']}…")
        cf = fetch_community_feed(feed, known_urls)
        print(f"  {len(cf)} items")
        new_items += cf
        known_urls.update(i["url"] for i in cf)

    print(f"Fetching Connpass ({len(CONNPASS_FEEDS)} feed(s))…")
    cp = fetch_connpass(known_urls)
    print(f"  {len(cp)} new events")
    new_items += cp
    known_urls.update(i["url"] for i in cp)

    # Merge: all existing items remain approved; new items use source defaults
    all_items = list(existing.values()) + new_items
    all_items.sort(key=lambda x: x.get("dateISO", ""), reverse=True)

    if dry_run:
        print(f"\nDRY RUN: would write {len(all_items)} items ({len(new_items)} new)")
        return

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(all_items, indent=2, ensure_ascii=False) + "\n")
    tmp.rename(OUT)
    print(f"\nWritten {len(all_items)} items ({len(new_items)} new) to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
