// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Site-wide constants for templates. baseUrl is the canonical public host
// (the one kapa.ai and other crawlers are pointed at) and always ends with
// a trailing slash so templates can append paths directly. The feeds
// intentionally do NOT use this — their tenstorrent.github.io URLs are baked
// into Atom <id> values, which must never change.
module.exports = {
  baseUrl: "https://docs.tenstorrent.com/tt-awesome/",
};
