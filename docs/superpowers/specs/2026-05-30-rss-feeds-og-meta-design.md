# Design: RSS Feeds & Open Graph Meta Tags

**Date:** 2026-05-30  
**Branch:** feat/rss+more  
**Status:** Approved

## Overview

Add open-format syndication feeds and improved Open Graph / Twitter meta tags to the tt-awesome GitHub Pages site. All feed generation happens inside the existing Eleventy build pass — no new build steps or dependencies. A one-time migration script backfills an `added_at` date field onto all existing entries using git history.

---

## 1. Feeds

Four feeds, all output by Eleventy Nunjucks templates at build time.

### 1.1 Feed URLs and formats

| Feed | Output path | Format | Content |
|------|-------------|--------|---------|
| Recent Releases | `_site/feeds/releases.xml` | Atom 1.0 | Latest stable release per project, newest-first. Max 50 items. |
| New Entries | `_site/feeds/new-entries.xml` | Atom 1.0 | Entries ordered by `added_at` descending. Max 50 items. |
| Articles | `_site/feeds/articles.xml` | Atom 1.0 | Links of type `article`, `lesson`, `paper`, `talk`, `video`, `demo` across all entries, deduplicated by URL, ordered by entry `added_at` descending. Max 50 items. |
| JSON Feed | `_site/feeds/feed.json` | JSON Feed 1.1 | All-in-one feed combining new entries, releases, and articles into a unified item list. |

### 1.2 Eleventy template approach

Each feed is a file in `src/feeds/`:
- `src/feeds/releases.njk` → outputs `feeds/releases.xml`
- `src/feeds/new-entries.njk` → outputs `feeds/new-entries.xml`
- `src/feeds/articles.njk` → outputs `feeds/articles.xml`
- `src/feeds/feed.njk` → outputs `feeds/feed.json`

Each template sets `permalink` and `eleventyExcludeFromCollections: true` in front matter. The Atom templates use standard Atom 1.0 structure with `<feed>`, `<entry>`, `<id>` (using the entry's repo URL as the IRI), `<title>`, `<updated>`, `<link>`, and `<summary>`.

### 1.3 Feed autodiscovery

`base.njk` `<head>` gets four `<link rel="alternate">` tags pointing to each feed. This allows feed readers and crawlers to auto-discover the feeds from any page load.

### 1.4 Data sources

- **Releases feed:** Uses the existing `recentReleases` data collection from `src/_data/recentReleases.js`. No changes needed to that file.
- **New entries feed:** Uses the `entries` data collection, sorted by `added_at` descending.
- **Articles feed:** Derived at template time by iterating all entries, collecting links whose `type` is in `{article, lesson, paper, talk, video, demo}`, deduplicating by URL, and sorting by the parent entry's `added_at` (entries without `added_at` sort to the end, using `updatedAt` from github_meta as a secondary fallback).
- **JSON Feed:** Iterates the same three data sources and merges them into a single `items` array sorted by date descending. Each item has: `id` (URL), `title`, `summary`, `url`, `date_published` (ISO 8601), and `tags` (entry categories + a feed-type tag like `"release"`, `"entry"`, or `"article"`).

---

## 2. `added_at` field

### 2.1 Backfill script

`scripts/backfill_added_at.py` — run once before or during the first build on this branch.

Algorithm:
1. For each `.json` file under `entries/`, check if `added_at` is already set; skip if so.
2. Run `git log --follow --diff-filter=A --format="%ai" -- <file>` to find the commit that first added the file.
3. Parse the date portion (`YYYY-MM-DD`) from the output.
4. Write `"added_at": "YYYY-MM-DD"` into the file (preserving all other fields).
5. Print a summary of files updated vs. skipped.

If `git log` returns no output for a file (e.g., untracked), the script skips it with a warning.

### 2.2 Schema validation

`scripts/validate.py` gets a new soft check: entries missing `added_at` emit a warning (not an error) so the build doesn't break but contributors are nudged to add it.

### 2.3 New entries going forward

`scripts/add_entry.py` is updated to auto-populate `added_at` with today's date (`datetime.date.today().isoformat()`) when creating a new entry JSON.

---

## 3. Open Graph & Twitter meta tags

### 3.1 Static social card image

A new `src/assets/og-card.svg` (1200×630) is created — a simple dark-background card with "⚡ tt-awesome" and the tagline "A curated list of Tenstorrent awesomeness". SVG is used so the asset is text-based and diff-friendly. **Caveat:** Twitter/X and Facebook do not support SVG for `og:image`; a future step should generate `og-card.png` at build time (e.g. via `sharp` or `resvg`) and reference that instead.

### 3.2 `base.njk` head block improvements

The existing static OG/Twitter block is replaced with a richer one:

```
og:type        = website
og:site_name   = tt-awesome
og:title       = tt-awesome — A curated list of Tenstorrent awesomeness
og:description = <dynamic: "Discover N projects across M categories — tools, AI models, kernels, compilers, and more for Tenstorrent hardware.">
og:url         = https://tenstorrent.github.io/tt-awesome/
og:image       = https://tenstorrent.github.io/tt-awesome/assets/og-card.svg
                 (SVG for now; replace with og-card.png for full Twitter/Facebook support)

twitter:card        = summary  (stays summary until a PNG card is available)
twitter:site        = @tenstorrent
twitter:title       = (same as og:title)
twitter:description = (same as og:description)
```

The description uses the `entries | length` and `categories | length` values already available in the template — so it reflects the real count at build time.

### 3.3 JSON-LD structured data

A `<script type="application/ld+json">` block is added to `base.njk`:

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "tt-awesome",
  "url": "https://tenstorrent.github.io/tt-awesome/",
  "description": "...",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://tenstorrent.github.io/tt-awesome/?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

Entry count and category count are rendered inline from Eleventy data at build time.

---

## 4. Files changed / created

| File | Change |
|------|--------|
| `scripts/backfill_added_at.py` | **New** — one-time git-blame backfill |
| `scripts/add_entry.py` | **Update** — auto-populate `added_at` on new entries |
| `scripts/validate.py` | **Update** — soft warning for missing `added_at` |
| `src/feeds/releases.njk` | **New** — Atom feed for releases |
| `src/feeds/new-entries.njk` | **New** — Atom feed for new entries |
| `src/feeds/articles.njk` | **New** — Atom feed for articles/links |
| `src/feeds/feed.njk` | **New** — JSON Feed 1.1 combined feed |
| `src/assets/og-card.svg` | **New** — 1200×630 social card (SVG; PNG needed for full Twitter/Facebook support) |
| `src/_includes/base.njk` | **Update** — richer OG/Twitter tags, JSON-LD, feed autodiscovery links |
| `entries/**/*.json` | **Update** — `added_at` field backfilled by script |

---

## 5. Out of scope

- Per-entry or per-category OG tags (SPA architecture; crawlers only see one HTML document)
- Server-side rendering or dynamic meta tag injection
- Feed hosting beyond GitHub Pages (feeds are static files)
- Podcast/media enclosure feeds
