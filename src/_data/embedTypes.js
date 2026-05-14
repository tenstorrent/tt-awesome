// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

const fs = require("fs");
const path = require("path");

function collectJsonFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) results.push(...collectJsonFiles(full));
    else if (entry.name.endsWith(".json")) results.push(full);
  }
  return results;
}

/** Returns the deduplicated set of embed types declared across all entries. */
module.exports = function () {
  const types = new Set();
  const entriesDir = path.join(__dirname, "../../entries");
  for (const file of collectJsonFiles(entriesDir)) {
    try {
      const data = JSON.parse(fs.readFileSync(file, "utf-8"));
      if (data.embed && typeof data.embed.type === "string") {
        types.add(data.embed.type);
      }
    } catch (_) {}
  }
  return [...types];
};
