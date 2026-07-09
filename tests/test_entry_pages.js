// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Build-output assertions for the static per-entry pages, sitemap, and
// crawlability surfaces. Unlike the unit tests in this directory, these
// checks read the built site, so run `npm run build` first:
//   npm run build && node tests/test_entry_pages.js

const assert = require("assert");
const fs = require("fs");
const path = require("path");

const entries = require("../src/_data/entries.js")();
const site = require("../src/_data/site.js");
const outDir = path.join(__dirname, "..", "_site");

// Nunjucks autoescapes interpolated text; apply the same escaping before
// searching built HTML for entry names/descriptions.
const esc = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

assert(
  fs.existsSync(path.join(outDir, "index.html")),
  "_site/index.html missing — run `npm run build` before this test"
);
assert(
  /\/$/.test(site.baseUrl),
  "site.baseUrl must end with a trailing slash"
);

// ── Every non-hidden entry gets a standalone page with stable extraction
//    anchor, its content, and a canonical URL ────────────────────────────────
for (const entry of entries) {
  const pagePath = path.join(outDir, "entry", entry.id, "index.html");
  assert(fs.existsSync(pagePath), `missing static page: entry/${entry.id}/`);
  const html = fs.readFileSync(pagePath, "utf-8");

  assert(
    html.includes('id="entry-content"'),
    `entry/${entry.id}/ lacks the #entry-content extraction container`
  );
  assert(
    html.includes(esc(entry.name)),
    `entry/${entry.id}/ does not contain the entry name`
  );
  assert(
    html.includes(esc(entry.description)),
    `entry/${entry.id}/ does not contain the entry description (no-JS content check)`
  );
  assert(
    html.includes(
      `<link rel="canonical" href="${site.baseUrl}entry/${entry.id}/">`
    ),
    `entry/${entry.id}/ lacks its canonical link`
  );
  assert(
    html.includes(`?entry=${entry.id}`),
    `entry/${entry.id}/ lacks an "Open in tt-awesome" link into the SPA`
  );
}

// ── sitemap.xml lists the root, planet, and every entry page ────────────────
const sitemapPath = path.join(outDir, "sitemap.xml");
assert(fs.existsSync(sitemapPath), "sitemap.xml missing from build output");
const sitemap = fs.readFileSync(sitemapPath, "utf-8");
assert(sitemap.startsWith("<?xml"), "sitemap.xml must start with an XML declaration");
assert(sitemap.includes(`<loc>${site.baseUrl}</loc>`), "sitemap missing site root");
assert(sitemap.includes(`<loc>${site.baseUrl}planet/</loc>`), "sitemap missing /planet/");
for (const entry of entries) {
  assert(
    sitemap.includes(`<loc>${site.baseUrl}entry/${entry.id}/</loc>`),
    `sitemap missing entry/${entry.id}/`
  );
}

// ── The SPA page links to every entry's static page (crawl discovery) ───────
const indexHtml = fs.readFileSync(path.join(outDir, "index.html"), "utf-8");
for (const entry of entries) {
  assert(
    indexHtml.includes(`href="/tt-awesome/entry/${entry.id}/"`),
    `index.html has no anchor to entry/${entry.id}/`
  );
}

// ── Release rows (releases-list.njk) independently get row-name-link
//    anchors — the entry-row loop above would pass even if release rows
//    regressed, since every entry id already appears via its entry row. ─────
assert(
  /class="release-row"[\s\S]{0,600}?class="row-name-link" href="\/tt-awesome\/entry\//.test(
    indexHtml
  ),
  "index.html release rows lack row-name-link anchors"
);

// ── Legacy ?entry= routes still map: restoreFromUrl() in main.js resolves a
//    deep link by finding `.entry-row[data-id="<id>"]` and showing the card
//    `#detail-<id>`, so both hooks must exist in index.html for every entry ──
for (const entry of entries) {
  assert(
    indexHtml.includes(`data-id="${entry.id}"`),
    `index.html lacks the entry-row data-id hook for ${entry.id} (breaks ?entry= deep links)`
  );
  assert(
    indexHtml.includes(`id="detail-${entry.id}"`),
    `index.html lacks the detail card #detail-${entry.id} (breaks ?entry= deep links)`
  );
}

// ── AGENTS.md ships with the site ───────────────────────────────────────────
assert(
  fs.existsSync(path.join(outDir, "AGENTS.md")),
  "AGENTS.md missing from build output"
);

console.log(`ok — ${entries.length} static entry pages + sitemap verified`);
