#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Build the digest that opens an automated metadata-refresh pull request.

Both CI fetch jobs (scripts/summarize_releases.py for GitHub releases,
scripts/fetch_planet_feeds.py for everything else) add items to
src/_data/planet_feeds.json and then open a PR. Before this module the PR body
was a fixed paragraph, so a reviewer had to read the JSON diff to learn what
the run had actually summarized.

The digest turns that batch into readable markdown:

    ### 🏷 6 new releases this run

    <lede: 2-3 model-written sentences orienting the reviewer>

    #### tt-bio — Aug 18–19
    - **[v0.3.0](…)** — Adds a Blackhole path to the folding demo.
    - **[v0.4.0](…)** — Ships the co-folding UI …

Design notes:

* **Grouped by project, not one heading per item.** A project that shipped
  five releases in three days reads as one run, matching how the planet page
  now renders the same burst as a single card (groupReleaseRuns in
  .eleventy.js).
* **The lede is best-effort.** It costs one model call per run and every
  failure path — API error, malformed prompt, missing PyYAML — degrades to an
  omitted paragraph rather than a failed job. The mechanical list is the part
  that must always ship, because it is assembled from summaries the run
  already paid for.
* **No items means no file.** write_pr_body() deliberately leaves the body
  file absent so peter-evans/create-pull-request falls back to the static
  `body:` in the workflow.

Used as a library, not a CLI.
"""

import os
import re
import sys
from pathlib import Path

import llm_client

# Anthropic-direct default model; the live foundry path uses
# FOUNDRY_DEFAULT_MODEL in llm_client, overridable via SUMMARY_MODEL.
MODEL = "claude-haiku-4-5-20251001"

# Caps on what we hand the model. A run that adds 80 items would otherwise
# build a manifest larger than the context we want to pay for, and the lede
# only needs enough of the batch to characterize it.
MANIFEST_MAX_ITEMS = 40
MANIFEST_DESC_CHARS = 240

# Cap on each summary reproduced in the PR body. Full summaries can run past
# 1200 characters; the body stays scannable and the untruncated text is one
# click away in the file diff.
BODY_DESC_CHARS = 600

# GitHub rejects a PR body or comment over 65536 characters. A run of ~90
# releases at full length would cross that, so the digest trims its own tail
# and says how many projects it dropped rather than letting the API 422.
BODY_MAX_CHARS = 60000

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Leading markdown structure the lede prompt asks the model not to emit. It
# usually complies; when it doesn't, a stray "## Summary" would outrank the
# digest's own headings and wreck the body's outline, so we strip it.
_LEADING_HEADING_RE = re.compile(r"^\s*#{1,6}\s.*?(?:\n|$)")


def _pretty_date(date_str: str) -> str:
    """Format "YYYY-MM-DD" as "Aug 18". Returns the input unchanged if unparseable."""
    parts = (date_str or "").split("-")
    if len(parts) < 3:
        return date_str or ""
    try:
        month = _MONTHS[int(parts[1]) - 1]
        return f"{month} {int(parts[2])}"
    except (ValueError, IndexError):
        return date_str


def _date_range(dates: list) -> str:
    """Render a group's date span: "Aug 18" for one day, "Aug 18–19" for a run."""
    clean = sorted(d for d in dates if d)
    if not clean:
        return ""
    first, last = _pretty_date(clean[0]), _pretty_date(clean[-1])
    if first == last:
        return first
    # Same month: "Aug 18–19" rather than the redundant "Aug 18–Aug 19".
    if clean[0][:7] == clean[-1][:7]:
        return f"{first}–{last.split()[-1]}"
    return f"{first}–{last}"


def _inline(text: str, limit: int) -> str:
    """Collapse a summary to one line and clamp it for inline display.

    Release summaries are one paragraph but can contain newlines, and a raw
    newline inside a markdown list item breaks the item. Truncation lands on a
    word boundary so a clamped summary doesn't end mid-token.
    """
    flat = " ".join((text or "").split())
    if len(flat) <= limit:
        return flat
    cut = flat[:limit]
    if " " in cut:
        cut = cut[:cut.rindex(" ")]
    return cut.rstrip(" ,;:") + "…"


def _sanitize_heading(text: str) -> str:
    """Make a string safe to place after "#### " on its own line.

    An item whose title happens to start with '#' or contain a newline could
    otherwise inject a heading of its own and break the body's outline.
    """
    return " ".join((text or "").split()).lstrip("#").strip() or "(untitled)"


def group_by_project(items: list) -> list:
    """Bucket items by project, newest group first, oldest item first within.

    Returns a list of ``{"project": str, "items": [item, …], "dates": [str, …]}``.
    Items with no ``projectName`` (papers, talks, blog posts) fall back to
    their title, so every planet item type groups without special-casing.
    """
    buckets = {}
    for item in items or []:
        key = item.get("projectName") or item.get("title") or "(untitled)"
        buckets.setdefault(key, []).append(item)

    groups = []
    for project, group_items in buckets.items():
        # Oldest first: within a project the releases should read as a run.
        group_items.sort(key=lambda i: i.get("dateISO") or i.get("date") or "")
        groups.append({
            "project": project,
            "items": group_items,
            "dates": [i.get("date", "") for i in group_items],
        })

    # Newest group first, keyed on the group's most recent item, so the most
    # relevant project heads the digest.
    groups.sort(key=lambda g: max((i.get("dateISO") or "") for i in g["items"]),
                reverse=True)
    return groups


def _short_label(item: dict) -> str:
    """The part of an item's title that isn't the project name.

    Release titles are "<project> <tag>", so stripping the project leaves the
    bare tag — which is all a grouped list needs. Non-release items keep their
    full title.
    """
    title = " ".join((item.get("title") or "").split())
    project = " ".join((item.get("projectName") or "").split())
    if project and title.startswith(project + " "):
        return title[len(project) + 1:] or title
    return title or "(untitled)"


def build_digest(items: list, *, kind: str, lede: str) -> str:
    """Render the batch as markdown. Returns "" when there is nothing to report.

    Args:
        items: The planet items this run added.
        kind: ``"release"`` for the GitHub-metadata job, ``"planet"`` for the
            feed job. Only affects wording and whether the approval callout
            can appear.
        lede: The model-written opening paragraph, or "" to omit it.
    """
    if not items:
        return ""

    noun = "release" if kind == "release" else "item"
    plural = "" if len(items) == 1 else "s"
    icon = "🏷" if kind == "release" else "🪐"

    parts = [f"### {icon} {len(items)} new {noun}{plural} this run"]

    if lede and lede.strip():
        parts.append(lede.strip())

    # Items the reviewer must act on. Trusted sources land approved=True and
    # publish immediately; untrusted ones wait for a human, and that decision
    # is the entire reason the planet-feeds PR exists.
    pending = [i for i in items if not i.get("approved", True)]
    if pending and kind != "release":
        listed = ", ".join(f"[{_sanitize_heading(i.get('title'))}]({i.get('url', '')})"
                           for i in pending)
        parts.append(
            f"> ⚠️ **{len(pending)} item{'' if len(pending) == 1 else 's'} "
            f"awaiting approval** — flip `approved` to `true` for anything you want "
            f"published, or record a decline (see below): {listed}"
        )

    # One part per project — heading and its list together. _clamp_body() drops
    # whole parts, so splitting them would let it keep a heading whose list did
    # not fit and emit a run of bare headings.
    sections = []
    for group in group_by_project(items):
        span = _date_range(group["dates"])
        heading = _sanitize_heading(group["project"])

        lines = [f"#### {heading}" + (f" — {span}" if span else ""), ""]
        for item in group["items"]:
            label = _sanitize_heading(_short_label(item))
            url = item.get("url", "")
            linked = f"[{label}]({url})" if url else label
            desc = _inline(item.get("description", ""), BODY_DESC_CHARS)
            flag = "" if item.get("approved", True) else " ⚠️ *awaiting approval*"
            lines.append(f"- **{linked}**{flag}" + (f" — {desc}" if desc else ""))
        sections.append("\n".join(lines))

    return _clamp_body(parts, sections)


def _clamp_body(header: list, sections: list) -> str:
    """Join header + project sections, dropping the tail that exceeds the cap.

    Args:
        header: The count heading, lede, and approval callout. Always kept —
            these are what orient a reviewer, and together they are small.
        sections: One self-contained markdown block per project (its heading and
            its release list), newest project first.

    Sections are dropped from the END and the loop STOPS at the first one that
    does not fit. Both matter: dropping from the end sheds the least-recent
    projects, and stopping — rather than skipping and continuing — keeps the
    digest a contiguous prefix. Skipping would let a later, smaller section
    slip in after an earlier one was dropped, so "the newest N projects" would
    silently become an arbitrary subset.
    """
    body = "\n\n".join(header + sections)
    if len(body) <= BODY_MAX_CHARS:
        return body

    kept = list(header)
    shown = 0
    for section in sections:
        # Leave room for the truncation notice we are about to append.
        if len("\n\n".join(kept + [section])) > BODY_MAX_CHARS - 250:
            break
        kept.append(section)
        shown += 1

    dropped = len(sections) - shown
    kept.append(
        "_Digest truncated to stay under GitHub's body size limit"
        + (f" — {dropped} more project(s) not shown." if dropped else ".")
        + " The full set of additions is in the file diff._"
    )
    return "\n\n".join(kept)


def build_manifest(items: list) -> str:
    """Render the batch as the compact plain-text list handed to the model.

    Deliberately not markdown: the model is writing prose about this list, not
    reformatting it, and the flat shape keeps the prompt small.
    """
    lines = []
    for item in (items or [])[:MANIFEST_MAX_ITEMS]:
        bits = [b for b in (item.get("affiliation"), item.get("type"),
                            item.get("date")) if b]
        flag = "" if item.get("approved", True) else " [AWAITING APPROVAL]"
        lines.append(f"{item.get('title', '(untitled)')} ({', '.join(bits)}){flag}")
        desc = _inline(item.get("description", ""), MANIFEST_DESC_CHARS)
        if desc:
            lines.append(f"  {desc}")

    overflow = len(items or []) - MANIFEST_MAX_ITEMS
    if overflow > 0:
        lines.append(f"… and {overflow} more item(s) not listed here.")
    return "\n".join(lines)


def request_lede(items: list, *, anthropic_api_key: str = "", github_token: str = "",
                 foundry_api_key: str = "") -> str:
    """Ask the active provider for the PR's opening paragraph. "" on any failure.

    Never raises: the digest's mechanical list is worth shipping on its own, so
    a dead backend, a malformed prompt file, or a missing PyYAML all degrade to
    an omitted lede with a WARN on stderr.
    """
    if not items:
        return ""  # nothing to characterize — don't spend a call

    try:
        text = llm_client.complete(
            "pr-digest",
            {"count": str(len(items)), "manifest": build_manifest(items)},
            anthropic_model=MODEL,
            anthropic_api_key=anthropic_api_key,
            github_token=github_token,
            foundry_api_key=foundry_api_key,
        )
    except Exception as e:  # noqa: BLE001 — a lede is never worth failing a run
        print(f"  WARN pr_digest: lede unavailable ({e})", file=sys.stderr)
        return ""

    if not text:
        print("  WARN pr_digest: provider returned no lede; digest ships without one",
              file=sys.stderr)
        return ""

    # The prompt forbids a leading heading; strip one if the model added it
    # anyway rather than letting it outrank the digest's own headings.
    return _LEADING_HEADING_RE.sub("", text, count=1).strip()


def write_pr_body(items: list, *, kind: str, lede: str, boilerplate: str,
                  path) -> str:
    """Write digest + boilerplate to ``path``; return the markdown written.

    When ``items`` is empty nothing is written and "" is returned, leaving the
    file absent so create-pull-request falls back to its static ``body:``.
    """
    digest = build_digest(items, kind=kind, lede=lede)
    if not digest:
        return ""

    body = digest
    if boilerplate and boilerplate.strip():
        body += "\n\n---\n\n" + boilerplate.strip()
    body += "\n"

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    return body


def append_step_summary(markdown: str) -> None:
    """Append markdown to the Actions run summary, if we're running in Actions.

    Best-effort by design: a missing or unwritable GITHUB_STEP_SUMMARY is not
    worth turning a successful fetch run red.
    """
    if not markdown or not markdown.strip():
        return
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    try:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(markdown.rstrip("\n") + "\n")
    except OSError as e:
        print(f"  WARN pr_digest: could not write GITHUB_STEP_SUMMARY ({e})",
              file=sys.stderr)
