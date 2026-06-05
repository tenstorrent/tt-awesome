#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Summarize new GitHub releases and append them to planet_feeds.json.

For each release URL in github_meta.json not already in planet_feeds.json:
  - Fetches the release body from the GitHub API
  - Skips if body is empty or under 150 characters
  - Calls GitHub Models to generate a one-paragraph human summary
  - Appends a type:"release" item (approved:false) to planet_feeds.json

Usage:
    python3 scripts/summarize_releases.py [--dry-run]
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"
META_IN = ROOT / "src" / "_data" / "github_meta.json"
FEEDS_OUT = ROOT / "src" / "_data" / "planet_feeds.json"

INFERENCE_URL = "https://models.github.ai/inference/chat/completions"
MODEL = "openai/gpt-4o-mini"
SPARSE_LIMIT = 150  # characters; bodies shorter than this are skipped

TOKEN = os.environ.get("GITHUB_TOKEN", "")

REPO_RE = re.compile(r"https://github\.com/([^/?#]+/[^/?#]+?)(?:\.git)?$")


def load_known_urls(feeds_path: Path) -> set:
    """Return the set of all URLs already in planet_feeds.json."""
    if not feeds_path.exists():
        return set()
    try:
        items = json.loads(feeds_path.read_text())
        return {item["url"] for item in items if item.get("url")}
    except Exception as e:
        print(f"  WARN: could not read {feeds_path}: {e}", file=sys.stderr)
        return set()


def resolve_affiliation(repo_url: str, entry_dirs: list) -> str:
    """Return affiliation for a repo URL by scanning entry JSONs."""
    for d in entry_dirs:
        for f in Path(d).rglob("*.json"):
            try:
                data = json.loads(f.read_text())
                for link in data.get("links", []):
                    if link.get("url", "").rstrip("/") == repo_url.rstrip("/"):
                        return data.get("affiliation", "community")
            except Exception:
                continue
    return "community"
