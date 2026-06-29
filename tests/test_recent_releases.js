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

console.log("\nAll recentReleases tests passed ✓");
