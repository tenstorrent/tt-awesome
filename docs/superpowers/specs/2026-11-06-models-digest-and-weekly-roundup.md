# Models job: PR digest, readable blurbs, weekly roundup

**Date:** 2026-11-06
**Status:** Approved in chat (Taylor, 2026-11-06). The call on LLM use: one
call per weekly roundup, none anywhere else.

## Problem

The nightly models job (`.github/workflows/nightly-models.yml`) rebuilds
`src/_data/models.json` and opens a PR whose body is a fixed paragraph. A
reviewer has to read a 1 MB JSON diff to learn what the run changed. The
same job produces the model blurbs on the Models pages by cutting the card
description at 240 characters and appending an ellipsis. Card descriptions
are long single sentences (median 776 characters across the 31 bundle cards
read on 2026-11-06), so 32 of 148 blurbs end mid-clause with "…". And the
Planet page never hears about models at all: a model landing in
tt-inference-server or as a tt-model bundle produces no Planet item.

## Goals

1. The models PR body says what changed: models added and removed, status
   changes, models entering the release spec, new and withdrawn bundles,
   kind and hardware changes, the spec release bump. Each run's digest is
   also posted as a PR comment, because the PR branch is reused across runs.
2. Blurbs are complete sentences. No ellipsis, ever.
3. Every Thursday the job publishes one Planet item summarizing the week in
   models, across both sources.

## Non-goals and anti-goals

- No LLM call for the PR digest or the blurbs. Both are mechanical. The
  roundup paragraph is the only model-written text, one call per week, and
  the item still ships (with a mechanical paragraph) when the call fails.
- No new Planet item type, badge, or template change. The roundup is a
  `type: "article"` item.
- No hand edits to `models.json`. It is regenerated nightly from the
  manifests; a better blurb rule rewrites all 148 on the next run.
- The build job keeps running no trusted code with a secret: the roundup
  step, which needs the LLM credential, runs in the `pr` job only.

## Design

### `scripts/models_diff.py` (new, library plus CLI)

`diff_models(old, new)` compares two `models.json` documents and returns:

| key | content |
|---|---|
| `spec` | old and new `{release, commit}` |
| `added` | models in new only: id, name, source, kind, status, hardware, bundle owners |
| `removed` | models in old only |
| `status` | models whose best status changed, including `None → X` |
| `entered_spec` | models that were bundle-only and are now in the release spec |
| `bundles_added` / `bundles_removed` | (model name, bundle repo) pairs |
| `kind` | models whose kind changed |
| `hardware` | models that gained a hardware name |
| `unreadable` | bundle repos that became or stopped being unreadable |

`render_pr_body(diff)` writes the nightly digest as markdown: a `###`
heading per non-empty section, one bullet per change, then the boilerplate
from `.github/pr-templates/models.md` under the
`<!-- tt-awesome-digest-boilerplate -->` marker, so the comment step can
strip it exactly as `nightly.yml` does. When nothing changed it writes
nothing and the workflow falls back to the template.

`build_roundup(diff, week_end)` returns the Planet item for the week ending
`week_end` (a Thursday). The title counts the two sources: "Models this
week: 8 new on tt-inference-server, 7 new tt-model bundles". The URL is the
Models page with a per-week fragment,
`https://docs.tenstorrent.com/tt-awesome/models/#week-2026-W45`, which
makes the item unique and lets the planet dedup by URL. The description is
the paragraph from `request_roundup_paragraph` or, when that returns "",
`fallback_paragraph(diff)`: one mechanical sentence per section, with model
names as links to their pages. The model-written paragraph gets the same
linking pass: the first mention of each changed model's name becomes a
markdown link to `models/<id>/`.

`request_roundup_paragraph(manifest)` is the one LLM call. It renders
`prompts/models-roundup.prompt.yml` through `llm_client.complete` with a
plain-text manifest of the diff (capped at 40 lines) and returns the reply
or "" on any failure, like `pr_digest.request_lede`. It is not called when
the diff is empty: a week with no changes produces no item.

`write_roundup(item, feeds_path)` inserts the item into `planet_feeds.json`
in `dateISO` order and skips when the URL is already present, so a rerun or
a manual dispatch on the same week cannot publish twice.

CLI:

```
models_diff.py pr-body --old OLD --new NEW --out pr-body.md
models_diff.py roundup --old OLD --new NEW --week-end YYYY-MM-DD [--dry-run]
```

### Workflow changes (`nightly-models.yml`, `pr` job)

1. `actions/checkout` with `fetch-depth: 0`. The repo is 24 MB and 367
   commits; the roundup needs `models.json` as of a week ago, read with
   `git show $(git rev-list -1 --before="7 days ago" HEAD):src/_data/models.json`.
2. The artifact is downloaded to `new/`, not over `src/_data`, so the
   committed file is still on disk as the "old" side of the nightly diff.
3. `models_diff.py pr-body` writes `pr-body.md`.
4. On Thursdays (`date -u +%u` is 4), or when the new `roundup` dispatch
   input is true, `models_diff.py roundup` runs with the week-old file as
   the old side and the artifact as the new side. The step has the LLM
   credential (`FOUNDRY_API_KEY`, same wiring as `nightly.yml`) and is
   skipped when the credential is absent.
5. `cp new/models.json src/_data/models.json`.
6. `create-pull-request` takes `body-path: pr-body.md` and adds
   `src/_data/planet_feeds.json` to `add-paths`.
7. A comment step posts the run's digest on the PR, copied from
   `nightly.yml`.

The same-day order matters: the nightly PR for Thursday carries both the
models.json refresh and the roundup item, so one merge publishes both.

### Blurbs (`build_models_data.py`)

`first_sentence` is replaced by `blurb(text, n=240)`:

1. Clean markdown as before and take the whole first sentence (split on
   `.`, `!` or `?` followed by whitespace and a capital letter or digit, so
   "0.17 x 0.17 m voxels" and "v5.0" do not end a sentence).
2. If it fits in `n`, use it.
3. Otherwise drop every parenthesized group (nested groups included) and
   tidy the punctuation. If that fits, use it, with a period.
4. Otherwise cut at the last `: `, `; ` or `, ` before `n` (falling back to
   the last space when that boundary is in the first half), strip trailing
   punctuation, and end with a period.

Measured on the 24 bundle cards whose first sentence exceeds 240 characters:
every output is a complete sentence. Example: "BEVFormer-small, a
59.5M-parameter camera-only 3D detector, run on six 1280x736 network inputs
through the graph of the TensorRT export Autoware deploys."

Spec-only models name their hardware instead of counting it: "Runs through
tt-inference-server on WH LoudBox/QuietBox and Galaxy; status Experimental."
followed by the bundle count sentence as before.

The helpers move into a `# ---- Card blurbs` block so
`tests/test_models_blurbs.py` can exec it the way `test_models_perf.py`
execs the speed block.

### Tests

- `tests/test_models_diff.py`: diff sections on hand-built documents;
  `render_pr_body` empty and non-empty; `build_roundup` title, URL,
  fallback paragraph, link pass on a model-written paragraph; `write_roundup`
  ordering and URL dedup; `request_roundup_paragraph` degrades to "" with
  `llm_client.complete` monkeypatched to raise.
- `tests/test_models_blurbs.py`: the four rule branches, the sentence
  splitter on decimals and version numbers, and a regression over the 24
  real card descriptions saved as a fixture, asserting no "…" and a
  terminal period.
- The JS filter tests already cover an `article` item rendering.

## Left to the builder

- Exact wording of the roundup prompt. It must forbid headings and bullets,
  ask for 3 to 5 sentences, name models and both sources, and refuse hype.
- Whether to show the roundup's "New:" link list after the paragraph when
  the model-written paragraph names fewer than half the new models. Default:
  yes, as one sentence.
