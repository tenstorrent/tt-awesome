# Recent Releases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Recent Releases" pane tracking tagged GitHub releases across all featured projects, with All/Official/Community toggle, fork indicators on project detail cards, and per-project release history.

**Architecture:** Extend the nightly `fetch_github_meta.py` script to pull releases (5 per repo) and fork info from the GitHub API, storing them in `github_meta.json`. A new `recentReleases.js` data file derives the top-50 stable feed at build time. A new `.releases-pane` renders alongside the existing `.list-pane`, toggled via CSS class. Entry detail cards gain a fork badge and a latest-callout + history section.

**Tech Stack:** Python 3 (fetch script), Eleventy 3 / Nunjucks (templates), vanilla JS (navigation state), CSS custom properties (theming).

**Spec:** `docs/superpowers/specs/2026-05-22-recent-releases-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/fetch_github_meta.py` | Modify | Add fork field extraction + `fetch_releases()` |
| `tests/test_fetch_github_meta.py` | Create | Unit tests for new fetch functions |
| `src/_data/entries.js` | Modify | Compute `latestStableRelease` per entry |
| `src/_data/recentReleases.js` | Create | Derive top-50 stable release feed |
| `src/assets/style.css` | Modify | Releases pane, release row, fork badge, callout styles |
| `src/_includes/sidebar.njk` | Modify | Add 🏷 Recent Releases nav item |
| `src/_includes/releases-list.njk` | Create | Releases pane markup with toggle |
| `src/index.njk` | Modify | Include releases-list.njk in panes |
| `src/assets/main.js` | Modify | Releases nav state, toggle, relative-time, URL handling |
| `src/_includes/entry-detail.njk` | Modify | Fork badge + releases section |

---

## Task 1: Extend fetch script — fork detection and releases fetch

**Files:**
- Modify: `scripts/fetch_github_meta.py`
- Create: `tests/test_fetch_github_meta.py`

- [ ] **Step 1: Write failing tests for fork detection and releases fetch**

Create `tests/test_fetch_github_meta.py`:

```python
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from fetch_github_meta import fetch_repo, fetch_releases


def _mock_response(data):
    """Return a context-manager mock that yields JSON-encoded data."""
    encoded = json.dumps(data).encode()
    mock = MagicMock()
    mock.read.return_value = encoded
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# ── fetch_repo fork detection ────────────────────────────────────────────────

def test_fetch_repo_non_fork_has_no_fork_fields():
    data = {
        "stargazers_count": 42,
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
        "fork": False,
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("foo/bar")
    assert result["stars"] == 42
    assert result["_is_fork"] is False
    assert result["_fork_parent_name"] == ""
    assert result["_fork_parent_url"] == ""


def test_fetch_repo_fork_captures_parent():
    data = {
        "stargazers_count": 10,
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
        "fork": True,
        "parent": {
            "full_name": "upstream/repo",
            "html_url": "https://github.com/upstream/repo",
        },
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("foo/bar")
    assert result["_is_fork"] is True
    assert result["_fork_parent_name"] == "upstream/repo"
    assert result["_fork_parent_url"] == "https://github.com/upstream/repo"


def test_fetch_repo_fork_without_parent_key():
    """fork:true but no parent key (edge case) — should not crash."""
    data = {
        "stargazers_count": 5,
        "updated_at": "2026-01-01T00:00:00Z",
        "default_branch": "main",
        "fork": True,
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_repo("foo/bar")
    assert result["_is_fork"] is True
    assert result["_fork_parent_name"] == ""


# ── fetch_releases ────────────────────────────────────────────────────────────

def test_fetch_releases_returns_non_draft_releases():
    data = [
        {
            "tag_name": "v1.1.0", "name": "v1.1.0",
            "published_at": "2026-05-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v1.1.0",
            "prerelease": False, "draft": False,
        },
        {
            "tag_name": "v1.0.0-rc1", "name": "RC1",
            "published_at": "2026-04-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v1.0.0-rc1",
            "prerelease": True, "draft": False,
        },
        {
            "tag_name": "v0.9.0", "name": "v0.9.0",
            "published_at": "2026-03-01T00:00:00Z",
            "html_url": "https://github.com/foo/bar/releases/tag/v0.9.0",
            "prerelease": False, "draft": True,   # draft — must be excluded
        },
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_releases("foo/bar")
    assert len(result) == 2
    assert result[0]["tagName"] == "v1.1.0"
    assert result[0]["prerelease"] is False
    assert result[1]["tagName"] == "v1.0.0-rc1"
    assert result[1]["prerelease"] is True


def test_fetch_releases_empty_repo():
    with patch("urllib.request.urlopen", return_value=_mock_response([])):
        result = fetch_releases("foo/bar")
    assert result == []


def test_fetch_releases_name_falls_back_to_tag():
    data = [{
        "tag_name": "v2.0.0", "name": "",
        "published_at": "2026-05-10T00:00:00Z",
        "html_url": "https://github.com/foo/bar/releases/tag/v2.0.0",
        "prerelease": False, "draft": False,
    }]
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        result = fetch_releases("foo/bar")
    assert result[0]["name"] == "v2.0.0"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /home/ttuser/code/tt-awesome
python3 -m pytest tests/test_fetch_github_meta.py -v 2>&1 | head -30
```

Expected: `ImportError` or `AttributeError` — `fetch_releases` doesn't exist yet and `fetch_repo` doesn't return fork fields.

- [ ] **Step 3: Add fork fields to `fetch_repo()` in `scripts/fetch_github_meta.py`**

Replace the return statement inside `fetch_repo` (lines 46–51) so it reads:

```python
def fetch_repo(repo: str) -> dict:
    try:
        with urllib.request.urlopen(_request(f"https://api.github.com/repos/{repo}"), timeout=10) as r:
            d = json.loads(r.read())
            parent = d.get("parent") or {}
            return {
                "stars": d.get("stargazers_count", 0),
                "updatedAt": d.get("updated_at", ""),
                "_default_branch": d.get("default_branch", "main"),
                "_is_fork": d.get("fork", False),
                "_fork_parent_name": parent.get("full_name", ""),
                "_fork_parent_url": parent.get("html_url", ""),
            }
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo}: {e}", file=sys.stderr)
    return {}
```

- [ ] **Step 4: Add `fetch_releases()` function to `scripts/fetch_github_meta.py`**

Insert this function after `fetch_readme_image` (after line 78, before `def main`):

```python
def fetch_releases(repo: str, per_page: int = 5) -> list:
    try:
        url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}"
        with urllib.request.urlopen(_request(url), timeout=10) as r:
            releases = json.loads(r.read())
            return [
                {
                    "tagName": rel["tag_name"],
                    "name": rel.get("name") or rel["tag_name"],
                    "publishedAt": rel.get("published_at", ""),
                    "url": rel.get("html_url", ""),
                    "prerelease": rel.get("prerelease", False),
                }
                for rel in releases
                if not rel.get("draft", False)
            ]
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo} releases: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo} releases: {e}", file=sys.stderr)
    return []
```

- [ ] **Step 5: Wire fork fields and releases into `main()` in `scripts/fetch_github_meta.py`**

Replace the `if result:` block inside `main()` (currently lines 95–101) with:

```python
        if result:
            default_branch = result.pop("_default_branch", "main")
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
                print(f"  releases: {len(releases)} fetched")
            meta[repo_link["url"]] = result
```

- [ ] **Step 6: Run tests — all should pass**

```bash
cd /home/ttuser/code/tt-awesome
python3 -m pytest tests/test_fetch_github_meta.py -v
```

Expected output:
```
tests/test_fetch_github_meta.py::test_fetch_repo_non_fork_has_no_fork_fields PASSED
tests/test_fetch_github_meta.py::test_fetch_repo_fork_captures_parent PASSED
tests/test_fetch_github_meta.py::test_fetch_repo_fork_without_parent_key PASSED
tests/test_fetch_github_meta.py::test_fetch_releases_returns_non_draft_releases PASSED
tests/test_fetch_github_meta.py::test_fetch_releases_empty_repo PASSED
tests/test_fetch_github_meta.py::test_fetch_releases_name_falls_back_to_tag PASSED
6 passed
```

- [ ] **Step 7: Run the full test suite to check for regressions**

```bash
cd /home/ttuser/code/tt-awesome
python3 -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/fetch_github_meta.py tests/test_fetch_github_meta.py
git commit -m "feat: add fork detection and release history to fetch_github_meta"
```

---

## Task 2: Data files — recentReleases.js and latestStableRelease in entries.js

**Files:**
- Modify: `src/_data/entries.js`
- Create: `src/_data/recentReleases.js`

- [ ] **Step 1: Add `latestStableRelease` computation to `entries.js`**

In `src/_data/entries.js`, inside the `module.exports = function()` block, after the existing URL safety block (after line 69 `if (!isSafeHttpsUrl(entry.preview_image)) delete entry.preview_image;`) and before `return entry;`, add:

```js
    // Pre-compute the first stable (non-prerelease) release for templates.
    // Nunjucks cannot filter arrays mid-loop in a way that persists to outer scope,
    // so we resolve this in the data layer instead.
    if (Array.isArray(entry.releases) && entry.releases.length) {
      const stable = entry.releases.find(r => !r.prerelease);
      if (stable) entry.latestStableRelease = stable;
    }
```

- [ ] **Step 2: Create `src/_data/recentReleases.js`**

```js
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

module.exports = function () {
  const allEntries = require("./entries")();

  const releases = [];
  for (const entry of allEntries) {
    const stable = entry.latestStableRelease;
    if (!stable) continue;
    const repoLink = (entry.links || []).find(l => l.type === "repo");
    releases.push({
      entryId: entry.id,
      entryName: entry.name,
      affiliation: entry.affiliation,
      tagName: stable.tagName,
      publishedAt: stable.publishedAt,
      url: stable.url,
      repoUrl: repoLink ? repoLink.url : "",
    });
  }

  releases.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
  return releases.slice(0, 50);
};
```

- [ ] **Step 3: Verify build succeeds**

```bash
cd /home/ttuser/code/tt-awesome
npm run build 2>&1 | tail -10
```

Expected: `[11ty] Wrote 1 file in ...` with no errors.

- [ ] **Step 4: Verify recentReleases is available in the build output**

```bash
node -e "
const r = require('./src/_data/recentReleases.js')();
console.log('releases count:', r.length);
console.log('first:', JSON.stringify(r[0], null, 2));
"
```

Expected: `releases count: 0` (because `github_meta.json` doesn't have `releases` data yet — that's correct, the nightly script will populate it). The count being 0 is expected; the important thing is no crash.

- [ ] **Step 5: Commit**

```bash
git add src/_data/entries.js src/_data/recentReleases.js
git commit -m "feat: add recentReleases data file and latestStableRelease to entries"
```

---

## Task 3: CSS — releases pane, release rows, fork badge, release callout

**Files:**
- Modify: `src/assets/style.css`

- [ ] **Step 1: Append releases and fork CSS to `src/assets/style.css`**

Add at the end of the file:

```css
/* ── Releases pane ───────────────────────────────────────────────────────── */
.releases-pane { width: var(--list-w); flex-shrink: 0; border-right: 1px solid var(--bg2);
                 display: flex; flex-direction: column; overflow: hidden; }
.panes.releases-active .list-pane     { display: none; }
.panes:not(.releases-active) .releases-pane { display: none; }
.panes.home-active .releases-pane     { display: none; }

.releases-toggle { display: flex; gap: 4px; padding: 6px 12px 0; }
.rtoggle-btn { font-size: 11px; padding: 3px 10px; border-radius: 12px; border: none;
               cursor: pointer; background: var(--bg1); color: var(--muted);
               transition: background 0.15s, color 0.15s; letter-spacing: 0.2px; }
.rtoggle-btn.active { background: rgba(79,209,197,0.12); color: var(--teal); }

.release-row { padding: 8px 12px; border-bottom: 1px solid var(--bg1); cursor: pointer;
               transition: background 0.1s; border-left: 3px solid transparent; }
.release-row:hover  { background: var(--bg1); }
.release-row.active { background: var(--bg1); border-left-color: var(--teal); }
.release-row.rview-hidden { display: none; }
.release-row .row-top { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.release-row .row-name { font-size: 12px; font-weight: 600; color: var(--text); }

.rel-tag  { font-size: 10px; font-family: ui-monospace, "SFMono-Regular", monospace;
            color: var(--teal-lt); background: rgba(79,209,197,0.08);
            padding: 1px 6px; border-radius: 3px; }
.rel-date { font-size: 10px; color: var(--muted); }
.rel-pre  { font-size: 8px; color: var(--gold);
            border: 1px solid rgba(244,196,113,0.4); padding: 0 4px; border-radius: 3px; }

/* ── Fork badge ─────────────────────────────────────────────────────────── */
.fork-badge { font-size: 9px; color: var(--teal-lt);
              border: 1px solid rgba(79,209,197,0.35); background: transparent;
              padding: 1px 7px; border-radius: 6px; text-decoration: none;
              font-family: ui-monospace, "SFMono-Regular", monospace; white-space: nowrap; }
.fork-badge:hover { border-color: var(--teal); color: var(--teal); }

/* ── Release history in detail card ─────────────────────────────────────── */
.latest-callout { background: rgba(79,209,197,0.06); border: 1px solid rgba(79,209,197,0.2);
                  border-radius: 6px; padding: 8px 12px; display: flex;
                  align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.latest-badge { font-size: 8px; background: var(--teal); color: var(--bg0);
                padding: 1px 5px; border-radius: 3px; font-weight: 700; flex-shrink: 0; }
.latest-tag { font-size: 13px; font-family: ui-monospace, "SFMono-Regular", monospace;
              color: var(--teal); font-weight: 700; }
.latest-date { font-size: 10px; color: var(--muted); }
.release-notes-link { font-size: 10px; color: var(--teal-lt); text-decoration: none;
                      margin-left: auto; white-space: nowrap; }
.release-notes-link:hover { color: var(--teal); text-decoration: underline;
                             text-underline-offset: 2px; }

.release-history-list { margin-bottom: 4px; }
.rel-hist-row { display: flex; align-items: center; gap: 8px; padding: 4px 0;
                border-bottom: 1px solid rgba(255,255,255,0.04); }
.rel-hist-row:last-child { border-bottom: none; }
.rel-hist-row .rel-tag { text-decoration: none; }
.rel-hist-row .rel-tag:hover { color: var(--teal); }

.releases-all-link { font-size: 10px; color: var(--teal); text-decoration: none;
                     display: block; text-align: right; margin-top: 4px; opacity: 0.7; }
.releases-all-link:hover { opacity: 1; text-decoration: underline; text-underline-offset: 2px; }
```

- [ ] **Step 2: Verify build**

```bash
cd /home/ttuser/code/tt-awesome
npm run build 2>&1 | tail -5
```

Expected: builds cleanly.

- [ ] **Step 3: Commit**

```bash
git add src/assets/style.css
git commit -m "feat: add releases pane, fork badge, and release history CSS"
```

---

## Task 4: Templates — sidebar, releases-list.njk, index.njk

**Files:**
- Modify: `src/_includes/sidebar.njk`
- Create: `src/_includes/releases-list.njk`
- Modify: `src/index.njk`

- [ ] **Step 1: Add Recent Releases item to `src/_includes/sidebar.njk`**

In `src/_includes/sidebar.njk`, insert after the `🏠 Home` item and before the first `<hr class="sidebar-hr">`:

```html
  <a class="sidebar-item" id="releases-item"
     href="?releases=all"
     onclick="selectReleases('all'); return false;">
    🏷 Recent Releases
  </a>
```

The full updated sidebar top will look like:
```html
<nav class="sidebar" id="sidebar">
  <a class="sidebar-item sidebar-home active" id="home-item"
     href="/"
     onclick="showHome(); return false;">
    🏠 Home
  </a>
  <a class="sidebar-item" id="releases-item"
     href="?releases=all"
     onclick="selectReleases('all'); return false;">
    🏷 Recent Releases
  </a>
  <hr class="sidebar-hr">
  <div class="sidebar-label">Categories</div>
  ...
```

- [ ] **Step 2: Create `src/_includes/releases-list.njk`**

```html
<div class="releases-pane" id="releases-pane">
  <div class="list-head">
    <div class="list-title-row">
      <div class="list-title">🏷 Recent Releases</div>
      <div class="list-count" id="releases-count">{{ recentReleases | length }} releases</div>
    </div>
    <div class="releases-toggle">
      <button class="rtoggle-btn active" data-rview="all"
              onclick="toggleReleasesView(this)">All</button>
      <button class="rtoggle-btn" data-rview="official"
              onclick="toggleReleasesView(this)">Official</button>
      <button class="rtoggle-btn" data-rview="community"
              onclick="toggleReleasesView(this)">Community</button>
    </div>
  </div>
  <div class="list-rows" id="releases-rows">
    {%- for rel in recentReleases %}
    <div class="release-row"
         data-id="{{ rel.entryId }}"
         data-affiliation="{{ rel.affiliation }}"
         onclick="selectEntry('{{ rel.entryId }}', this)">
      <div class="row-top">
        <span class="row-name">{{ rel.entryName }}</span>
        <span class="badge badge--{{ rel.affiliation }}">{{ rel.affiliation }}</span>
        <span class="rel-tag">{{ rel.tagName }}</span>
      </div>
      <div class="rel-date" data-ts="{{ rel.publishedAt }}">{{ rel.publishedAt }}</div>
    </div>
    {%- endfor %}
  </div>
</div>
```

- [ ] **Step 3: Include `releases-list.njk` in `src/index.njk`**

In `src/index.njk`, add the include after `entry-list.njk`:

```html
  <div class="panes home-active" id="panes">
    {%- include "sidebar.njk" -%}
    {%- include "home.njk" -%}
    {%- include "entry-list.njk" -%}
    {%- include "releases-list.njk" -%}
    {%- include "entry-detail.njk" -%}
  </div>
```

- [ ] **Step 4: Verify build**

```bash
cd /home/ttuser/code/tt-awesome
npm run build 2>&1 | tail -5
```

Expected: builds cleanly, no template errors.

- [ ] **Step 5: Verify releases pane exists in built HTML**

```bash
grep -c "releases-pane" _site/index.html
```

Expected: `1`

- [ ] **Step 6: Commit**

```bash
git add src/_includes/sidebar.njk src/_includes/releases-list.njk src/index.njk
git commit -m "feat: add releases pane template and sidebar nav item"
```

---

## Task 5: JavaScript — releases navigation, toggle, relative-time, URL state

**Files:**
- Modify: `src/assets/main.js`

- [ ] **Step 1: Add `activeReleasesView` state variable**

At the top of `src/assets/main.js`, after the existing state vars (after line 7 `let activeAuthorFilter = null;`), add:

```js
let activeReleasesView = 'all';
```

- [ ] **Step 2: Add `relativeTime()` helper function**

Insert after the state vars block and before `document.addEventListener("DOMContentLoaded"`:

```js
function relativeTime(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins} minute${mins !== 1 ? "s" : ""} ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs !== 1 ? "s" : ""} ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days} day${days !== 1 ? "s" : ""} ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks} week${weeks !== 1 ? "s" : ""} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months !== 1 ? "s" : ""} ago`;
  const years = Math.floor(days / 365);
  return `${years} year${years !== 1 ? "s" : ""} ago`;
}
```

- [ ] **Step 3: Wire `relativeTime` in `DOMContentLoaded`**

In the `document.addEventListener("DOMContentLoaded", ...)` callback (currently ends around line 35), add a call to convert all `data-ts` elements before `restoreFromUrl()`:

```js
document.addEventListener("DOMContentLoaded", () => {
  restoreFromUrl();

  document.querySelectorAll("[data-ts]").forEach(el => {
    if (el.dataset.ts) el.textContent = relativeTime(el.dataset.ts);
  });

  document.getElementById("search").addEventListener("input", (e) => {
    // ... existing search handler unchanged ...
  });

  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => toggleChip(chip))
  );

  window.addEventListener("popstate", restoreFromUrl);
});
```

- [ ] **Step 4: Update `_applyHome()` to clear `releases-active`**

In `_applyHome()` (around line 98), add `releases-active` removal:

```js
function _applyHome() {
  activeCategory = null;
  activeEntryId = null;
  activeAuthorFilter = null;
  const panes = document.getElementById("panes");
  panes.classList.add("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("home-item").classList.add("active");
}
```

- [ ] **Step 5: Update `_applyCategory()` to clear `releases-active`**

In `_applyCategory()` (around line 149), add removal:

```js
function _applyCategory(slug, el) {
  activeCategory = slug;
  activeAuthorFilter = null;
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("list-title").textContent = el.textContent.trim();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
  _clearDetail();
}
```

- [ ] **Step 6: Update `_applyAuthorFilter()` to clear `releases-active`**

In `_applyAuthorFilter()` (around line 124), add removal:

```js
function _applyAuthorFilter(name) {
  activeAuthorFilter = name;
  activeCategory = null;
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("list-title").textContent = name;
  _clearDetail();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
}
```

- [ ] **Step 7: Update `_applyEntry()` to also clear `.release-row` active states**

In `_applyEntry()` (around line 171), update the querySelectorAll to include `.release-row`:

```js
function _applyEntry(id, el) {
  activeEntryId = id;
  document.querySelectorAll(".entry-row, .release-row").forEach((r) => r.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("detail-empty").style.display = "none";
  document.querySelectorAll(".detail-card").forEach((c) => c.classList.remove("visible"));
  const card = document.getElementById("detail-" + id);
  if (card) card.classList.add("visible");
}
```

- [ ] **Step 8: Update `selectEntry()` to emit correct URL when in releases mode**

In `selectEntry()` (around line 161), add the releases-mode branch:

```js
function selectEntry(id, el) {
  if (activeAuthorFilter) {
    pushUrl({ author: activeAuthorFilter, entry: id });
  } else if (document.getElementById("panes").classList.contains("releases-active")) {
    pushUrl({ releases: activeReleasesView, entry: id });
  } else {
    pushUrl({ cat: activeCategory, entry: id });
  }
  _applyEntry(id, el);
}
```

- [ ] **Step 9: Add releases navigation functions**

After the `_applyAuthorFilter` function, add:

```js
/** Public: navigate to releases pane with given view. Updates URL. */
function selectReleases(view) {
  pushUrl({ releases: view });
  _applyReleases(view);
}

/** Internal: activate releases pane without touching history. */
function _applyReleases(view) {
  activeReleasesView = view || 'all';
  activeCategory = null;
  activeAuthorFilter = null;
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.add("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  const relItem = document.getElementById("releases-item");
  if (relItem) relItem.classList.add("active");
  applyReleasesFilter(activeReleasesView);
  _clearDetail();
}

/** Toggle the All/Official/Community button strip in the releases pane. */
function toggleReleasesView(btn) {
  selectReleases(btn.dataset.rview);
}

/** Show/hide release rows and update toggle button states. */
function applyReleasesFilter(view) {
  let visible = 0;
  document.querySelectorAll(".release-row").forEach(row => {
    const aff = row.dataset.affiliation;
    const show = view === "all"
      || (view === "official" && aff === "official")
      || (view === "community" && (aff === "community" || aff === "affiliated"));
    row.classList.toggle("rview-hidden", !show);
    if (show) visible++;
  });
  const countEl = document.getElementById("releases-count");
  if (countEl) countEl.textContent = `${visible} release${visible !== 1 ? "s" : ""}`;
  document.querySelectorAll(".rtoggle-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.rview === view);
  });
}
```

- [ ] **Step 10: Update `restoreFromUrl()` to handle `?releases=` param**

In `restoreFromUrl()` (around line 57), add releases handling before the `cat` check:

```js
function restoreFromUrl() {
  const params = new URLSearchParams(location.search);
  const cat = params.get("cat");
  const author = params.get("author");
  const releases = params.get("releases");
  const entryId = params.get("entry");

  if (releases) {
    _applyReleases(releases);
    if (entryId) {
      const row = document.querySelector(
        `.entry-row[data-id="${CSS.escape(entryId)}"], .release-row[data-id="${CSS.escape(entryId)}"]`
      );
      if (row) _applyEntry(entryId, row);
    }
    return;
  }
  if (cat) {
    const el = document.querySelector(`.sidebar-item[data-category="${CSS.escape(cat)}"]`);
    if (el) {
      _applyCategory(cat, el);
      if (entryId) {
        const row = document.querySelector(`.entry-row[data-id="${CSS.escape(entryId)}"]`);
        if (row) _applyEntry(entryId, row);
      }
      return;
    }
  }
  if (author) {
    _applyAuthorFilter(author);
    if (entryId) {
      const row = document.querySelector(`.entry-row[data-id="${CSS.escape(entryId)}"]`);
      if (row) _applyEntry(entryId, row);
    }
    return;
  }
  _applyHome();
}
```

- [ ] **Step 11: Verify build**

```bash
cd /home/ttuser/code/tt-awesome
npm run build 2>&1 | tail -5
```

Expected: builds cleanly.

- [ ] **Step 12: Smoke-test in browser**

```bash
cd /home/ttuser/code/tt-awesome
npm run serve
```

Open `http://localhost:8080`. Verify:
- "🏷 Recent Releases" appears in sidebar
- Clicking it switches to the releases pane (list pane disappears, releases pane appears)
- Toggle buttons (All / Official / Community) are visible
- Since `github_meta.json` has no releases data yet, the pane shows 0 rows — that is expected
- Clicking another category returns to normal list pane
- Browser back/forward restores state correctly (test `?releases=all` in URL bar directly)

- [ ] **Step 13: Commit**

```bash
git add src/assets/main.js
git commit -m "feat: add releases pane navigation, toggle, and relative-time to main.js"
```

---

## Task 6: Entry detail — fork badge and release history section

**Files:**
- Modify: `src/_includes/entry-detail.njk`

- [ ] **Step 1: Add fork badge to the detail title row**

In `src/_includes/entry-detail.njk`, in the `.detail-title-row` div (around line 8), add the fork badge after the existing `badge` span:

```html
      <div class="detail-title-row">
        <h1 class="detail-name">{{ entry.name }}</h1>
        <span class="badge badge--{{ entry.affiliation }}">{{ entry.affiliation }}</span>
        {%- if entry.isFork and entry.forkParentUrl %}
        <a class="fork-badge" href="{{ entry.forkParentUrl }}"
           target="_blank" rel="noopener noreferrer">⑂ {{ entry.forkParent }}</a>
        {%- endif %}
        {%- if entry.featured %}<span class="featured-star">★ featured</span>{%- endif %}
      </div>
```

- [ ] **Step 2: Add releases section after the links section**

In `src/_includes/entry-detail.njk`, after the closing `{%- endif %}` of the links section (after line 50), add:

```html
    {%- if entry.releases and entry.releases.length %}
    {%- set repoLink = entry.links | selectattr("type", "equalto", "repo") | first if entry.links else null %}
    <div class="detail-section">
      <div class="section-label">Releases</div>
      {%- if entry.latestStableRelease %}
      <div class="latest-callout">
        <span class="latest-badge">LATEST</span>
        <span class="latest-tag">{{ entry.latestStableRelease.tagName }}</span>
        <span class="latest-date" data-ts="{{ entry.latestStableRelease.publishedAt }}">{{ entry.latestStableRelease.publishedAt }}</span>
        <a class="release-notes-link" href="{{ entry.latestStableRelease.url }}"
           target="_blank" rel="noopener noreferrer">Release notes ↗</a>
      </div>
      {%- endif %}
      {%- if entry.releases | length > 1 %}
      <div class="release-history-list">
        {%- set latestTag = entry.latestStableRelease.tagName if entry.latestStableRelease else "" %}
        {%- for rel in entry.releases %}
        {%- if rel.tagName != latestTag %}
        <div class="rel-hist-row">
          <a class="rel-tag" href="{{ rel.url }}"
             target="_blank" rel="noopener noreferrer">{{ rel.tagName }}</a>
          {%- if rel.prerelease %}<span class="rel-pre">pre</span>{%- endif %}
          <span class="rel-date" data-ts="{{ rel.publishedAt }}">{{ rel.publishedAt }}</span>
        </div>
        {%- endif %}
        {%- endfor %}
      </div>
      {%- endif %}
      {%- for lnk in entry.links %}
      {%- if lnk.type == "repo" %}
      <a class="releases-all-link" href="{{ lnk.url }}/releases"
         target="_blank" rel="noopener noreferrer">See all releases on GitHub ↗</a>
      {%- endif %}
      {%- endfor %}
    </div>
    {%- endif %}
```

> **Note on `selectattr`:** Nunjucks does not have `selectattr` built in (it's a Jinja2 filter). The template above iterates `entry.links` with a `for` + `if` instead, which is idiomatic Nunjucks. The `repoLink` variable set at the top is unused — remove that line.

The corrected Step 2 block (without the unused `repoLink` set):

```html
    {%- if entry.releases and entry.releases.length %}
    <div class="detail-section">
      <div class="section-label">Releases</div>
      {%- if entry.latestStableRelease %}
      <div class="latest-callout">
        <span class="latest-badge">LATEST</span>
        <span class="latest-tag">{{ entry.latestStableRelease.tagName }}</span>
        <span class="latest-date" data-ts="{{ entry.latestStableRelease.publishedAt }}">{{ entry.latestStableRelease.publishedAt }}</span>
        <a class="release-notes-link" href="{{ entry.latestStableRelease.url }}"
           target="_blank" rel="noopener noreferrer">Release notes ↗</a>
      </div>
      {%- endif %}
      {%- if entry.releases | length > 1 %}
      {%- set latestTag = entry.latestStableRelease.tagName if entry.latestStableRelease else "" %}
      <div class="release-history-list">
        {%- for rel in entry.releases %}
        {%- if rel.tagName != latestTag %}
        <div class="rel-hist-row">
          <a class="rel-tag" href="{{ rel.url }}"
             target="_blank" rel="noopener noreferrer">{{ rel.tagName }}</a>
          {%- if rel.prerelease %}<span class="rel-pre">pre</span>{%- endif %}
          <span class="rel-date" data-ts="{{ rel.publishedAt }}">{{ rel.publishedAt }}</span>
        </div>
        {%- endif %}
        {%- endfor %}
      </div>
      {%- endif %}
      {%- for lnk in entry.links %}
      {%- if lnk.type == "repo" %}
      <a class="releases-all-link" href="{{ lnk.url }}/releases"
         target="_blank" rel="noopener noreferrer">See all releases on GitHub ↗</a>
      {%- endif %}
      {%- endfor %}
    </div>
    {%- endif %}
```

- [ ] **Step 3: Verify build**

```bash
cd /home/ttuser/code/tt-awesome
npm run build 2>&1 | tail -5
```

Expected: builds cleanly.

- [ ] **Step 4: Inject test release data to verify detail card rendering**

Temporarily add test data to `src/_data/github_meta.json` for one repo (e.g., `https://github.com/tenstorrent/tt-smi`) to verify the template renders correctly:

```bash
# Back up the file first
cp src/_data/github_meta.json src/_data/github_meta.json.bak
```

Open `src/_data/github_meta.json`, find the `https://github.com/tenstorrent/tt-smi` key and manually add test data:

```json
"https://github.com/tenstorrent/tt-smi": {
  "stars": 60,
  "updatedAt": "2026-05-21T17:34:51Z",
  "isFork": true,
  "forkParent": "Syllo/nvtop",
  "forkParentUrl": "https://github.com/Syllo/nvtop",
  "releases": [
    {
      "tagName": "v3.1.0",
      "name": "v3.1.0",
      "publishedAt": "2026-05-18T14:00:00Z",
      "url": "https://github.com/tenstorrent/tt-smi/releases/tag/v3.1.0",
      "prerelease": false
    },
    {
      "tagName": "v3.0.2",
      "name": "v3.0.2",
      "publishedAt": "2026-04-30T10:00:00Z",
      "url": "https://github.com/tenstorrent/tt-smi/releases/tag/v3.0.2",
      "prerelease": false
    },
    {
      "tagName": "v3.0.0-rc1",
      "name": "RC1",
      "publishedAt": "2026-04-15T10:00:00Z",
      "url": "https://github.com/tenstorrent/tt-smi/releases/tag/v3.0.0-rc1",
      "prerelease": true
    }
  ],
  "preview_image": "https://raw.githubusercontent.com/tenstorrent/tt-smi/main/images/tt_smi.png"
}
```

- [ ] **Step 5: Build and verify in browser**

```bash
cd /home/ttuser/code/tt-awesome
npm run serve
```

Open `http://localhost:8080`. Navigate: Hardware & System → tt-smi. Verify:
- Fork badge `⑂ Syllo/nvtop` appears in title row, links to `https://github.com/Syllo/nvtop`
- "RELEASES" section appears below Links
- "LATEST" callout shows `v3.1.0` with a relative date ("4 days ago" etc.) and "Release notes ↗" link
- History list shows `v3.0.2` and `v3.0.0-rc1` (with `pre` pill)
- "See all releases on GitHub ↗" link appears at the bottom
- Click "🏷 Recent Releases" in sidebar — `tt-smi v3.1.0` appears in the feed
- Click the row — detail card opens showing tt-smi

- [ ] **Step 6: Restore original github_meta.json**

```bash
cd /home/ttuser/code/tt-awesome
mv src/_data/github_meta.json.bak src/_data/github_meta.json
npm run build 2>&1 | tail -5
```

Expected: builds cleanly, releases section absent (no release data in JSON yet).

- [ ] **Step 7: Commit**

```bash
git add src/_includes/entry-detail.njk
git commit -m "feat: add fork badge and release history to entry detail card"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| fetch_github_meta: fork detection via existing repo call | Task 1 |
| fetch_github_meta: releases fetch (5 per repo, skip drafts) | Task 1 |
| github_meta.json gains isFork, forkParent, forkParentUrl, releases | Task 1 |
| entries.js: latestStableRelease pre-computed | Task 2 |
| recentReleases.js: top-50 stable feed sorted by publishedAt | Task 2 |
| Affiliated groups under Community in toggle | Task 5 `applyReleasesFilter` |
| Toggle: All / Official / Community | Tasks 4 + 5 |
| URL state: ?releases=all/official/community | Task 5 |
| ?releases=all&entry=X restores pane + detail | Task 5 `restoreFromUrl` |
| Fork badge in detail title row | Task 6 |
| Latest release callout in detail | Task 6 |
| Release history list (older releases) | Task 6 |
| Pre-releases shown in detail history, excluded from feed | Task 2 `recentReleases.js` (only stable in feed), Task 6 (prerelease shown in detail) |
| "See all on GitHub" footer link | Task 6 |
| Nightly workflow unchanged | No task needed — confirmed in spec |

All requirements covered. ✓
