# Release Summarization for Planet Tenstorrent

**Date:** 2026-06-05
**Status:** Approved

## Problem

The nightly metadata crawler (`fetch_github_meta.py`) tracks GitHub releases across all watched repos, but release notes land in `github_meta.json` as raw data — never surfaced to Planet Tenstorrent readers. Maintainers have no way to share a humanized "what's new" summary without manual work.

## Goal

When the nightly job detects a new release with enough release notes to summarize, automatically generate a one-paragraph human-readable summary and append it to `planet_feeds.json` as a `type: "release"` item with `approved: true` for immediate inclusion in the Planet feed.

## Non-Goals

- Summarizing releases with sparse notes (body under ~150 characters, or empty)
- Holding release summaries for manual review (items are `approved: true` immediately)
- Modifying the Planet UI or frontend templates
- Adding any new workflow files

## Architecture

No new workflow file. The summarization step is a new script (`scripts/summarize_releases.py`) invoked by the existing `nightly.yml` job immediately after `fetch_github_meta.py`. Both scripts share the same job and the same `create-pull-request` step — which expands `add-paths` to cover `planet_feeds.json` alongside `github_meta.json`. The summarization step is gated on the `ANTHROPIC_API_KEY` secret and skipped entirely when the secret is absent.

```
nightly.yml job
  ├── fetch_github_meta.py      (existing — writes github_meta.json)
  ├── summarize_releases.py     (new — reads github_meta.json, appends to planet_feeds.json)
  └── create-pull-request       (existing — now stages both files)
```

## Data Flow

1. `fetch_github_meta.py` runs as today, writing `github_meta.json` with `releases[]` per repo
2. `summarize_releases.py` runs next:
   - Loads `github_meta.json` (all current releases, keyed by repo URL)
   - Loads `planet_feeds.json` (builds dedup set of known URLs)
   - Loads entry JSONs to resolve `affiliation` per repo
3. For each release URL not in the dedup set:
   - Fetches the GitHub release `body` via `GET /repos/{owner}/{repo}/releases/tags/{tag}`
   - If `body` is empty or under 150 characters: skip, log reason, continue
   - Otherwise: calls the Anthropic Messages API with the release body
4. Each successful summary is appended to `planet_feeds.json` as a new item with `approved: true`
5. `create-pull-request` opens a PR with both changed files (or only one if only metadata changed)

## Planet Feed Item Schema

New release items match the existing `planet_feeds.json` shape exactly:

```json
{
  "type": "release",
  "source": "github",
  "approved": true,
  "title": "{projectName} {tagName}",
  "url": "https://github.com/{repo}/releases/tag/{tagName}",
  "description": "...humanized paragraph...",
  "date": "YYYY-MM-DD",
  "dateISO": "YYYY-MM-DDTHH:MM:SSZ",
  "label": "{owner}/{repo}",
  "projectName": "{repo name}",
  "projectId": null,
  "affiliation": "official" | "community" | "affiliated"
}
```

`affiliation` is resolved from the matching entry JSON, the same source `fetch_github_meta.py` already reads.

## Anthropic API Integration

- **Endpoint:** `POST https://api.anthropic.com/v1/messages`
- **Auth:** `x-api-key: $ANTHROPIC_API_KEY`
- **Model:** `claude-haiku-4-5-20251001` (fast, low-cost)
- **Secret required:** `ANTHROPIC_API_KEY` repo secret; step is skipped when absent
- **Implementation:** raw `urllib` HTTP call in the Python script — no new dependencies
- **GitHub REST API** (fetching release bodies) still uses `GITHUB_TOKEN`

## Prompt

**System:**
```
You write brief, engaging release summaries for Planet Tenstorrent, an aggregator
read by developers and researchers following the Tenstorrent ecosystem. Your tone
is warm and technically literate — like a knowledgeable colleague sharing what's
new, not a press release. Write one paragraph of 2–4 sentences. Focus on what
changed and why it matters. Do not repeat the version number or project name.
Do not use hype words like "exciting" or "powerful". Do not use bullet points.
```

**User:**
```
Summarize this release for Planet Tenstorrent readers.

Project: {owner}/{repo} ({affiliation})
Release: {release name}

Release notes:
{body}
```

## Sparse Body Threshold

Skip summarization (do not add a feed item) if:
- `body` is `null` or empty string
- `body` stripped of whitespace is under 150 characters

Log the skip reason to stdout so the nightly job output is inspectable.

## Dry Run Mode

`summarize_releases.py --dry-run`:
- Reads all inputs normally
- Calls the Anthropic API and prints candidate summaries to stdout
- Writes nothing to `planet_feeds.json`
- Exits 0

`nightly.yml` `workflow_dispatch` input `dry_run: boolean` (default `false`):
- Passes `--dry-run` flag to the script
- Skips the `create-pull-request` step
- Used for end-to-end CI verification before enabling live integration

## Workflow Changes

```yaml
# nightly.yml additions

permissions:
  contents: write
  pull-requests: write

steps:
  # ... existing fetch step unchanged ...

  - name: Summarize new releases        # NEW STEP — skipped when secret absent
    if: ${{ secrets.ANTHROPIC_API_KEY != '' }}
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: python3 scripts/summarize_releases.py

  - name: Create pull request if changed
    uses: peter-evans/create-pull-request@v7
    with:
      add-paths: |                       # EXPANDED
        src/_data/github_meta.json
        src/_data/planet_feeds.json
      # ... rest unchanged ...
```

## Testing Strategy

1. **Local dry run:** `ANTHROPIC_API_KEY=... python3 scripts/summarize_releases.py --dry-run` against existing `github_meta.json` data — iterate on prompt without touching any files
2. **CI dry run:** trigger `nightly.yml` via `workflow_dispatch` with `dry_run: true` — confirms API call works end-to-end
3. **Live:** enable with `dry_run: false`, review the first real PR with both files changed
