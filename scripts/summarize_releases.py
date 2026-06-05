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


def main(argv: list | None = None):
    """Entry point: scan github_meta.json and append new release summaries to planet_feeds.json.

    Args:
        argv: Command-line arguments. Pass ``[]`` in tests to avoid reading sys.argv.
              Recognized flags:
                ``--dry-run``  Print summaries without writing any files.
    """
    if argv is None:
        argv = sys.argv[1:]
    dry_run = "--dry-run" in argv

    if not TOKEN and not dry_run:
        print("ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    # ── Load input data ──────────────────────────────────────────────────────
    meta = {}
    if META_IN.exists():
        try:
            meta = json.loads(META_IN.read_text())
        except Exception as e:
            print(f"ERROR: cannot read {META_IN}: {e}", file=sys.stderr)
            sys.exit(1)

    # URLs already in planet_feeds.json — we skip these to avoid duplicates.
    known_urls = load_known_urls(FEEDS_OUT)

    # The current contents of planet_feeds.json (used when writing back merged output).
    existing_feeds = []
    if FEEDS_OUT.exists():
        try:
            existing_feeds = json.loads(FEEDS_OUT.read_text())
        except Exception:
            pass  # If the file is malformed we start fresh; load_known_urls already warned.

    new_items = []

    # ── Iterate over every repo and its releases ─────────────────────────────
    for repo_url, repo_data in meta.items():
        m = REPO_RE.match(repo_url)
        if not m:
            # repo_url does not look like a github.com repo URL — skip silently.
            continue
        repo = m.group(1)          # e.g. "tenstorrent/tt-metal"
        repo_name = repo.split("/")[-1]  # e.g. "tt-metal"

        for release in repo_data.get("releases", []):
            url = release.get("url", "")
            if not url or url in known_urls:
                # Missing URL or already processed — nothing to do.
                continue

            tag  = release["tagName"]
            name = release.get("name") or tag

            # Fetch and quality-gate the release body before calling the LLM.
            body = fetch_release_body(repo, tag)
            if is_sparse(body):
                print(f"  SKIP {repo}@{tag}: body too sparse ({len(body.strip())} chars)")
                continue

            # Determine whether this repo is official, community, etc.
            affiliation = resolve_affiliation(repo_url, [ENTRIES_DIR])

            summary = call_github_models(repo, name, body, affiliation)
            if not summary:
                print(f"  SKIP {repo}@{tag}: summarization failed")
                continue

            # Build the ISO date string and short date for display/sorting.
            date_str = release.get("publishedAt", "")[:10] or "1970-01-01"
            item = {
                "type":        "release",
                "source":      "github",
                "approved":    False,   # requires human review before appearing publicly
                "title":       f"{repo_name} {tag}",
                "url":         url,
                "description": summary,
                "date":        date_str,
                "dateISO":     release.get("publishedAt", f"{date_str}T00:00:00Z"),
                "label":       repo,
                "projectName": repo_name,
                "projectId":   None,
                "affiliation": affiliation,
            }

            if dry_run:
                # In dry-run mode we print the summary but never mutate any file.
                print(f"\n--- DRY RUN: {repo}@{tag} ---")
                print(summary)
            else:
                # Track the URL immediately so later iterations in the same run
                # don't re-process the same release (e.g. if it appears twice).
                known_urls.add(url)
                print(f"  ADDED {repo}@{tag}")
            # Accumulate in both modes so the dry-run summary count is accurate.
            new_items.append(item)

    # ── Dry-run: report and exit without touching the filesystem ─────────────
    if dry_run:
        print(f"\nDRY RUN complete. {len(new_items)} items would be added.")
        return

    # ── Write output atomically via a temp file ───────────────────────────────
    if new_items:
        all_items = existing_feeds + new_items
        # Sort newest-first so the feed renders in chronological order without
        # requiring a downstream sort step.
        all_items.sort(key=lambda x: x.get("dateISO", ""), reverse=True)
        tmp = FEEDS_OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(all_items, indent=2, ensure_ascii=False) + "\n")
        tmp.rename(FEEDS_OUT)
        # Show a project-relative path when possible; fall back to absolute path
        # (e.g. when FEEDS_OUT is a tmp_path in tests).
        try:
            display_path = FEEDS_OUT.relative_to(ROOT)
        except ValueError:
            display_path = FEEDS_OUT
        print(f"\nWrote {len(new_items)} new release item(s) to {display_path}")
    else:
        print("\nNo new release items.")


if __name__ == "__main__":
    main()
