// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Retired entry ids that must keep resolving.
//
// An entry's published URL is entry/<id>/, so renaming an id (a project renames
// itself, a typo gets fixed) silently 404s every existing link and bookmark to
// the old one. Any entry that has been renamed lists its old ids in
// `previous_ids`, and this data file turns those into one alias record per old
// id so entry-aliases.njk can emit a redirect stub for each.
//
// Aliases are deliberately absent from sitemap.xml and llms.txt: they exist for
// inbound links, not for discovery, and each stub points its canonical URL at
// the entry's current page.
const entriesData = require("./entries.js");

module.exports = async function (configData) {
  const entries = await entriesData(configData);
  const aliases = [];
  for (const entry of entries) {
    for (const oldId of entry.previous_ids || []) {
      aliases.push({ oldId, id: entry.id, name: entry.name });
    }
  }
  return aliases;
};
