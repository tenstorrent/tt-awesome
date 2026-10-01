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
npm run generate                    # README + data.json; data.json must exist before the build
npm run build                       # must precede the JS suites
node tests/test_entry_pages.js      # build-output assertions (incl. data.json present + fresh)
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

### 2026-09-07 — vLLM TT plugin: blog link, planet item, and planet-card precedence

Prompt: *"Let's make sure the new TT vllm plugin is listed in tt-awesome. Official. It's a
big deal! Then get this blog post linked from its entry and get the blog post itself into
the TT planet feed. https://vllm.ai/blog/2026-09-07-vllm-tt-plugin"* — then, on being shown
a workaround: *"the item should be tagged as blog article. we shouldn't incite side effects
because of that. we don't want this as a community feed. just an article that ends up in
planet too"*.

**The entry already existed** — `entries/ai-models/vllm-tt-plugin.json`, added 2026-08-05
in #153, already `official` with an accurate description. So the work was the blog post
plus a correctness pass, not a new entry.

**The collision.** `planetItems` treats any link in `ARTICLE_TYPES` (article, lesson, paper,
talk, video, demo) as an entry-derived planet card dated `entry.added_at`, and it claimed
the URL in `seenUrls` *before* external feeds were processed — so typing the blog link
`article` produced one card dated **2026-08-05** titled "vllm-tt-plugin", and silently
swallowed the hand-written planet item carrying the real headline and date.

My first pass dodged this by typing the link `website` (the `cloud-native-support` shape,
which does exactly that). Taylor rejected the workaround: the link *is* a blog article, and
the type shouldn't be bent to steer rendering. Correct call — the fix belonged in the
render logic.

**The fix: a published planet item outranks the entry-derived card.** An entry card is a
fallback — it can only date itself `added_at` and title itself after the project. When
planet_feeds.json carries the real headline and publication date for that exact URL, the
entry steps aside. Two constraints make it safe:

* **All-or-nothing.** An entry bundling a talk with its recording is ONE event (that's the
  whole point of "one card per entry, not per link"), so a feed item covering only *part*
  of an entry must not split it into two cards. The entry steps aside only when **every**
  one of its article links is already published; partial coverage keeps the bundle and
  claims every URL exactly as before. Existing **test 20d** pins this and caught the first,
  too-blunt version of the change, which dropped covered links individually.
* **`approved` only.** Unapproved items are held for human review and never render, so they
  must not claim a URL away from the entry card — that would erase the link from the planet
  entirely.

Push order is safe to reason about because `planetItems` date-sorts everything at the end;
source order only ever decided dedup precedence, never display position.

**It fixed a live bug.** Exactly one collision existed in the current data: the arXiv
spectral-element paper, whose entry has **no `added_at`** (it's the standing `validate.py`
WARN). The entry card was winning with the `|| "1970-01-01"` fallback, so the paper rendered
under a **"January 1970"** month heading at the very bottom of the planet page. It now sits
at its real date, Aug 24 2026, with its real title. Measured before changing anything —
worth doing again before touching this precedence, via the entry-link/feed-URL intersection.

**Also corrected while verifying:** `hardware` was `[wormhole, blackhole]`. The README
documents `MESH_DEVICE` values `N150`/`N300`/`T3K`/`TG`/`BH-Galaxy` and names QuietBox
explicitly, so `quietbox` and `galaxy` were added. Sourced from the repo README rather than
the blog post alone.

**Deliberately did *not* add vllm.ai to `COMMUNITY_FEEDS`** (Taylor confirmed: "we don't
want this as a community feed"). `fetch_community_feed()` does no topic filtering — the
comment there says to list only feeds whose *whole* output is on-topic. The vLLM blog is
overwhelmingly non-Tenstorrent, so it would land a steady stream of unapproved items in the
review queue. Hand-curated instead, like jasondavies.com.

Since the link is now honestly `article`, the post also flows into `articles.xml` and
`feed.json` — that feed is entry-curation keyed to `added_at`, which is the right home for
"a resource this entry cites", while the planet item is the dated news card.

`github_meta.json` was left alone (stars 10, `updatedAt` 2026-09-04 vs. a live push today).
Nightly CI owns that file; hand-editing it only creates churn.

### 2026-09-15 — three Medium posts from Arni Steingrimsson's QuietBox series

Prompt: *"Let's add https://medium.com/@arnis.us/780-tokens-per-second-on-the-same-tenstorrent-quietbox-a50b2f4b642a
as a planet feed item. Look for other posts by the same author too that are relevant to
tenstorrent. do not add a planet feed subscription"*

**Medium blocks WebFetch and curl (403). The author's RSS feed does not.**
`https://medium.com/feed/@arnis.us` returns 200 with `content:encoded` carrying the *full*
post body — 7k–34k chars of text, not a truncated excerpt. That is how all three summaries
were sourced. Worth remembering for any future Medium item: skip the article URL, fetch
`medium.com/feed/@<handle>` and parse `content:encoded`.

The feed also answered the "other posts" half of the prompt exhaustively: it carries exactly
four items, and all four are Tenstorrent work. One ("First Pass at World Model on Tenstorrent
Hardware", Aug 3) was already curated in #149, so three were new:

* **780 Tokens per Second on the Same Tenstorrent QuietBox** (Sep 14) — speculative decoding,
  SRAM-resident draft model, ~400 → ~780 tok/s.
* **400 Tokens per Second on a $12,000 Tenstorrent QuietBox** (Aug 31) — the baseline for the
  above: Marco-Nano-Instruct at 397.7 tok/s, batch one, residency-versus-staging argument.
* **Building on a Frozen World Model** (Aug 4) — part two of the V-JEPA series; imitation vs.
  RL on the frozen encoder, plus the "clonability" result.

Each summary names the author's own caveats, because all three posts state them plainly and a
summary that dropped them would oversell the numbers — the draft tuned on the same prompt it
was measured on, the excluded prefill/warmup, the retracted 509-pipe demo video.

**`affiliation: "community"`, matching the existing item.** `employee_search` returns no
Tenstorrent employee by that name — he is an outside developer working on hardware he owns.
Not `affiliated`: that value is for TT staff blogging (dev.to/mando222, tsingletarytt.github.io).

**No feed subscription added** (Taylor: "do not add a planet feed subscription"). The right
call independent of the instruction: `fetch_community_feed()` does no topic filtering, and
while all four current posts are on-topic, a personal Medium account is not a whole-output-on-
topic source the way a project blog is. Hand-curated instead, like the vllm.ai post and
jasondavies.com. Items are written to the exact schema `fetch_planet_feeds.py` emits and keyed
by URL, so `load_existing`/`merge_items` preserve them on every nightly run.

Sorted into place newest-first the same way `merge_items` does — the file was already fully
sorted by `dateISO` descending, so the diff is 42 pure insertions with no reordering churn.

### 2026-09-23 — tenstorrent/skills and tenstorrent/tt-transformers

Prompt: *"Make sure we are tracking https://github.com/tenstorrent/skills and the new
tenstorrent/tt-transformers please"*

Neither was listed. Added `agents/tenstorrent-skills.json` (id avoids the bare, ambiguous
`skills`) and `ai-models/tt-transformers.json`, both `official`. Everything was taken from
the repos themselves. The skills README still says "restricted visibility", but both repos
are PUBLIC; that was checked with `gh repo view` and an anonymous 200.
tt-transformers hardware comes from `SUPPORT.md` (N150/N300/T3K plus P150/P150_X4, so
`quietbox` too, but no Galaxy geometry). It is not on PyPI (404) and installs from a
checkout, so the entry has no `packages`.

**No planet items.** Neither repo has any releases or tags yet. Nightly
`fetch_github_meta` → `summarize_releases` will pick up the first release on its own now
that the entries exist. `github_meta.json` was updated for just these two repos by
importing the fetcher's functions, the same way as for tt-finetune.

### 2026-09-28 — 10 candidates from investor-analysis, plus two stale-entry fixes

Prompt: *"Let's look at reports in ~/code/investor-analysis for new candidates to add to
tt-awesome, then create a new branch to contain them"*

**Where the candidates live.** Not in `reports/` so much as the database. The worklist is
`discord_shared_projects` in `~/code/investor-analysis/data/investor_analysis.db`
(`should_be_in_tt_awesome = 1` or unjudged `tier='candidate'`; note `database/investor_analysis.db`
is a 0-byte decoy), plus the `keep` verdicts in `data/awesome_candidate_verdicts.json` from the
code-search crawl. I cross-checked against the *current* entry URLs rather than the DB's
`tt_awesome_id`, which lags. That gave 86 distinct unlisted candidates. About 30 fell on metadata
alone: verbatim mirrors of TT repos, forks of polaris/blackhole-py, 2024 intern tools, internal
hackathon/CI repos, coursework. The remaining ~55 were read at the source by five parallel agents
(models, engines, tools, research, Hugging Face).

**Result: 20 new entries** (after the two cuts below). The bar was TT-specific working code a reader can run or learn from,
and for model bundles, published measurements. Folded rather than duplicated: daisytuner's two
case studies became one `docc` entry, and yiding's llama.cpp fork (a slimmed derivative with P150
TP) became a link on `llama-cpp-metalium`.

**Then a freshness cut.** Taylor: *"remove these ones that are from april or before."* Seven
drafted entries were dropped because their last push was on or before 2026-04-30: corsix
wormhole-vector, tt-fetch, autoresearch-tenstorrent, the k8s device plugin, tt-train-roofline,
tt-metal-nix and tt-lang-kernels. The SwiftNPU code-repo link (last push Apr 29) was reverted too.
The measure is GitHub `pushed_at`, which counts a push to any branch; for fork entries whose TT
work lives on a branch, check that branch's last commit instead. agillm-3 stayed, because its
primary GitHub repo was pushed May 4 even though its HF checkpoints date from March.

**Two stale entries found along the way:**
* `tt-kernel-package-manager` → the repo was renamed `tenstorrent/tt-model-manager` (CLI
  `tt-model`); the old URL only redirects. **The id was kept on purpose.** It's the permalink, and
  investor-analysis joins on `tt_awesome_id`. Name, URL, description and links changed.
* `wallabmc` moved to `tenstorrent-riscv-software`.
* Both old `github_meta.json` keys were dropped so the moved repos don't render twice.

**First Hugging Face entries.** Five entries are HF repos (`website` links). These are mostly
tt-model *recipe bundles* (code + patches + launch config, weights referenced upstream), so they
are labelled "Model bundle on Hugging Face", never "Weights". HF repos churn: two candidates
(`mando2222/Qwen3-32B-blackhole`, `vibethinker-3b-P150`) had already been deleted and
republished under `-v51` names. That's a case for a link-check in nightly CI.

**Heads-up on releases.** `sglang-jax` and `vllm.cpp` are general-purpose upstreams with their
own releases (5 and 4 in the current window), so the nightly summarizer will put them on the
planet, the same as the dstack/nvtop/zyx precedent. If that proves noisy, the fix belongs in
`summarize_releases.py` as a per-entry opt-out, not in bending the entry.

**Affiliation came from Glean, but `employee_search` misses people.** It missed Suhail Alnahari
(tt_symbiote, whose commits are from a tenstorrent.com address, so `affiliated`) and Martin
Chang (kept `community` to match his three existing kernel entries, although his backend docs
say he joined TT). Commit email and Glean doc ownership are better evidence than a directory miss.

**Rule for tt-model bundles: catalog-listed only.** Taylor: *"let's only have confirmed catalog
listings for tt-model manager models."* A tt-model bundle earns an entry only if its HF repo
carries the `tt-model-catalog` tag, which is the author's explicit `tt-model publish` opt-in. It
also means the bundle passed tt-model's card check (`card.performance` + `card.limitations`)
and is current enough for `tt serve` to accept. Check it live with
`curl -s https://huggingface.co/api/models/<ns>/<name>` and look at `tags`. A bundle is
recognisable by `tt_kernel_manifest.json` / `tt-model.yaml` in `siblings`.
Dropped under this rule: `gemma-4-26b-a4b-qb2`, a `tt-kernel`-era bundle that was never
listed, and the mando2222 vision/Q4-KV variant link on `qwen38-27b-dflash2-p300x2`. The rule
does *not* cover HF repos that aren't bundles at all: `openjev-p300x2` (patches + results) and
`agillm-3-tenstorrent` (training checkpoints) stay.

The catalog had 58 bundles on 2026-09-28, three weeks in, and 30 of them are changh95's, so
hand-listing every bundle won't scale. Discussed but not yet built: a `tt-model` package type
rendering `tt serve <ns>/<name>` (tt-cli is the consumer front door for both catalog and
community models), and a nightly generated bundles page from the catalog tag.

**`tt-model` install type (same session).** Taylor: *"go ahead and build the install type"*.
A `packages` entry `{"type": "tt-model", "name": "<ns>/<bundle>"}` renders `▶️ tt serve
<ns>/<bundle>` as a copyable badge linking the Hub, plus a note that it runs with tt-cli (`uv tool
install tenstorrent`) and is a community bundle. The command is tt-cli's `tt serve`, not
`tt-model serve`. tt-cli is the consumer front door for both released and community models, and
hands bundle ids to tt-model-manager, which pulls on first use. So one line is a real run command,
checked in tt-cli's `commands/serve.py`. `validate.py` requires a bare HF repo id (no URL, no
`@rev`), because a pasted URL would render an unrunnable command. The catalog-only rule is
documented in CONTRIBUTING.md next to the package table. It is **not** machine-checked: validate
is offline, so a nightly tag check is the natural follow-up.

**Coverage gap, measured:** `entry-card-body.njk` has two package blocks. The first sits inside
`{% if entry.releases %}`, the second is `packages and not releases`. The new
`test_entry_pages.js` assertion goes red when the tt-model branch is removed from the second
block, and stays green when it is removed from the first. That's because no tt-model entry has
GitHub releases (bundles live on HF), so the first block is unreachable with today's data. It
becomes reachable only if a GitHub-repo entry with releases gains a tt-model package.

**Planet video:** "Tenstorrent Tensix Core Explained" by Jake (@jakedvs), published 2026-09-27,
hand-added as an approved `community` YouTube item. Title, date and description came from
YouTube's oEmbed and the watch page's `uploadDate`/`shortDescription`. There is no channel
subscription, same as the other hand-curated items.

**Review cut to 10 (PR #228).** Taylor kept torpedo, tt-blackhole-fan-win, vllm-cpp,
tt-symbiote, kimi-linear, deepseek-v41-flash, openjev-p300x2, museglimmer, granite-4-ttnn and
blackhole-qwen3-8-27b, and passed "for now" on the other ten: sglang-jax-tt, llama-cpp-metalium,
docc, tenstorrent-open-me, bhtop, tenstorrent-homebrew-tools, tt-qwen-3-8-flash-next,
qwen36-a3b-blackhole, qwen38-27b-dflash2-p300x2 and agillm-3-tenstorrent. The drafts are still in
git history (commit 5c4d36c) if any come back. The `tt-model` install type stays, but it has
**no users** now that both catalog bundles are out, so its build-output assertion is vacuous
until one returns. The two stale-entry fixes and the Planet video stay.

### 2026-10-01 — tt-lab entry and its public-debut planet card

Prompt: *"Add a colorful, exciting entry for https://github.com/tenstorrent/tt-lab and its
first release into the planet feed"*

**tt-lab has no GitHub release.** `/releases` and `/tags` are both empty (checked via the API,
not the web UI). The "first release" is the repo going public: the initial source drop landed
9/28 and the "Prepare documentation and legal files for public release" commit on 9/30 at
20:47 UTC, with Matt Craighead announcing it in Slack that evening. So the planet item is a
hand-written `type:"release"` whose URL is the **repo itself**, dated to that commit, with
`projectId` set explicitly (the summarizer's backfill only matches `/releases/` URLs). It
cannot collide with a future real release: that one arrives with a `/releases/tag/` URL and
a `tt-lab <tag>` title, so neither the URL dedup nor `release_key()` sees a match.

**Why not a `lesson` link for the ttsim walkthrough.** The ttsim README has a public "Running
an LLM with tt-lab" section worth linking. Typing it `lesson` would make `planetItems` emit
an entry-derived card dated `added_at` — a second launch card next to the hand-written one.
It is `website` with a label instead; the planet gets exactly one card.

**Numbers were taken only from public sources.** The README publishes 3.83 ms/token of
*device command time* (20b, 32 tiles) and says outright it is not end-to-end throughput, so
the copy says "device time per token" rather than converting it to tok/s. The ttsim README
supplies "roughly 12,000 lines of C++". Internal Slack carried a headline 120b tok/s figure;
it is not in the repo, so it is not on the site.

`featured: true` is what "colorful, exciting" maps to on this site — the ★ star on the card
and top-of-tier placement in README and the home showcase. Easy to flip off if it crowds
something out. `hardware` is `blackhole`/`quietbox`/`ttsim`: the README is explicit that the
backend is Blackhole-only and the dev machine is a QuietBox 2 with two P300 boards.

`github_meta.json` got the one record via `fetch_repo`, inserted in the slot `main()` would
give it so the diff is a pure 4-line insertion. README regenerated with `generate_readme.py`.

**Follow-up (same day): tt-operator is back.** Taylor: *"yes let's add tt-operator back in.
nothing else for now"*, after a sweep of `~/code/investor-analysis` for candidates new since
9/28. The entry was first added in #99 (2026-07-01) and dropped in 7d3d057 because the repo had
gone private; it was re-opened for public release on 2026-09-17 (`ospo/public-release-prep`).
Restored under the **same id** (permalink, and investor-analysis joins on it), with the
description rewritten from today's README (OCI chart, DRA driver, kind dev loop, v0.3.0) and
links to the two public component repos (`tt-k8s-driver-manager`, `tt-dra-driver`;
`tt-telemetry` and `tt-fabric-manager` are still internal). `added_at` is today, so the
new-entries feed announces the re-listing. `cloud-native-support` gets its `related` link back
and the old v0.1.0 planet item its `projectId`.

`summarize_releases.py` has **no date window**: with the entry restored, the next nightly will
summarize every un-published release `fetch_releases` returns — v0.3.0, v0.2.0, and the June
v0.0.4/v0.0.5 — at their real dates. The June ones chain with v0.1.0 into one grouped card.

Sweep result, for the record: the Discord share table (refreshed 9/30) held three genuinely
new candidates — tt-operator, `ndaly/Mistral-Small-4-119B-2603-tt-p300x2` (catalog-tagged,
TT PM, would be the first `tt-model` install-type user) and `Adraca/mamba2-tt-bringup`
(Mamba-2 SSD on TTNN, confirmed on N150, no license file). Taylor passed on the latter two
for now. The code-search verdicts file is unchanged since 9/1.

**`data.json` untracked (same PR).** Copilot's review flagged the checked-in `data.json` as
stale, which it was — 133 entries dated 8/5 against 169 live. But the live file was never built
from it: `deploy.yml` regenerates it before every build, and no entry PR since #153 had
committed it. Taylor: *"add it to this PRs scope"*. So rather than regenerate-and-commit (which
would drift again by the next PR), it is now a build output: `git rm --cached`, gitignored,
`build-check.yml` gained the same generate step `deploy.yml` already had, and
`test_entry_pages.js` asserts `_site/data.json` exists *and* `meta.total_entries` equals the
entries this build rendered. Eleventy silently skips a passthrough whose source is missing, so
without that assertion a dropped generate step builds green and serves nothing. Watched it fail
both ways (stale copy on disk → "133 vs 171"; no copy → "missing") before it went green.
`.github/CI.md` had the opposite claim ("not regenerated by CI") and was corrected.
