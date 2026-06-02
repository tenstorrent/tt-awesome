// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Eleventy data file: exposes planet_feeds.json as the `planetFeeds` global.
// Returns [] if the file doesn't exist yet (first build before nightly run).
const fs = require("fs");
const path = require("path");

module.exports = function () {
  const p = path.join(__dirname, "planet_feeds.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf8"));
};
