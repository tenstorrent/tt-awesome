#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Decline a planet feed item — record that we saw it and chose not to publish.

Some feeds are broader than Planet Tenstorrent (clehaxze.tw, for instance,
mixes Tenstorrent posts with Arch/ROCm/search-engine ones). Those land
unapproved for review, and most of them will never be published. Leaving
them sitting in planet_feeds.json as approved=False works, but it grows the
published-feed file without bound and makes "not yet reviewed" and "reviewed
and rejected" look identical.

This moves them to src/_data/planet_declined.json instead: a slim record of
url + title + date + source + reason. fetch_planet_feeds.py seeds those URLs
into its known-URL set, so the source never re-proposes them.

Usage:
    python3 scripts/decline_planet_item.py <url> [<url> …] [--reason off-topic]

The move is all-or-nothing: if any URL matches neither file, nothing is
written. That way a typo'd URL fails loudly instead of half-applying a batch.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT     = Path(__file__).parent.parent
FEEDS    = ROOT / "src" / "_data" / "planet_feeds.json"
DECLINED = ROOT / "src" / "_data" / "planet_declined.json"


def _read(path: Path) -> list:
    """Read a JSON array, treating a missing file as empty.

    Both files are read before anything is written, so exiting here keeps the
    all-or-nothing promise — a corrupt file stops the move with a readable
    message instead of a traceback, and leaves both files untouched.
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        print(f"ERROR: {path} is not valid JSON ({e}) — fix or restore it first.",
              file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, list):
        print(f"ERROR: {path} should hold a JSON array, got {type(data).__name__}.",
              file=sys.stderr)
        sys.exit(1)
    rows = [r for r in data if isinstance(r, dict)]
    if len(rows) != len(data):
        print(f"WARN: skipped {len(data) - len(rows)} malformed row(s) in {path}",
              file=sys.stderr)
    return rows


def _write(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def decline(feeds_path: Path, declined_path: Path, urls: list, reason: str) -> list:
    """Move `urls` from the feed file to the declined list.

    Returns the tombstones written. Exits non-zero if a URL is in neither
    file — see the module docstring on why this is all-or-nothing.
    """
    feeds    = _read(feeds_path)
    declined = _read(declined_path)

    by_url           = {i["url"]: i for i in feeds if i.get("url")}
    already_declined = {d["url"] for d in declined if d.get("url")}

    unknown = [u for u in urls if u not in by_url and u not in already_declined]
    if unknown:
        print("ERROR: not found in the feed or declined list:", file=sys.stderr)
        for u in unknown:
            print(f"  {u}", file=sys.stderr)
        sys.exit(1)

    new_tombstones = []
    for url in urls:
        if url in already_declined:
            continue  # idempotent — re-declining is a no-op
        item = by_url[url]
        new_tombstones.append({
            "url":    url,
            "title":  item.get("title", ""),
            "date":   item.get("date", ""),
            "source": item.get("source", ""),
            "reason": reason,
        })
        already_declined.add(url)

    declined += new_tombstones
    # Newest first, matching planet_feeds.json's ordering.
    declined.sort(key=lambda d: d.get("date", ""), reverse=True)

    targets = set(urls)
    _write(feeds_path, [i for i in feeds if i.get("url") not in targets])
    _write(declined_path, declined)
    return new_tombstones


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("urls", nargs="+", help="feed item URL(s) to decline")
    ap.add_argument("--reason", default="off-topic",
                    help="why it was declined (default: off-topic)")
    args = ap.parse_args()

    written = decline(FEEDS, DECLINED, args.urls, args.reason)
    print(f"Declined {len(written)} item(s) "
          f"({len(args.urls) - len(written)} already on the list)")
    for d in written:
        print(f"  {d['date']}  {d['title']}")


if __name__ == "__main__":
    main()
