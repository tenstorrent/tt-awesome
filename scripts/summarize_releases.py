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


def _gh_request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    return req


def fetch_release_body(repo: str, tag: str) -> str:
    """Fetch the markdown body of a specific release. Returns '' on any error."""
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    try:
        with urllib.request.urlopen(_gh_request(url), timeout=10) as r:
            data = json.loads(r.read())
            return data.get("body") or ""
    except urllib.error.HTTPError as e:
        print(f"  WARN fetch_release_body {repo}@{tag}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN fetch_release_body {repo}@{tag}: {e}", file=sys.stderr)
    return ""


def is_sparse(body: str) -> bool:
    """Return True if the release body is too short to summarize."""
    return len(body.strip()) < SPARSE_LIMIT


SYSTEM_PROMPT = (
    "You write brief, engaging release summaries for Planet Tenstorrent, an aggregator "
    "read by developers and researchers following the Tenstorrent ecosystem. Your tone "
    "is warm and technically literate — like a knowledgeable colleague sharing what's "
    "new, not a press release. Write one paragraph of 2–4 sentences. Focus on what "
    "changed and why it matters. Do not repeat the version number or project name. "
    "Do not use hype words like \"exciting\" or \"powerful\". Do not use bullet points."
)


def call_github_models(repo: str, release_name: str, body: str, affiliation: str) -> str:
    """Call GitHub Models inference API and return the summary string, or '' on error."""
    user_message = (
        f"Summarize this release for Planet Tenstorrent readers.\n\n"
        f"Project: {repo} ({affiliation})\n"
        f"Release: {release_name}\n\n"
        f"Release notes:\n{body}"
    )
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        INFERENCE_URL,
        data=payload,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"  WARN call_github_models {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN call_github_models {repo}: {e}", file=sys.stderr)
    return ""
