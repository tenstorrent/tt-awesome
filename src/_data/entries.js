// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

const fs = require("fs");
const path = require("path");
const meta = require("./github_meta.json");

const metaByUrl = {};
for (const [url, data] of Object.entries(meta)) {
  metaByUrl[url] = data;
}

const AFFILIATION_ORDER = { community: 0, affiliated: 1, official: 2 };

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
    if (Array.isArray(entry.releases) && entry.releases.length) {
      const stable = entry.releases.find(r => r.prerelease === false);
      if (stable) entry.latestStableRelease = stable;
    }
    return entry;
  });

  // Exclude entries marked hidden — they stay in the JSON database for
  // historical reference but must not appear on the public website.
  const visibleEntries = entries.filter((e) => e.hidden !== true);

  return visibleEntries.sort((a, b) => {
    // Unknown affiliation falls back to rank 2 (official tier); validate.py enforces valid values.
    const tierDiff =
      (AFFILIATION_ORDER[a.affiliation] ?? 2) -
      (AFFILIATION_ORDER[b.affiliation] ?? 2);
    if (tierDiff !== 0) return tierDiff;
    const featDiff = (a.featured ? 0 : 1) - (b.featured ? 0 : 1);
    if (featDiff !== 0) return featDiff;
    return (b.stars || 0) - (a.stars || 0);
  });
};
