#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Fetch stars, updatedAt, and a preview image for all repo-linked entries.
Writes src/_data/github_meta.json."""
import base64
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"
META_OUT = ROOT / "src" / "_data" / "github_meta.json"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_RE = re.compile(r"https://github\.com/([^/?#]+/[^/?#]+?)(?:\.git)?$")

# Badge/CI image patterns to skip — these are tiny status icons, not previews.
SKIP_IMG_RE = re.compile(
    r"(shield|badge|travis|circleci|codecov|github[/_]workflow|actions/workflows|"
    r"img\.shields\.io|flat\.badgen|pepy\.tech|bestpractices|ossf|snyk\.io|"
    r"buildstatus|favicon|/button\.|_logo_stacked|logo\.png|deploy/button)",
    re.I,
)
IMG_MD_RE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)')
IMG_HTML_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)


def _request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    return req


def fetch_repo(repo: str) -> dict:
    try:
        with urllib.request.urlopen(_request(f"https://api.github.com/repos/{repo}"), timeout=10) as r:
            d = json.loads(r.read())
            # Use `or {}` so that fork:true with a missing/null parent key never raises.
            parent = d.get("parent") or {}
            return {
                "stars": d.get("stargazers_count", 0),
                "updatedAt": d.get("updated_at", ""),
                "_default_branch": d.get("default_branch", "main"),
                # Private fields consumed in main() and converted to public keys
                # only when the repo is actually a fork with a known parent.
                "_is_fork": d.get("fork", False),
                "_fork_parent_name": parent.get("full_name", ""),
                "_fork_parent_url": parent.get("html_url", ""),
            }
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo}: {e}", file=sys.stderr)
    return {}


def fetch_readme_image(repo: str, default_branch: str = "main") -> str | None:
    """Return absolute URL of the first meaningful image in the README, or None."""
    try:
        with urllib.request.urlopen(_request(f"https://api.github.com/repos/{repo}/readme"), timeout=10) as r:
            data = json.loads(r.read())
            raw = base64.b64decode(data.get("content", "").replace("\n", ""))
            content = raw.decode("utf-8", errors="replace")
    except Exception:
        return None

    for pattern in (IMG_MD_RE, IMG_HTML_RE):
        for m in pattern.finditer(content):
            url = m.group(1).strip().split(" ")[0]  # drop trailing title text
            if SKIP_IMG_RE.search(url):
                continue
            if url.startswith("http"):
                return url
            # Normalize repo-relative path to raw.githubusercontent URL
            path = url.lstrip("./")
            return f"https://raw.githubusercontent.com/{repo}/{default_branch}/{path}"
    return None


def fetch_releases(repo: str, per_page: int = 5) -> list:
    """Fetch the most recent releases for a repo, excluding drafts.

    Returns a list of dicts with camelCase keys matching the frontend schema:
        tagName, name, publishedAt, url, prerelease
    Draft releases are skipped; pre-releases are included (caller can filter).
    Returns an empty list on any error so a single bad repo never aborts the run.
    """
    try:
        url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}"
        with urllib.request.urlopen(_request(url), timeout=10) as r:
            releases = json.loads(r.read())
            return [
                {
                    "tagName": rel["tag_name"],
                    # Fall back to the tag name when the release has no display name.
                    "name": rel.get("name") or rel["tag_name"],
                    "publishedAt": rel.get("published_at", ""),
                    "url": rel.get("html_url", ""),
                    "prerelease": rel.get("prerelease", False),
                }
                for rel in releases
                if not rel.get("draft", False)
            ]
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo} releases: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo} releases: {e}", file=sys.stderr)
    return []


def main():
    entries = [json.loads(f.read_text()) for f in sorted(ENTRIES_DIR.rglob("*.json"))]
    meta = {}
    for entry in entries:
        repo_link = next((l for l in entry.get("links", []) if l["type"] == "repo"), None)
        if not repo_link:
            continue
        m = REPO_RE.match(repo_link["url"])
        if not m:
            continue
        repo = m.group(1)
        print(f"Fetching {repo}…")
        result = fetch_repo(repo)
        if result:
            default_branch = result.pop("_default_branch", "main")
            # Consume private fork fields; expose public keys only for actual forks.
            is_fork = result.pop("_is_fork", False)
            fork_parent_name = result.pop("_fork_parent_name", "")
            fork_parent_url = result.pop("_fork_parent_url", "")
            if is_fork and fork_parent_name:
                result["isFork"] = True
                result["forkParent"] = fork_parent_name
                result["forkParentUrl"] = fork_parent_url
            image = fetch_readme_image(repo, default_branch)
            if image:
                result["preview_image"] = image
                print(f"  preview: {image[:80]}")
            releases = fetch_releases(repo)
            if releases:
                result["releases"] = releases
                print(f"  releases: {len(releases)} fetched")
            meta[repo_link["url"]] = result
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {len(meta)} entries to {META_OUT}")


if __name__ == "__main__":
    main()
