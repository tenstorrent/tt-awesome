# Recent Releases Feature — Design Spec

**Date:** 2026-05-22  
**Branch:** feat/release-tracker  
**Status:** Approved, ready for implementation

---

## Overview

Add a "Recent Releases" section to tt-awesome that tracks tagged GitHub releases (not just pushes to main) across all featured projects. The feed shows the 50 most recent stable releases, newest first, with a toggle between All / Official / Community views. Individual project detail cards gain a release history section and a fork indicator.

---

## Decisions Log

| Question | Decision |
|---|---|
| Dual-view treatment | Toggle pill (All / Official / Community) inside pane |
| Affiliated affiliation in toggle | Groups under "Community" |
| Fork indicator style | Badge `⑂ owner/repo` in title row, links to parent |
| Detail card history style | Latest callout + compact older list |
| Releases fetched per project | 5 |
| Feed cap | 50 entries |
| Prerelease handling | Show in per-project detail history only; exclude from main feed |

---

## Section 1: Data Layer

### 1.1 `scripts/fetch_github_meta.py` changes

**Fork detection** — the existing `/repos/{owner}/{repo}` call already returns `fork: bool` and `parent: {full_name, html_url}`. Extract and store these; no additional API request needed.

**Release fetch** — add one new call per repo:
```
GET /repos/{owner}/{repo}/releases?per_page=5
```
- Skip drafts (`draft: true`)
- Include prereleases (stored in data; filtered at render time)
- Store up to 5 results

**Updated `github_meta.json` schema per repo entry:**
```json
{
  "stars": 60,
  "updatedAt": "2026-05-18T...",
  "preview_image": "...",
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
      "publishedAt": "2026-04-30T...",
      "url": "...",
      "prerelease": false
    }
  ]
}
```

Fields `isFork`, `forkParent`, `forkParentUrl`, and `releases` are omitted (not written) when not applicable — repos with no releases get no `releases` key; non-forks get no fork keys.

### 1.2 `src/_data/entries.js` — no changes

`Object.assign(entry, metaByUrl[repoLink.url])` already merges all `github_meta.json` fields onto entries. The new fields (`isFork`, `forkParent`, `forkParentUrl`, `releases`) flow through automatically.

### 1.3 New `src/_data/recentReleases.js`

Derives the release feed at Eleventy build time. No runtime cost.

Logic:
1. Call `entries()` to get all visible entries with merged meta
2. For each entry, find `releases[0]` where `prerelease === false` (first stable release)
3. Skip entries with no qualifying release
4. Map to: `{ entryId, entryName, affiliation, categories, tagName, publishedAt, url }`
5. Sort by `publishedAt` descending
6. Slice to 50

**Affiliation grouping for the toggle:**
- `official` filter → `affiliation === 'official'`
- `community` filter → `affiliation === 'community' || affiliation === 'affiliated'`
- `all` filter → everything

The `recentReleases` array is passed to templates via Eleventy's data cascade.

---

## Section 2: Releases Pane

### 2.1 Sidebar (`src/_includes/sidebar.njk`)

Add a `🏷 Recent Releases` sidebar item above the category `<hr>`, wired to `selectReleases('all')`. Active state uses the existing `.sidebar-item.active` styling.

```html
<a class="sidebar-item" id="releases-item"
   href="?releases=all"
   onclick="selectReleases('all'); return false;">
  🏷 Recent Releases
</a>
<hr class="sidebar-hr">
<div class="sidebar-label">Categories</div>
```

### 2.2 New `src/_includes/releases-list.njk`

A `.releases-pane` div rendered alongside the existing `.list-pane` inside `.panes`. Visibility is toggled via a `releases-active` class on `.panes`.

**Structure:**
```
.releases-pane
  .list-head
    .list-title  "🏷 Recent Releases"
    .list-count  "N releases"
    .releases-toggle
      button[data-rview=all]       "All"
      button[data-rview=official]  "Official"
      button[data-rview=community] "Community"
  .list-rows
    for each release in recentReleases:
      .release-row[data-affiliation][data-id]
        .row-top
          .row-name   entry name
          .badge      affiliation badge
          .rel-tag    version tag (monospace)
        .row-sub      relative date (rendered as data-ts ISO; JS converts to "N days ago")
```

Each `.release-row` click calls `selectEntry(entryId, correspondingEntryRow)` — navigates to the project's detail card in the right panel. The tag/version itself is not a link; the release notes link lives inside the detail card.

### 2.3 CSS additions (`src/assets/style.css`)

- `.releases-pane` — same dimensions and flex behavior as `.list-pane`
- `.panes.releases-active .list-pane { display: none }` and `.panes:not(.releases-active) .releases-pane { display: none }`
- `.panes.home-active .releases-pane { display: none }` — hide on home view
- `.releases-toggle` — flex row, inherits `.chip`-style toggle buttons
- `.release-row` — same base as `.entry-row`
- `.rel-tag` — `font-family: monospace; color: var(--teal-lt); background: rgba(79,209,197,0.08); padding: 1px 6px; border-radius: 3px; font-size: 10px;`
- `.rel-pre` — small gold pill for prerelease label
- `.release-row.rview-hidden { display: none }` — applied by JS toggle

### 2.4 JavaScript additions (`src/assets/main.js`)

**New state variable:** `activeReleasesView = 'all'` (values: `'all'`, `'official'`, `'community'`)

**New functions:**
- `selectReleases(view)` — pushes `?releases={view}` URL, calls `_applyReleases(view)`
- `_applyReleases(view)` — sets `releases-active` on `.panes`, activates sidebar item, calls `applyReleasesFilter(view)`
- `applyReleasesFilter(view)` — toggles `rview-hidden` on `.release-row` elements based on `data-affiliation` matching the view; updates count display
- `toggleReleasesView(btn)` — called by toggle buttons, calls `selectReleases(btn.dataset.rview)`

**`restoreFromUrl()` update:** check for `releases` param; if present, call `_applyReleases(value)`.

**`selectEntry()` update:** when `releases-active` is set on `.panes`, push `?releases={activeReleasesView}&entry={id}` instead of `?cat=null&entry={id}`. The `.release-row` element is passed as `el` to `_applyEntry` directly — `_applyEntry` clears all `.entry-row` active states then calls `el.classList.add('active')`, which works correctly whether `el` is an `.entry-row` or a `.release-row`.

**`applyFilters()` update:** when `releases-active` is set, skip the regular entry filter (it operates on `.entry-row` elements only and is unaffected).

### 2.5 URL scheme

| URL | State |
|---|---|
| `?releases=all` | Releases pane, all toggle active |
| `?releases=official` | Releases pane, official toggle active |
| `?releases=community` | Releases pane, community toggle active |
| `?releases=all&entry=tt-smi` | Releases pane + entry detail open |

---

## Section 3: Entry Detail Additions

### 3.1 Fork badge (`src/_includes/entry-detail.njk`)

In `.detail-title-row`, after the affiliation badge, render conditionally:

```njk
{%- if entry.isFork and entry.forkParentUrl %}
<a class="fork-badge" href="{{ entry.forkParentUrl }}"
   target="_blank" rel="noopener noreferrer">⑂ {{ entry.forkParent }}</a>
{%- endif %}
```

**CSS:** `font-size: 9px; color: var(--teal-lt); border: 1px solid rgba(79,209,197,0.35); background: transparent; padding: 1px 7px; border-radius: 6px; text-decoration: none; font-family: ui-monospace, monospace;`  
Hover: `border-color: var(--teal); color: var(--teal);`

### 3.2 Releases section (`src/_includes/entry-detail.njk`)

Added as a new `detail-section` after the Links section. Rendered only when `entry.releases` is non-empty.

**Structure:**
```
.detail-section  (conditional: entry.releases exists and length > 0)
  .section-label  "RELEASES"
  .latest-callout  (first release in entry.releases where prerelease=false, if any — GitHub returns newest-first so this may not be index 0)
    .latest-badge   "LATEST"
    .latest-tag     tagName
    .latest-date    publishedAt (data-ts attr; JS converts to relative)
    a.release-notes-link  "Release notes ↗"  → entry.releases[0].url
  .release-history-list
    for each release in entry.releases starting at index 1:
      .rel-hist-row
        a.rel-tag  → release.url (external)
        .rel-pre   (if prerelease)
        .rel-date  (data-ts; relative time)
  a.releases-all-link  "See all releases on GitHub ↗"  → repoUrl + /releases
```

**Relative-time rendering:** A small helper in `main.js` (`relativeTime(isoString)`) converts ISO timestamps to "N days ago" / "N weeks ago" / "N months ago". Called on `DOMContentLoaded` for all elements with a `data-ts` attribute.

**CSS additions:**
- `.latest-callout` — `background: rgba(79,209,197,0.06); border: 1px solid rgba(79,209,197,0.2); border-radius: 6px; padding: 8px 12px; display: flex; align-items: center; gap: 10px; margin-bottom: 8px;`
- `.latest-badge` — `font-size: 8px; background: var(--teal); color: var(--bg0); padding: 1px 5px; border-radius: 3px; font-weight: 700;`
- `.latest-tag` — `font-size: 13px; font-family: ui-monospace, monospace; color: var(--teal); font-weight: 700;`
- `.latest-date`, `.release-notes-link` — muted/teal-lt small text
- `.release-notes-link { margin-left: auto }`
- `.rel-hist-row` — same as `.rel-row-a` from mockup
- `.releases-all-link` — `font-size: 10px; color: var(--teal); display: block; text-align: right; margin-top: 4px;`

---

## Section 4: Nightly Workflow

No workflow changes required. The existing nightly CI job runs `fetch_github_meta.py` and opens a PR updating `github_meta.json`. The new release and fork fields are simply included in that same file. The `recentReleases.js` data file is computed at build time from the updated JSON, so the deploy step picks it up automatically.

API budget impact: adds one request per repo (releases endpoint). 77 repos → 77 additional requests per nightly run. Well within GitHub's rate limits (5,000 req/hr authenticated).

---

## Files Changed

| File | Change type |
|---|---|
| `scripts/fetch_github_meta.py` | Modify — add fork fields + releases fetch |
| `src/_data/github_meta.json` | Auto-generated (updated by script) |
| `src/_data/recentReleases.js` | New |
| `src/_includes/sidebar.njk` | Modify — add releases nav item |
| `src/_includes/releases-list.njk` | New |
| `src/_includes/entry-detail.njk` | Modify — fork badge + releases section |
| `src/index.njk` | Modify — include releases-list.njk in panes |
| `src/assets/main.js` | Modify — releases nav, toggle, relative-time helper |
| `src/assets/style.css` | Modify — releases pane, badges, callout styles |

---

## Out of Scope

- Per-project release RSS feed
- Release body / changelog text (just tag + date + link)
- Webhook-triggered updates (nightly is sufficient)
- Filtering the releases feed by category/hardware
