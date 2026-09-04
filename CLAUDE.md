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

### 2026-09-04 — tt-finetune entry, and SPARSE_LIMIT 120 → 70

Prompt: *"Let's add https://github.com/danielisraeli2409-jpg/tt-finetune to the awesome list
and include its latest release in the planet feed"*, then *"ok let's add it to make the
complete card. let's lower our sparse limit to 70 chars and see how ti goes?"*

**Entry.** `community` — personal account, no TT org, and `employee_search` finds no
matching Tenstorrent employee (Jeremy introduced it in `#devrel-private` as a community
project). `language: Python` despite GitHub reporting C++ by byte count: the C++ is the
bundled TT-XLA/TT-Metal runtime under `tt_finetune/_resident_bundles`, while every source
directory is Python. No `packages` — the README states outright it does not claim PyPI
publication, and the wheel installs from a release URL.

`github_meta.json` was updated by importing `fetch_github_meta`'s functions for this one
repo rather than running `main()`, which rewrites all 119 entries and would have buried
the change in unrelated star churn.

**Planet items written by hand.** No `ANTHROPIC_API_KEY`/`FOUNDRY_API_KEY` in the local
environment, so `summarize_releases.py` cannot run here. The three items were written to
the exact schema `main()` emits, following `summarize-release.prompt.yml`. Grouping then
did its job at render time: v0.2.0 (8/26), v0.2.1 (8/28), demo (8/29) chain into one card,
"3 releases · Aug 26 – Aug 29".

**SPARSE_LIMIT 120 → 70.** Measured rather than guessed: of the releases in
`github_meta.json` that the gate is the *only* thing blocking (11, after pre-release and
rename filters), five sit in [70, 120) and six have literally empty bodies. Nothing at all
falls in 1–69 in the current window, so 70 is a clean place to stand.

**The 70-char gate exposed a hole, and the fix went a different way than proposed.**
`zk4x/zyx v0.14.0` is 73 chars and its entire body is `**Full Changelog**:
https://github.com/zk4x/zyx/compare/v0.13.0...v0.14.0` — GitHub's auto-generated link and
nothing else. It clears 70 *only because the URL is long*. I proposed stripping URLs
before measuring; Taylor asked instead: *"When we see this Full Changelog and URL line
like this, can we ask our script/agent to crawl it and summarize from that?"* — which is
the better answer, because it turns a skip into a real item.

`body_defers_to_compare` + `parse_compare_url` + `fetch_compare_log` follow the link and
summarize the commit subjects. Deliberately mirrors the existing
`body_defers_to_changelog` → `fetch_changelog_section` pattern, and runs *after* it, since
curated notes beat a raw commit log whenever both exist.

Key decisions:
* **Only fires when the link is the *whole* body.** GitHub's generated "What's Changed"
  notes also end with a Full Changelog line, and those already have content — the check
  strips the pointer line and crawls only if what remains is itself sparse. Verified
  against all five newly-admitted releases: only zyx v0.14.0 crawls.
* **Merge commits dropped, duplicate subjects collapsed.** Working branches restate the
  same subject repeatedly — zyx v0.14.0 says "work on multi head attention" twice.
* **The sparse gate is applied to the commit subjects alone, before the framing header is
  added.** The header is ~200 chars, so gating the finished string would carry a
  single-`bump`-commit release straight through. This is the one non-obvious bit; there is
  a test pinning it.
* **The header tells the model these are raw commit messages, not curated notes.** Left
  implicit, summaries of a commit log drift into describing it as a polished release.
* Best-effort throughout: any API failure returns None and the release falls back to being
  skipped, never published from nothing.

Result on the real release: 73 chars of URL → 835 chars of genuine commit log. The
subjects are rough ("deinit", "licence", "cleanup") so the summary will be modest — but
sourced rather than invented, which was the whole point.

**Gotcha while writing the tests:** three of my own commit subjects in the
merge-filtering test summed to 67 chars, so it failed on the sparse gate rather than on
merge filtering. When writing fixtures for this path, keep subject text comfortably over
`SPARSE_LIMIT` unless sparseness is what you are testing.
