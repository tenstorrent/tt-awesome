// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

const fs = require("fs");
const path = require("path");

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

  // Sort newest-first by release publish date
  releases.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));

  // Cap at 50 to keep page weight low; nightly fetch already limits per-repo
  return releases.slice(0, 50);
};

module.exports.resolveReleaseSummary = resolveReleaseSummary;
