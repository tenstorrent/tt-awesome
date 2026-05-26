// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

// State
let activeCategory = null;
let activeFilters = new Set(["community", "affiliated", "official"]);
let activeEntryId = null;
let activeAuthorFilter = null;
let activeReleasesView = 'all';

/** Convert an ISO date string to a human-friendly "N days ago" string. */
function relativeTime(iso) {
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return iso;
  const diff = Math.max(0, Date.now() - ts);
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins} minute${mins !== 1 ? "s" : ""} ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs !== 1 ? "s" : ""} ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days} day${days !== 1 ? "s" : ""} ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks} week${weeks !== 1 ? "s" : ""} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months !== 1 ? "s" : ""} ago`;
  const years = Math.floor(days / 365);
  return `${years} year${years !== 1 ? "s" : ""} ago`;
}

document.addEventListener("DOMContentLoaded", () => {
  // Restore view from query string (?cat=…&entry=…) before first paint,
  // so direct links and browser history both land in the right place.
  restoreFromUrl();

  document.querySelectorAll("[data-ts]").forEach(el => {
    if (el.dataset.ts) el.textContent = relativeTime(el.dataset.ts);
  });

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
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null)
  );
  const qs = new URLSearchParams(clean).toString();
  const url = qs ? `?${qs}` : location.pathname;
  history.pushState(clean, "", url);
}

/**
 * Read the current query string and navigate to the matching view.
 * Called on DOMContentLoaded and on every popstate (back / forward).
 * Does NOT push a new history entry.
 */
function restoreFromUrl() {
  const params = new URLSearchParams(location.search);
  const cat = params.get("cat");
  const author = params.get("author");
  const releases = params.get("releases");
  const entryId = params.get("entry");

  if (releases) {
    _applyReleases(releases);
    if (entryId) {
      // releases pane rows come after entry-list rows in DOM order, so query
      // .release-row explicitly to avoid matching a hidden .entry-row first.
      const row = document.querySelector(`.release-row[data-id="${CSS.escape(entryId)}"]`);
      if (row) _applyEntry(entryId, row);
    }
    return;
  }
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
  if (author) {
    _applyAuthorFilter(author);
    if (entryId) {
      const row = document.querySelector(`.entry-row[data-id="${CSS.escape(entryId)}"]`);
      if (row) _applyEntry(entryId, row);
    }
    return;
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
  const panes = document.getElementById("panes");
  panes.classList.add("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("home-item").classList.add("active");
}

/** Internal: show list pane with no category filter (cross-category search). No history push. */
function _applySearchAll() {
  activeCategory = null;
  activeAuthorFilter = null;
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("list-title").textContent = "All";
  _clearDetail();
}

/** Public: filter all entries to those by a given author name. Updates URL. */
function filterByAuthor(name) {
  pushUrl({ author: name });
  _applyAuthorFilter(name);
}

/** Internal: show author-filtered list without touching history. */
function _applyAuthorFilter(name) {
  activeAuthorFilter = name;
  activeCategory = null;
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("list-title").textContent = name;
  _clearDetail();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
}

/* ── Releases pane ──────────────────────────────────────────────────────── */

/** Public: navigate to releases pane with given view. Updates URL. */
function selectReleases(view) {
  pushUrl({ releases: view });
  _applyReleases(view);
}

/** Internal: activate releases pane without touching history. */
function _applyReleases(view) {
  const VALID_VIEWS = new Set(['all', 'official', 'community']);
  activeReleasesView = VALID_VIEWS.has(view) ? view : 'all';
  activeCategory = null;
  activeAuthorFilter = null;
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.add("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  const relItem = document.getElementById("releases-item");
  if (relItem) relItem.classList.add("active");
  applyReleasesFilter(activeReleasesView);
  _clearDetail();
}

/** Toggle the All/Official/Community button strip in the releases pane. */
function toggleReleasesView(btn) {
  selectReleases(btn.dataset.rview);
}

/** Show/hide release rows and update toggle button states and count. */
function applyReleasesFilter(view) {
  let visible = 0;
  document.querySelectorAll(".release-row").forEach(row => {
    const aff = row.dataset.affiliation;
    const show = view === "all"
      || (view === "official" && aff === "official")
      || (view === "community" && (aff === "community" || aff === "affiliated"));
    row.classList.toggle("rview-hidden", !show);
    if (show) visible++;
  });
  const countEl = document.getElementById("releases-count");
  if (countEl) countEl.textContent = `${visible} release${visible !== 1 ? "s" : ""}`;
  document.querySelectorAll(".rtoggle-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.rview === view);
  });
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
  const panes = document.getElementById("panes");
  panes.classList.remove("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("list-title").textContent = el.textContent.trim();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
  _clearDetail();
}

/** Public: select entry and update URL. */
function selectEntry(id, el) {
  if (activeAuthorFilter) {
    pushUrl({ author: activeAuthorFilter, entry: id });
  } else if (document.getElementById("panes").classList.contains("releases-active")) {
    pushUrl({ releases: activeReleasesView, entry: id });
  } else {
    pushUrl({ cat: activeCategory, entry: id });
  }
  _applyEntry(id, el);
}

/** Internal: show an entry detail card without touching history. */
function _applyEntry(id, el) {
  activeEntryId = id;
  document.querySelectorAll(".entry-row, .release-row").forEach((r) => r.classList.remove("active"));
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
  document.querySelectorAll(".entry-row, .release-row").forEach((r) => r.classList.remove("active"));
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
  // Skip entry-row filtering while the releases pane is active — it operates on
  // a separate set of rows and the list pane is not visible.
  if (document.getElementById("panes").classList.contains("releases-active")) return;
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
