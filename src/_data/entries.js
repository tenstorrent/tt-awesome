const fs = require("fs");
const path = require("path");
const meta = require("./github_meta.json");

const metaByUrl = {};
for (const [url, data] of Object.entries(meta)) {
  metaByUrl[url] = data;
}

const AFFILIATION_ORDER = { community: 0, affiliated: 1, official: 2 };

module.exports = function () {
  const entriesDir = path.join(__dirname, "../../entries");
  const files = fs.readdirSync(entriesDir).filter((f) => f.endsWith(".json"));

  const entries = files.map((f) => {
    const entry = JSON.parse(
      fs.readFileSync(path.join(entriesDir, f), "utf8")
    );
    const repoLink = (entry.links || []).find((l) => l.type === "repo");
    if (repoLink && metaByUrl[repoLink.url]) {
      Object.assign(entry, metaByUrl[repoLink.url]);
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
