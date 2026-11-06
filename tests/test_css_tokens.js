// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Every var(--token) a stylesheet uses must be defined in style.css (the site's
// one :root block) or in the stylesheet itself. An unresolved var() silently
// invalidates the whole declaration, so a misspelt token drops a border or a
// color with no error anywhere. Caught on PR #314, where the roundup table
// styles used --border and --text3, neither of which exists.
// Run with: node tests/test_css_tokens.js

const assert = require("assert");
const fs = require("fs");
const path = require("path");

const ASSETS = path.join(__dirname, "..", "src", "assets");
const defined = new Set();
const defRe = /--([a-z0-9-]+)\s*:/g;
// A use that carries its own fallback, var(--x, #abc), resolves without a definition.
const useRe = /var\(--([a-z0-9-]+)\s*\)/g;

const rootCss = fs.readFileSync(path.join(ASSETS, "style.css"), "utf8");
for (const m of rootCss.matchAll(defRe)) defined.add(m[1]);

let checked = 0;
for (const file of fs.readdirSync(ASSETS).filter((f) => f.endsWith(".css"))) {
  const css = fs.readFileSync(path.join(ASSETS, file), "utf8");
  const local = new Set([...css.matchAll(defRe)].map((m) => m[1]));
  const missing = [...new Set([...css.matchAll(useRe)].map((m) => m[1]))]
    .filter((t) => !defined.has(t) && !local.has(t));
  assert.deepStrictEqual(missing, [], `${file} uses undefined tokens: ${missing.join(", ")}`);
  checked++;
}
console.log(`✓ css tokens: every var() in ${checked} stylesheets resolves`);
