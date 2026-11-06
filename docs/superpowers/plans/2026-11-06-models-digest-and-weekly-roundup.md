# Models digest, blurbs and weekly roundup: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The nightly models job explains its PR, writes blurbs that are whole sentences, and publishes a weekly Planet roundup of models on Thursdays.

**Architecture:** One new library `scripts/models_diff.py` computes a change set between two `models.json` documents and renders it two ways: a mechanical PR body for the nightly run, and a Planet item for the week (one LLM call for its paragraph, with a mechanical fallback). The blurb rule lives in `scripts/build_models_data.py`. The `pr` job of `nightly-models.yml` wires both.

**Tech Stack:** Python 3.11 stdlib, `scripts/llm_client.py` for the one model call, pytest locally (Python tests are not in CI), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-06-models-digest-and-weekly-roundup.md`

## Global Constraints

- No LLM call anywhere except `request_roundup_paragraph`; none when the week's diff is empty.
- The LLM credential is only available to the `pr` job; the `build` job (which runs tt-model, downloaded code) never sees it.
- No ellipsis ("…" or "...") may end a blurb. Blurbs end with `.`, `!` or `?`.
- Roundup items are `type: "article"`, `approved: true`, URL `https://docs.tenstorrent.com/tt-awesome/models/#week-<ISO year>-W<ISO week>`.
- `models.json` is never hand-edited; it is regenerated nightly.
- Comments explain why, per repo style (see the existing scripts).

## Review Focus

1. A model that leaves the spec but keeps a bundle (`inSpec` True → False): `diff_models` reports it under `status` (X → None), not as removed. Test in Task 2.
2. A week-old `models.json` that predates a schema change (missing `unreadableBundles` or `hardware` on a model): `diff_models` treats missing keys as empty, never raises. Test in Task 2.
3. A model name that is a prefix of another ("Qwen3.5-27B" and "Qwen3.5-27B-Instruct"): the link pass links whole names only, longest first. Test in Task 4.
4. A card description whose first sentence ends in a decimal or version ("v5.0 planner. Six…"): the splitter does not end the sentence at "5." Test in Task 1.
5. A rerun on the same Thursday (dispatch after the scheduled run): `write_roundup` sees the URL already present and writes nothing. Test in Task 4.

---

### Task 1: Blurbs that are whole sentences

**Files:**
- Modify: `scripts/build_models_data.py` (replace `first_sentence`, lines 315–318; the spec summary at line 474)
- Create: `tests/test_models_blurbs.py`
- Create: `tests/fixtures/model_card_descriptions.json` (the 24 long descriptions from the 2026-11-06 Hugging Face read; a list of strings)

**Interfaces:**
- Produces: `blurb(text: str | None, n: int = 240) -> str` and `split_first_sentence(text: str) -> str`, both inside a block that starts with the comment line `# ---- Card blurbs` and ends before `\n# A decision model` so the test can exec it the way `tests/test_models_perf.py` does for the speed block.

- [ ] **Step 1: Write the failing tests**

```python
def test_short_first_sentence_is_kept_whole(): assert blurb("Short one. Then more.") == "Short one."
def test_decimal_and_version_do_not_end_the_sentence():
    assert split_first_sentence("Planner v5.0 on 0.17 m voxels. Next.") == "Planner v5.0 on 0.17 m voxels."
def test_parentheticals_are_dropped_when_too_long():
    long = "BEVFormer-small, a detector (" + "x" * 300 + "), run on six inputs. Next."
    assert blurb(long) == "BEVFormer-small, a detector, run on six inputs."
def test_clause_cut_ends_with_a_period():
    long = "Name, a thing: " + ", ".join(f"part{i}" for i in range(80)) + ". Next."
    out = blurb(long); assert len(out) <= 241 and out.endswith(".") and "…" not in out
def test_real_cards_never_end_in_an_ellipsis():
    for d in json.load(open(FIXTURE)):
        out = blurb(d); assert not out.endswith("…") and out[-1] in ".!?" and len(out) <= 241
def test_markdown_is_stripped(): assert blurb("**Bold** [link](https://x) `code`. Next.") == "Bold link code."
```

- [ ] **Step 2: Run them; expect `KeyError: 'blurb'` (block not found)**

Run: `python3 -m pytest tests/test_models_blurbs.py -q`

- [ ] **Step 3: Implement the block in `scripts/build_models_data.py`**

Sentence split: `re.search(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", t)`. Parenthesis removal walks characters with a depth counter, then collapses whitespace and removes space before `,.;:` and doubled commas. Clause cut: last of `": "`, `"; "`, `", "` within `t[:n]`, falling back to the last space when that index is below `n // 2`; strip trailing ` ,;:` and append `.`. Replace the call site `blurb=first_sentence(card.get("description"))` with `blurb=blurb(...)`.

- [ ] **Step 4: Reword the spec summary at line 474**

`f"Runs through tt-inference-server on {names}; status {m['status']}."` where `names` joins the sorted hardware names with ", " and a final " and ". Keep the bundle-count sentence.

- [ ] **Step 5: Run tests; expect PASS. Also `python3 -m pytest tests/test_models_perf.py -q` still PASS.**

- [ ] **Step 6: Commit** `feat(models): blurbs are whole sentences, never cut with an ellipsis`

---

### Task 2: `diff_models`

**Files:**
- Create: `scripts/models_diff.py`
- Create: `tests/test_models_diff.py`

**Interfaces:**
- Produces: `diff_models(old: dict, new: dict) -> dict` with keys `spec` (`{"old": {...}, "new": {...}}`), `added`, `removed`, `status`, `entered_spec`, `bundles_added`, `bundles_removed`, `kind`, `hardware`, `unreadable`. Each list is sorted by model name. `added`/`removed` hold `{"id","name","source","kind","status","hardware","owners"}`; `status`/`kind` hold `{"id","name","old","new"}`; `bundles_*` hold `{"model","id","repo"}`; `hardware` holds `{"id","name","added":[...]}`; `unreadable` holds `{"now_unreadable":[...],"now_readable":[...]}`; `entered_spec` holds `{"id","name","status"}`. `is_empty(diff) -> bool` is true when every list is empty and the spec release is unchanged.

- [ ] **Step 1: Write the failing tests** (fixtures built by a `model(id, **kw)` helper with the real key set: `id,name,source,kind,status,inSpec,hardware,bundles[{repo,owner,updated}]`)

```python
def test_added_and_removed_models()
def test_status_change_and_entering_spec()      # inSpec False→True lands in both status and entered_spec
def test_leaving_spec_is_a_status_change_not_a_removal()   # Review Focus 1
def test_bundle_added_and_removed_on_an_existing_model()
def test_kind_and_hardware_changes()
def test_missing_keys_in_the_old_document_are_empty()      # Review Focus 2: old lacks hardware, unreadableBundles
def test_spec_bump_alone_is_not_empty_but_no_lists_is_empty()
```

- [ ] **Step 2: Run; expect `ModuleNotFoundError: models_diff`**

- [ ] **Step 3: Implement `diff_models` and `is_empty` in `scripts/models_diff.py`** with the module docstring explaining the two consumers (nightly PR body, weekly roundup).

- [ ] **Step 4: Run; expect PASS**

- [ ] **Step 5: Commit** `feat(models): diff two models.json documents`

---

### Task 3: PR body

**Files:**
- Modify: `scripts/models_diff.py`
- Create: `.github/pr-templates/models.md` (the current `body:` text from the workflow, preceded by the line `<!-- tt-awesome-digest-boilerplate -->`)
- Test: `tests/test_models_diff.py`

**Interfaces:**
- Produces: `render_pr_body(diff: dict, boilerplate: str) -> str` returning "" when `is_empty(diff)`; otherwise `### ` headings in this order and wording: "🆕 N new models", "➖ N models removed", "📈 N status changes", "📦 N new bundles", "📦 N bundles withdrawn", "🔁 N kind changes", "🖥 N hardware additions", "⚠ Unreadable bundles", then "tt-inference-server spec: 0.25.0 → 0.26.1" as a line when the release changed, then the boilerplate. Bullets: added `- **Name** (source, kind, status) — hardware list`; status `- **Name**: Functional → Complete`; bundles `- **Name**: owner/repo`.
- Produces: `write_pr_body(diff, out: Path, template: Path) -> bool` (writes, returns True; writes nothing and returns False when empty).

- [ ] **Step 1: Write the failing tests**

```python
def test_render_pr_body_is_empty_for_no_changes()
def test_render_pr_body_sections_and_boilerplate_marker()   # headings present only for non-empty sections; marker line present once; spec line present
def test_write_pr_body_leaves_no_file_when_empty(tmp_path)
```

- [ ] **Step 2: Run; expect AttributeError on `render_pr_body`**
- [ ] **Step 3: Implement; create the template file**
- [ ] **Step 4: Run; expect PASS**
- [ ] **Step 5: Commit** `feat(models): nightly PR body lists what the refresh changed`

---

### Task 4: Weekly roundup item

**Files:**
- Modify: `scripts/models_diff.py`
- Create: `prompts/models-roundup.prompt.yml`
- Test: `tests/test_models_diff.py`

**Interfaces:**
- Consumes: `llm_client.complete(prompt_name, variables, *, anthropic_model, anthropic_api_key, github_token, foundry_api_key)`.
- Produces:
  - `week_fragment(week_end: date) -> str` → `"week-2026-W45"` (ISO calendar).
  - `roundup_title(diff) -> str` → `"Models this week: 8 new on tt-inference-server, 7 new tt-model bundles"`; a zero count is omitted; when both are zero: `"Models this week: N changes"` with N the total bullet count.
  - `build_manifest(diff, cap: int = 40) -> str` plain text, one line per change, truncated with a final `… and N more` line.
  - `request_roundup_paragraph(manifest, *, anthropic_api_key="", github_token="", foundry_api_key="") -> str`, "" on any exception or empty reply, leading heading stripped (reuse `pr_digest._LEADING_HEADING_RE`).
  - `fallback_paragraph(diff) -> str`: one sentence per non-empty section, names joined with ", " and " and ".
  - `link_models(text, models: list[dict]) -> str`: first whole-word mention of each model `name` becomes `[name](https://docs.tenstorrent.com/tt-awesome/models/<id>/)`, longest names first; never inside an existing link.
  - `build_roundup(diff, week_end: date, paragraph: str, now: datetime) -> dict` → the planet item: `type "article"`, `source "models-roundup"`, `approved True`, `title`, `url`, `description` (linked paragraph, plus the sentence `New: A, B and C.` when the paragraph names fewer than half of `added`), `date` = week_end ISO, `dateISO` = now in `%Y-%m-%dT%H:%M:%SZ`, `label "Models this week"`, `projectName "Models"`, `projectId None`, `affiliation "official"`.
  - `write_roundup(item, feeds_path: Path) -> bool`: insert in `dateISO` descending order; False when the URL is already present.

- [ ] **Step 1: Write the failing tests**

```python
def test_week_fragment_uses_iso_week(): assert week_fragment(date(2026, 11, 5)) == "week-2026-W45"
def test_title_counts_both_sources_and_omits_zero()
def test_fallback_paragraph_names_models_per_section()
def test_link_models_links_whole_names_longest_first()     # Review Focus 3
def test_link_models_skips_text_already_inside_a_link()
def test_build_roundup_item_shape_and_new_sentence_when_paragraph_is_thin()
def test_request_paragraph_degrades_to_empty(monkeypatch)   # llm_client.complete raises
def test_write_roundup_inserts_in_date_order_and_dedups_by_url(tmp_path)   # Review Focus 5
```

- [ ] **Step 2: Run; expect AttributeError**
- [ ] **Step 3: Implement the functions; write the prompt file** in the `pr-digest.prompt.yml` format: system message asks for 3 to 5 sentences of plain prose for Planet Tenstorrent readers, naming models and saying which came through tt-inference-server and which as tt-model bundles, no headings, bullets, counts restated, or hype; user message passes `{{ week }}` and `{{ manifest }}`; `maxTokens: 500`; a `testData` entry.
- [ ] **Step 4: Run; expect PASS**
- [ ] **Step 5: Commit** `feat(planet): weekly models roundup item from the models diff`

---

### Task 5: CLI, workflow, docs

**Files:**
- Modify: `scripts/models_diff.py` (add `main(argv)`)
- Modify: `.github/workflows/nightly-models.yml` (`pr` job)
- Modify: `AGENTS.md` (Releases / Generated files sections)
- Test: `tests/test_models_diff.py`

**Interfaces:**
- Produces: `main(argv: list[str]) -> int` with subcommands `pr-body --old --new --out [--template]` and `roundup --old --new --week-end YYYY-MM-DD [--feeds PATH] [--dry-run]`. `roundup` exits 0 and prints `no changes this week` when the diff is empty; prints the item JSON under `--dry-run` instead of writing.

- [ ] **Step 1: Write the failing tests**

```python
def test_cli_pr_body_writes_file(tmp_path, capsys)
def test_cli_roundup_dry_run_prints_item_and_writes_nothing(tmp_path, monkeypatch)   # monkeypatch request_roundup_paragraph → "A paragraph."
def test_cli_roundup_no_changes(tmp_path, capsys)
```

- [ ] **Step 2: Run; expect AttributeError on `main`**
- [ ] **Step 3: Implement `main`; credentials read from `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `FOUNDRY_API_KEY` env like `summarize_releases.py`**
- [ ] **Step 4: Run; expect PASS**
- [ ] **Step 5: Edit the workflow `pr` job** per the spec: `fetch-depth: 0`; `workflow_dispatch` input `roundup` (boolean, default false); download artifact to `new/`; `pip install pyyaml`; step "Describe the changes" runs `pr-body --old src/_data/models.json --new new/models.json --out pr-body.md`; step "Weekly roundup" with `if: ${{ env.FOUNDRY_API_KEY != '' && (inputs.roundup || github.event_name == 'schedule') }}` and a shell test that it is Thursday unless `inputs.roundup`, computing `OLD=$(git rev-list -1 --before="7 days ago" HEAD)` and `git show "$OLD:src/_data/models.json" > old-week.json`, then `roundup --old old-week.json --new new/models.json --week-end "$(date -u +%F)"`; "Prepare PR body" copies the template when `pr-body.md` is absent; `cp new/models.json src/_data/models.json`; `create-pull-request` with `body-path: pr-body.md` and `add-paths` of both files; the comment step copied from `nightly.yml` with the marker. Move the old `body:` text into `.github/pr-templates/models.md` (done in Task 3) and delete it from the workflow. Also list `FOUNDRY_API_KEY: ${{ secrets.FOUNDRY_API_KEY }}` under the job `env` the way `nightly.yml` does.
- [ ] **Step 6: Validate the workflow YAML** `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/nightly-models.yml'))"` and run a local end-to-end: `python3 scripts/models_diff.py roundup --old <week-old file from git> --new src/_data/models.json --week-end 2026-11-05 --dry-run` prints an item (paragraph is the fallback locally, no key).
- [ ] **Step 7: Update AGENTS.md**: one bullet under Releases describing the Thursday roundup item and its URL/dedup rule; one under Generated files noting the models PR body is the diff and that `planet_feeds.json` is also owned by the models workflow on Thursdays.
- [ ] **Step 8: Commit** `feat(ci): models PR explains its changes; Thursday roundup on the planet`
