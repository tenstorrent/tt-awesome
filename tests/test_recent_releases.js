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

// Tag must match as the trailing URL segment, NOT a substring: a release whose
// tag is a prefix of another tag (1.3.0 vs 1.3.0rc1) must not be mismatched.
{
  const relPrefix = {
    entryName: "tt-forge-onnx",
    tagName: "1.3.0",
    repoUrl: "https://github.com/tenstorrent/tt-forge-onnx",
    url: "https://github.com/tenstorrent/tt-forge-onnx/releases/tag/1.3.0",
  };
  // Only a pre-release whose tag *contains* "1.3.0" is present — must NOT match.
  const feeds = [
    {
      type: "release",
      url: "https://github.com/tenstorrent/tt-forge-onnx/releases/tag/1.3.0rc1",
      description: "Pre-release summary — should NOT be used for 1.3.0.",
    },
  ];
  assert.strictEqual(
    resolveReleaseSummary(relPrefix, feeds),
    "tt-forge-onnx released 1.3.0. Repository: https://github.com/tenstorrent/tt-forge-onnx",
    "prefix tag collision falls through to the one-liner, not the rc summary"
  );
  console.log("✓ resolveReleaseSummary: tag matched as trailing segment, not substring");
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
  assert.strictEqual(
    resolveReleaseSummary(rel, feeds),
    "tt-forge-onnx released 1.3.0. Repository: https://github.com/tenstorrent/tt-forge-onnx",
    "non-release items ignored"
  );
  console.log("✓ resolveReleaseSummary: ignores non-release feed items");
}

// ── resolveRunSummaries ─────────────────────────────────────────────────────
// The release feed carries one entry per project, so earlier releases from the
// same burst ride along in that entry's <content>.
{
  const { resolveRunSummaries } = require("../src/_data/recentReleases.js");
  const repo = "https://github.com/tenstorrent/tt-bio";
  const feedItem = (tag, dateISO, description = "Summary.") => ({
    type: "release",
    url: `${repo}/releases/tag/${tag}`,
    dateISO,
    date: dateISO.slice(0, 10),
    description,
  });

  const latest = { repoUrl: repo, url: `${repo}/releases/tag/v0.4.0`,
                   publishedAt: "2026-08-19T12:00:00Z", tagName: "v0.4.0" };

  // A release two days earlier is part of the run.
  {
    const run = resolveRunSummaries(latest, [
      feedItem("v0.4.0", "2026-08-19T12:00:00Z"),
      feedItem("v0.3.0", "2026-08-17T12:00:00Z", "Older summary."),
    ]);
    assert.strictEqual(run.length, 1, "the 2-day-earlier release joins the run");
    assert.strictEqual(run[0].tag, "v0.3.0");
    assert.strictEqual(run[0].description, "Older summary.");
    console.log("✓ resolveRunSummaries: nearby earlier release is included");
  }

  // A release well outside the window is not.
  {
    const run = resolveRunSummaries(latest, [
      feedItem("v0.1.0", "2026-07-01T12:00:00Z"),
    ]);
    assert.deepStrictEqual(run, [], "a release 7 weeks earlier is a separate run");
    console.log("✓ resolveRunSummaries: a distant release is excluded");
  }

  // Gaps chain: each step is measured from the previous release.
  {
    const run = resolveRunSummaries(latest, [
      feedItem("v0.3.0", "2026-08-17T12:00:00Z"),
      feedItem("v0.2.0", "2026-08-15T12:00:00Z"),
      feedItem("v0.1.0", "2026-08-13T12:00:00Z"),
    ]);
    assert.deepStrictEqual(run.map((r) => r.tag), ["v0.3.0", "v0.2.0", "v0.1.0"]);
    console.log("✓ resolveRunSummaries: consecutive gaps chain backwards");
  }

  // The chain stops at the first gap wider than the window — releases beyond
  // it belong to an earlier run even if they are individually close together.
  {
    const run = resolveRunSummaries(latest, [
      feedItem("v0.3.0", "2026-08-17T12:00:00Z"),
      feedItem("v0.2.0", "2026-08-01T12:00:00Z"),
      feedItem("v0.1.0", "2026-07-31T12:00:00Z"),
    ]);
    assert.deepStrictEqual(run.map((r) => r.tag), ["v0.3.0"]);
    console.log("✓ resolveRunSummaries: the chain stops at the first wide gap");
  }

  // The release itself never appears in its own run list.
  {
    const run = resolveRunSummaries(latest, [feedItem("v0.4.0", "2026-08-19T12:00:00Z")]);
    assert.deepStrictEqual(run, []);
    console.log("✓ resolveRunSummaries: the release excludes itself");
  }

  // Other repos never leak in, even on the same day.
  {
    const run = resolveRunSummaries(latest, [{
      type: "release",
      url: "https://github.com/tenstorrent/tt-metal/releases/tag/v0.77.0",
      dateISO: "2026-08-18T12:00:00Z", date: "2026-08-18", description: "Other repo.",
    }]);
    assert.deepStrictEqual(run, [], "a different repo is never part of this run");
    console.log("✓ resolveRunSummaries: other repos are excluded");
  }

  // Missing data degrades to an empty list rather than throwing.
  {
    assert.deepStrictEqual(resolveRunSummaries({ repoUrl: "", publishedAt: "" }, []), []);
    assert.deepStrictEqual(resolveRunSummaries(latest, null), []);
    assert.deepStrictEqual(resolveRunSummaries(latest, undefined), []);
    console.log("✓ resolveRunSummaries: missing inputs return an empty list");
  }

  // Non-release items and summary-less items are ignored.
  {
    const run = resolveRunSummaries(latest, [
      { type: "video", url: `${repo}/releases/tag/v0.3.0`, dateISO: "2026-08-18T12:00:00Z",
        description: "Not a release." },
      { type: "release", url: `${repo}/releases/tag/v0.2.0`, dateISO: "2026-08-18T12:00:00Z" },
    ]);
    assert.deepStrictEqual(run, []);
    console.log("✓ resolveRunSummaries: non-releases and empty summaries are skipped");
  }
}

console.log("\nAll recentReleases tests passed ✓");
