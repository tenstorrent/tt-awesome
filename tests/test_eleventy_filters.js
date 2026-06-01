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

console.log("\nAll eleventy filter tests passed ✓");
