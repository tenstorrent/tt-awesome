// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// State
let activeCategory = null;
let activeFilters = new Set(["community", "affiliated", "official"]);
let activeEntryId = null;
let activeAuthorFilter = null;

document.addEventListener("DOMContentLoaded", () => {
  // Restore view from query string (?cat=…&entry=…) before first paint,
  // so direct links and browser history both land in the right place.
  restoreFromUrl();

  // Search — when typing while on the home view, switch to cross-category search mode.
  // When the query is cleared in that mode, return home.
  document.getElementById("search").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (q && isHomeActive()) {
      _applySearchAll();
    } else if (!q && activeCategory === null && activeAuthorFilter === null && !isHomeActive()) {
      _applyHome();
      return;
    }
    applyFilters(q);
  });

  // Filter chips
  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => toggleChip(chip))
  );

  // Browser back / forward
  window.addEventListener("popstate", restoreFromUrl);
});

/* ── URL helpers ─────────────────────────────────────────────────────────── */

/**
 * Push a new history entry with the given query params.
 * Pass an empty object {} to return to the root path with no query string.
 */
function pushUrl(params) {
  const qs = new URLSearchParams(params).toString();
  const url = qs ? `?${qs}` : location.pathname;
  history.pushState(params, "", url);
}

/**
 * Read the current query string and navigate to the matching view.
 * Called on DOMContentLoaded and on every popstate (back / forward).
 * Does NOT push a new history entry.
 */
function restoreFromUrl() {
  const params = new URLSearchParams(location.search);
  const cat = params.get("cat");
  const entryId = params.get("entry");

  if (cat) {
    const el = document.querySelector(`.sidebar-item[data-category="${CSS.escape(cat)}"]`);
    if (el) {
      _applyCategory(cat, el);
      if (entryId) {
        const row = document.querySelector(`.entry-row[data-id="${CSS.escape(entryId)}"]`);
        if (row) _applyEntry(entryId, row);
      }
      return;
    }
  }
  _applyHome();
}

/* ── Home view ──────────────────────────────────────────────────────────── */

function isHomeActive() {
  return document.getElementById("panes").classList.contains("home-active");
}

/** Public: show home and update URL. */
function showHome() {
  pushUrl({});
  _applyHome();
}

/** Internal: show home without touching history. */
function _applyHome() {
  activeCategory = null;
  activeEntryId = null;
  activeAuthorFilter = null;
  document.getElementById("panes").classList.add("home-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("home-item").classList.add("active");
}

/** Internal: show list pane with no category filter (cross-category search). No history push. */
function _applySearchAll() {
  activeCategory = null;
  activeAuthorFilter = null;
  document.getElementById("panes").classList.remove("home-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("list-title").textContent = "All";
  _clearDetail();
}

/** Public: filter all entries to those by a given author name. */
function filterByAuthor(name) {
  activeAuthorFilter = name;
  activeCategory = null;
  document.getElementById("panes").classList.remove("home-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("list-title").textContent = name;
  _clearDetail();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
}

/** Navigate to a category by slug — used by the home page card clicks. */
function selectCategoryBySlug(slug) {
  const el = document.querySelector(`.sidebar-item[data-category="${CSS.escape(slug)}"]`);
  if (el) selectCategory(slug, el);
}

/* ── Category / entry selection ─────────────────────────────────────────── */

/** Public: select category and update URL. */
function selectCategory(slug, el) {
  pushUrl({ cat: slug });
  _applyCategory(slug, el);
}

/** Internal: select category without touching history. */
function _applyCategory(slug, el) {
  activeCategory = slug;
  activeAuthorFilter = null;
  document.getElementById("panes").classList.remove("home-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("list-title").textContent = el.textContent.trim();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
  _clearDetail();
}

/** Public: select entry and update URL. */
function selectEntry(id, el) {
  pushUrl({ cat: activeCategory, entry: id });
  _applyEntry(id, el);
}

/** Internal: show an entry detail card without touching history. */
function _applyEntry(id, el) {
  activeEntryId = id;
  document.querySelectorAll(".entry-row").forEach((r) => r.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("detail-empty").style.display = "none";
  document.querySelectorAll(".detail-card").forEach((c) => c.classList.remove("visible"));
  const card = document.getElementById("detail-" + id);
  if (card) card.classList.add("visible");
}

/** Internal: clear detail panel without touching history. */
function _clearDetail() {
  activeEntryId = null;
  document.getElementById("detail-empty").style.display = "";
  document.querySelectorAll(".detail-card").forEach((c) => c.classList.remove("visible"));
  document.querySelectorAll(".entry-row").forEach((r) => r.classList.remove("active"));
}

/* ── Filter chips ───────────────────────────────────────────────────────── */

function toggleChip(chip) {
  const f = chip.dataset.filter;
  if (f === "all") {
    activeFilters = activeFilters.size === 3
      ? new Set()
      : new Set(["community", "affiliated", "official"]);
  } else {
    activeFilters.has(f) ? activeFilters.delete(f) : activeFilters.add(f);
  }
  document.querySelectorAll(".chip").forEach((c) => {
    const cf = c.dataset.filter;
    c.classList.toggle("active",
      cf === "all" ? activeFilters.size === 3 : activeFilters.has(cf)
    );
  });
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
}

/* ── Row visibility ─────────────────────────────────────────────────────── */

function applyFilters(query) {
  let visible = 0;
  const authorFilter = activeAuthorFilter ? activeAuthorFilter.toLowerCase() : null;
  document.querySelectorAll(".entry-row").forEach((row) => {
    const cats  = (row.dataset.categories || "").split(",");
    const aff   = row.dataset.affiliation;
    const text  = row.dataset.search || "";
    const show  =
      (!activeCategory || cats.includes(activeCategory)) &&
      activeFilters.has(aff) &&
      (!query || text.includes(query)) &&
      (!authorFilter || (row.dataset.author || "") === authorFilter);
    row.classList.toggle("hidden", !show);
    if (show) visible++;
  });
  document.getElementById("list-count").textContent = `${visible} entr${visible === 1 ? "y" : "ies"}`;
  // If the active entry is now filtered out, clear the detail panel
  if (activeEntryId) {
    const row = document.querySelector(`.entry-row[data-id="${activeEntryId}"]`);
    if (row && row.classList.contains("hidden")) _clearDetail();
  }
}
