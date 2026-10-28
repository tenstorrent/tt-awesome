#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Fetch stars, updatedAt, and a preview image for all repo-linked entries.
Writes src/_data/github_meta.json.

Also detects repos that were renamed or moved between orgs since the entry was
written. GitHub answers a request for the old name with a 301 that urllib
follows, so the JSON describes the repo under its *current* name. When that
differs from the entry's, main() rewrites the entry's canonical repo link,
records the old name in the entry's `previous_repos`, and writes a markdown
section to repo-renames.md for the nightly PR body. The summarizer reads
`previous_repos` so releases re-arriving under the new URL are not published
twice. Name, description and id are left alone — a rebrand (tt-sim → Wolfpine)
needs a human to decide what the entry should now say.

    python3 scripts/fetch_github_meta.py [--dry-run]

--dry-run reports renames without touching entries/ or writing repo-renames.md;
github_meta.json is still written, keyed by the URL each entry currently has.
"""
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
# Markdown the nightly workflow prepends to the PR body when this run moved an
# entry to a renamed repo. Gitignored; absent when there was nothing to report.
RENAMES_OUT = ROOT / "repo-renames.md"
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
                # The repo's name as GitHub reports it now. Differs from the
                # requested name after a rename or org move (see rename_target).
                "_full_name": d.get("full_name", ""),
                "_html_url": d.get("html_url", ""),
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


ASSET_EXTS = re.compile(r'\.(deb|whl|tar\.gz|tgz|zip|rpm|dmg|exe|AppImage)$', re.IGNORECASE)
# The trailing alternative catches builds cut from a work branch, like sfpi's
# "7.67.0-strength-49763" (version + branch word + CI run number) and
# "7.92.0-stov" (version + branch word) — GitHub marks these non-prerelease,
# so only the tag shape identifies them.
PRE_RELEASE_TAG = re.compile(r"[.\-]dev[.\d]|[-.]rc\d|[-.]alpha|[-.]beta|[-.]qa[\d.]|\d-[a-z]+(?:-\d+)?$", re.IGNORECASE)
CHANGELOG_NAMES = ("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "CHANGES", "HISTORY.md")
CHANGELOG_MAX = 3000


def _parse_release(rel: dict) -> dict:
    """Convert a GitHub API release object to our camelCase frontend schema."""
    assets = [
        {
            "name": a["name"],
            "url": a["browser_download_url"],
            "size": a["size"],
        }
        for a in rel.get("assets", [])
        if ASSET_EXTS.search(a["name"])
    ]
    entry = {
        "tagName": rel["tag_name"],
        "name": rel.get("name") or rel["tag_name"],
        "publishedAt": rel.get("published_at", ""),
        "url": rel.get("html_url", ""),
        "prerelease": rel.get("prerelease", False),
    }
    if assets:
        entry["assets"] = assets
    return entry


def fetch_releases(repo: str, per_page: int = 5) -> list:
    """Fetch the most recent releases for a repo, excluding drafts.

    Returns a list of dicts with camelCase keys matching the frontend schema:
        tagName, name, publishedAt, url, prerelease, assets
    Draft releases are skipped; pre-releases are included (caller can filter).
    Returns an empty list on any error so a single bad repo never aborts the run.

    The list is sorted newest-published first. This is not cosmetic:
    src/_data/entries.js resolves latestStableRelease with releases.find(...),
    which takes the first match in array order and so assumes newest-first.
    GitHub's list-releases endpoint sorts by *created_at*, which is the tag's
    date — a release tagged from an older commit but published later arrives
    out of order and silently changes which release the site calls "latest".
    tt-finetune's demo-2026-08-29 (same created_at as v0.2.1, published a day
    later) is the case that surfaced it. Sorting here makes the invariant the
    data layer documents hold for every repo on every run, rather than by luck
    of how a maintainer happened to cut their tags.
    """
    try:
        url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}"
        with urllib.request.urlopen(_request(url), timeout=10) as r:
            releases = json.loads(r.read())
            parsed = [
                _parse_release(rel)
                for rel in releases
                if not rel.get("draft", False)
            ]
            # `or ""` keeps a null published_at (possible on a draft just
            # promoted to a release) sorting last instead of raising and
            # costing us the repo's entire release list.
            parsed.sort(key=lambda r: r.get("publishedAt") or "", reverse=True)
            return parsed
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo} releases: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo} releases: {e}", file=sys.stderr)
    return []


def fetch_latest_stable(repo: str) -> dict | None:
    """Fetch the latest published full release for a repo.

    Strategy:
    1. Try GitHub's /releases/latest. If it returns a clean (non-dev/non-rc)
       tag, that's our answer.
    2. If /releases/latest returns a dev/rc tag (common when repos publish
       nightly dev builds without setting prerelease=true), fall back to
       fetching up to 50 releases and returning the first clean-tagged one.
    3. Returns None if no stable release is found (404, network error, etc).
    """
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        with urllib.request.urlopen(_request(url), timeout=10) as r:
            parsed = _parse_release(json.loads(r.read()))
            if not PRE_RELEASE_TAG.search(parsed["tagName"]):
                return parsed
            # /releases/latest returned a dev build — fall through to deep scan
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  WARN {repo} releases/latest: HTTP {e.code}", file=sys.stderr)
        # 404 means no releases at all; skip the deep scan too
        else:
            return None
    except Exception as e:
        print(f"  WARN {repo} releases/latest: {e}", file=sys.stderr)
        return None

    # Deep scan: fetch a larger batch and find the first clean-tagged release
    try:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=50"
        with urllib.request.urlopen(_request(url), timeout=10) as r:
            for rel in json.loads(r.read()):
                if rel.get("draft", False):
                    continue
                parsed = _parse_release(rel)
                if not PRE_RELEASE_TAG.search(parsed["tagName"]):
                    return parsed
    except Exception as e:
        print(f"  WARN {repo} deep release scan: {e}", file=sys.stderr)
    return None


def fetch_changelog(repo: str, default_branch: str = "main") -> str | None:
    """Return the first CHANGELOG_MAX chars of the repo's changelog, or None."""
    for name in CHANGELOG_NAMES:
        url = f"https://api.github.com/repos/{repo}/contents/{name}?ref={default_branch}"
        try:
            with urllib.request.urlopen(_request(url), timeout=10) as r:
                data = json.loads(r.read())
                content = base64.b64decode(data.get("content", "").replace("\n", ""))
                text = content.decode("utf-8", errors="replace")
                return text[:CHANGELOG_MAX].strip() or None
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"  WARN {repo} changelog {name}: HTTP {e.code}", file=sys.stderr)
        except Exception as e:
            print(f"  WARN {repo} changelog {name}: {e}", file=sys.stderr)
    return None


def rename_target(requested: str, current: str) -> str | None:
    """Return the repo's current "owner/name" if it differs from the one requested.

    GitHub repo names are case-insensitive, so a case-only difference is the
    same repo and not a rename. An empty `current` (failed fetch, old API shape)
    is never treated as a rename: moving an entry on missing data would be
    worse than leaving it stale.
    """
    if not requested or not current:
        return None
    if requested.lower() == current.lower():
        return None
    return current


def apply_rename(entry_path: Path, old_repo: str, new_repo: str, new_url: str) -> None:
    """Point an entry's canonical repo link at a renamed repo.

    Rewrites only the first `repo` link — other links (wiki, docs under the
    old path) are left for the reviewer, as is every other field: the author
    did not change because the repo moved, and the display name and id need a
    human decision. The old "owner/name" is appended to `previous_repos`,
    which the summarizer uses to recognise releases arriving under the new URL
    (see summarize_releases.load_previous_repos).

    The file is rewritten with the same key order, UTF-8 intact and a trailing
    newline, so the PR diff shows only the lines that changed.
    """
    entry = json.loads(entry_path.read_text())
    for link in entry.get("links", []):
        if link.get("type") == "repo":
            link["url"] = new_url
            break
    prev = [r for r in (entry.get("previous_repos") or []) if isinstance(r, str)]
    if old_repo not in prev:
        prev.append(old_repo)
    entry["previous_repos"] = prev
    entry_path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")


def format_renames_md(renames: list) -> str:
    """Markdown section for the PR body listing this run's repo renames.

    Starts with a `### ` heading on purpose: the nightly workflow comments any
    pr-body section carrying one onto the PR, so a rename is surfaced in the
    notification and not just the diff.
    """
    n = len(renames)
    noun = "repo rename" if n == 1 else "repo renames"
    lines = [f"### 🔀 {n} {noun} detected", ""]
    lines.append(
        "GitHub now reports these repos under a new owner or name. The entry's "
        "canonical `repo` link has been moved and the old name recorded in "
        "`previous_repos`, so Planet will not re-announce old releases under the "
        "new URL. Everything else needs a look before merging:"
    )
    lines.append("")
    for r in renames:
        lines.append(f"- **{r['entry_id']}** — `{r['old_repo']}` → "
                     f"[`{r['new_repo']}`]({r['new_url']}) (`{r['entry_path']}`)")
    lines += [
        "",
        "Checklist per entry:",
        "- [ ] `name` and `description` — is this a rebrand, or just a move?",
        "- [ ] `id` — if the project is known by the new name, rename the file and "
        "add the old id to `previous_ids` so existing links redirect",
        "- [ ] `author` — unchanged by the move; fix it only if the maintainer changed",
        "- [ ] `affiliation` — a move into or out of a Tenstorrent org changes it, "
        "and `scripts/validate.py` will fail until it matches",
        "- [ ] `packages` and other links still under the old path",
        "- [ ] existing Planet items whose `label` carries the old name",
        "",
    ]
    return "\n".join(lines)


def main(argv: list | None = None):
    args = sys.argv[1:] if argv is None else argv
    dry_run = "--dry-run" in args
    entry_files = sorted(ENTRIES_DIR.rglob("*.json"))
    meta = {}
    renames = []
    for entry_path in entry_files:
        entry = json.loads(entry_path.read_text())
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
            # Rename / org move: the API answered for a different owner/name
            # than the entry asked for. Move the entry now so the rest of this
            # run (and the site, which looks metadata up by the entry's URL)
            # works from the new name.
            new_repo = rename_target(repo, result.pop("_full_name", ""))
            new_url = result.pop("_html_url", "") or f"https://github.com/{new_repo}"
            meta_key = repo_link["url"]
            if new_repo:
                rel_path = entry_path.relative_to(ROOT) if entry_path.is_relative_to(ROOT) \
                    else entry_path.relative_to(ENTRIES_DIR.parent)
                record = {
                    "entry_id": entry.get("id", entry_path.stem),
                    "entry_path": str(rel_path),
                    "old_repo": repo, "new_repo": new_repo, "new_url": new_url,
                }
                if dry_run:
                    print(f"  RENAME {repo} → {new_repo} (dry run; entry not changed)")
                else:
                    apply_rename(entry_path, repo, new_repo, new_url)
                    renames.append(record)
                    meta_key = new_url
                    print(f"  RENAME {repo} → {new_repo}: entry moved, old name "
                          f"recorded in previous_repos")
                repo = new_repo
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
                asset_count = sum(len(r.get("assets", [])) for r in releases)
                print(f"  releases: {len(releases)} fetched, {asset_count} assets")
                # When all recent releases are dev/rc builds, the latest stable
                # release may lie beyond the fetched window. Fetch it explicitly
                # so the UI can always display a LATEST stable callout.
                # Check tag name too — GitHub sometimes marks dev builds non-prerelease.
                has_stable = any(
                    not r["prerelease"] and not PRE_RELEASE_TAG.search(r["tagName"])
                    for r in releases
                )
                if not has_stable:
                    stable = fetch_latest_stable(repo)
                    if stable:
                        result["latestStableRelease"] = stable
                        print(f"  latestStable: {stable['tagName']} (beyond recent window)")
            changelog = fetch_changelog(repo, default_branch)
            if changelog:
                result["changelog_excerpt"] = changelog
                print(f"  changelog: {len(changelog)} chars")
            meta[meta_key] = result
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {len(meta)} entries to {META_OUT}")

    # A stale file from an earlier run would otherwise be read by the workflow
    # as this run's findings, so it is removed whenever there is nothing to say.
    if renames:
        RENAMES_OUT.write_text(format_renames_md(renames))
        print(f"Wrote {len(renames)} rename(s) to {RENAMES_OUT}")
    elif RENAMES_OUT.exists():
        RENAMES_OUT.unlink()


if __name__ == "__main__":
    main()
