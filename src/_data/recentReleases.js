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
 *     summary:     string   — human-quality release summary (LLM or fallback)
 *     runSummaries: array   — earlier releases in the same burst, newest first:
 *                             [{tag,url,date,description}]; [] when the release
 *                             stands alone. Rendered by feedContentHtml.
 *     description: string   — same as summary; satisfies feedContentHtml contract
 *     added_at:    string   — YYYY-MM-DD publish date
 *     links:       array    — [{type,url,label}] repo + release links
 *   }
 *
 * Note: only entries that have a `latestStableRelease` (pre-computed in
 * entries.js) are included — pre-release-only and unreleased entries are
 * intentionally excluded.
 */

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
  // 2. Same-repo release whose URL's final path segment is exactly this tag
  //    (handles html_url vs tag-url shape differences between GitHub's API and
  //    the summarizer). Match the tag as the trailing segment, NOT a substring:
  //    a substring match would let tag "0.20.25" wrongly match a ".../0.20.25rc1"
  //    release URL when both exist for the same repo.
  if (rel.repoUrl && rel.tagName) {
    const prefix = rel.repoUrl + "/releases/";
    for (const item of feeds) {
      if (item.type !== "release" || !item.description || !item.url) continue;
      if (!item.url.startsWith(prefix)) continue;
      const norm = item.url.replace(/[?#].*$/, "").replace(/\/+$/, "");
      const lastSegment = norm.slice(norm.lastIndexOf("/") + 1);
      if (lastSegment === rel.tagName) return item.description;
    }
  }
  // 3. Fallback one-liner.
  return `${rel.entryName} released ${rel.tagName}.` +
    (rel.repoUrl ? ` Repository: ${rel.repoUrl}` : "");
}

// Days between consecutive releases that still count as one run. Kept equal to
// RELEASE_RUN_WINDOW_DAYS in .eleventy.js so the feed's "Also in this run"
// list and the planet page's grouped card describe the same set of releases.
const RUN_WINDOW_DAYS = 3;
// Ceiling on how many earlier releases a feed entry carries, so one very busy
// project can't bloat every reader's download.
const RUN_MAX = 7;

// Whole days between two ISO date strings; Infinity when either is unparseable
// (an unknown date must never be treated as adjacent).
function dayGap(a, b) {
  const day = (s) => {
    const [y, m, d] = String(s || "").slice(0, 10).split("-").map(Number);
    return Number.isFinite(y) && Number.isFinite(m) && Number.isFinite(d)
      ? Date.UTC(y, m - 1, d) / 86400000
      : NaN;
  };
  const gap = Math.abs(day(b) - day(a));
  return Number.isFinite(gap) ? gap : Infinity;
}

/**
 * Earlier releases belonging to the same burst as `rel`, newest first.
 *
 * The release feed carries one entry per project, so a project that shipped
 * v0.3.0 and v0.4.0 two days apart previously published only v0.4.0's summary
 * and v0.3.0 reached no subscriber. This walks backwards from the latest
 * release through same-repo summarized items in planet_feeds.json, chaining
 * while each consecutive gap is within RUN_WINDOW_DAYS.
 *
 * Returns [] when the release stands alone — the common case.
 */
function resolveRunSummaries(rel, planetFeeds) {
  if (!rel.repoUrl || !rel.publishedAt) return [];
  const prefix = rel.repoUrl + "/releases/";

  // Same-repo release items strictly older than this one, newest first.
  const siblings = (planetFeeds || [])
    .filter((i) => i && i.type === "release" && i.description && i.url &&
                   i.url.startsWith(prefix) && i.url !== rel.url &&
                   (i.dateISO || "") < rel.publishedAt)
    // Three-way compare so equal timestamps return 0; a comparator that never
    // returns 0 violates the sort contract and can reorder same-timestamp
    // siblings, changing which releases the "Also in this run" list shows.
    .sort((a, b) => (a.dateISO < b.dateISO ? 1 : a.dateISO > b.dateISO ? -1 : 0));

  const run = [];
  let anchor = rel.publishedAt;
  for (const sib of siblings) {
    if (run.length >= RUN_MAX) break;
    if (dayGap(anchor, sib.dateISO) > RUN_WINDOW_DAYS) break; // run ends here
    // Trailing path segment is the tag (see resolveReleaseSummary's note on
    // why a substring match would be wrong).
    const norm = sib.url.replace(/[?#].*$/, "").replace(/\/+$/, "");
    run.push({
      tag: norm.slice(norm.lastIndexOf("/") + 1),
      url: sib.url,
      date: sib.date || (sib.dateISO || "").slice(0, 10),
      description: sib.description,
    });
    anchor = sib.dateISO; // chain from this release, not the newest one
  }
  return run;
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

  // Reuse the planetFeeds loader so malformed planet_feeds.json fails the build
  // with a clear error (its contract: [] when absent, throw when malformed) —
  // rather than silently downgrading every release summary to the fallback.
  const planetFeeds = require("./planetFeeds")();
  for (const rel of releases) {
    rel.summary = resolveReleaseSummary(rel, planetFeeds);
    // Conform to the feedContentHtml contract (see .eleventy.js Task 1):
    rel.description = rel.summary;
    // Earlier releases from the same burst, so the feed's <content> covers the
    // whole run rather than only the newest version.
    rel.runSummaries = resolveRunSummaries(rel, planetFeeds);
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
module.exports.resolveRunSummaries = resolveRunSummaries;
