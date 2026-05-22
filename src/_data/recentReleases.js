// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

/**
 * Eleventy data file: recentReleases
 *
 * Produces a flat, sorted list of the most-recent stable release per entry,
 * capped at 50 items. This feed is consumed by the "Recent Releases" sidebar
 * panel and any page that renders release activity.
 *
 * Each item has the shape:
 *   {
 *     entryId:     string   — entry id (matches entry.id)
 *     entryName:   string   — human-readable project name
 *     affiliation: string   — "official" | "affiliated" | "community"
 *     tagName:     string   — e.g. "v2.0.0"
 *     publishedAt: string   — ISO 8601 date string
 *     url:         string   — link to the GitHub release page
 *     repoUrl:     string   — link to the GitHub repo root
 *   }
 *
 * Note: only entries that have a `latestStableRelease` (pre-computed in
 * entries.js) are included — pre-release-only and unreleased entries are
 * intentionally excluded.
 */

module.exports = function () {
  const allEntries = require("./entries")();

  const releases = [];
  for (const entry of allEntries) {
    const stable = entry.latestStableRelease;
    if (!stable) continue;

    const repoLink = (entry.links || []).find(l => l.type === "repo");
    releases.push({
      entryId: entry.id,
      entryName: entry.name,
      affiliation: entry.affiliation,
      tagName: stable.tagName,
      publishedAt: stable.publishedAt,
      url: stable.url,
      repoUrl: repoLink ? repoLink.url : "",
    });
  }

  // Sort newest-first by release publish date
  releases.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));

  // Cap at 50 to keep page weight low; nightly fetch already limits per-repo
  return releases.slice(0, 50);
};
