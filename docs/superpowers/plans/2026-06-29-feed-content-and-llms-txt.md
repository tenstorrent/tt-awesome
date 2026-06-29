# Feed Content Enrichment & llms.txt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every RSS/Atom/JSON feed item a rich, markdown-formatted `<content>` block (links, attribution, tags) while keeping `<summary>` a clean one-liner, wire the existing LLM release summaries into the release feeds, and publish a curated `/llms.txt`.

**Architecture:** Extend the tested JS filter layer in `.eleventy.js` (where `jsonFeedItems`/`articleFeedItems` already live) rather than Nunjucks. A single `feedContentHtml` builder produces the rich HTML block from one normalized object shape. Each data source (`entries`, `articleFeedItems` output, `recentReleases`) is shaped to conform to that contract, so every template just pipes `X | feedContentHtml`. Templates stay thin and everything is unit-testable through `tests/test_eleventy_filters.js`.

**Tech Stack:** Eleventy (11ty), Nunjucks templates, `markdown-it`, Node's built-in `assert` for tests.

## Global Constraints

- License header on every new/modified source file (match existing):
  `// SPDX-License-Identifier: Apache-2.0` and `// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.`
- Markdown renderers MUST keep the existing safety posture: `new MarkdownIt({ html: false, linkify: false })` then `.disable("image")` — feeds carry untrusted external content; never emit `<img>` or raw HTML from source text.
- All HTML attribute/text interpolation in `feedContentHtml` MUST be escaped via `mdBlock.utils.escapeHtml`. URLs are already validated as safe https in `entries.js`, but escape them anyway.
- Site base URL for absolute links: `https://tenstorrent.github.io/tt-awesome/`.
- Atom `<content>` and `<summary>` that contain HTML use `type="html"` and wrap the value in `<![CDATA[ ... ]]>` piped through the existing `cdataSafe` filter.
- Tests are plain `node` scripts run with `node tests/test_eleventy_filters.js` (no test framework). Follow the existing stub-config harness at the top of that file.

---

### Task 1: `feedContentHtml` builder + block markdown renderer

**Files:**
- Modify: `.eleventy.js` (add `mdBlock` near the existing `mdInline` at lines 15-19; add `buildFeedContentHtml` function + `feedContentHtml` filter registration in the `addFilter` block)
- Test: `tests/test_eleventy_filters.js`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `mdBlock` — module-scope `MarkdownIt` with block rendering (`.render()`), same safety config as `mdInline`.
  - `buildFeedContentHtml(item)` — module-scope pure function returning an HTML string. Input shape (all fields optional except none required; missing → section omitted):
    ```
    { description: string, links: [{type, url, label}], author: string,
      author_url: string, affiliation: string, tags: [string],
      categories: [string], added_at: string }
    ```
  - `feedContentHtml` — Eleventy filter wrapping `buildFeedContentHtml`. Returns `""` for falsy input.

- [ ] **Step 1: Write the failing tests**

Add this block to `tests/test_eleventy_filters.js` just before the final `console.log("\nAll eleventy filter tests passed ✓");` line:

```js
// ── feedContentHtml tests ────────────────────────────────────────────────────
const feedContentHtml = filters["feedContentHtml"];
assert(typeof feedContentHtml === "function", "feedContentHtml filter not registered");
{
  const html = feedContentHtml({
    description: "Boltz-2 on **Blackhole**.",
    links: [
      { type: "repo", url: "https://github.com/test/repo", label: "GitHub" },
      { type: "article", url: "https://example.com/post" },
    ],
    author: "moritztng",
    author_url: "https://github.com/moritztng",
    affiliation: "community",
    tags: ["blackhole", "drug-discovery"],
    categories: ["ai-models"],
    added_at: "2026-05-13",
  });
  // description rendered as block markdown
  assert.ok(html.includes("<strong>Blackhole</strong>"), "renders markdown emphasis");
  // links list with both links; missing label falls back to title-cased type
  assert.ok(html.includes('<a href="https://github.com/test/repo">GitHub</a>'), "labeled link");
  assert.ok(html.includes('<a href="https://example.com/post">Article</a>'), "fallback label is title-cased type");
  // attribution: linked author handle, affiliation, added date
  assert.ok(html.includes('<a href="https://github.com/moritztng">@moritztng</a>'), "linked author handle");
  assert.ok(html.includes("community"), "affiliation present");
  assert.ok(html.includes("2026-05-13"), "added date present");
  // tags + categories
  assert.ok(html.includes("blackhole") && html.includes("ai-models"), "tags + categories present");
  console.log("✓ feedContentHtml: renders description, links, attribution, tags");
}
{
  // Missing sections are omitted, not rendered empty.
  const html = feedContentHtml({ description: "Just a description." });
  assert.ok(html.includes("Just a description."), "description present");
  assert.ok(!html.includes("<ul>"), "no links list when no links");
  assert.ok(!html.includes("Links:"), "no Links heading when no links");
  console.log("✓ feedContentHtml: omits absent sections");
}
{
  // Escapes HTML in text fields and never emits an <img>.
  const html = feedContentHtml({
    description: "![x](http://evil/pixel.gif)",
    author: "a<b>c",
    links: [{ type: "repo", url: "https://x/y", label: "<script>" }],
    tags: ["t&g"],
  });
  assert.ok(!html.includes("<img"), "no img from image markdown");
  assert.ok(!html.includes("<script>"), "label HTML escaped");
  assert.ok(html.includes("a&lt;b&gt;c"), "author HTML escaped");
  assert.ok(html.includes("t&amp;g"), "tag ampersand escaped");
  console.log("✓ feedContentHtml: escapes text fields, blocks images");
}
{
  assert.strictEqual(feedContentHtml(null), "", "null input → empty string");
  assert.strictEqual(feedContentHtml(undefined), "", "undefined input → empty string");
  console.log("✓ feedContentHtml: empty input safe");
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node tests/test_eleventy_filters.js`
Expected: FAIL — `AssertionError: feedContentHtml filter not registered`.

- [ ] **Step 3: Add the block markdown renderer**

In `.eleventy.js`, immediately after the `mdInline.disable("image");` line (currently line 19), add:

```js
// Block-level markdown renderer for full feed <content> blocks. Same safety
// posture as mdInline (no raw HTML, no auto-fetching images), but keeps block
// wrappers so multi-paragraph release summaries render as real <p> tags.
const mdBlock = new MarkdownIt({ html: false, linkify: false });
mdBlock.disable("image");

// Shared HTML escaper for text we interpolate directly into the content block.
const escapeHtml = mdBlock.utils.escapeHtml;

// Build the rich HTML <content> block shared by every feed (Atom <content
// type="html"> and JSON Feed content_html). Sections whose data is absent are
// omitted entirely. Accepts a single normalized object — see plan Task 1.
function buildFeedContentHtml(item) {
  if (!item) return "";
  const parts = [];

  // 1. Description / summary — block markdown (paragraphs preserved).
  if (item.description) parts.push(mdBlock.render(item.description));

  // 2. Links — every typed link as a labeled anchor. Label falls back to a
  //    title-cased link type (e.g. "article" → "Article").
  const links = (item.links || []).filter((l) => l && l.url);
  if (links.length) {
    const lis = links
      .map((l) => {
        const label = l.label
          ? escapeHtml(l.label)
          : l.type
          ? escapeHtml(l.type.charAt(0).toUpperCase() + l.type.slice(1))
          : escapeHtml(l.url);
        return `<li><a href="${escapeHtml(l.url)}">${label}</a></li>`;
      })
      .join("");
    parts.push(`<p><strong>Links:</strong></p>\n<ul>${lis}</ul>`);
  }

  // 3. Attribution — author (linked when we have a profile URL), affiliation,
  //    date added, separated by middots.
  const attr = [];
  if (item.author) {
    attr.push(
      item.author_url
        ? `By <a href="${escapeHtml(item.author_url)}">@${escapeHtml(item.author)}</a>`
        : `By @${escapeHtml(item.author)}`
    );
  }
  if (item.affiliation) attr.push(escapeHtml(item.affiliation));
  if (item.added_at) attr.push(`added ${escapeHtml(item.added_at)}`);
  if (attr.length) parts.push(`<p>${attr.join(" · ")}</p>`);

  // 4. Tags + categories — comma-separated, emphasized.
  const tagBits = [...(item.tags || []), ...(item.categories || [])];
  if (tagBits.length) {
    parts.push(`<p><em>${tagBits.map(escapeHtml).join(", ")}</em></p>`);
  }

  return parts.join("\n");
}
```

- [ ] **Step 4: Register the filter**

In `.eleventy.js`, inside `module.exports = function (eleventyConfig) { ... }`, add after the `markdownInline` filter registration (currently ends at line 38):

```js
  // Render the full rich HTML content block for a feed item. Pair with
  // `| cdataSafe | safe` in Atom templates. See buildFeedContentHtml above.
  eleventyConfig.addFilter("feedContentHtml", (item) => buildFeedContentHtml(item));
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `node tests/test_eleventy_filters.js`
Expected: PASS — all four new `✓ feedContentHtml:` lines print, no assertion errors.

- [ ] **Step 6: Commit**

```bash
git add .eleventy.js tests/test_eleventy_filters.js
git commit -m "feat: add feedContentHtml builder for rich feed content blocks"
```

---

### Task 2: Resolve rich release summaries in `recentReleases.js`

**Files:**
- Modify: `src/_data/recentReleases.js`
- Test: `tests/test_eleventy_filters.js`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent of Task 1).
- Produces:
  - `resolveReleaseSummary(rel, planetFeeds)` — module-scope pure function, exported as `module.exports.resolveReleaseSummary`. Returns the matched planet-feed `description` (rich text), else the fallback string `"{entryName} released {tagName}. Repository: {repoUrl}"`.
  - Each item returned by `recentReleases()` gains: `summary` (string), `description` (= summary, for `feedContentHtml`), `links` (`[{type:"repo",...},{type:"release",...}]`), `added_at` (`publishedAt` truncated to `YYYY-MM-DD`). Existing fields are unchanged.

- [ ] **Step 1: Write the failing tests**

Add a new test module `tests/test_recent_releases.js`:

```js
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Tests for resolveReleaseSummary in src/_data/recentReleases.js.
// Run with: node tests/test_recent_releases.js
const assert = require("assert");
const { resolveReleaseSummary } = require("../src/_data/recentReleases.js");

assert(typeof resolveReleaseSummary === "function", "resolveReleaseSummary not exported");

const rel = {
  entryName: "tt-forge-onnx",
  tagName: "1.3.0",
  repoUrl: "https://github.com/tenstorrent/tt-forge-onnx",
  url: "https://github.com/tenstorrent/tt-forge-onnx/releases/tag/1.3.0",
};

// Exact URL match → rich description.
{
  const feeds = [
    { type: "release", url: rel.url, description: "Rich synchronized-updates summary." },
  ];
  assert.strictEqual(resolveReleaseSummary(rel, feeds), "Rich synchronized-updates summary.");
  console.log("✓ resolveReleaseSummary: exact URL match returns rich description");
}

// Same-repo /releases/ + tag match (URLs differ slightly) → rich description.
{
  const feeds = [
    {
      type: "release",
      url: "https://github.com/tenstorrent/tt-forge-onnx/releases/1.3.0",
      description: "Fuzzy-matched summary.",
    },
  ];
  assert.strictEqual(resolveReleaseSummary(rel, feeds), "Fuzzy-matched summary.");
  console.log("✓ resolveReleaseSummary: same-repo + tag fallback match");
}

// No match → fallback string.
{
  const feeds = [
    { type: "release", url: "https://github.com/other/repo/releases/tag/9.9.9", description: "Unrelated." },
  ];
  assert.strictEqual(
    resolveReleaseSummary(rel, feeds),
    "tt-forge-onnx released 1.3.0. Repository: https://github.com/tenstorrent/tt-forge-onnx"
  );
  console.log("✓ resolveReleaseSummary: no match returns fallback string");
}

// Missing/empty feeds → fallback (does not throw).
{
  assert.strictEqual(
    resolveReleaseSummary(rel, []),
    "tt-forge-onnx released 1.3.0. Repository: https://github.com/tenstorrent/tt-forge-onnx"
  );
  assert.strictEqual(
    resolveReleaseSummary(rel, undefined),
    "tt-forge-onnx released 1.3.0. Repository: https://github.com/tenstorrent/tt-forge-onnx"
  );
  console.log("✓ resolveReleaseSummary: empty/undefined feeds safe");
}

// Non-release feed items are ignored.
{
  const feeds = [{ type: "article", url: rel.url, description: "Should be ignored." }];
  assert.ok(resolveReleaseSummary(rel, feeds).startsWith("tt-forge-onnx released"),
    "non-release items ignored");
  console.log("✓ resolveReleaseSummary: ignores non-release feed items");
}

console.log("\nAll recentReleases tests passed ✓");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test_recent_releases.js`
Expected: FAIL — `AssertionError: resolveReleaseSummary not exported` (or a `TypeError` on the destructure).

- [ ] **Step 3: Implement the resolver and enrich items**

In `src/_data/recentReleases.js`, add `fs`/`path` requires at the top (after the license header) and the resolver function above `module.exports`:

```js
const fs = require("fs");
const path = require("path");

// Load planet_feeds.json (the source of LLM-generated release summaries).
// Returns [] when absent (first build before the nightly summarize job runs).
function loadPlanetFeeds() {
  const p = path.join(__dirname, "planet_feeds.json");
  if (!fs.existsSync(p)) return [];
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch (_) {
    return [];
  }
}

// Resolve a human-quality summary for a release. Prefers the LLM-generated
// description from planet_feeds.json (matched by exact release URL, then by
// same-repo /releases/ path + tag name), falling back to a terse one-liner.
function resolveReleaseSummary(rel, planetFeeds) {
  const feeds = planetFeeds || [];
  // 1. Exact URL match.
  for (const item of feeds) {
    if (item.type !== "release" || !item.description) continue;
    if (item.url === rel.url) return item.description;
  }
  // 2. Same-repo release whose URL carries the same tag (handles html_url vs
  //    tag-url shape differences between GitHub's API and the summarizer).
  if (rel.repoUrl && rel.tagName) {
    const prefix = rel.repoUrl + "/releases/";
    for (const item of feeds) {
      if (item.type !== "release" || !item.description || !item.url) continue;
      if (item.url.startsWith(prefix) && item.url.includes(rel.tagName)) {
        return item.description;
      }
    }
  }
  // 3. Fallback one-liner.
  return `${rel.entryName} released ${rel.tagName}.` +
    (rel.repoUrl ? ` Repository: ${rel.repoUrl}` : "");
}
```

Then, inside the existing `module.exports = function () { ... }`, after the `releases.push({...})` loop populates each release but before the final `sort`, enrich each item. Replace the existing `releases.push({ ... })` call so it also captures what we need, then add enrichment after the loop:

```js
  const planetFeeds = loadPlanetFeeds();
  for (const rel of releases) {
    rel.summary = resolveReleaseSummary(rel, planetFeeds);
    // Conform to the feedContentHtml contract (see .eleventy.js Task 1):
    rel.description = rel.summary;
    rel.added_at = rel.publishedAt ? rel.publishedAt.slice(0, 10) : "";
    rel.links = [
      rel.repoUrl ? { type: "repo", url: rel.repoUrl, label: "Repository" } : null,
      rel.url ? { type: "release", url: rel.url, label: rel.tagName } : null,
    ].filter(Boolean);
  }
```

Finally, at the very bottom of the file (after `module.exports = function ...`), export the resolver for testing:

```js
module.exports.resolveReleaseSummary = resolveReleaseSummary;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test_recent_releases.js`
Expected: PASS — all five `✓ resolveReleaseSummary:` lines print.

- [ ] **Step 5: Commit**

```bash
git add src/_data/recentReleases.js tests/test_recent_releases.js
git commit -m "feat: resolve rich LLM release summaries in recentReleases"
```

---

### Task 3: Wire rich content into the JSON feed (`jsonFeedItems`)

**Files:**
- Modify: `.eleventy.js` (the `jsonFeedItems` filter, lines 174-253)
- Test: `tests/test_eleventy_filters.js`

**Interfaces:**
- Consumes: `buildFeedContentHtml` (Task 1); `rel.summary` (Task 2).
- Produces: each JSON Feed item's `content_html` is now the rich block; release items' `summary` is `rel.summary`.

- [ ] **Step 1: Update the existing failing test (Test 9b)**

In `tests/test_eleventy_filters.js`, find Test 9b (the `✓ jsonFeedItems: items carry rendered content_html + plain summary` block). Replace its two `content_html` assertions so they expect the rich block instead of a bare inline render:

```js
  // content_html is now the rich block — it CONTAINS the rendered description.
  assert.ok(entryItem.content_html.includes("<code>tt_metal</code>"),
    "content_html renders the description as markdown");
  assert.strictEqual(entryItem.summary, "Uses `tt_metal` under the hood.",
    "summary stays plain text");
  assert.ok(items.every((i) => typeof i.content_html === "string"),
    "every item has content_html");
```

Also add a new release-summary assertion right after Test 8 (`✓ jsonFeedItems: release items have correct shape`):

```js
// Test 8b: release items use rel.summary as their summary text.
{
  const rel = makeRelease({ summary: "Rich release summary here." });
  const items = jsonFeedItems([], [rel]);
  assert.strictEqual(items[0].summary, "Rich release summary here.",
    "release summary comes from rel.summary");
  assert.ok(items[0].content_html.includes("Rich release summary here."),
    "release content_html renders the summary");
  console.log("✓ jsonFeedItems: release items use rel.summary");
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node tests/test_eleventy_filters.js`
Expected: FAIL — Test 9b assertion `content_html renders the description as markdown` fails (current code sets `content_html` to the bare inline render, which equals `Uses <code>tt_metal</code> under the hood.` and DOES include `<code>tt_metal</code>` — so this passes — but Test 8b fails because `rel.summary` is undefined in current code and summary is the computed one-liner). Confirm Test 8b fails with a summary mismatch.

- [ ] **Step 3: Update `jsonFeedItems`**

In `.eleventy.js`, in the `jsonFeedItems` filter:

(a) Release items (the first `for (const rel of recentReleases || [])` loop) — replace the body so summary/content use the resolved fields:

```js
    for (const rel of recentReleases || []) {
      const summary = rel.summary ||
        `${rel.entryName} released ${rel.tagName}. Repository: ${rel.repoUrl}`;
      items.push({
        id:             rel.url,
        url:            rel.url,
        title:          `${rel.entryName} ${rel.tagName}`,
        content_html:   buildFeedContentHtml(rel),
        summary:        summary,
        date_published: rel.publishedAt,
        tags:           [rel.affiliation, "release"].filter(Boolean),
      });
    }
```

(b) Entry items (the `2a.` push) — set `content_html` to the rich block:

```js
        content_html:   buildFeedContentHtml(entry),
```

(c) Article-link items (the `2b.` push) — same: the entry conforms to the contract, so render its block:

```js
          content_html:   buildFeedContentHtml(entry),
```

Leave every `summary:` field as-is (entry/article summary stays `entry.description`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `node tests/test_eleventy_filters.js`
Expected: PASS — `✓ jsonFeedItems: release items use rel.summary` and all existing jsonFeedItems lines print.

- [ ] **Step 5: Commit**

```bash
git add .eleventy.js tests/test_eleventy_filters.js
git commit -m "feat: rich content_html + LLM release summaries in JSON feed"
```

---

### Task 4: Extend `articleFeedItems` to carry content-block fields

**Files:**
- Modify: `.eleventy.js` (the `articleFeedItems` filter, lines 128-160)
- Test: `tests/test_eleventy_filters.js`

**Interfaces:**
- Consumes: nothing new.
- Produces: each `articleFeedItems` output object additionally carries `description` (= entry description), `links` (entry's full links array), `author`, `author_url`, `tags` — so the object conforms to the `feedContentHtml` contract. Existing fields (`entryId`, `entryName`, `entryDesc`, `affiliation`, `categories`, `linkType`, `linkUrl`, `linkLabel`, `added_at`) are unchanged.

- [ ] **Step 1: Write the failing test**

Add after the existing articleFeedItems tests (before the jsonFeedItems section) in `tests/test_eleventy_filters.js`:

```js
// articleFeedItems carries fields needed by feedContentHtml.
{
  const entry = makeEntry({
    author: "alice",
    author_url: "https://github.com/alice",
    tags: ["blackhole"],
    links: [
      { type: "repo", url: "https://github.com/test/repo" },
      { type: "article", url: "https://example.com/article", label: "Read more" },
    ],
  });
  const items = articleFeedItems([entry], 50);
  const it = items[0];
  assert.strictEqual(it.description, "A test entry.", "carries entry description");
  assert.strictEqual(it.author, "alice", "carries author");
  assert.strictEqual(it.author_url, "https://github.com/alice", "carries author_url");
  assert.deepStrictEqual(it.tags, ["blackhole"], "carries tags");
  assert.strictEqual(it.links.length, 2, "carries entry's full links array");
  console.log("✓ articleFeedItems: carries feedContentHtml contract fields");
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/test_eleventy_filters.js`
Expected: FAIL — `it.description` is `undefined` (current code only sets `entryDesc`).

- [ ] **Step 3: Add the fields to the pushed object**

In `.eleventy.js`, in the `articleFeedItems` filter, extend the `items.push({ ... })` object with the contract fields (keep all existing keys):

```js
        items.push({
          entryId:    entry.id,
          entryName:  entry.name,
          entryDesc:  entry.description || "",
          affiliation: entry.affiliation || "",
          categories: entry.categories || [],
          linkType:   link.type,
          linkUrl:    link.url,
          linkLabel:  link.label || (link.type.charAt(0).toUpperCase() + link.type.slice(1)),
          added_at:   entry.added_at || "1970-01-01",
          // feedContentHtml contract fields:
          description: entry.description || "",
          links:      entry.links || [],
          author:     entry.author || "",
          author_url: entry.author_url || "",
          tags:       entry.tags || [],
        });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test_eleventy_filters.js`
Expected: PASS — `✓ articleFeedItems: carries feedContentHtml contract fields`.

- [ ] **Step 5: Commit**

```bash
git add .eleventy.js tests/test_eleventy_filters.js
git commit -m "feat: carry content-block fields through articleFeedItems"
```

---

### Task 5: Add `<content>` to the three Atom feeds

**Files:**
- Modify: `src/feeds/new-entries.njk`
- Modify: `src/feeds/articles.njk`
- Modify: `src/feeds/releases.njk`

**Interfaces:**
- Consumes: `feedContentHtml` filter (Task 1); `recentReleases` items conforming to the contract (Task 2); `articleFeedItems` items conforming to the contract (Task 4); entries already conform.
- Produces: each Atom `<entry>` now has a `<content type="html">` alongside its existing `<summary>`.

No unit test — verified by a full build (Step 4) and feed validity check.

- [ ] **Step 1: `new-entries.xml` — add `<content>` after `<summary>`**

In `src/feeds/new-entries.njk`, after the existing `<summary ...>` line (line 25) and before `<category term="{{ entry.affiliation }}"/>`, add:

```njk
    {#- Full rich content block for feed readers; summary above stays a clean
        one-liner so Slack's RSS app (which flattens HTML) still reads well. #}
    <content type="html"><![CDATA[{{ entry | feedContentHtml | cdataSafe | safe }}]]></content>
```

- [ ] **Step 2: `articles.xml` — add `<content>` after `<summary>`**

In `src/feeds/articles.njk`, after the existing `<summary ...>` line (line 23) and before `<category term="{{ item.linkType }}"/>`, add:

```njk
    <content type="html"><![CDATA[{{ item | feedContentHtml | cdataSafe | safe }}]]></content>
```

- [ ] **Step 3: `releases.xml` — use rich summary + add `<content>`**

In `src/feeds/releases.njk`, replace the existing `<summary>` line (line 22):

```njk
    <summary>{{ rel.entryName }} released {{ rel.tagName }}. Repository: {{ rel.repoUrl }}</summary>
```

with the resolved summary (kept as plain text so Slack reads cleanly) plus a content block:

```njk
    <summary type="html"><![CDATA[{{ rel.summary | markdownInline | cdataSafe | safe }}]]></summary>
    <content type="html"><![CDATA[{{ rel | feedContentHtml | cdataSafe | safe }}]]></content>
```

- [ ] **Step 4: Build and verify all three feeds render**

Run: `npm run build`
Expected: build completes with no errors. Then verify each feed contains a `<content` element and is well-formed:

```bash
grep -c "<content" _site/feeds/new-entries.xml _site/feeds/articles.xml _site/feeds/releases.xml
```
Expected: each file reports a count ≥ 1 (one `<content>` per entry).

Verify XML well-formedness (catches an unescaped/early-closed CDATA):

```bash
for f in new-entries articles releases; do xmllint --noout "_site/feeds/$f.xml" && echo "$f ok"; done
```
Expected: `new-entries ok`, `articles ok`, `releases ok` with no parse errors.

- [ ] **Step 5: Commit**

```bash
git add src/feeds/new-entries.njk src/feeds/articles.njk src/feeds/releases.njk
git commit -m "feat: add rich <content> blocks to Atom feeds"
```

---

### Task 6: Add the `/llms.txt` template

**Files:**
- Create: `src/llms-txt.njk`

**Interfaces:**
- Consumes: the `entries` and `categories` Eleventy data globals (already used by `src/index.njk`).
- Produces: `/llms.txt` at the site root.

No unit test — verified by build (Step 3).

- [ ] **Step 1: Inspect the categories data shape**

Run: `node -e "console.log(JSON.stringify(require('./src/_data/categories.js')().slice(0,2),null,2))" 2>/dev/null || node -e "console.log(JSON.stringify(require('./src/_data/categories.js').slice(0,2),null,2))"`
Expected: prints category objects. Confirm each has a `slug`, a display `name` (or `title`), and note the exact property names for use in Step 2. (If the export is an array, the second command prints; if a function, the first.)

- [ ] **Step 2: Create the template**

Create `src/llms-txt.njk`. Use the property names confirmed in Step 1 (this plan assumes `cat.slug` and `cat.name`; adjust if Step 1 shows `cat.title`):

```njk
---
permalink: /llms.txt
eleventyExcludeFromCollections: true
---
# tt-awesome

> A curated directory of projects, tools, models, and research for Tenstorrent hardware — contributed by the community and the Tenstorrent team. Generated from the entries in this repository.

## Feeds & Data

- [JSON Feed](https://tenstorrent.github.io/tt-awesome/feeds/feed.json): combined releases, entries, and articles (JSON Feed 1.1).
- [New Entries (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/new-entries.xml): newly added projects and resources.
- [Articles & Resources (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/articles.xml): articles, papers, lessons, talks, videos, demos.
- [Recent Releases (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/releases.xml): latest stable releases.
- [data.json](https://tenstorrent.github.io/tt-awesome/data.json): the full machine-readable entry database.
- [README](https://github.com/tenstorrent/tt-awesome/blob/main/README.md): human-readable directory.
{% for cat in categories %}
## {{ cat.name }}
{% for entry in entries | sort(false, false, "name") %}{% if entry.categories and (cat.slug in entry.categories) %}{%- set repoLink = entry.links | selectattr("type", "equalto", "repo") | first %}{%- set anyLink = entry.links | first %}
- [{{ entry.name }}]({{ repoLink.url if repoLink else (anyLink.url if anyLink else "https://tenstorrent.github.io/tt-awesome/#" + entry.id) }}): {{ entry.description | striptags | replace("\n", " ") }}
{%- endif %}{% endfor %}
{% endfor %}
```

- [ ] **Step 3: Build and verify**

Run: `npm run build`
Expected: build completes; `_site/llms.txt` exists.

```bash
head -20 _site/llms.txt
```
Expected: starts with `# tt-awesome`, the blockquote summary, a `## Feeds & Data` section, then `## <Category>` sections with `- [name](url): description` bullets. Confirm no `[object Object]` or empty `()` links.

- [ ] **Step 4: Commit**

```bash
git add src/llms-txt.njk
git commit -m "feat: publish curated /llms.txt site index"
```

---

### Task 7: Document the feed enrichment and llms.txt in the README

**Files:**
- Modify: `README.md` (the feeds section)

**Interfaces:** none.

- [ ] **Step 1: Locate the feeds section**

Run: `grep -n "feeds/\|feed.json\|Atom\|RSS\|llms" README.md | head -20`
Expected: line numbers for the existing feeds documentation. Note the section heading.

- [ ] **Step 2: Update the feeds documentation**

In the feeds section of `README.md`, update the description so it states that:
- Each Atom/JSON item now carries a full rich `<content>` block (description, links, attribution, tags) in addition to a short `<summary>`;
- Release feed items use the LLM-generated release summaries when available;
- A curated `/llms.txt` index is published at `https://tenstorrent.github.io/tt-awesome/llms.txt`.

Add an `llms.txt` bullet to the feeds/resources list using the same style as the existing feed bullets (match the surrounding markdown — do not invent a new format). Keep wording factual and concise.

- [ ] **Step 3: Verify the README still generates cleanly (if applicable)**

Run: `grep -n "llms.txt" README.md`
Expected: the new bullet appears. (The README's auto-generated entry list is produced by `scripts/generate_readme.py`; this edit is to the hand-written feeds section only — do not edit the auto-generated entry blocks.)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document rich feed content and /llms.txt"
```

---

### Task 8: Full verification

**Files:** none (verification only).

- [ ] **Step 1: Run all JS tests**

Run: `node tests/test_eleventy_filters.js && node tests/test_recent_releases.js`
Expected: both end with `All ... tests passed ✓`, no assertion errors.

- [ ] **Step 2: Run the Python test suite (unchanged, confirm no regressions)**

Run: `python3 -m pytest tests/ -q`
Expected: all pass (this change does not touch Python, so the suite should be green).

- [ ] **Step 3: Full build + feed validity**

Run: `npm run build && for f in new-entries articles releases; do xmllint --noout "_site/feeds/$f.xml" && echo "$f ok"; done && node -e "JSON.parse(require('fs').readFileSync('_site/feeds/feed.json','utf8')); console.log('feed.json ok')" && test -f _site/llms.txt && echo "llms.txt ok"`
Expected: `new-entries ok`, `articles ok`, `releases ok`, `feed.json ok`, `llms.txt ok`.

- [ ] **Step 4: Spot-check rendered content**

Run: `grep -A2 "<content" _site/feeds/releases.xml | head -20`
Expected: a release `<content>` block containing the rich LLM summary text (for a release that has one in `planet_feeds.json`), a `Links:` list, and an affiliation line.

---

## Self-Review

**Spec coverage:**
- Rich release summaries wired into releases.xml + feed.json → Tasks 2, 3, 5. ✓
- `feedContentHtml` block (description, links, attribution, tags/categories) → Task 1. ✓
- summary vs content / graceful degradation → Tasks 3 (JSON), 5 (Atom; summary stays clean). ✓
- All four feeds enriched → Task 3 (feed.json) + Task 5 (three Atom feeds). ✓
- llms.txt curated, category-organized → Task 6. ✓
- Tests for feedContentHtml + recentReleases + jsonFeedItems → Tasks 1, 2, 3, 4. ✓
- README docs → Task 7. ✓
- Out of scope (stars/release stats in block, llms-full.txt) → not present. ✓

**Placeholder scan:** No TBD/TODO; all code blocks complete. Task 6 Step 1 explicitly resolves the one unknown (categories property names) before writing the template, and Task 6 Step 2 notes the fallback. ✓

**Type consistency:** `buildFeedContentHtml(item)` contract is defined in Task 1 and every producer (entries — native; `recentReleases` — Task 2; `articleFeedItems` — Task 4) is shaped to it. `resolveReleaseSummary(rel, planetFeeds)` signature is consistent between Task 2 definition and its test. `rel.summary` produced in Task 2, consumed in Task 3. ✓
