#!/usr/bin/env python3
"""Fetch stars + updatedAt for all repo-linked entries. Writes src/_data/github_meta.json."""
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


def fetch_repo(repo: str) -> dict:
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return {"stars": d.get("stargazers_count", 0), "updatedAt": d.get("updated_at", "")}
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo}: {e}", file=sys.stderr)
    return {}


def main():
    entries = [json.loads(f.read_text()) for f in sorted(ENTRIES_DIR.glob("*.json"))]
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
            meta[repo_link["url"]] = result
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {len(meta)} entries to {META_OUT}")


if __name__ == "__main__":
    main()
