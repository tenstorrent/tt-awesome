#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Summarize new GitHub releases and append them to planet_feeds.json.

For each release URL in github_meta.json not already in planet_feeds.json:
  - Fetches the release body from the GitHub API
  - Skips if body is empty or under 120 characters
  - Runs prompts/summarize-release.prompt.yml through llm_client (Claude on
    Microsoft Foundry by default; SUMMARY_PROVIDER=anthropic calls Anthropic
    direct. The former `github` GitHub Models path was retired 2026-07-30.)
  - Appends a type:"release" item (approved:true) to planet_feeds.json

Usage:
    python3 scripts/summarize_releases.py [--dry-run]
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
META_IN = ROOT / "src" / "_data" / "github_meta.json"
FEEDS_OUT = ROOT / "src" / "_data" / "planet_feeds.json"

import llm_client

MODEL = "claude-haiku-4-5-20251001"  # Anthropic-direct default; see llm_client
SPARSE_LIMIT = 120  # characters; bodies shorter than this are skipped.
# Set to 120 (down from 150) so terse-but-substantive notes — a few real
# bullet points, e.g. ttsim v1.8.4's ~134-char changelog — still get
# summarized, while one-liners like "Bug fixes." remain filtered out.

TOKEN = os.environ.get("ANTHROPIC_API_KEY", "")     # LLM calls when SUMMARY_PROVIDER=anthropic
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")       # GitHub REST API (release bodies, changelogs)
FOUNDRY_KEY = os.environ.get("FOUNDRY_API_KEY", "")  # LLM calls on the default foundry provider

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


def release_key(title: str) -> str:
    """Rename-proof identity for a release item.

    URLs are not stable: GitHub reports the *current* owner/name for a release,
    so when a repo is renamed or moved between orgs the same release starts
    arriving under a new URL and slips past the URL check, publishing twice.
    That is how "tt-bh-linux v0.11" (tenstorrent → tenstorrent-riscv-software)
    and "BarraCUDA v0.5.0" (BarraCUDA → Booth) both landed on the planet twice.

    The title is "<repo basename from the entry> <tag>", derived from the entry
    rather than from the API response, so it survives a rename on GitHub's side.
    """
    return " ".join((title or "").lower().split())


def load_known_release_keys(feeds_path: Path) -> set:
    """Identities of the release items already in planet_feeds.json.

    Skips and reports individual malformed items rather than giving up on the
    whole set: returning an empty set here silently disables rename dedup and
    re-publishes every renamed repo's releases, so one bad record must not cost
    us the other few hundred good ones.
    """
    if not feeds_path.exists():
        return set()
    try:
        items = json.loads(feeds_path.read_text())
    except Exception:
        # An unreadable/malformed file is already reported by load_known_urls,
        # which main() calls first — don't warn twice about the same thing.
        return set()

    keys = set()
    for i in items:
        if not isinstance(i, dict) or i.get("type") != "release":
            continue
        title = i.get("title")
        if isinstance(title, str) and title.strip():
            keys.add(release_key(title))
        else:
            print(f"  WARN: release item has no usable title ({title!r}); it cannot "
                  f"be matched against a renamed repo — url={i.get('url')!r}",
                  file=sys.stderr)
    return keys


def build_affiliation_map(entry_dirs: list) -> dict:
    """Scan all entry JSONs once and return a repo_url -> affiliation mapping."""
    mapping = {}
    for d in entry_dirs:
        for f in Path(d).rglob("*.json"):
            try:
                data = json.loads(f.read_text())
                affil = data.get("affiliation", "community")
                for link in data.get("links", []):
                    url = link.get("url", "").rstrip("/")
                    if url:
                        mapping[url] = affil
            except Exception:
                continue
    return mapping


def resolve_affiliation(repo_url: str, entry_dirs: list) -> str:
    """Return affiliation for a repo URL by scanning entry JSONs."""
    return build_affiliation_map(entry_dirs).get(repo_url.rstrip("/"), "community")


def _gh_request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GH_TOKEN:
        req.add_header("Authorization", f"Bearer {GH_TOKEN}")
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


# Files we look in for a per-version changelog, in priority order. Mirrors the
# list in fetch_github_meta.py so both scripts agree on what "the changelog" is.
CHANGELOG_NAMES = ("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "CHANGES", "HISTORY.md")

# A release body "defers to the changelog" when it points readers at a changelog
# file for the actual changes instead of listing them inline. This is the
# signature of a boilerplate template body (install steps + prerequisites +
# "What's New → See CHANGELOG.md"), e.g. tt-vscode-toolkit's releases. Matching
# the *.md filename keeps this narrow: bodies that inline their own notes almost
# never link out to a changelog file.
_DEFERS_RE = re.compile(r"\b(?:CHANGELOG|CHANGES|HISTORY)\.md\b", re.IGNORECASE)


def body_defers_to_changelog(body: str) -> bool:
    """Return True if the release body points to a changelog file for the changes.

    These bodies are fixed boilerplate (install instructions, prerequisites, and
    a "See CHANGELOG.md" pointer) that the same for every release — summarizing
    them yields a generic blurb, so the caller should fetch the real changelog
    section instead.
    """
    return bool(_DEFERS_RE.search(body or ""))


def extract_changelog_section(changelog_text: str, tag: str, date: str | None = None) -> str | None:
    """Return the changelog section for a given release tag, or None.

    Parses "Keep a Changelog"-style markdown — version sections introduced by a
    heading such as ``## [0.0.514] - 2026-06-23`` — and returns just the block
    for the version matching ``tag`` (leading ``v`` stripped), up to but not
    including the next heading of the same or higher level. Sub-headings within
    the section (e.g. ``### Fixed``) are preserved.

    Args:
        changelog_text: Full changelog markdown.
        tag: Release tag, e.g. ``v0.0.514``; a leading ``v`` is stripped.
        date: Optional ``YYYY-MM-DD`` release date. When a changelog contains
            more than one heading for the same version (an upstream duplicate),
            the heading whose line carries this date is preferred; otherwise the
            first matching heading is used.

    Returns None if the changelog is empty or the version is not found.
    """
    if not changelog_text or not tag:
        return None

    version = tag.lstrip("vV")
    ver_re = re.escape(version)
    # A markdown heading line that contains the version as a standalone token.
    # Boundaries keep the match from being a substring of a different version:
    #   - lookbehind rejects a preceding digit/dot (so "0.0.51" never matches
    #     inside "10.0.51") while still allowing a leading "v" (e.g. "## v0.0.51");
    #   - lookahead rejects a trailing word char, dot, or hyphen, so a stable
    #     tag never matches a longer version or a pre-release heading such as
    #     "[0.0.514-rc1]" when "0.0.514" was requested.
    heading_re = re.compile(
        rf"^(#{{1,6}})\s.*?(?<![\d.]){ver_re}(?![\w.-]).*$",
        re.MULTILINE,
    )
    matches = list(heading_re.finditer(changelog_text))
    if not matches:
        return None

    # Disambiguate duplicate version headings by the release date when given,
    # so a republished version maps to the right notes (e.g. two "[0.0.454]"
    # headings dated differently). Fall back to the first heading otherwise.
    m = matches[0]
    if date:
        for cand in matches:
            if date in cand.group(0):
                m = cand
                break

    level = len(m.group(1))  # number of leading '#' on the matched heading
    # The section ends at the next heading of the same or higher level (fewer or
    # equal '#'); deeper sub-headings stay inside this version's block.
    next_re = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    nxt = next_re.search(changelog_text, m.end())
    end = nxt.start() if nxt else len(changelog_text)

    section = changelog_text[m.start():end].strip()
    return section or None


def _fetch_url_text(url: str) -> str | None:
    """GET a URL and return its body as text, or None on error."""
    try:
        with urllib.request.urlopen(_gh_request(url), timeout=10) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  WARN _fetch_url_text {url}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN _fetch_url_text {url}: {e}", file=sys.stderr)
    return None


def _fetch_changelog_text(repo: str, ref: str) -> str | None:
    """Return the raw changelog markdown for a repo at a git ref, or None.

    Tries each name in CHANGELOG_NAMES. A candidate that exists but yields no
    usable text does not abort the search — the next candidate is tried. The
    Contents API only inlines base64 ``content`` for files up to ~1MB; larger
    files come back with empty content and a ``download_url``, which we follow.
    """
    for name in CHANGELOG_NAMES:
        url = f"https://api.github.com/repos/{repo}/contents/{name}?ref={ref}"
        try:
            with urllib.request.urlopen(_gh_request(url), timeout=10) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"  WARN _fetch_changelog_text {repo}@{ref} {name}: HTTP {e.code}", file=sys.stderr)
            continue  # not found / error — try the next candidate name
        except Exception as e:
            print(f"  WARN _fetch_changelog_text {repo}@{ref} {name}: {e}", file=sys.stderr)
            continue

        # Common case: file <=1MB, content is inlined as base64.
        encoded = (data.get("content") or "").replace("\n", "")
        if encoded:
            text = base64.b64decode(encoded).decode("utf-8", errors="replace")
            if text.strip():
                return text

        # Large files (>1MB) carry empty content and only a download_url.
        download_url = data.get("download_url")
        if download_url:
            text = _fetch_url_text(download_url)
            if text and text.strip():
                return text

        # This candidate yielded nothing usable; fall through to the next name.
    return None


def _fetch_default_branch(repo: str) -> str:
    """Return a repo's default branch name, falling back to 'main' on any error."""
    url = f"https://api.github.com/repos/{repo}"
    try:
        with urllib.request.urlopen(_gh_request(url), timeout=10) as r:
            return json.loads(r.read()).get("default_branch") or "main"
    except urllib.error.HTTPError as e:
        print(f"  WARN _fetch_default_branch {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN _fetch_default_branch {repo}: {e}", file=sys.stderr)
    return "main"


def fetch_changelog_section(repo: str, tag: str, date: str | None = None) -> str | None:
    """Fetch a repo's changelog and return the section for a release tag.

    Tries the changelog *at the release tag* first (``?ref={tag}``) — that's the
    changelog as it shipped with the build. If the version's section isn't there
    yet (the changelog entry can land in a separate commit, lagging the tag), it
    falls back to the repo's actual default branch (resolved via the API, so
    repos on ``trunk``/``develop`` work, not just ``main``/``master``). Returns
    None if no section is found.
    """
    # 1. Changelog as it shipped at the release tag.
    text = _fetch_changelog_text(repo, tag)
    if text:
        section = extract_changelog_section(text, tag, date=date)
        if section:
            return section

    # 2. Fall back to the tip of the default branch (the entry may post-date the tag).
    branch = _fetch_default_branch(repo)
    if branch != tag:
        text = _fetch_changelog_text(repo, branch)
        if text:
            section = extract_changelog_section(text, tag, date=date)
            if section:
                return section
    return None


# The prompt (system + user template) lives in prompts/summarize-release.prompt.yml
# — the single source of truth shared with the GitHub Models playground/evals.
# Its single-paragraph constraint matters downstream: the release Atom feed
# renders the summary as a one-line <summary> (see src/feeds/releases.njk,
# which also defensively collapses newlines via the `singleLine` filter). The
# full text appears with paragraph breaks in the feed's <content> block.


def call_summarization_model(repo: str, release_name: str, body: str, affiliation: str) -> str:
    """Run the release-summary prompt on the active provider. '' on error."""
    return llm_client.complete(
        "summarize-release",
        {
            "repo": repo,
            "affiliation": affiliation,
            "release_name": release_name,
            "notes": body,
        },
        anthropic_model=MODEL,
        anthropic_api_key=TOKEN,
        github_token=GH_TOKEN,
        foundry_api_key=FOUNDRY_KEY,
    )


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

    missing = llm_client.missing_credential(
        anthropic_api_key=TOKEN, github_token=GH_TOKEN, foundry_api_key=FOUNDRY_KEY
    )
    if missing:
        print(f"ERROR: {missing} not set", file=sys.stderr)
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
    # Second line of defence for repos that were renamed or moved orgs; see
    # release_key() for why the URL alone is not enough.
    known_release_keys = load_known_release_keys(FEEDS_OUT)

    # The current contents of planet_feeds.json (used when writing back merged output).
    existing_feeds = []
    if FEEDS_OUT.exists():
        try:
            existing_feeds = json.loads(FEEDS_OUT.read_text())
        except Exception:
            pass  # If the file is malformed we start fresh; load_known_urls already warned.

    # Precompute once — avoids O(repos × entries) file reads per run.
    affiliation_map = build_affiliation_map([ENTRIES_DIR])

    new_items = []
    # Counts provider calls that came back empty. A summarization backend that
    # is entirely down (retired endpoint, token without a Copilot seat, revoked
    # key) otherwise looks exactly like "nothing new to summarize" — every
    # release logs a SKIP line and the job stays green. See the exit below.
    failures = 0

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

            tag = release.get("tagName", "")
            if not tag:
                continue
            name = release.get("name") or tag

            # Skip pre-release builds — dev/nightly, RC, QA, alpha/beta tags
            # add noise. Keep in sync with PRE_RELEASE_TAG in entries.js and
            # fetch_github_meta.py.
            # dev:   "1.3.0.dev20260609", "v0.73.0-dev20260610"
            # RC:    "v0.72.0-rc4", "ttkmd-2.9.0-rc1"
            # QA:    "v1.0.0-qa1"
            # alpha/beta: "v0.17.0-alpha" (tt-buda)
            # CI experiment tags: "7.67.0-strength-49763" (version + branch
            # word + run number) — non-prerelease on GitHub, noise regardless.
            if re.search(r"[.\-]dev[.\d]|[-.]rc\d|[-.]alpha|[-.]beta|[-.]qa[\d.]|\d-[a-z]+-\d+$", tag, re.IGNORECASE):
                print(f"  SKIP {repo}@{tag}: pre-release build")
                continue

            # Same release arriving under a new URL because the repo was
            # renamed or moved orgs. Checked before summarizing so a rename
            # does not burn an LLM call on a duplicate.
            rkey = release_key(f"{repo_name} {tag}")
            if rkey in known_release_keys:
                print(f"  SKIP {repo}@{tag}: already published as '{repo_name} {tag}' "
                      f"(repo likely renamed/moved)")
                continue

            # Fetch the release body — this is what we summarize by default.
            body = fetch_release_body(repo, tag)

            # Some repos publish a fixed boilerplate body (install steps +
            # prerequisites + "See CHANGELOG.md") and keep the real per-version
            # changes in the changelog. Summarizing the boilerplate produces a
            # generic blurb, so when the body defers to the changelog we fetch
            # that version's section and summarize it instead.
            content = body
            if body_defers_to_changelog(body):
                # Pass the release date so a duplicated version heading in the
                # changelog resolves to the notes for this specific release.
                release_date = (release.get("publishedAt") or "")[:10] or None
                section = fetch_changelog_section(repo, tag, date=release_date)
                if section:
                    content = section
                    print(f"  CHANGELOG {repo}@{tag}: summarizing changelog section "
                          f"({len(section.strip())} chars) — body defers to it")

            # Quality-gate whatever content we actually plan to summarize.
            if is_sparse(content):
                print(f"  SKIP {repo}@{tag}: content too sparse ({len(content.strip())} chars)")
                continue

            # Determine whether this repo is official, community, etc.
            affiliation = affiliation_map.get(repo_url.rstrip("/"), "community")

            summary = call_summarization_model(repo, name, content, affiliation)
            if not summary:
                failures += 1
                print(f"  SKIP {repo}@{tag}: summarization failed")
                continue

            # Build the ISO date string and short date for display/sorting.
            date_str = (release.get("publishedAt") or "")[:10] or "1970-01-01"
            item = {
                "type":        "release",
                "source":      "github",
                "approved":    True,    # auto-approved; summaries go live immediately
                "title":       f"{repo_name} {tag}",
                "url":         url,
                "description": summary,
                "date":        date_str,
                "dateISO":     (release.get("publishedAt") or f"{date_str}T00:00:00Z"),
                "label":       repo,
                "projectName": repo_name,
                "projectId":   None,
                "affiliation": affiliation,
            }

            # Claim this release in both modes. These are in-memory sets, not
            # files, so a dry run stays read-only while still behaving like the
            # real thing. Updating them only in the real branch meant a release
            # reachable twice in one run — two entries pointing at the same
            # repo, one via its old name, say — got summarized twice under
            # --dry-run only, so the preview diverged from the actual run.
            known_urls.add(url)
            known_release_keys.add(rkey)

            if dry_run:
                # In dry-run mode we print the summary but never mutate any file.
                print(f"\n--- DRY RUN: {repo}@{tag} ---")
                print(summary)
            else:
                print(f"  ADDED {repo}@{tag}")
            # Accumulate in both modes so the dry-run summary count is accurate.
            new_items.append(item)

    # ── Fail loudly when the provider is down ────────────────────────────────
    # Every call failing and none succeeding means the backend is unreachable,
    # not that the releases were unremarkable. Exit non-zero so CI goes red
    # instead of opening a PR that silently summarized nothing.
    if failures and not new_items:
        print(
            f"\nERROR: all {failures} summarization call(s) failed on provider "
            f"'{llm_client.active_provider()}' — check the WARN lines above for the "
            "HTTP status, and verify SUMMARY_PROVIDER and its credential.",
            file=sys.stderr,
        )
        sys.exit(1)
    if failures:
        print(f"\nWARN: {failures} summarization call(s) failed; {len(new_items)} succeeded.",
              file=sys.stderr)

    # ── Dry-run: report and exit without touching the filesystem ─────────────
    if dry_run:
        noun = "item" if len(new_items) == 1 else "items"
        print(f"\nDRY RUN complete. {len(new_items)} {noun} would be added.")
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
