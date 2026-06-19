// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Tests for articleFeedItems and jsonFeedItems Eleventy filters.
// Run with: node tests/test_eleventy_filters.js

const assert = require("assert");

// ── Extract filters from .eleventy.js without running Eleventy ───────────────
// We call the module export with a stub eleventyConfig that captures addFilter
// calls, then test the registered functions directly.

const filters = {};
const stubConfig = {
  addFilter: (name, fn) => { filters[name] = fn; },
  addPassthroughCopy: () => {},
  addShortcode: () => {},
};

// Stub fs so .eleventy.js doesn't fail on missing entry files for inlineFile
const fs = require("fs");
const _origReadFileSync = fs.readFileSync;
fs.readFileSync = function(p, enc) {
  if (typeof p === "string" && (p.endsWith("style.css") || p.endsWith("main.js"))) return "";
  return _origReadFileSync.apply(this, arguments);
};

require("../.eleventy.js")(stubConfig);

fs.readFileSync = _origReadFileSync;

const articleFeedItems = filters["articleFeedItems"];
const jsonFeedItems    = filters["jsonFeedItems"];

assert(typeof articleFeedItems === "function", "articleFeedItems filter not registered");
assert(typeof jsonFeedItems    === "function", "jsonFeedItems filter not registered");

// ── Shared test fixtures ──────────────────────────────────────────────────────

function makeEntry(overrides) {
  return {
    id:          "test-entry",
    name:        "Test Entry",
    description: "A test entry.",
    affiliation: "official",
    categories:  ["kernels"],
    added_at:    "2026-03-01",
    links: [
      { type: "repo",    url: "https://github.com/test/repo" },
      { type: "article", url: "https://example.com/article", label: "Read more" },
    ],
    ...overrides,
  };
}

function makeRelease(overrides) {
  return {
    entryId:     "test-entry",
    entryName:   "Test Entry",
    affiliation: "official",
    tagName:     "v1.0.0",
    publishedAt: "2026-04-01T00:00:00Z",
    url:         "https://github.com/test/repo/releases/tag/v1.0.0",
    repoUrl:     "https://github.com/test/repo",
    ...overrides,
  };
}

// ── articleFeedItems tests ────────────────────────────────────────────────────

// Test 1: only article-type links are included
{
  const entry = makeEntry();
  const items = articleFeedItems([entry], 50);
  assert.strictEqual(items.length, 1, "should emit 1 article item");
  assert.strictEqual(items[0].linkUrl, "https://example.com/article");
  assert.strictEqual(items[0].linkType, "article");
  console.log("✓ articleFeedItems: only article-type links included");
}

// Test 2: repo links are excluded
{
  const entry = makeEntry({ links: [{ type: "repo", url: "https://github.com/test/repo" }] });
  const items = articleFeedItems([entry], 50);
  assert.strictEqual(items.length, 0, "repo links should not appear in articles feed");
  console.log("✓ articleFeedItems: repo links excluded");
}

// Test 3: all six article types are included
{
  const types = ["article", "lesson", "paper", "talk", "video", "demo"];
  const links = types.map((t, i) => ({ type: t, url: `https://example.com/${t}` }));
  const entry = makeEntry({ links });
  const items = articleFeedItems([entry], 50);
  assert.strictEqual(items.length, types.length, `all ${types.length} article types should be included`);
  const gotTypes = items.map((i) => i.linkType).sort();
  assert.deepStrictEqual(gotTypes, types.slice().sort());
  console.log("✓ articleFeedItems: all six article link types included");
}

// Test 4: deduplication by URL across entries
{
  const url = "https://example.com/shared-article";
  const e1 = makeEntry({ id: "e1", links: [{ type: "article", url }] });
  const e2 = makeEntry({ id: "e2", links: [{ type: "article", url }] });
  const items = articleFeedItems([e1, e2], 50);
  assert.strictEqual(items.length, 1, "duplicate URLs should be deduplicated");
  console.log("✓ articleFeedItems: deduplicates by URL across entries");
}

// Test 5: limit is respected
{
  const entries = Array.from({ length: 10 }, (_, i) =>
    makeEntry({ id: `e${i}`, links: [{ type: "article", url: `https://example.com/a${i}` }] })
  );
  const items = articleFeedItems(entries, 3);
  assert.strictEqual(items.length, 3, "limit should cap output at 3");
  console.log("✓ articleFeedItems: limit parameter respected");
}

// Test 6: items are sorted by entry added_at descending
{
  const old  = makeEntry({ id: "old",  added_at: "2026-01-01", links: [{ type: "paper", url: "https://example.com/old" }] });
  const mid  = makeEntry({ id: "mid",  added_at: "2026-03-01", links: [{ type: "paper", url: "https://example.com/mid" }] });
  const newE = makeEntry({ id: "new",  added_at: "2026-05-01", links: [{ type: "paper", url: "https://example.com/new" }] });
  const items = articleFeedItems([old, mid, newE], 50);
  assert.strictEqual(items[0].added_at, "2026-05-01", "newest entry should be first");
  assert.strictEqual(items[2].added_at, "2026-01-01", "oldest entry should be last");
  console.log("✓ articleFeedItems: sorted by added_at descending");
}

// Test 7: entry with missing added_at falls back to 1970-01-01
{
  const entry = makeEntry({ added_at: undefined, links: [{ type: "article", url: "https://example.com/no-date" }] });
  const items = articleFeedItems([entry], 50);
  assert.strictEqual(items[0].added_at, "1970-01-01");
  console.log("✓ articleFeedItems: missing added_at falls back to 1970-01-01");
}

// ── jsonFeedItems tests ───────────────────────────────────────────────────────

// Test 8: release items appear with correct shape
{
  const rel = makeRelease();
  const items = jsonFeedItems([], [rel]);
  assert.strictEqual(items.length, 1);
  const item = items[0];
  assert.strictEqual(item.id, rel.url);
  assert.strictEqual(item.url, rel.url);
  assert.ok(item.title.includes(rel.tagName), "title should include tagName");
  assert.ok(item.tags.includes("release"));
  assert.ok(item.tags.includes("official"));
  console.log("✓ jsonFeedItems: release items have correct shape");
}

// Test 9: entry items appear with correct shape
{
  const entry = makeEntry({ links: [{ type: "repo", url: "https://github.com/test/repo" }] });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  assert.ok(entryItem, "should have an entry-tagged item");
  assert.strictEqual(entryItem.url, "https://github.com/test/repo");
  assert.ok(entryItem.tags.includes("official"));
  assert.ok(entryItem.tags.includes("kernels"));
  console.log("✓ jsonFeedItems: entry items have correct shape");
}

// Test 9b: items carry content_html (JSON Feed 1.1 requires content_html or
// content_text) with inline markdown rendered; summary stays plain text.
{
  const entry = makeEntry({
    description: "Uses `tt_metal` under the hood.",
    links: [{ type: "repo", url: "https://github.com/test/repo" }],
  });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  assert.strictEqual(entryItem.content_html, "Uses <code>tt_metal</code> under the hood.",
    "content_html renders inline markdown");
  assert.strictEqual(entryItem.summary, "Uses `tt_metal` under the hood.",
    "summary stays plain text");
  assert.ok(items.every((i) => typeof i.content_html === "string"),
    "every item has content_html");
  console.log("✓ jsonFeedItems: items carry rendered content_html + plain summary");
}

// Test 10: article-type links produce article items
{
  const entry = makeEntry();
  const items = jsonFeedItems([entry], []);
  const articleItem = items.find((i) => i.tags.includes("article"));
  assert.ok(articleItem, "should have an article-tagged item");
  assert.strictEqual(articleItem.url, "https://example.com/article");
  console.log("✓ jsonFeedItems: article link items produced");
}

// Test 11: output is sorted newest-first by date_published
{
  const oldRel = makeRelease({ publishedAt: "2025-01-01T00:00:00Z", url: "https://github.com/test/repo/releases/tag/v0.1" });
  const newRel = makeRelease({ publishedAt: "2026-06-01T00:00:00Z", url: "https://github.com/test/repo/releases/tag/v2.0" });
  const entry  = makeEntry({ added_at: "2026-03-01", links: [{ type: "repo", url: "https://github.com/test/repo" }] });
  const items  = jsonFeedItems([entry], [oldRel, newRel]);
  // Verify strict descending order
  for (let i = 0; i < items.length - 1; i++) {
    assert.ok(
      items[i].date_published >= items[i + 1].date_published,
      `items[${i}] (${items[i].date_published}) should be >= items[${i+1}] (${items[i+1].date_published})`
    );
  }
  assert.strictEqual(items[0].date_published, "2026-06-01T00:00:00Z", "newest item should be first");
  console.log("✓ jsonFeedItems: output sorted newest-first by date_published");
}

// Test 12: empty affiliation is filtered from tags
{
  const entry = makeEntry({ affiliation: "", links: [{ type: "repo", url: "https://github.com/test/repo" }] });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  assert.ok(!entryItem.tags.includes(""), "empty affiliation should not appear in tags");
  console.log("✓ jsonFeedItems: empty affiliation filtered from tags");
}

// Test 13: entries without repo link fall back to first available link URL
{
  const entry = makeEntry({ links: [{ type: "article", url: "https://example.com/article" }] });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  // anyLink fallback: uses the article URL rather than the homepage anchor
  assert.strictEqual(entryItem.url, "https://example.com/article", "no-repo entry should use first available link URL");
  console.log("✓ jsonFeedItems: no-repo entry falls back to first available link URL");
}

// Test 14: entries with no links at all fall back to anchor URL
{
  const entry = makeEntry({ links: [] });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  assert.ok(entryItem.url.includes("#test-entry"), "linkless entry should use anchor fallback");
  console.log("✓ jsonFeedItems: linkless entry falls back to anchor URL");
}

// ── planetItems tests ───────────────────────────────────────────────────────

const planetItems = filters["planetItems"];
const monthLabel  = filters["monthLabel"];
const monthKey    = filters["monthKey"];

assert(typeof planetItems  === "function", "planetItems filter not registered");
assert(typeof monthLabel   === "function", "monthLabel filter not registered");
assert(typeof monthKey     === "function", "monthKey filter not registered");

// Test 15: article links appear in planet items
{
  const entry = makeEntry({ links: [
    { type: "repo",    url: "https://github.com/test/repo" },
    { type: "paper",   url: "https://arxiv.org/abs/1234.5678", label: "arXiv:1234.5678" },
  ]});
  const items = planetItems([entry], [], []);
  assert.strictEqual(items.length, 1, "only article-type links, not repo");
  assert.strictEqual(items[0].type, "paper");
  assert.strictEqual(items[0].url, "https://arxiv.org/abs/1234.5678");
  assert.strictEqual(items[0].title, "Test Entry", "title should be entry.name, not link.label");
  assert.strictEqual(items[0].label, "arXiv:1234.5678", "label is the link citation, shown as source");
  assert.strictEqual(items[0].projectId, "test-entry");
  console.log("✓ planetItems: article links included with correct shape");
}

// Test 16: releases appear with type "release"
{
  const rel = makeRelease();
  const items = planetItems([], [rel], []);
  assert.strictEqual(items.length, 1);
  assert.strictEqual(items[0].type, "release");
  assert.strictEqual(items[0].projectId, "test-entry");
  assert.ok(items[0].title.includes("v1.0.0"));
  assert.ok(items[0].date.match(/^\d{4}-\d{2}-\d{2}$/), "date should be YYYY-MM-DD");
  console.log("✓ planetItems: releases included with correct shape");
}

// Test 17: output sorted newest-first
{
  const old  = makeEntry({ id: "old",  added_at: "2025-01-01", links: [{ type: "article", url: "https://example.com/old" }] });
  const newE = makeEntry({ id: "newE", added_at: "2026-06-01", links: [{ type: "article", url: "https://example.com/new" }] });
  const items = planetItems([old, newE], [], []);
  assert.strictEqual(items[0].date, "2026-06-01", "newest first");
  assert.strictEqual(items[1].date, "2025-01-01", "oldest last");
  console.log("✓ planetItems: sorted newest-first");
}

// Test 18: deduplication by URL
{
  const e1 = makeEntry({ id: "e1", links: [{ type: "article", url: "https://example.com/same" }] });
  const e2 = makeEntry({ id: "e2", links: [{ type: "article", url: "https://example.com/same" }] });
  const items = planetItems([e1, e2], [], []);
  assert.strictEqual(items.length, 1, "duplicate URLs deduplicated");
  console.log("✓ planetItems: deduplicates by URL");
}

// Test 19: all six article types included
{
  const types = ["article", "lesson", "paper", "talk", "video", "demo"];
  const links = types.map((t) => ({ type: t, url: `https://example.com/${t}` }));
  const entry = makeEntry({ links });
  const items = planetItems([entry], [], []);
  assert.strictEqual(items.length, types.length);
  const gotTypes = items.map((i) => i.type).sort();
  assert.deepStrictEqual(gotTypes, types.slice().sort());
  console.log("✓ planetItems: all six article types included");
}

// Test 20: monthLabel converts correctly
{
  assert.strictEqual(monthLabel("2026-05"),    "May 2026");
  assert.strictEqual(monthLabel("2026-05-01"), "May 2026");
  assert.strictEqual(monthLabel("2026-01"),    "January 2026");
  assert.strictEqual(monthLabel("2026-12-31"), "December 2026");
  assert.strictEqual(monthLabel(""),           "");
  console.log("✓ monthLabel: converts YYYY-MM and YYYY-MM-DD correctly");
}

// Test 21: monthKey slices YYYY-MM from date strings
{
  assert.strictEqual(monthKey("2026-05-01"), "2026-05");
  assert.strictEqual(monthKey("2026-12-31"), "2026-12");
  assert.strictEqual(monthKey("2026-05"),    "2026-05");
  assert.strictEqual(monthKey(""),           "");
  assert.strictEqual(monthKey(null),         "");
  console.log("✓ monthKey: slices YYYY-MM correctly");
}

// Test 22: monthLabel guards invalid month numbers
{
  assert.strictEqual(monthLabel("2026-00-15"), "2026-00-15"); // month 0 → returns dateStr
  assert.strictEqual(monthLabel("2026-13-01"), "2026-13-01"); // month 13 → returns dateStr
  console.log("✓ monthLabel: guards out-of-range month numbers");
}

// Test 23: planetItems excludes dev releases (all known patterns)
{
  const mkRel = (tagName, url) => ({
    entryId: "x", entryName: "X", affiliation: "official",
    tagName, publishedAt: "2026-05-30T00:00:00Z",
    url: `https://github.com/test/x/releases/tag/${url || tagName}`, repoUrl: "https://github.com/test/x",
  });
  const devRels = [
    mkRel("1.2.0.dev20260530"),          // forge pattern: .dev<digits>
    mkRel("v0.72.0-dev20260529"),         // tt-metal pattern: -dev<digits>
    mkRel("v0.9.5-dev.260424"),           // tt-metal pattern: -dev.<digits>
  ];
  const stableRel = mkRel("v1.0.0");
  const items = planetItems([], [...devRels, stableRel], []);
  const releaseItems = items.filter((i) => i.type === "release");
  assert.strictEqual(releaseItems.length, 1, "only stable release should appear");
  assert.strictEqual(releaseItems[0].label, "v1.0.0");
  console.log("✓ planetItems: excludes .dev, -dev, and -dev.<digits> release tags");
}

// Test 24: approved external items appear
{
  const extApproved1 = {
    type: "video", source: "youtube", approved: true,
    title: "TT Video", url: "https://www.youtube.com/watch?v=abc",
    description: "A video.", date: "2026-06-01", dateISO: "2026-06-01T00:00:00Z",
    label: "Tenstorrent — YouTube", projectName: "Tenstorrent", projectId: null, affiliation: "official",
  };
  const extApproved2 = {
    type: "article", source: "reddit", approved: true,
    title: "Reddit Post", url: "https://reddit.com/r/test/1",
    description: "A post.", date: "2026-06-01", dateISO: "2026-06-01T00:00:00Z",
    label: "r/tenstorrent", projectName: "r/tenstorrent", projectId: null, affiliation: "community",
  };
  const extUnapproved = {
    type: "article", source: "reddit", approved: false,
    title: "Unapproved Post", url: "https://reddit.com/r/test/2",
    description: "Not yet.", date: "2026-06-01", dateISO: "2026-06-01T00:00:00Z",
    label: "r/tenstorrent", projectName: "r/tenstorrent", projectId: null, affiliation: "community",
  };
  const items = planetItems([], [], [extApproved1, extApproved2, extUnapproved]);
  const urls = items.map(i => i.url);
  assert.strictEqual(items.length, 2, "unapproved external items should be excluded");
  assert.ok(urls.includes("https://www.youtube.com/watch?v=abc"), "approved YouTube item included");
  assert.ok(urls.includes("https://reddit.com/r/test/1"), "approved Reddit item included");
  assert.ok(!urls.includes("https://reddit.com/r/test/2"), "unapproved item excluded");
  console.log("✓ planetItems: approved external items included, unapproved excluded");
}

// ── markdownInline tests ────────────────────────────────────────────────────
const markdownInline = filters["markdownInline"];
assert(typeof markdownInline === "function", "markdownInline filter not registered");

{
  // Inline markdown is converted to HTML.
  assert.strictEqual(
    markdownInline("Adds `ARC_MSG_QCB_PTR` register support"),
    "Adds <code>ARC_MSG_QCB_PTR</code> register support",
    "backticks become <code>"
  );
  assert.strictEqual(markdownInline("**bold** and _em_"),
    "<strong>bold</strong> and <em>em</em>", "bold/em rendered");
  assert.strictEqual(markdownInline("see [docs](https://example.com)"),
    'see <a href="https://example.com">docs</a>', "links rendered");

  // No block wrapper — output nests safely inside <p>.
  assert.ok(!markdownInline("plain text").includes("<p>"), "renderInline adds no <p> wrapper");

  // Falsy input is safe.
  assert.strictEqual(markdownInline(""), "", "empty string → empty");
  assert.strictEqual(markdownInline(undefined), "", "undefined → empty");

  // Raw HTML from (untrusted) feed sources is escaped, not emitted.
  const xss = markdownInline('<img src=x onerror=alert(1)> hi');
  assert.ok(!xss.includes("<img"), "raw HTML is escaped, not passed through");
  // Dangerous link schemes are neutralized by markdown-it's link validator:
  // the syntax is left as inert text rather than becoming a clickable anchor.
  const js = markdownInline("[x](javascript:alert(1))");
  assert.ok(!/<a\b/.test(js) && !js.includes('href="javascript'),
    "javascript: links are not rendered as anchors");
  // Image syntax must not produce an <img> — it auto-fetches (tracking pixel)
  // and this runs on untrusted feed content.
  assert.ok(!markdownInline("![x](http://evil/pixel.gif)").includes("<img"),
    "image markdown does not produce an <img> tag");
  console.log("✓ markdownInline: renders inline markdown, escapes HTML, blocks images + bad links");
}

// ── cdataSafe tests ─────────────────────────────────────────────────────────
const cdataSafe = filters["cdataSafe"];
assert(typeof cdataSafe === "function", "cdataSafe filter not registered");
{
  assert.strictEqual(cdataSafe("a]]>b"), "a]]]]><![CDATA[>b",
    "]]> is split so it cannot close the CDATA section early");
  assert.strictEqual(cdataSafe("no markers here"), "no markers here", "plain text untouched");
  assert.strictEqual(cdataSafe(""), "", "empty input safe");
  assert.strictEqual(cdataSafe(undefined), "", "undefined input safe");
  console.log("✓ cdataSafe: neutralizes ]]> sequences");
}

console.log("\nAll eleventy filter tests passed ✓");
