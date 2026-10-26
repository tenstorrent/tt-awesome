// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// Data for the Models pages: one page per model, and one page per collection, family, kind,
// hardware type, status and implementation. Reads src/_data/models.json (scripts/build_models_data.py)
// and groups it. Nothing here adds a fact; every grouping is a field of that file.

const data = require("./models.json");

const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
// Complete, then Functional, then Experimental, then models with no spec status (community bundles), each by name.
const STATUS_ORDER = { Complete: 0, Functional: 1, Experimental: 2 };
const statusRank = (m) => (m.status in STATUS_ORDER ? STATUS_ORDER[m.status] : 3);
const byListing = (a, b) => (statusRank(a) - statusRank(b)) || a.name.localeCompare(b.name);

// A support page is linked only when its path has the expected shape: <folder>/<file>.md.
const DOC_BASE = "https://github.com/tenstorrent/tt-inference-server/blob/main/docs/model_support/";
const docUrl = (doc) => (typeof doc === "string" && /^[a-z]+\/[A-Za-z0-9._-]+\.md$/.test(doc) ? DOC_BASE + doc : null);

const models = data.models.map((m) => ({
  ...m,
  url: `/models/${m.id}/`,
  rows: m.rows.map((r) => ({ ...r, docUrl: docUrl(r.doc) })),
}));
const hardwareOrder = data.hardware.map((h) => h.product);

// Each set is one heading on the Models index and one group in the sidebar.
const sets = [];
const pages = [];
function addSet(group, label, intro) {
  const set = { group, label, intro, pages: [] };
  sets.push(set);
  return (key, title, blurb, list) => {
    if (!list.length) return;
    const page = { group, groupLabel: label, slug: slug(key), title, blurb, models: list, count: list.length,
                   url: `/models/${group}/${slug(key)}/` };
    set.pages.push(page);
    pages.push(page);
  };
}
const pick = (test) => models.filter(test).sort(byListing);

// Collections
{
  const add = addSet("collections", "Collections", "Ready-made lists.");
  add("all", "All models", "Every model listed in tt-inference-server or published as a tt-model bundle. Complete models come first, then Functional, then Experimental, then community bundles.", pick(() => true));
  add("single-card", "Runs on a single card",
    "Models with a supported device that tt-inference-server lists as one card: e150, n150, n300, p100, p150 or BH P300 (one card with two dies). Includes tt-model bundles built for those cards.",
    pick((m) => m.singleCard));
  add("in-tt-inference-server", "Official model support", "Models in tt-inference-server's release spec.", pick((m) => m.inSpec));
  add("has-bundle", "Community-supported models", "Models with at least one published tt-model bundle.", pick((m) => m.bundles.length > 0));
  add("newest-bundles", "Newest tt-model bundles", "The 20 models with the most recently pushed tt-model bundles, newest first.",
    models.filter((m) => m.newest).sort((a, b) => b.newest.localeCompare(a.newest) || a.name.localeCompare(b.name)).slice(0, 20));
}

// Families: a family with one model gets no page.
{
  const add = addSet("families", "Families", "Models grouped by the start of their name. Only families with two or more models are listed.");
  const fam = {};
  models.forEach((m) => { (fam[m.family] = fam[m.family] || []).push(m); });
  Object.keys(fam).sort((a, b) => fam[b].length - fam[a].length || a.localeCompare(b, undefined, { sensitivity: "base" }))
    .filter((f) => fam[f].length > 1)
    .forEach((f) => add(f, f, `Models whose name starts with ${f}.`, fam[f].sort(byListing)));
}

// Kinds
{
  const add = addSet("kinds", "Kinds", "What the model does, as tt-inference-server or the bundle's card says.");
  const kinds = {};
  models.forEach((m) => { (kinds[m.kind] = kinds[m.kind] || []).push(m); });
  // A bundle whose card states no task, and that has no inference, has no kind page. It is still in All models.
  const stated = (k) => !/task not stated/i.test(k);
  Object.keys(kinds).filter(stated).sort((a, b) => kinds[b].length - kinds[a].length || a.localeCompare(b))
    .forEach((k) => add(k, k, k === "Decision model"
      ? "Models that answer typed questions (choice, score, noul) about a text, JSON or image state with a probability for each option, and generate no text. Each bundle card names the System One (Jev) API they serve. They are not chat models, so tt launch has no client for them."
      : `Models of this kind. A tt-inference-server model's kind is its model type. A tt-model bundle's kind is the task tag on its card.${kinds[k].some((m) => m.kindInferred) ? " A bundle with no tag was placed here by an inference from its name and manifest, and its card says so." : ""}`,
      kinds[k].sort(byListing)));
}

// Hardware: tt-inference-server's names, in its own order, then names it does not list.
{
  const add = addSet("hardware", "Hardware", "Where a model runs. Names are tt-inference-server's own (DeviceTypes.to_product_str).");
  const hw = {};
  models.forEach((m) => m.hardware.forEach((h) => { (hw[h] = hw[h] || []).push(m); }));
  const keysFor = (p) => data.hardware.filter((h) => h.product === p).map((h) => h.key);
  const listed = hardwareOrder.filter((p, i) => hardwareOrder.indexOf(p) === i && hw[p]);
  const unlisted = Object.keys(hw).filter((p) => !hardwareOrder.includes(p)).sort();
  listed.forEach((p) => add(p, p, `Device keys in tt-inference-server: ${keysFor(p).join(", ")}.`, hw[p].sort(byListing)));
  unlisted.forEach((p) => add(p, p, "tt-inference-server's device list has no product name for this. It is shown as the source spells it.", hw[p].sort(byListing)));
}

// Status
{
  const add = addSet("status", "Status", "Best status a model has in tt-inference-server's release spec.");
  ["Complete", "Functional", "Experimental"].forEach((s) =>
    add(s, s, `Models whose best status in the release spec is ${s}.`, pick((m) => m.status === s)));
}

// Implementations: the tt-metal code that runs the model, from the spec.
{
  const add = addSet("implementations", "Implementations", "The tt-metal code that runs a model, as named in the release spec.");
  const impls = {};
  models.forEach((m) => m.impls.forEach((i) => { (impls[i] = impls[i] || []).push(m); }));
  Object.keys(impls).sort((a, b) => impls[b].length - impls[a].length || a.localeCompare(b))
    .forEach((i) => add(i, i, `Models the release spec runs with the ${i} implementation.`, impls[i].sort(byListing)));
}

// URL lookups for templates
const urls = { hardware: {}, family: {}, kind: {}, implementation: {} };
pages.forEach((p) => {
  const map = { hardware: urls.hardware, families: urls.family, kinds: urls.kind, implementations: urls.implementation }[p.group];
  if (map) map[p.title] = p.url;
});

module.exports = { models, pages, sets, urls, hardware: data.hardware, spec: data.spec, count: models.length };
