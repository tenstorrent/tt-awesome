# Static per-entry pages for crawlability

**Date:** 2026-07-09 · **Branch:** `make_crawlable`

## Problem

The site is a single-page app at one URL. Every entry's detail card is
server-rendered into `index.html` but hidden (`display: none`); JavaScript
reads `?entry=<id>` from the query string and adds `.visible` to the matching
`.detail-card`. This defeats crawlers — kapa.ai specifically:

1. **No discoverable per-entry URLs.** Entry rows are `<div onclick>`, not
   anchors, so a crawler starting at the root finds no links to `?entry=`
   URLs and only ever renders the home view, where no card is `.visible`.
2. **Query-string URLs are unreliable crawl targets.** GitHub Pages returns
   byte-identical HTML for every `?entry=` value, so crawlers dedupe or strip
   them. Even with JS rendering and a wait-for-class, `.detail-card.visible`
   never appears.
3. **No attribution.** All ~115 entries share one URL; nothing in the HTML
   (title, meta, canonical) says which entry a URL refers to.

## Solution

Add build-time static pages — one real HTML document per entry — alongside
the untouched SPA. Same Eleventy build, GitHub Pages just serves more files.
Crawlers and humans see the same content at the same URL (no cloaking; this
is progressive enhancement).

### 1. Per-entry pages: `/entry/<id>/`

A new template (`src/entry-pages.njk`) paginates `entries` with `size: 1`:

```yaml
pagination:
  data: entries
  size: 1
  alias: entry
permalink: "entry/{{ entry.id }}/"
```

Each page:

- Wraps the entry content in a single stable, always-visible container:
  `<article id="entry-content">`. This is the reliable selector kapa (or any
  extractor) targets — present in raw HTML, no JS, no wait-for-class.
- Reuses the detail-card markup. Extract the card body from
  `src/_includes/entry-detail.njk` into a shared partial
  (`src/_includes/entry-card-body.njk`) included by both the SPA detail pane
  and the static page, so the two never drift.
- Is a standalone, styled, readable page (site header, existing CSS) with a
  prominent **"Open in tt-awesome →"** link to `/?entry=<id>`. No
  auto-redirect — humans landing from a citation or search result get a real
  page, not a flash-and-bounce.
- Carries per-entry `<title>`, `<meta name="description">` (the entry
  description), `og:title`/`og:description`, and
  `<link rel="canonical" href="…/entry/<id>/">`.
- Static-page JS is limited to nonessential niceties (e.g. relative dates);
  all content renders without JS.

### 2. Discovery: `sitemap.xml` + real anchors

- New `src/sitemap.njk` → `/sitemap.xml` listing the root, `/planet/`, and
  every `/entry/<id>/` page. Kapa's crawler is pointed at the sitemap (or the
  root) — no JS rendering needed, no query strings involved.
- SPA entry rows become real anchors: `<a class="entry-row"
  href="entry/<id>/">`. `main.js` intercepts clicks (`preventDefault`) and
  runs the existing `selectEntry()` SPA behavior, so in-app UX is unchanged
  while crawlers and no-JS users follow the real link. Keyboard/middle-click
  open the static page — acceptable and arguably correct.

### 3. Canonical host

Feeds currently hardcode `https://tenstorrent.github.io/tt-awesome/`; kapa
crawls `https://docs.tenstorrent.com/tt-awesome/`. Introduce a site data var
(`src/_data/site.js` with `baseUrl`) used by the sitemap and canonical tags.
Set it to `https://docs.tenstorrent.com/tt-awesome/` (the user-facing host).
Feeds keep their existing URLs — Atom `<id>` values must never change.

### 4. `AGENTS.md` — declare the site's intent to agents

A standardized `AGENTS.md` (per the agents.md convention) at the repo root,
also copied into the build so it is fetchable at `…/tt-awesome/AGENTS.md`.

Its job is to state the intent explicitly: **agentic-oriented developers need
prior art, tools, articles, and latest releases to accomplish goals, and
tt-awesome + Planet Tenstorrent provide that in a form agents can rely on and
utilize.** Concretely it covers:

- **What this is:** a curated, machine-readable directory of the Tenstorrent
  ecosystem (projects, models, tools, guides, research), plus Planet
  Tenstorrent (`/planet/`) aggregating community articles — check here first
  for prior art before building something new.
- **Machine surfaces and when to use each:**
  - `data.json` — the full entry database (richest; structured fields:
    links, releases, packages, tags, hardware).
  - `/entry/<id>/` pages — one readable HTML document per entry
    (`#entry-content`), discoverable via `/sitemap.xml`.
  - `llms.txt` — compact categorized index for LLM context.
  - Feeds (`/feeds/*.xml`, `/feeds/feed.json`) — new entries, articles, and
    **latest releases**, updated by nightly CI.
- **Freshness:** GitHub metadata and release data refresh nightly via CI, so
  release/version info here can be trusted as current.
- **Contributing:** entries live as one file each under `entries/`; how to
  add or correct one.

### 5. Optional follow-up (not in this change): `llms-full.txt`

A full-content variant of the existing `/llms.txt` for direct LLM ingestion.
Deferred; the static pages alone solve the kapa problem.

## Compatibility guarantees

- `?entry=` bookmarks: unchanged — SPA routing (`restoreFromUrl`,
  `pushState`) is untouched.
- RSS/Atom/JSON feeds: untouched files; entry links already point at external
  repo URLs, never `?entry=`.
- `llms.txt`, `data.json`: untouched.
- No existing URL changes or redirects; this change is purely additive.

## Kapa configuration (after deploy)

- Source: website crawler seeded with `…/sitemap.xml` (or root URL).
- Extraction selector: `#entry-content`.
- JS rendering: **off**.

## Testing

- Build assertions (existing `tests/` conventions): `_site/entry/<id>/
  index.html` exists for every non-hidden entry; each contains
  `id="entry-content"`, the entry name, and a canonical link; `sitemap.xml`
  lists every entry page; `curl`-style check that raw HTML (no JS) contains
  the entry description.
- `AGENTS.md` exists at repo root and is copied into `_site/` by the build.
- Manual: click a row (SPA behavior intact), open `/entry/<id>/` directly,
  disable JS and browse via row links.
