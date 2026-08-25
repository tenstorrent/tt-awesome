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
  const base = {
    entryId:     "test-entry",
    entryName:   "Test Entry",
    affiliation: "official",
    tagName:     "v1.0.0",
    publishedAt: "2026-04-01T00:00:00Z",
    url:         "https://github.com/test/repo/releases/tag/v1.0.0",
    repoUrl:     "https://github.com/test/repo",
    ...overrides,
  };
  // Conform to feedContentHtml contract: description = summary
  if (!base.description && base.summary) base.description = base.summary;
  return base;
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

// Test 8: articleFeedItems carries fields needed by feedContentHtml.
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

// ── jsonFeedItems tests ───────────────────────────────────────────────────────

// Test 9: release items appear with correct shape
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

// Test 9b: release items use rel.summary as their summary text.
{
  const rel = makeRelease({ summary: "Rich release summary here." });
  const items = jsonFeedItems([], [rel]);
  assert.strictEqual(items[0].summary, "Rich release summary here.",
    "release summary comes from rel.summary");
  assert.ok(items[0].content_html.includes("Rich release summary here."),
    "release content_html renders the summary");
  console.log("✓ jsonFeedItems: release items use rel.summary");
}

// Test 9c: release with no rel.summary falls back to the one-liner string.
{
  const rel = makeRelease(); // no summary field
  const items = jsonFeedItems([], [rel]);
  assert.strictEqual(
    items[0].summary,
    "Test Entry released v1.0.0. Repository: https://github.com/test/repo",
    "release summary falls back to one-liner when rel.summary absent"
  );
  console.log("✓ jsonFeedItems: release summary falls back to one-liner");
}

// Test 10: entry items appear with correct shape
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

// Test 10b: items carry content_html (JSON Feed 1.1 requires content_html or
// content_text) — now a rich block with inline markdown rendered inside it; summary stays plain text.
{
  const entry = makeEntry({
    description: "Uses `tt_metal` under the hood.",
    links: [{ type: "repo", url: "https://github.com/test/repo" }],
  });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  // content_html is now the rich block — it CONTAINS the rendered description.
  assert.ok(entryItem.content_html.includes("<code>tt_metal</code>"),
    "content_html renders the description as markdown");
  assert.strictEqual(entryItem.summary, "Uses `tt_metal` under the hood.",
    "summary stays plain text");
  assert.ok(items.every((i) => typeof i.content_html === "string"),
    "every item has content_html");
  console.log("✓ jsonFeedItems: items carry rendered content_html + plain summary");
}

// Test 11: article-type links produce article items
{
  const entry = makeEntry();
  const items = jsonFeedItems([entry], []);
  const articleItem = items.find((i) => i.tags.includes("article"));
  assert.ok(articleItem, "should have an article-tagged item");
  assert.strictEqual(articleItem.url, "https://example.com/article");
  console.log("✓ jsonFeedItems: article link items produced");
}

// Test 11b: an article-link item's content lists ONLY its own link, not the
// entry's whole link set (the entry item already carries all links). Avoids
// byte-identical duplicate content across the two items.
{
  const entry = makeEntry(); // has a repo link + an article link
  const items = jsonFeedItems([entry], []);
  const entryItem   = items.find((i) => i.tags.includes("entry"));
  const articleItem = items.find((i) => i.tags.includes("article"));
  assert.ok(entryItem.content_html.includes("https://github.com/test/repo"),
    "entry item content includes the repo link");
  assert.ok(!articleItem.content_html.includes("https://github.com/test/repo"),
    "article item content omits the repo link (focuses on its own link)");
  assert.ok(articleItem.content_html.includes("https://example.com/article"),
    "article item content includes its own link");
  assert.notStrictEqual(entryItem.content_html, articleItem.content_html,
    "entry and article item content are not byte-identical");
  console.log("✓ jsonFeedItems: article item content focuses on its own link");
}

// Test 12: output is sorted newest-first by date_published
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

// Test 13: empty affiliation is filtered from tags
{
  const entry = makeEntry({ affiliation: "", links: [{ type: "repo", url: "https://github.com/test/repo" }] });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  assert.ok(!entryItem.tags.includes(""), "empty affiliation should not appear in tags");
  console.log("✓ jsonFeedItems: empty affiliation filtered from tags");
}

// Test 14: entries without repo link fall back to first available link URL
{
  const entry = makeEntry({ links: [{ type: "article", url: "https://example.com/article" }] });
  const items = jsonFeedItems([entry], []);
  const entryItem = items.find((i) => i.tags.includes("entry"));
  // anyLink fallback: uses the article URL rather than the homepage anchor
  assert.strictEqual(entryItem.url, "https://example.com/article", "no-repo entry should use first available link URL");
  console.log("✓ jsonFeedItems: no-repo entry falls back to first available link URL");
}

// Test 15: entries with no links at all fall back to anchor URL
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

// Test 16: article links appear in planet items
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

// Test 17: releases appear with type "release"
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

// Test 18: output sorted newest-first
{
  const old  = makeEntry({ id: "old",  added_at: "2025-01-01", links: [{ type: "article", url: "https://example.com/old" }] });
  const newE = makeEntry({ id: "newE", added_at: "2026-06-01", links: [{ type: "article", url: "https://example.com/new" }] });
  const items = planetItems([old, newE], [], []);
  assert.strictEqual(items[0].date, "2026-06-01", "newest first");
  assert.strictEqual(items[1].date, "2025-01-01", "oldest last");
  console.log("✓ planetItems: sorted newest-first");
}

// Test 19: deduplication by URL
{
  const e1 = makeEntry({ id: "e1", links: [{ type: "article", url: "https://example.com/same" }] });
  const e2 = makeEntry({ id: "e2", links: [{ type: "article", url: "https://example.com/same" }] });
  const items = planetItems([e1, e2], [], []);
  assert.strictEqual(items.length, 1, "duplicate URLs deduplicated");
  console.log("✓ planetItems: deduplicates by URL");
}

// Test 20: an entry becomes ONE card, whatever its article-type links
// (every link shares the entry's added_at, so per-link cards only ever rendered
// as a clump of near-identical duplicates — see the planetItems comment).
{
  const types = ["article", "lesson", "paper", "talk", "video", "demo"];
  const links = types.map((t) => ({ type: t, url: `https://example.com/${t}` }));
  const entry = makeEntry({ links });
  const items = planetItems([entry], [], []);
  assert.strictEqual(items.length, 1, "one card per entry, not per link");

  // Richest medium leads: video outranks talk/demo/paper/article/lesson.
  assert.strictEqual(items[0].type, "video");
  assert.strictEqual(items[0].url, "https://example.com/video");

  // Nothing is lost — the other five ride along on the same card.
  assert.strictEqual(items[0].extraLinks.length, types.length - 1);
  const reachable = [items[0].url, ...items[0].extraLinks.map((l) => l.url)].sort();
  assert.deepStrictEqual(reachable, links.map((l) => l.url).sort(),
    "every article-type link is still reachable from the card");
  console.log("✓ planetItems: one card per entry, richest medium leads");
}

// Test 20b: lead priority falls through when there is no video
{
  const entry = makeEntry({ links: [
    { type: "lesson",  url: "https://example.com/lesson" },
    { type: "paper",   url: "https://example.com/paper" },
    { type: "article", url: "https://example.com/article" },
  ]});
  const items = planetItems([entry], [], []);
  assert.strictEqual(items[0].type, "paper", "paper outranks article and lesson");
  console.log("✓ planetItems: lead priority falls through to paper");
}

// Test 20c: equal-priority links keep the author's order
{
  const entry = makeEntry({ links: [
    { type: "lesson", url: "https://example.com/one",   label: "One" },
    { type: "lesson", url: "https://example.com/two",   label: "Two" },
    { type: "lesson", url: "https://example.com/three", label: "Three" },
  ]});
  const items = planetItems([entry], [], []);
  assert.strictEqual(items[0].url, "https://example.com/one", "first listed leads");
  assert.deepStrictEqual(items[0].extraLinks.map((l) => l.label), ["Two", "Three"]);
  console.log("✓ planetItems: equal-priority links keep entry order");
}

// Test 20d: extra-link URLs are claimed too, so an external feed item covering
// the same page cannot add a second card for it.
{
  const entry = makeEntry({ links: [
    { type: "talk",  url: "https://example.com/session" },
    { type: "video", url: "https://example.com/recording" },
  ]});
  const feed = [{ approved: true, type: "talk", title: "Dup",
                  url: "https://example.com/session", date: "2026-03-02" }];
  const items = planetItems([entry], [], feed);
  assert.strictEqual(items.length, 1, "feed item for an extra link is deduped");
  console.log("✓ planetItems: extra-link URLs are claimed for dedup");
}

// Test 21: monthLabel converts correctly
{
  assert.strictEqual(monthLabel("2026-05"),    "May 2026");
  assert.strictEqual(monthLabel("2026-05-01"), "May 2026");
  assert.strictEqual(monthLabel("2026-01"),    "January 2026");
  assert.strictEqual(monthLabel("2026-12-31"), "December 2026");
  assert.strictEqual(monthLabel(""),           "");
  console.log("✓ monthLabel: converts YYYY-MM and YYYY-MM-DD correctly");
}

// Test 22: monthKey slices YYYY-MM from date strings
{
  assert.strictEqual(monthKey("2026-05-01"), "2026-05");
  assert.strictEqual(monthKey("2026-12-31"), "2026-12");
  assert.strictEqual(monthKey("2026-05"),    "2026-05");
  assert.strictEqual(monthKey(""),           "");
  assert.strictEqual(monthKey(null),         "");
  console.log("✓ monthKey: slices YYYY-MM correctly");
}

// Test 23: monthLabel guards invalid month numbers
{
  assert.strictEqual(monthLabel("2026-00-15"), "2026-00-15"); // month 0 → returns dateStr
  assert.strictEqual(monthLabel("2026-13-01"), "2026-13-01"); // month 13 → returns dateStr
  console.log("✓ monthLabel: guards out-of-range month numbers");
}

// Test 24: planetItems excludes dev releases (all known patterns)
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
    mkRel("v0.17.0-alpha"),               // tt-buda pattern: -alpha
    mkRel("v1.0.0-beta2"),                // -beta<digits>
    mkRel("7.67.0-strength-49763"),       // sfpi CI experiment tag
  ];
  const stableRel = mkRel("v1.0.0");
  const items = planetItems([], [...devRels, stableRel], []);
  const releaseItems = items.filter((i) => i.type === "release");
  assert.strictEqual(releaseItems.length, 1, "only stable release should appear");
  assert.strictEqual(releaseItems[0].label, "v1.0.0");
  console.log("✓ planetItems: excludes dev/rc/qa/alpha/beta/CI-experiment release tags");
}

// Test 25: approved external items appear
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
{
  // Defense-in-depth: non-http(s) link schemes must not become live hrefs.
  const html = feedContentHtml({
    description: "x",
    links: [
      { type: "repo", url: "javascript:alert(1)", label: "evil" },
      { type: "repo", url: "https://github.com/ok/repo", label: "ok" },
    ],
  });
  assert.ok(!html.includes("javascript:"), "javascript: scheme dropped");
  assert.ok(html.includes("https://github.com/ok/repo"), "https link kept");
  console.log("✓ feedContentHtml: drops non-http(s) link schemes");
}
{
  // Links render inline with " · ", NOT as a <ul>/<li> list, so they stay
  // readable when a client flattens the HTML to plain text (Slack RSS).
  const html = feedContentHtml({
    description: "x",
    links: [
      { type: "repo", url: "https://github.com/a/b", label: "Repo" },
      { type: "release", url: "https://github.com/a/b/releases/tag/1.3.0", label: "1.3.0" },
    ],
  });
  assert.ok(!html.includes("<ul>") && !html.includes("<li>"), "no list markup");
  assert.ok(html.includes("</a> · <a"), "links joined by middot separator");
  assert.ok(html.includes("<strong>Links:</strong> <a"), "inline Links label");
  console.log("✓ feedContentHtml: links render inline with separator");
}
{
  // Attribution: '@handle' only when author_url is a github.com profile.
  const gh = feedContentHtml({ author: "geohot", author_url: "https://github.com/geohot" });
  assert.ok(gh.includes('By <a href="https://github.com/geohot">@geohot</a>'), "github author → @handle linked");

  // A display name / author list with NO url → plain "By Name", no '@'.
  const name = feedContentHtml({ author: "Jenny Lynn Almerol, Mario Spera" });
  assert.ok(name.includes("By Jenny Lynn Almerol, Mario Spera"), "plain name rendered");
  assert.ok(!name.includes("@"), "no bogus @ prefix on a non-handle author");

  // A non-github profile url → linked name without '@'.
  const other = feedContentHtml({ author: "Martin Chang", author_url: "https://example.com/martin" });
  assert.ok(other.includes('By <a href="https://example.com/martin">Martin Chang</a>'), "non-github url → linked name");
  assert.ok(!other.includes("@"), "no @ for non-github profile");

  // Defense-in-depth: a dangerous-scheme author_url must NOT become a live href.
  const evil = feedContentHtml({ author: "x", author_url: "javascript:alert(1)" });
  assert.ok(!evil.includes("javascript:"), "javascript: author_url dropped");
  assert.ok(!evil.includes("<a "), "no anchor for non-http(s) author_url");
  assert.ok(evil.includes("By x"), "author rendered as plain text");
  console.log("✓ feedContentHtml: @handle only for github.com authors; author_url scheme-guarded");
}
// ── firstLinkOfType tests ────────────────────────────────────────────────────
const firstLinkOfType = filters["firstLinkOfType"];
assert(typeof firstLinkOfType === "function", "firstLinkOfType filter not registered");
{
  const links = [
    { type: "article", url: "https://x/a" },
    { type: "repo", url: "https://x/repo" },
    { type: "repo", url: "https://x/repo2" },
  ];
  assert.strictEqual(firstLinkOfType(links, "repo").url, "https://x/repo", "returns first matching type");
  assert.strictEqual(firstLinkOfType(links, "video"), null, "no match → null");
  assert.strictEqual(firstLinkOfType(undefined, "repo"), null, "missing links → null");
  assert.strictEqual(firstLinkOfType([{}, null], "repo"), null, "skips falsy/typeless entries");
  console.log("✓ firstLinkOfType: selects first link of a type, null otherwise");
}
// ── feedDateTime tests ───────────────────────────────────────────────────────
const feedDateTime = filters["feedDateTime"];
assert(typeof feedDateTime === "function", "feedDateTime filter not registered");
{
  // Date-only input gets a synthesized descending time keyed to feed index, so
  // earlier (newer) items sort above later ones on the same day.
  const newer = feedDateTime("2026-05-08", 0);
  const older = feedDateTime("2026-05-08", 5);
  assert.strictEqual(newer, "2026-05-08T23:59:59Z", "index 0 → end of day");
  assert.strictEqual(older, "2026-05-08T23:59:54Z", "index 5 → 5s earlier");
  assert.ok(newer > older, "earlier feed index sorts later in time (newest-first preserved)");
  // A value that already carries a time passes through untouched.
  assert.strictEqual(feedDateTime("2026-06-29T07:46:11Z", 3), "2026-06-29T07:46:11Z", "full timestamp passthrough");
  // Empty input is safe.
  assert.strictEqual(feedDateTime("", 0), "1970-01-01T00:00:00Z", "empty → epoch");
  console.log("✓ feedDateTime: deterministic intra-day ordering + passthrough");
}
// ── singleLine tests ─────────────────────────────────────────────────────────
const singleLine = filters["singleLine"];
assert(typeof singleLine === "function", "singleLine filter not registered");
{
  assert.strictEqual(singleLine("a\n\nb\n  c"), "a b c", "collapses newlines and runs of whitespace");
  assert.strictEqual(singleLine("  trim me  "), "trim me", "trims ends");
  assert.strictEqual(singleLine(undefined), "", "undefined → empty");
  console.log("✓ singleLine: collapses whitespace to a single line");
}

// ── diversifiedFeatured tests ────────────────────────────────────────────────
const diversifiedFeatured = filters["diversifiedFeatured"];
assert(typeof diversifiedFeatured === "function", "diversifiedFeatured filter not registered");
{
  const mk = (id, affiliation, stars, extra = {}) => ({
    id, name: id, affiliation, stars, categories: ["tools"], ...extra,
  });
  const cats = [{ slug: "tools" }];

  // Picks up to 3 per category with one entry from each affiliation tier,
  // presented official → affiliated → community.
  const mixed = diversifiedFeatured(
    [
      mk("com-big", "community", 900),
      mk("com-small", "community", 10),
      mk("aff", "affiliated", 50),
      mk("off", "official", 5),
    ],
    cats
  )["tools"];
  assert.strictEqual(mixed.length, 3, "three picks when candidates allow");
  assert.deepStrictEqual(
    mixed.map((e) => e.id),
    ["off", "aff", "com-big"],
    "one pick per tier, ordered official → affiliated → community"
  );
  console.log("✓ diversifiedFeatured: mixes affiliations, official first");

  // When a tier is missing, remaining slots fill with the best leftover
  // candidates by rank (featured first, then stars).
  const topped = diversifiedFeatured(
    [
      mk("com-1", "community", 300),
      mk("com-2", "community", 200),
      mk("com-feat", "community", 1, { featured: true }),
      mk("off", "official", 5),
    ],
    cats
  )["tools"];
  assert.deepStrictEqual(
    topped.map((e) => e.id),
    ["off", "com-feat", "com-1"],
    "missing tier tops up by rank; featured beats stars within a tier"
  );
  console.log("✓ diversifiedFeatured: tops up missing tiers by rank");

  // Each entry appears at most once across the whole home page.
  const twoCats = [{ slug: "a" }, { slug: "b" }];
  const shared = [
    { id: "only", name: "only", affiliation: "official", stars: 9, categories: ["a", "b"] },
  ];
  const perCat = diversifiedFeatured(shared, twoCats);
  assert.strictEqual(perCat["a"].length, 1, "first category takes the entry");
  assert.strictEqual(perCat["b"].length, 0, "entry is not reused in a later category");
  console.log("✓ diversifiedFeatured: entries unique across categories");

  // Grayskull-only / BUDA entries stay last-resort.
  const depri = diversifiedFeatured(
    [
      mk("buda-thing", "official", 999),
      mk("gs-only", "community", 500, { hardware: ["grayskull"] }),
      mk("fresh", "community", 5),
    ],
    cats
  )["tools"];
  assert.strictEqual(depri[0].id, "fresh", "non-deprioritized entry leads");
  assert.strictEqual(depri.length, 3, "deprioritized entries still fill empty slots");
  console.log("✓ diversifiedFeatured: deprioritizes BUDA/Grayskull-only to last resort");

  // home_pinned entries always get a slot, even when outgunned on stars.
  const pinned = diversifiedFeatured(
    [
      mk("big-1", "official", 1000),
      mk("big-2", "official", 900),
      mk("big-3", "official", 800),
      mk("tiny-pinned", "official", 1, { home_pinned: true }),
    ],
    cats
  )["tools"];
  assert.ok(
    pinned.some((e) => e.id === "tiny-pinned"),
    "pinned entry claims a showcase slot despite low stars"
  );
  assert.strictEqual(pinned.length, 3, "card still capped at three picks");
  console.log("✓ diversifiedFeatured: home_pinned guarantees a slot");

  // A pinned pick satisfies its affiliation tier — the mix pass must not
  // grab a second entry from that tier while other tiers go unrepresented.
  const pinnedMix = diversifiedFeatured(
    [
      mk("pinned-off", "official", 1, { home_pinned: true }),
      mk("big-off", "official", 1000),
      mk("aff", "affiliated", 50),
      mk("com", "community", 30),
    ],
    cats
  )["tools"];
  assert.deepStrictEqual(
    pinnedMix.map((e) => e.id),
    ["pinned-off", "aff", "com"],
    "pinned official covers the official slot; affiliated + community still shown"
  );
  console.log("✓ diversifiedFeatured: pinned pick satisfies its tier in the mix pass");
}

// ── prettyDateRange tests ───────────────────────────────────────────────────
{
  const prettyDateRange = filters["prettyDateRange"];
  assert(typeof prettyDateRange === "function", "prettyDateRange filter not registered");

  // Same year: the year is printed once, on the later date.
  assert.strictEqual(prettyDateRange("2026-08-17", "2026-08-24"), "Aug 17 – Aug 24, 2026");
  // Spanning a year boundary: both years are needed.
  assert.strictEqual(prettyDateRange("2025-12-30", "2026-01-02"),
                     "Dec 30, 2025 – Jan 2, 2026");
  // A single day collapses to one date.
  assert.strictEqual(prettyDateRange("2026-08-17", "2026-08-17"), "Aug 17, 2026");
  // Missing halves degrade to whichever date exists.
  assert.strictEqual(prettyDateRange("", "2026-08-17"), "Aug 17, 2026");
  assert.strictEqual(prettyDateRange("2026-08-17", ""), "Aug 17, 2026");
  assert.strictEqual(prettyDateRange("", ""), "");
  // An unparseable date passes through rather than rendering "undefined".
  assert.strictEqual(prettyDateRange("nope", "nope"), "nope");
  console.log("✓ prettyDateRange: single/same-year/cross-year spans and fallbacks");
}

// ── groupReleaseRuns tests ──────────────────────────────────────────────────
// Bursts of same-project releases collapse into one card carrying each
// version's own summary. See the helper in .eleventy.js for the window/cap
// rationale.
{
  const groupReleaseRuns = filters["groupReleaseRuns"];
  assert(typeof groupReleaseRuns === "function", "groupReleaseRuns filter not registered");

  const rel = (project, tag, date, description = "Summary.") => ({
    type: "release",
    title: `${project} ${tag}`,
    projectName: project,
    projectId: project,
    url: `https://github.com/tenstorrent/${project}/releases/tag/${tag}`,
    description,
    date,
    dateISO: `${date}T12:00:00Z`,
    affiliation: "official",
  });

  // A lone release must come through completely untouched — no `releases`
  // array, no rewritten title.
  {
    const out = groupReleaseRuns([rel("tt-bio", "v1.0", "2026-08-18")]);
    assert.strictEqual(out.length, 1);
    assert.strictEqual(out[0].title, "tt-bio v1.0");
    assert.strictEqual(out[0].releases, undefined, "single release gets no stack");
    console.log("✓ groupReleaseRuns: a lone release passes through unchanged");
  }

  // Same-day burst → one card holding all three.
  {
    const out = groupReleaseRuns([
      rel("tt-bio", "v0.2.0", "2026-07-09"),
      rel("tt-bio", "v0.2.1", "2026-07-09"),
      rel("tt-bio", "v0.2.2", "2026-07-09"),
    ]);
    assert.strictEqual(out.length, 1, "three same-day releases make one card");
    assert.strictEqual(out[0].releaseCount, 3);
    assert.strictEqual(out[0].title, "tt-bio v0.2.0 → v0.2.2");
    console.log("✓ groupReleaseRuns: same-day burst collapses to one card");
  }

  // Chaining: each gap is measured against the previous release, so a run can
  // span more than the window in total.
  {
    const out = groupReleaseRuns([
      rel("tt-bio", "v0.2.0", "2026-07-09"),
      rel("tt-bio", "v0.2.1", "2026-07-11"),
      rel("tt-bio", "v0.2.2", "2026-07-13"),
    ]);
    assert.strictEqual(out.length, 1, "2-day gaps chain into one 4-day run");
    assert.strictEqual(out[0].releaseCount, 3);
    console.log("✓ groupReleaseRuns: consecutive gaps chain beyond the window");
  }

  // A gap wider than the window splits the run.
  {
    const out = groupReleaseRuns([
      rel("tt-bio", "v0.2.0", "2026-07-01"),
      rel("tt-bio", "v0.3.0", "2026-07-20"),
    ]);
    assert.strictEqual(out.length, 2, "19 days apart is not one run");
    assert.ok(out.every((i) => i.releases === undefined));
    console.log("✓ groupReleaseRuns: a gap beyond the window splits the run");
  }

  // The cap stops a pathological run from becoming one unbounded card.
  {
    const many = Array.from({ length: 11 }, (_, i) =>
      rel("churn", `v0.0.${i}`, "2026-07-09"));
    const out = groupReleaseRuns(many);
    assert.strictEqual(out.length, 2, "11 same-day releases split at the cap of 8");
    const counts = out.map((i) => i.releaseCount || 1).sort((a, b) => b - a);
    assert.deepStrictEqual(counts, [8, 3]);
    console.log("✓ groupReleaseRuns: the max-group cap splits an oversized run");
  }

  // Different projects never merge, even on the same day.
  {
    const out = groupReleaseRuns([
      rel("tt-bio", "v1.0", "2026-08-18"),
      rel("tt-metal", "v2.0", "2026-08-18"),
    ]);
    assert.strictEqual(out.length, 2, "two projects stay two cards");
    console.log("✓ groupReleaseRuns: different projects are never merged");
  }

  // Every release keeps its own summary, newest first.
  {
    const out = groupReleaseRuns([
      rel("tt-bio", "v0.3.0", "2026-08-18", "The older one."),
      rel("tt-bio", "v0.4.0", "2026-08-19", "The newer one."),
    ]);
    assert.strictEqual(out[0].releases.length, 2);
    assert.deepStrictEqual(out[0].releases.map((r) => r.tag), ["v0.4.0", "v0.3.0"]);
    assert.strictEqual(out[0].releases[0].description, "The newer one.");
    assert.strictEqual(out[0].releases[1].description, "The older one.");
    console.log("✓ groupReleaseRuns: per-release summaries are kept, newest first");
  }

  // The card's identity comes from the newest release — that's where a reader
  // clicking through should land.
  {
    const out = groupReleaseRuns([
      rel("tt-bio", "v0.3.0", "2026-08-18"),
      rel("tt-bio", "v0.4.0", "2026-08-19"),
    ]);
    assert.ok(out[0].url.endsWith("v0.4.0"), "grouped card links the newest release");
    assert.strictEqual(out[0].dateISO, "2026-08-19T12:00:00Z");
    assert.deepStrictEqual(out[0].dateRange, { from: "2026-08-18", to: "2026-08-19" });
    console.log("✓ groupReleaseRuns: the newest release supplies the card identity");
  }

  // Non-release items are never touched.
  {
    const paper = { type: "paper", title: "A Paper", date: "2026-08-18",
                    dateISO: "2026-08-18T00:00:00Z", url: "https://arxiv.org/abs/1" };
    const out = groupReleaseRuns([paper, rel("tt-bio", "v1.0", "2026-08-18")]);
    assert.strictEqual(out.length, 2);
    assert.ok(out.includes(paper), "the paper object passes through by reference");
    console.log("✓ groupReleaseRuns: non-release items pass through untouched");
  }

  // A release with no projectName can't be grouped safely — pass it through.
  {
    const orphan = { type: "release", title: "mystery v1.0", date: "2026-08-18",
                     dateISO: "2026-08-18T00:00:00Z", url: "https://example.com/r" };
    const out = groupReleaseRuns([orphan]);
    assert.strictEqual(out.length, 1);
    assert.strictEqual(out[0].releases, undefined);
    console.log("✓ groupReleaseRuns: a release without projectName is left alone");
  }

  // An unparseable date must not silently merge into a neighbouring run.
  {
    const broken = rel("tt-bio", "v9.9", "not-a-date");
    const out = groupReleaseRuns([rel("tt-bio", "v1.0", "2026-08-18"), broken]);
    assert.strictEqual(out.length, 2, "a bad date never joins a run");
    console.log("✓ groupReleaseRuns: an unparseable date does not merge");
  }

  // Same-timestamp releases: the comparator must return 0 for ties so the
  // run's "oldest → newest" title stays derived from the input order rather
  // than from whatever an unstable sort produced.
  {
    const tied = ["v0.2.0", "v0.2.1", "v0.2.2", "v0.2.3", "v0.2.4"].map((tag) => ({
      ...rel("tt-bio", tag, "2026-07-09"),
      dateISO: "2026-07-09T00:00:00Z",   // identical timestamps
    }));
    const out = groupReleaseRuns(tied);
    assert.strictEqual(out.length, 1);
    assert.strictEqual(out[0].title, "tt-bio v0.2.0 → v0.2.4",
      "tied timestamps must keep input order for the run's endpoints");
    assert.deepStrictEqual(
      out[0].releases.map((r) => r.tag),
      ["v0.2.4", "v0.2.3", "v0.2.2", "v0.2.1", "v0.2.0"],
      "stack stays newest-first under ties"
    );
    console.log("✓ groupReleaseRuns: identical timestamps keep a stable order");
  }

  // Empty and missing input are both fine.
  {
    assert.deepStrictEqual(groupReleaseRuns([]), []);
    assert.deepStrictEqual(groupReleaseRuns(null), []);
    console.log("✓ groupReleaseRuns: empty and null input return an empty list");
  }

  // End to end through planetItems: the burst arrives as one card and the
  // page's release count reflects the grouping.
  {
    const feeds = [
      rel("tt-bio", "v0.3.0", "2026-08-18"),
      rel("tt-bio", "v0.4.0", "2026-08-19"),
    ].map((i) => ({ ...i, approved: true, source: "github" }));
    const out = planetItems([], [], feeds);
    assert.strictEqual(out.length, 1, "planetItems groups the burst");
    assert.strictEqual(out[0].releaseCount, 2);
    console.log("✓ planetItems: release bursts arrive grouped");
  }
}

console.log("\nAll eleventy filter tests passed ✓");
