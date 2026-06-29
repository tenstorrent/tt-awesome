# Feed Content Enrichment & llms.txt — Design

**Date:** 2026-06-29
**Branch:** `improvements/rss_and_atom`
**Status:** Approved (design)

## Problem

The site publishes four feeds, but every item carries only a short one-line
`<summary>` (the entry's description rendered as inline markdown). Three gaps:

1. **Releases are impoverished.** Rich, LLM-generated release summaries already
   exist in `src/_data/planet_feeds.json` (e.g. the multi-sentence tt-forge-onnx
   1.3.0 writeup produced by `scripts/summarize_releases.py`), but
   `feeds/releases.xml` and the release items in `feeds/feed.json` ignore them in
   favor of the boring string `"{name} released {tag}. Repository: {url}"`.
2. **No full content.** Atom and JSON Feed both distinguish a short `<summary>`
   from a full `<content>` / `content_html`. We only ever emit summary, so the
   author, typed links, tags, and categories that already live in every entry
   are wasted in the feed.
3. **No `llms.txt`.** There is no machine-navigable index for LLMs at `/llms.txt`
   (per llmstxt.org), despite the site being a curated directory ideally suited
   to one.

## Goals

- Wire the existing rich release summaries into both `releases.xml` and `feed.json`.
- Add a full, markdown-formatted `<content>` block to every feed item, while
  keeping `<summary>` a clean one-liner so it degrades gracefully.
- Publish a curated, category-organized `/llms.txt`.

## Consumption target: degrade gracefully

The feeds serve two audiences and the design must satisfy both:

- **General feed readers** (NetNewsWire, Feedly, Reeder) render full HTML
  `<content>` — links, lists, bold. This is where the rich block shines.
- **Slack's RSS app** strips most HTML and shows title + a plain-text snippet
  drawn from the summary. So `<summary>` must stay clean, meaningful text and
  never depend on HTML structure to make sense.

Rule: `<summary>` = clean one-liner; `<content>` = full rich HTML block.

## Architecture

Feed logic already lives in tested JS filters in `.eleventy.js`
(`jsonFeedItems`, `articleFeedItems`) with thin Nunjucks templates. We extend
that filter layer rather than pushing logic into Nunjucks, which the codebase
already documents as unreliable for this kind of work (see comments in
`entries.js` re: `selectattr` / loop-scope). Everything stays unit-testable
through the existing `tests/test_eleventy_filters.js` harness.

### Component 1 — Rich release summaries in `recentReleases.js`

`src/_data/recentReleases.js` gains a `summary` field per release item, resolved
from `planet_feeds.json`:

- Load `planet_feeds.json` via the existing `planetFeeds` loader pattern
  (`fs.existsSync` guard; return `[]` when absent — first build before nightly).
- Build a lookup from the `release`-type planet-feed items. Match a release to a
  summary by:
  1. Exact `url` match, then
  2. Fallback: the planet item's `url` starts with `{repoUrl}/releases/`
     (the same heuristic already proven in the `planetItems` filter).
- `summary` = matched planet-feed `description` (rich text) when found, else the
  existing fallback string `"{entryName} released {tagName}. Repository: {repoUrl}"`.

Because `releases.xml` reads `recentReleases` directly and `jsonFeedItems`
receives it as an argument, **both feeds get rich summaries from this one change.**
`jsonFeedItems` is updated to read `rel.summary` instead of recomputing the
fallback string inline.

### Component 2 — `feedContentHtml` filter

New filter in `.eleventy.js`. Output: an HTML string suitable for Atom
`<content type="html">` (wrapped in CDATA by the template) and JSON `content_html`.

**Input contract.** `feedContentHtml` accepts a single normalized object and
never reaches back into other globals:

```
{
  description: string,   // markdown; the rich summary or entry description
  links:       [{type, url, label}],   // all typed links to render
  author:      string?,  // bare handle, no "@"
  author_url:  string?,
  affiliation: string?,
  tags:        [string]?,
  categories:  [string]?,
  added_at:    string?,  // YYYY-MM-DD
}
```

- **`new-entries.xml`** passes the raw `entry` — it already has `links`,
  `author`, `author_url`, `tags`, `categories`, `added_at`. Compatible as-is.
- **`articles.xml`** — `articleFeedItems` is extended to carry the *entry's full*
  `links` array plus `author` / `author_url` (it already carries `entryDesc`,
  `affiliation`, `categories`, `added_at`). The template maps these onto the
  contract. `tags` is included when present on the entry.
- **`releases.xml`** — the template builds the contract object inline:
  `description` = the resolved rich `rel.summary`; `links` = repo + release-page
  links; `affiliation` from the release; `added_at` from `publishedAt`.
- **`feed.json`** — `jsonFeedItems` builds the same contract object per item and
  calls the shared builder so HTML matches the Atom feeds exactly.

Block structure (sections omitted when their data is absent):

1. **Description / summary** — rendered with a new block-level markdown renderer
   (`mdBlock`), so multi-paragraph release summaries get real `<p>` tags. Inline
   one-liners render as a single paragraph.
2. **Links** — `<p><strong>Links:</strong></p><ul>` of every typed link as
   `<a href="url">label</a>`. Label falls back to a title-cased type. Includes
   repo, website, article, paper, talk, video, demo.
3. **Attribution** — a line with author (`@handle`, linked to `author_url` when
   present), affiliation, and date added.
4. **Tags + categories** — comma-separated topic tags and category slugs.

A new `mdBlock = new MarkdownIt({ html: false, linkify: false })` with
`mdBlock.disable("image")` mirrors the existing `mdInline` safety posture
(escape raw HTML, no auto-fetching images) but keeps block wrappers. The link
list and metadata are emitted as literal, already-escaped HTML (URLs validated
upstream in `entries.js` via `isSafeHttpsUrl`; link/tag/author text escaped to
neutralize `<`, `>`, `&`).

### Component 3 — Template wiring

- **`feeds/new-entries.xml`** — keep existing `<summary type="html">` (clean
  inline description); add `<content type="html"><![CDATA[{{ entry | feedContentHtml | cdataSafe | safe }}]]></content>`.
- **`feeds/articles.xml`** — same: keep `<summary>`, add `<content>` built from
  the article-link item context.
- **`feeds/releases.xml`** — `<summary>` becomes the resolved `rel.summary`
  one-liner/rich text (clean); add `<content>` built from the release context
  (rich summary as paragraphs + repo/release links + affiliation).
- **`feeds/feed.json`** — `jsonFeedItems` sets `content_html` to the
  `feedContentHtml` block and keeps `summary` as the clean text per item type.

### Component 4 — `llms.txt`

New template `src/llms-txt.njk`, `permalink: /llms.txt`,
`eleventyExcludeFromCollections: true`. Built from `entries` + `categories`:

- `# tt-awesome` + a blockquote one-line summary of the directory.
- `## Feeds & Data` — links to the four feeds, `data.json`, and the README.
- One `##` section per category (using `categories` for title + slug), each a
  bulleted list of `- [name](url): description` for entries in that category.
  Prefer the repo link; fall back to first link or the homepage anchor. Trim
  description to a single line. Entries appear under each of their categories.

Generated at build time alongside the feeds, so it stays current automatically.
Follows the llmstxt.org structure (H1, blockquote, then `##` link sections).

## Out of scope

- Repo stars / latest-release stats inside the content block.
- A separate `llms-full.txt` dump.
- Any change to how `planet_feeds.json` / summaries are generated.

## Testing

Extend `tests/test_eleventy_filters.js` (plain `node` + `assert`, capturing
filters from the stub config — existing pattern):

- `feedContentHtml`:
  - emits a Links list containing every typed link with correct labels;
  - emits the attribution line (author handle, affiliation, date);
  - emits tags + categories;
  - omits sections whose data is absent (no links / no author / no tags);
  - escapes `<`, `>`, `&` in text fields; never emits an `<img>`.
- `recentReleases` summary resolution:
  - exact-URL match attaches the rich planet-feed description;
  - `{repoUrl}/releases/` fallback match works;
  - no match falls back to the `"{name} released {tag}"` string;
  - missing `planet_feeds.json` does not throw (returns fallback).
- `jsonFeedItems`: release items now carry `rel.summary` in `summary`, and
  `content_html` is the rich block; entry/article items carry the rich block in
  `content_html` and clean text in `summary`.

Run: `node tests/test_eleventy_filters.js` and a full `npm run build` to confirm
all four feeds and `/llms.txt` render as valid output.

## Docs

Update the README feeds section to document the `<content>` enrichment and the
new `/llms.txt` resource.
