# Release Summarization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the nightly metadata job detects a new GitHub release with sufficient release notes, generate a humanized one-paragraph summary via the Anthropic API and queue it as an `approved: false` planet feed item.

**Architecture:** A new standalone script `scripts/summarize_releases.py` runs after `fetch_github_meta.py` in the existing `nightly.yml` job. It reads `github_meta.json` (all current releases) and `planet_feeds.json` (dedup set), fetches the release body for each new release URL via the GitHub REST API, calls the Anthropic Messages API if body is substantial enough, and appends new `type: "release"` items to `planet_feeds.json`. The existing `create-pull-request` step stages both files. The summarization step is gated on `secrets.ANTHROPIC_API_KEY` and skipped entirely when absent.

**Tech Stack:** Python 3.11, `urllib` (stdlib only — no new deps), Anthropic Messages API (`https://api.anthropic.com/v1/messages`), `claude-haiku-4-5-20251001` model, `ANTHROPIC_API_KEY` secret (for LLM calls) + `GITHUB_TOKEN` (for GitHub REST API release body fetches).

**Spec:** `docs/superpowers/specs/2026-06-05-release-summarization-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `scripts/summarize_releases.py` | Core script: dedup, body fetch, sparse check, summarize, write |
| Create | `tests/test_summarize_releases.py` | Unit tests for all functions in the script |
| Modify | `.github/workflows/nightly.yml` | Add gated summarization step, `dry_run` input, expand `add-paths` |

---

## Task 1: Scaffold `summarize_releases.py` with helpers and dry-run support

**Files:**
- Create: `scripts/summarize_releases.py`
- Create: `tests/test_summarize_releases.py`

- [ ] **Step 1: Write failing tests for `load_known_urls` and `resolve_affiliation`**

```python
# tests/test_summarize_releases.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import summarize_releases as sr


def test_load_known_urls_returns_set_of_urls(tmp_path):
    feeds = [
        {"url": "https://github.com/foo/bar/releases/tag/v1.0", "type": "release"},
        {"url": "https://youtube.com/watch?v=abc", "type": "video"},
    ]
    f = tmp_path / "planet_feeds.json"
    f.write_text(json.dumps(feeds))
    result = sr.load_known_urls(f)
    assert result == {
        "https://github.com/foo/bar/releases/tag/v1.0",
        "https://youtube.com/watch?v=abc",
    }


def test_load_known_urls_returns_empty_set_when_file_missing(tmp_path):
    result = sr.load_known_urls(tmp_path / "nonexistent.json")
    assert result == set()


def test_resolve_affiliation_finds_matching_entry(tmp_path):
    entry = {
        "affiliation": "official",
        "links": [{"type": "repo", "url": "https://github.com/tenstorrent/tt-metal"}],
    }
    f = tmp_path / "tt-metal.json"
    f.write_text(json.dumps(entry))
    result = sr.resolve_affiliation("https://github.com/tenstorrent/tt-metal", [tmp_path])
    assert result == "official"


def test_resolve_affiliation_returns_community_when_no_match(tmp_path):
    result = sr.resolve_affiliation("https://github.com/unknown/repo", [tmp_path])
    assert result == "community"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /path/to/tt-awesome
python3 -m pytest tests/test_summarize_releases.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'summarize_releases'`

- [ ] **Step 3: Create `scripts/summarize_releases.py` with the helpers**

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Summarize new GitHub releases and append them to planet_feeds.json.

For each release URL in github_meta.json not already in planet_feeds.json:
  - Fetches the release body from the GitHub API
  - Skips if body is empty or under 150 characters
  - Calls the Anthropic Messages API to generate a one-paragraph human summary
  - Appends a type:"release" item (approved:false) to planet_feeds.json

Usage:
    python3 scripts/summarize_releases.py [--dry-run]
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT         = Path(__file__).parent.parent
ENTRIES_DIR  = ROOT / "entries"
META_IN      = ROOT / "src" / "_data" / "github_meta.json"
FEEDS_OUT    = ROOT / "src" / "_data" / "planet_feeds.json"

INFERENCE_URL = "https://models.github.ai/inference/chat/completions"
MODEL         = "openai/gpt-4o-mini"
SPARSE_LIMIT  = 150  # characters; bodies shorter than this are skipped

TOKEN = os.environ.get("GITHUB_TOKEN", "")

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


def resolve_affiliation(repo_url: str, entry_dirs: list) -> str:
    """Return affiliation for a repo URL by scanning entry JSONs."""
    for d in entry_dirs:
        for f in Path(d).rglob("*.json"):
            try:
                data = json.loads(f.read_text())
                for link in data.get("links", []):
                    if link.get("url", "").rstrip("/") == repo_url.rstrip("/"):
                        return data.get("affiliation", "community")
            except Exception:
                continue
    return "community"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_summarize_releases.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/summarize_releases.py tests/test_summarize_releases.py
git commit -m "feat: scaffold summarize_releases with helpers and tests"
```

---

## Task 2: Fetch release body and sparse check

**Files:**
- Modify: `scripts/summarize_releases.py`
- Modify: `tests/test_summarize_releases.py`

- [ ] **Step 1: Write failing tests for `fetch_release_body` and `is_sparse`**

Add to `tests/test_summarize_releases.py`:

```python
def _mock_urlopen(data):
    encoded = json.dumps(data).encode()
    mock = MagicMock()
    mock.read.return_value = encoded
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_fetch_release_body_returns_body(tmp_path):
    with patch("urllib.request.urlopen", return_value=_mock_urlopen({"body": "## What's new\n\nAdded feature X."})):
        result = sr.fetch_release_body("tenstorrent/tt-metal", "v1.0.0")
    assert result == "## What's new\n\nAdded feature X."


def test_fetch_release_body_returns_empty_on_http_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 404, "Not Found", {}, None)):
        result = sr.fetch_release_body("tenstorrent/tt-metal", "v1.0.0")
    assert result == ""


def test_fetch_release_body_returns_empty_when_body_is_none():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen({"body": None})):
        result = sr.fetch_release_body("tenstorrent/tt-metal", "v1.0.0")
    assert result == ""


def test_is_sparse_true_for_empty():
    assert sr.is_sparse("") is True
    assert sr.is_sparse("   \n  ") is True


def test_is_sparse_true_for_short_body():
    assert sr.is_sparse("Bug fixes.") is True


def test_is_sparse_false_for_substantial_body():
    body = "A" * 151
    assert sr.is_sparse(body) is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_summarize_releases.py::test_fetch_release_body_returns_body -v
```

Expected: `AttributeError: module 'summarize_releases' has no attribute 'fetch_release_body'`

- [ ] **Step 3: Add `fetch_release_body` and `is_sparse` to the script**

Add to `scripts/summarize_releases.py` after the helpers:

```python
def _gh_request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_summarize_releases.py -v
```

Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/summarize_releases.py tests/test_summarize_releases.py
git commit -m "feat: add fetch_release_body and is_sparse"
```

---

## Task 3: GitHub Models summarization call

**Files:**
- Modify: `scripts/summarize_releases.py`
- Modify: `tests/test_summarize_releases.py`

- [ ] **Step 1: Write failing test for `call_github_models`**

Add to `tests/test_summarize_releases.py`:

```python
def test_call_github_models_returns_summary():
    api_response = {
        "choices": [{"message": {"content": "This release adds multi-chip support."}}]
    }
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_response)):
        result = sr.call_github_models(
            repo="tenstorrent/tt-metal",
            release_name="v0.58.0",
            body="## Multi-chip support\n\nAdds routing for n300 configurations across 4 chips...\n" + "x" * 120,
            affiliation="official",
        )
    assert result == "This release adds multi-chip support."


def test_call_github_models_returns_empty_on_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 429, "Too Many Requests", {}, None)):
        result = sr.call_github_models(
            repo="tenstorrent/tt-metal",
            release_name="v0.58.0",
            body="x" * 200,
            affiliation="official",
        )
    assert result == ""
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_summarize_releases.py::test_call_github_models_returns_summary -v
```

Expected: `AttributeError: module 'summarize_releases' has no attribute 'call_github_models'`

- [ ] **Step 3: Add `call_github_models` to the script**

Add to `scripts/summarize_releases.py`:

```python
SYSTEM_PROMPT = (
    "You write brief, engaging release summaries for Planet Tenstorrent, an aggregator "
    "read by developers and researchers following the Tenstorrent ecosystem. Your tone "
    "is warm and technically literate — like a knowledgeable colleague sharing what's "
    "new, not a press release. Write one paragraph of 2–4 sentences. Focus on what "
    "changed and why it matters. Do not repeat the version number or project name. "
    "Do not use hype words like \"exciting\" or \"powerful\". Do not use bullet points."
)


def call_github_models(repo: str, release_name: str, body: str, affiliation: str) -> str:
    """Call GitHub Models inference API and return the summary string, or '' on error."""
    user_message = (
        f"Summarize this release for Planet Tenstorrent readers.\n\n"
        f"Project: {repo} ({affiliation})\n"
        f"Release: {release_name}\n\n"
        f"Release notes:\n{body}"
    )
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        INFERENCE_URL,
        data=payload,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"  WARN call_github_models {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN call_github_models {repo}: {e}", file=sys.stderr)
    return ""
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_summarize_releases.py -v
```

Expected: 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/summarize_releases.py tests/test_summarize_releases.py
git commit -m "feat: add call_github_models summarization"
```

---

## Task 4: `main()` — wire everything together with `--dry-run`

**Files:**
- Modify: `scripts/summarize_releases.py`
- Modify: `tests/test_summarize_releases.py`

- [ ] **Step 1: Write failing test for `main()`**

Add to `tests/test_summarize_releases.py`:

```python
def test_main_appends_new_release_item(tmp_path, monkeypatch):
    # Arrange: one repo with one release not yet in planet_feeds
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{
                "tagName": "v1.0.0",
                "name": "v1.0.0",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0",
                "prerelease": False,
            }]
        }
    }
    feeds = []
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))

    # Entry JSON for affiliation lookup
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()
    (entry_dir / "tt-metal.json").write_text(json.dumps({
        "affiliation": "official",
        "links": [{"type": "repo", "url": "https://github.com/tenstorrent/tt-metal"}],
    }))

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_github_models",  return_value="A great summary."):
        sr.main([])

    result = json.loads(feeds_file.read_text())
    assert len(result) == 1
    item = result[0]
    assert item["type"] == "release"
    assert item["source"] == "github"
    assert item["approved"] is False
    assert item["affiliation"] == "official"
    assert item["description"] == "A great summary."
    assert item["url"] == "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0"


def test_main_skips_sparse_body(tmp_path, monkeypatch):
    meta = {
        "https://github.com/foo/bar": {
            "releases": [{
                "tagName": "v0.1",
                "name": "v0.1",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/foo/bar/releases/tag/v0.1",
                "prerelease": False,
            }]
        }
    }
    feeds = []
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)

    with patch.object(sr, "fetch_release_body", return_value="Bug fixes."):
        sr.main([])

    result = json.loads(feeds_file.read_text())
    assert result == []


def test_main_dry_run_does_not_write(tmp_path, monkeypatch):
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{
                "tagName": "v2.0.0",
                "name": "v2.0.0",
                "publishedAt": "2026-06-01T12:00:00Z",
                "url": "https://github.com/tenstorrent/tt-metal/releases/tag/v2.0.0",
                "prerelease": False,
            }]
        }
    }
    feeds = []
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)

    with patch.object(sr, "fetch_release_body", return_value="x" * 200), \
         patch.object(sr, "call_github_models",  return_value="A summary."):
        sr.main(["--dry-run"])

    # File must be untouched
    result = json.loads(feeds_file.read_text())
    assert result == []


def test_main_skips_already_known_url(tmp_path, monkeypatch):
    url = "https://github.com/tenstorrent/tt-metal/releases/tag/v1.0.0"
    meta = {
        "https://github.com/tenstorrent/tt-metal": {
            "releases": [{"tagName": "v1.0.0", "name": "v1.0.0",
                          "publishedAt": "2026-06-01T12:00:00Z",
                          "url": url, "prerelease": False}]
        }
    }
    feeds = [{"url": url, "type": "release", "approved": True}]
    meta_file  = tmp_path / "github_meta.json"
    feeds_file = tmp_path / "planet_feeds.json"
    meta_file.write_text(json.dumps(meta))
    feeds_file.write_text(json.dumps(feeds))
    entry_dir = tmp_path / "entries"
    entry_dir.mkdir()

    monkeypatch.setattr(sr, "META_IN",     meta_file)
    monkeypatch.setattr(sr, "FEEDS_OUT",   feeds_file)
    monkeypatch.setattr(sr, "ENTRIES_DIR", entry_dir)

    with patch.object(sr, "fetch_release_body") as mock_body:
        sr.main([])

    mock_body.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_summarize_releases.py::test_main_appends_new_release_item -v
```

Expected: `AttributeError: module 'summarize_releases' has no attribute 'main'`

- [ ] **Step 3: Add `main()` and `__main__` block to the script**

Add to the end of `scripts/summarize_releases.py`:

```python
def main(argv: list | None = None):
    if argv is None:
        argv = sys.argv[1:]
    dry_run = "--dry-run" in argv

    if not TOKEN and not dry_run:
        print("ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    meta = {}
    if META_IN.exists():
        try:
            meta = json.loads(META_IN.read_text())
        except Exception as e:
            print(f"ERROR: cannot read {META_IN}: {e}", file=sys.stderr)
            sys.exit(1)

    known_urls = load_known_urls(FEEDS_OUT)

    # Load existing feeds so we can append
    existing_feeds = []
    if FEEDS_OUT.exists():
        try:
            existing_feeds = json.loads(FEEDS_OUT.read_text())
        except Exception:
            pass

    new_items = []

    for repo_url, repo_data in meta.items():
        m = REPO_RE.match(repo_url)
        if not m:
            continue
        repo = m.group(1)  # "owner/name"
        repo_name = repo.split("/")[-1]

        for release in repo_data.get("releases", []):
            url = release.get("url", "")
            if not url or url in known_urls:
                continue

            tag  = release["tagName"]
            name = release.get("name") or tag

            body = fetch_release_body(repo, tag)
            if is_sparse(body):
                print(f"  SKIP {repo}@{tag}: body too sparse ({len(body.strip())} chars)")
                continue

            affiliation = resolve_affiliation(repo_url, [ENTRIES_DIR])
            summary = call_github_models(repo, name, body, affiliation)
            if not summary:
                print(f"  SKIP {repo}@{tag}: summarization failed")
                continue

            date_str = release.get("publishedAt", "")[:10] or "1970-01-01"
            item = {
                "type":        "release",
                "source":      "github",
                "approved":    False,
                "title":       f"{repo_name} {tag}",
                "url":         url,
                "description": summary,
                "date":        date_str,
                "dateISO":     release.get("publishedAt", f"{date_str}T00:00:00Z"),
                "label":       repo,
                "projectName": repo_name,
                "projectId":   None,
                "affiliation": affiliation,
            }

            if dry_run:
                print(f"\n--- DRY RUN: {repo}@{tag} ---")
                print(summary)
            else:
                new_items.append(item)
                known_urls.add(url)
                print(f"  ADDED {repo}@{tag}")

    if dry_run:
        print(f"\nDRY RUN complete. {len(new_items)} items would be added.")
        return

    if new_items:
        all_items = existing_feeds + new_items
        all_items.sort(key=lambda x: x.get("dateISO", ""), reverse=True)
        tmp = FEEDS_OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(all_items, indent=2, ensure_ascii=False) + "\n")
        tmp.rename(FEEDS_OUT)
        print(f"\nWrote {len(new_items)} new release item(s) to {FEEDS_OUT.relative_to(ROOT)}")
    else:
        print("\nNo new release items.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
python3 -m pytest tests/test_summarize_releases.py -v
```

Expected: 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/summarize_releases.py tests/test_summarize_releases.py
git commit -m "feat: add main() with dry-run support to summarize_releases"
```

---

## Task 5: Update `nightly.yml`

**Files:**
- Modify: `.github/workflows/nightly.yml`

- [ ] **Step 1: Read the current workflow**

```bash
cat .github/workflows/nightly.yml
```

- [ ] **Step 2: Apply the three changes**

**a)** Add `workflow_dispatch` input and `models: read` permission.

Replace the existing `on:` and `permissions:` blocks:

```yaml
on:
  schedule:
    - cron: "17 6,18 * * *"
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Dry run — print summaries, write nothing"
        type: boolean
        default: false
permissions:
  contents: write
  pull-requests: write
  models: read
```

**b)** Add the summarization step immediately after the existing `Fetch metadata` step:

```yaml
      - name: Summarize new releases
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          FLAGS=""
          if [ "${{ inputs.dry_run }}" = "true" ]; then FLAGS="--dry-run"; fi
          python3 scripts/summarize_releases.py $FLAGS
```

**c)** Expand the `add-paths` in the `Create pull request if changed` step:

```yaml
          add-paths: |
            src/_data/github_meta.json
            src/_data/planet_feeds.json
```

- [ ] **Step 3: Verify the workflow is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/nightly.yml'))" && echo "YAML OK"
```

Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/nightly.yml
git commit -m "ci: add release summarization step to nightly workflow"
```

---

## Task 6: Local dry-run smoke test

**Files:** none changed

- [ ] **Step 1: Run a local dry-run against real data**

```bash
GITHUB_TOKEN=<your-token> python3 scripts/summarize_releases.py --dry-run
```

Expected output: for each watched repo that has releases with substantial body text, you should see a `--- DRY RUN: owner/repo@tag ---` block followed by a 2–4 sentence paragraph. Repos with sparse notes print `SKIP`.

If no repos have qualifying releases yet (all current releases have sparse notes), the script prints `DRY RUN complete. 0 items would be added.` — that's fine, it means the dedup/sparse logic is working correctly.

- [ ] **Step 2: Run the full test suite to confirm nothing regressed**

```bash
python3 -m pytest tests/ -v
```

Expected: all existing tests plus the 16 new ones PASS

- [ ] **Step 3: Commit if tests pass (no source changes needed)**

No commit needed for this task unless you found a bug and fixed it.

---

## Task 7: CI dry-run verification (manual trigger)

**Files:** none changed

- [ ] **Step 1: Push the branch to origin**

```bash
git push origin tricks/summarization
```

- [ ] **Step 2: Trigger the nightly workflow manually with `dry_run: true`**

Go to: `https://github.com/tenstorrent/tt-awesome/actions/workflows/nightly.yml`

Click **Run workflow**, set `dry_run: true`, click **Run workflow**.

- [ ] **Step 3: Confirm the job passes**

In the Actions run log, look for the `Summarize new releases` step. It should complete without error. If the step fails with a permissions error about `models: read`, confirm the `permissions:` block in `nightly.yml` includes `models: read` at the job level (not just top-level).

- [ ] **Step 4: If all looks good, open PR to main**

```bash
gh pr create --title "feat: summarize new GitHub releases into Planet feed" \
  --body "Adds summarize_releases.py — on each nightly run, new releases with substantial notes get a humanized one-paragraph summary queued as approved:false planet feed items via GitHub Models (openai/gpt-4o-mini)."
```
