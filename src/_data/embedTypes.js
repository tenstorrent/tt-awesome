// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

const fs = require("fs");
const path = require("path");

const ENTRIES_BASE = path.resolve(path.join(__dirname, "../../entries"));

function collectJsonFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.resolve(path.join(dir, entry.name));
    // Never escape the entries base directory
    if (!full.startsWith(ENTRIES_BASE + path.sep) && full !== ENTRIES_BASE) continue;
    if (entry.isDirectory()) results.push(...collectJsonFiles(full));
    else if (entry.name.endsWith(".json")) results.push(full);
  }
  return results;
}

/** Returns the deduplicated set of embed types declared across all entries. */
module.exports = function () {
  const types = new Set();
  for (const file of collectJsonFiles(ENTRIES_BASE)) {
    try {
      const data = JSON.parse(fs.readFileSync(file, "utf-8"));
      if (data.embed && typeof data.embed.type === "string") {
        types.add(data.embed.type);
      }
    } catch (error) {
      throw new Error(`Failed to read or parse entry JSON: ${file}: ${error.message}`);
    }
  }
  return [...types];
};
