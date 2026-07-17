// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

const fs = require("fs");
const path = require("path");
const meta = require("./github_meta.json");

const metaByUrl = {};
for (const [url, data] of Object.entries(meta)) {
  metaByUrl[url] = data;
}

// Default site ordering: Tenstorrent-org (official) entries first, then
// affiliated, then community — each tier sorted by stars (see sort below).
const AFFILIATION_ORDER = { official: 0, affiliated: 1, community: 2 };

/** Returns true only for well-formed https URLs with a non-empty hostname. */
function isSafeHttpsUrl(url) {
  if (!url || typeof url !== "string") return false;
  try {
    const { protocol, hostname } = new URL(url);
    return protocol === "https:" && hostname.length > 0;
  } catch (_) {
    return false;
  }
}

/** Recursively collect all .json file paths under a directory. */
function collectJsonFiles(dir) {
  const results = [];
  for (const f of fs.readdirSync(dir)) {
    const full = path.join(dir, f);
    if (fs.statSync(full).isDirectory()) {
      results.push(...collectJsonFiles(full));
    } else if (f.endsWith(".json")) {
      results.push(full);
    }
  }
  return results;
}

module.exports = function () {
  const entriesDir = path.join(__dirname, "../../entries");
  const files = collectJsonFiles(entriesDir);

  const entries = files.map((f) => {
    const entry = JSON.parse(
      fs.readFileSync(f, "utf8")
    );
    const repoLink = (entry.links || []).find((l) => l.type === "repo");
    if (repoLink && metaByUrl[repoLink.url]) {
      Object.assign(entry, metaByUrl[repoLink.url]);
    }
    // Derive author profile URL from the GitHub repo owner when not explicitly set
    if (!entry.author_url && repoLink && repoLink.url) {
      try {
        const parsed = new URL(repoLink.url);
        if (parsed.hostname === "github.com") {
          const owner = parsed.pathname.split("/")[1];
          if (owner) entry.author_url = `https://github.com/${owner}`;
        }
      } catch (_) {}
    }
    // Enforce safe https URLs — drops anything malformed or non-https
    if (!isSafeHttpsUrl(entry.author_url)) delete entry.author_url;
    if (entry.links) {
      entry.links = entry.links.filter(
        (l) => !l.url || isSafeHttpsUrl(l.url)
      );
    }
    if (!isSafeHttpsUrl(entry.preview_image)) delete entry.preview_image;
    // Pre-compute latestStableRelease so Nunjucks templates can use it directly.
    // Nunjucks lacks selectattr and loop-scoped variables don't persist to outer
    // scope, so this must be resolved in the data layer, not in templates.
    //
    // Strategy (in priority order):
    //   1. Most recent release GitHub explicitly flags non-prerelease — authoritative.
    //   2. If all recent releases are dev/rc by TAG NAME, use the latestStableRelease
    //      fetched from /releases/latest (may lie beyond the 5-release window).
    //   3. If recent releases have clean version tags but GitHub mis-labels them
    //      prerelease, use the most recent clean-tagged one as effective stable.
    // The trailing alternative catches CI experiment tags like sfpi's
    // "7.67.0-strength-49763" (version + branch word + run number) — GitHub
    // marks these non-prerelease, so only the tag shape identifies them.
    const PRE_RELEASE_TAG = /[.\-]dev[.\d]|[-.]rc\d+|[-.]alpha|[-.]beta|[-.]qa[\d.]|\d-[a-z]+-\d+$/i;

    if (Array.isArray(entry.releases) && entry.releases.length) {
      // Check both GitHub's prerelease flag AND the tag name — GitHub sometimes
      // marks dev/rc builds as non-prerelease, so the tag is the tiebreaker.
      let stable = entry.releases.find(
        r => !r.prerelease && !PRE_RELEASE_TAG.test(r.tagName)
      );

      if (!stable) {
        const allTagsAreDev = entry.releases.every(r => PRE_RELEASE_TAG.test(r.tagName));

        if (allTagsAreDev && entry.latestStableRelease) {
          // All recent builds are dev/rc; the true latest stable lives beyond the
          // fetch window — it was retrieved via /releases/latest and stored in meta.
          // Prepend it to releases so the history count is consistent.
          const alreadyInList = entry.releases.some(
            (r) => r.tagName === entry.latestStableRelease.tagName
          );
          if (!alreadyInList) {
            entry.releases = [entry.latestStableRelease, ...entry.releases];
          }
          stable = entry.latestStableRelease;
        } else if (!allTagsAreDev) {
          // Some recent releases have clean version tags but GitHub mis-labels them
          // prerelease (common for repos that never toggle the flag off). Use the
          // most recent clean-tagged release as the effective stable.
          stable = entry.releases.find(r => !PRE_RELEASE_TAG.test(r.tagName));
        }
      }

      if (stable) entry.latestStableRelease = stable;
    }
    return entry;
  });

  // Exclude entries marked hidden — they stay in the JSON database for
  // historical reference but must not appear on the public website.
  const visibleEntries = entries.filter((e) => e.hidden !== true);

  return visibleEntries.sort((a, b) => {
    // Unknown affiliation falls back to rank 2 (community tier); validate.py enforces valid values.
    const tierDiff =
      (AFFILIATION_ORDER[a.affiliation] ?? 2) -
      (AFFILIATION_ORDER[b.affiliation] ?? 2);
    if (tierDiff !== 0) return tierDiff;
    // Within a tier, order purely by stars. (`featured` no longer jumps the
    // list queue — it still boosts entries in the home-page showcase filter.)
    return (b.stars || 0) - (a.stars || 0);
  });
};
