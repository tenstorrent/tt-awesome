// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Tests for latestStableRelease in entries.js and recentReleases.js
// Run with: node tests/test_data_files.js

const assert = require("assert");
const path = require("path");

// ── Test latestStableRelease via entries module ──────────────────────────────

// Patch require to inject test github_meta.json
const Module = require("module");
const _origLoad = Module._load;

Module._load = function (request, parent, isMain) {
  if (request.endsWith("github_meta.json")) {
    return {
      "https://github.com/test/stable": {
        stars: 10,
        updatedAt: "2026-01-01T00:00:00Z",
        releases: [
          { tagName: "v2.0.0", name: "v2.0.0", publishedAt: "2026-05-01T00:00:00Z",
            url: "https://github.com/test/stable/releases/tag/v2.0.0", prerelease: false },
          { tagName: "v1.0.0-rc1", name: "RC1", publishedAt: "2026-04-01T00:00:00Z",
            url: "https://github.com/test/stable/releases/tag/v1.0.0-rc1", prerelease: true },
        ],
      },
      "https://github.com/test/preonly": {
        stars: 5,
        updatedAt: "2026-01-01T00:00:00Z",
        releases: [
          { tagName: "v0.1.0-alpha", name: "alpha", publishedAt: "2026-03-01T00:00:00Z",
            url: "https://github.com/test/preonly/releases/tag/v0.1.0-alpha", prerelease: true },
        ],
      },
      "https://github.com/test/noreleases": {
        stars: 3,
        updatedAt: "2026-01-01T00:00:00Z",
      },
      // Newest release is a dated demo tag carrying no version number. It is a
      // genuine non-prerelease, so a plain "newest non-prerelease wins" rule
      // would advertise a screen recording as the project's latest stable
      // build. The version-shaped tag has to win. (Real case: tt-finetune's
      // demo-2026-08-29, published a day after v0.2.1.)
      "https://github.com/test/demotag": {
        stars: 1,
        updatedAt: "2026-08-29T00:00:00Z",
        releases: [
          { tagName: "demo-2026-08-29", name: "Demo", publishedAt: "2026-08-29T15:44:38Z",
            url: "https://github.com/test/demotag/releases/tag/demo-2026-08-29", prerelease: false },
          { tagName: "v0.2.1", name: "v0.2.1", publishedAt: "2026-08-28T17:21:58Z",
            url: "https://github.com/test/demotag/releases/tag/v0.2.1", prerelease: false },
          { tagName: "v0.2.0", name: "v0.2.0", publishedAt: "2026-08-26T07:14:15Z",
            url: "https://github.com/test/demotag/releases/tag/v0.2.0", prerelease: false },
        ],
      },
      // No release here carries a version number at all — polaris ships tags
      // like "pre_perfmodel_merge". The newest non-prerelease must still win,
      // or the entry silently loses its release callout.
      "https://github.com/test/noversion": {
        stars: 2,
        updatedAt: "2026-01-01T00:00:00Z",
        releases: [
          { tagName: "pre_perfmodel_merge", name: "pre merge", publishedAt: "2026-06-01T00:00:00Z",
            url: "https://github.com/test/noversion/releases/tag/pre_perfmodel_merge", prerelease: false },
        ],
      },
    };
  }
  return _origLoad.apply(this, arguments);
};

// Also patch collectJsonFiles so entries.js uses test data
const testEntries = [
  { id: "entry-stable", name: "Stable Project", affiliation: "official",
    links: [{ type: "repo", url: "https://github.com/test/stable" }] },
  { id: "entry-preonly", name: "PreOnly Project", affiliation: "community",
    links: [{ type: "repo", url: "https://github.com/test/preonly" }] },
  { id: "entry-noreleases", name: "No Releases Project", affiliation: "official",
    links: [{ type: "repo", url: "https://github.com/test/noreleases" }] },
  { id: "entry-demotag", name: "Demo Tag Project", affiliation: "community",
    links: [{ type: "repo", url: "https://github.com/test/demotag" }] },
  { id: "entry-noversion", name: "No Version Project", affiliation: "official",
    links: [{ type: "repo", url: "https://github.com/test/noversion" }] },
];

// Patch fs.readdirSync and fs.readFileSync for test entries
const fs = require("fs");
const _origReaddir = fs.readdirSync;
const _origReadFile = fs.readFileSync;
const _origStatSync = fs.statSync;

fs.readdirSync = function(dir) {
  if (dir.includes("entries")) return testEntries.map(e => `${e.id}.json`);
  return _origReaddir.apply(this, arguments);
};
fs.readFileSync = function(f, enc) {
  const match = testEntries.find(e => f.includes(`${e.id}.json`));
  if (match) return JSON.stringify(match);
  return _origReadFile.apply(this, arguments);
};
fs.statSync = function(f) {
  if (testEntries.some(e => f.includes(`${e.id}.json`))) return { isDirectory: () => false };
  return _origStatSync.apply(this, arguments);
};

let entries;
try {
  delete require.cache[require.resolve("../src/_data/entries.js")];
  entries = require("../src/_data/entries.js")();
} finally {
  fs.readdirSync = _origReaddir;
  fs.readFileSync = _origReadFile;
  fs.statSync = _origStatSync;
  Module._load = _origLoad;
}

// Test 1: entry with stable release gets latestStableRelease
const stableEntry = entries.find(e => e.id === "entry-stable");
assert(stableEntry, "entry-stable not found");
assert(stableEntry.latestStableRelease, "latestStableRelease should be set for stable entry");
assert.strictEqual(stableEntry.latestStableRelease.tagName, "v2.0.0", "should pick first non-prerelease");

// Test 2: entry with only prereleases has no latestStableRelease
const preonlyEntry = entries.find(e => e.id === "entry-preonly");
assert(preonlyEntry, "entry-preonly not found");
assert(!preonlyEntry.latestStableRelease, "latestStableRelease should not be set for prerelease-only entry");

// Test 3: entry with no releases has no latestStableRelease
const norelEntry = entries.find(e => e.id === "entry-noreleases");
assert(norelEntry, "entry-noreleases not found");
assert(!norelEntry.latestStableRelease, "latestStableRelease should not be set for no-releases entry");

// Test 4: a dated demo tag never becomes the latest *stable* release, even
// though it is the newest non-prerelease in the list.
const demoEntry = entries.find(e => e.id === "entry-demotag");
assert(demoEntry, "entry-demotag not found");
assert(demoEntry.latestStableRelease, "latestStableRelease should be set for demo-tag entry");
assert.strictEqual(demoEntry.latestStableRelease.tagName, "v0.2.1",
  "should skip the newer non-version demo tag and pick the version-shaped release");

// Test 5: when nothing carries a version number, fall back to the newest
// non-prerelease rather than dropping the callout.
const noverEntry = entries.find(e => e.id === "entry-noversion");
assert(noverEntry, "entry-noversion not found");
assert(noverEntry.latestStableRelease, "latestStableRelease should fall back when no tag has a version");
assert.strictEqual(noverEntry.latestStableRelease.tagName, "pre_perfmodel_merge",
  "should fall back to the newest non-prerelease when no version-shaped tag exists");

console.log("✓ latestStableRelease tests passed");

// ── Test recentReleases.js ────────────────────────────────────────────────────

// Reload with patched entries
Module._load = function (request, parent, isMain) {
  if (request === path.resolve(__dirname, "../src/_data/entries.js") || request === "./entries") {
    return () => [
      { id: "entry-stable", name: "Stable Project", affiliation: "official",
        links: [{ type: "repo", url: "https://github.com/test/stable" }],
        latestStableRelease: { tagName: "v2.0.0", publishedAt: "2026-05-01T00:00:00Z",
                               url: "https://github.com/test/stable/releases/tag/v2.0.0", prerelease: false } },
      { id: "entry-preonly", name: "PreOnly Project", affiliation: "community",
        links: [{ type: "repo", url: "https://github.com/test/preonly" }] },
    ];
  }
  return _origLoad.apply(this, arguments);
};

let recentReleases;
try {
  delete require.cache[require.resolve("../src/_data/recentReleases.js")];
  recentReleases = require("../src/_data/recentReleases.js")();
} finally {
  Module._load = _origLoad;
}

// Test 4: only entries with latestStableRelease appear in feed
assert.strictEqual(recentReleases.length, 1, "only 1 stable release expected in feed");
assert.strictEqual(recentReleases[0].entryId, "entry-stable");
assert.strictEqual(recentReleases[0].tagName, "v2.0.0");
assert.strictEqual(recentReleases[0].affiliation, "official");

// Test 5: feed shape has required fields
const rel = recentReleases[0];
assert("entryId" in rel, "entryId required");
assert("entryName" in rel, "entryName required");
assert("affiliation" in rel, "affiliation required");
assert("tagName" in rel, "tagName required");
assert("publishedAt" in rel, "publishedAt required");
assert("url" in rel, "url required");
assert("repoUrl" in rel, "repoUrl required");

console.log("✓ recentReleases tests passed");

// Test 6: feed is sorted newest-first
Module._load = function (request, parent, isMain) {
  if (request === path.resolve(__dirname, "../src/_data/entries.js") || request === "./entries") {
    return () => [
      { id: "old", name: "Old Project", affiliation: "official",
        links: [{ type: "repo", url: "https://github.com/test/old" }],
        latestStableRelease: { tagName: "v1.0.0", publishedAt: "2026-01-01T00:00:00Z",
                               url: "https://github.com/test/old/releases/tag/v1.0.0" } },
      { id: "new", name: "New Project", affiliation: "community",
        links: [{ type: "repo", url: "https://github.com/test/new" }],
        latestStableRelease: { tagName: "v2.0.0", publishedAt: "2026-05-01T00:00:00Z",
                               url: "https://github.com/test/new/releases/tag/v2.0.0" } },
    ];
  }
  return _origLoad.apply(this, arguments);
};

let sorted;
try {
  delete require.cache[require.resolve("../src/_data/recentReleases.js")];
  sorted = require("../src/_data/recentReleases.js")();
} finally {
  Module._load = _origLoad;
}

assert.strictEqual(sorted.length, 2, "both entries should appear");
assert.strictEqual(sorted[0].entryId, "new", "newest entry should be first");
assert.strictEqual(sorted[1].entryId, "old", "oldest entry should be second");

console.log("✓ sort order test passed");

// Test 7: feed is capped at 50 entries
Module._load = function (request, parent, isMain) {
  if (request === path.resolve(__dirname, "../src/_data/entries.js") || request === "./entries") {
    return () => Array.from({ length: 60 }, (_, i) => ({
      id: `entry-${i}`,
      name: `Project ${i}`,
      affiliation: "official",
      links: [{ type: "repo", url: `https://github.com/test/repo-${i}` }],
      latestStableRelease: {
        tagName: `v1.${i}.0`,
        publishedAt: new Date(2026, 0, i + 1).toISOString(),
        url: `https://github.com/test/repo-${i}/releases/tag/v1.${i}.0`,
      },
    }));
  }
  return _origLoad.apply(this, arguments);
};

let capped;
try {
  delete require.cache[require.resolve("../src/_data/recentReleases.js")];
  capped = require("../src/_data/recentReleases.js")();
} finally {
  Module._load = _origLoad;
}

assert.strictEqual(capped.length, 50, "feed should be capped at 50 entries");

console.log("✓ cap test passed");
console.log("All tests passed ✓");
