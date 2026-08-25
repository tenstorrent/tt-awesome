# CLAUDE.md — tt-awesome

Project-specific notes for agentic work in this repo. The public, consumer-facing
declaration of what this site is lives in `AGENTS.md` — keep that one polished for
outside readers; this file is the working log.

## Architecture quick map

* `entries/<category>/*.json` — the source of truth for every entry. `scripts/validate.py`
  enforces the schema (categories, link types, hardware vocab, package types).
* `scripts/fetch_github_meta.py` → `src/_data/github_meta.json` — stars, releases, changelogs.
* `scripts/summarize_releases.py` → appends `type:"release"` items to
  `src/_data/planet_feeds.json`, one per release, LLM-summarized.
* `scripts/fetch_planet_feeds.py` → the same file, for YouTube / arXiv / Reddit / blogs /
  connpass. Trusted sources land `approved:true`; the rest wait for a human.
* `scripts/llm_client.py` — provider-agnostic LLM front door. Prompts live in
  `prompts/*.prompt.yml` (GitHub Models format, kept as a provider-neutral container even
  though that service died 2026-07-30). Flip backends with the `SUMMARY_PROVIDER` repo
  Variable: `foundry` (default) | `anthropic`.
* `.eleventy.js` — all rendering logic as testable filters. `planetItems` builds the planet
  page's card list; `buildFeedContentHtml` builds every feed's rich `<content>`.

## Testing

No test runner config — suites are invoked directly, and `build-check.yml` runs the JS ones:

```
python3 scripts/validate.py         # entry schema
python3 -m pytest tests/ -q         # all python suites
npm run build                       # must precede the JS suites
node tests/test_entry_pages.js      # build-output assertions
node tests/test_data_files.js
node tests/test_eleventy_filters.js
node tests/test_recent_releases.js
```

JS filter tests reach into `.eleventy.js` by calling its export with a stub
`eleventyConfig` that captures `addFilter`. That's why helpers meant to be tested get
registered as filters even when no template calls them.

## Session log

### 2026-08-25 — CI digests, grouped release cards, tt-local-generator PPA

Prompt: *"When a single CI metadata (planet or releases) fetch job happens and the
summarization phase occurs, can we 1) summarize any new summaries added in the PR itself
(comments or body) and then 2) When a single project has multiple releases in a small
period of time, can we make only one planet entry, but summarize each release in that
entry? Extend the size of entries/feed items as needed. Make sure we style them nicely"*
Follow-up mid-turn: *"Also, tt-local-generator can now be installed from the Tenstorrent
PPA and can have updated install instructions"*.

**1. PR digests** (`scripts/pr_digest.py`, `prompts/pr-digest.prompt.yml`). Both fetch
jobs now write `pr-body.md` — an LLM-written lede plus the run's summaries grouped by
project — and pass it to `create-pull-request` as `body-path`, then post it as a per-run
comment. The boilerplate moved to `.github/pr-templates/*.md`, shared between the script
and the workflow's fallback `cp`, so there's one copy of it. Also appended to
`$GITHUB_STEP_SUMMARY`.

Key decision: **the lede is best-effort.** Every failure path (API error, malformed
prompt, missing PyYAML) degrades to an omitted paragraph rather than a failed job — the
mechanical list is assembled from summaries the run already paid for and must always
ship. `build_digest` also self-truncates at 60k chars because GitHub 422s a body over
65536.

**2. Grouped release cards.** Chose **render-time** grouping (`groupReleaseRuns` in
`.eleventy.js`) over write-time in the summarizer, because the fetch job runs twice daily
and real bursts routinely span runs — `tt-bio-demo v0.2.2` (8/18) and `v0.4.0` (8/19)
were summarized in different runs. Render-time also fixed the whole existing history at
once: 298 releases now render as 232 cards, 42 of them grouped. `planet_feeds.json` keeps
one record per release, so the summarizer never changed.

Window is a **chained** 3 days, capped at 8. Chained means `tt-bio` v0.2.0–v0.2.4 (all
one day) plus v0.2.5 two days later is one run of six. Measured over the history, 3 days
collapses 43 bursts covering 116 items — tight enough that a steady weekly cadence still
gets a card per release.

The release Atom feed carries one entry per project, so older releases in a burst reached
no subscriber at all; `resolveRunSummaries` in `_data/recentReleases.js` now attaches them
and `buildFeedContentHtml` renders an "Also in this run" list. `RUN_WINDOW_DAYS` there
must stay equal to `RELEASE_RUN_WINDOW_DAYS` in `.eleventy.js`.

Also raised `summarize-release.prompt.yml` `maxTokens` 400 → 700: 400 was clipping real
summaries mid-word (tt-bio v0.7.0 ended at "on qb"). The prompt's own 2–5 sentence limit
is what keeps summaries short; the ceiling only exists to stop a runaway.

**3. tt-local-generator.** Verified against the live PPA
(`ppa.tenstorrent.com/ubuntu/dists/noble/main/binary-amd64/Packages`) rather than
assuming the package name — it ships as `tt-local-generator` 0.96.1. Adding a `packages`
entry generates install instructions everywhere automatically (README, entry card + copy
button, list badge). Deliberately did **not** add a badge for
`tt-local-generator-models-all`: it's a ~360 GB metapackage and a one-click copy command
for that is a footgun. The entry's description and `hardware` were stale too (said
QuietBox-only; the package supports Wormhole and Blackhole P150x4/P300x2).

**Gotcha for future visual checks:** headless Chrome's `--window-size=430,…` does *not*
emulate a mobile viewport — it lays out at ~800px and crops the image to 430. A screenshot
that looks like right-edge clipping at "mobile width" is usually that artifact, not a CSS
overflow bug. Verify by shooting at 800px and comparing.
