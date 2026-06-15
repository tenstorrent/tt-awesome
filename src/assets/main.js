// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

function copyPkgCmd(btn) {
  navigator.clipboard.writeText(btn.dataset.copy).then(() => {
    btn.textContent = "copied!";
    btn.classList.add("copied");
    setTimeout(() => { btn.textContent = "copy"; btn.classList.remove("copied"); }, 1800);
  });
}

// State
let activeCategory = null;
let activeFilters = new Set(["community", "affiliated", "official"]);
let activeEntryId = null;
let activeAuthorFilter = null;
let activeReleasesView = 'all';

/* ── Mobile helpers ─────────────────────────────────────────────────────── */

/** True when the mobile breakpoint is active. */
function isMobile() {
  return window.matchMedia("(max-width: 767px)").matches;
}

/** Open the nav drawer (mobile only). */
function openDrawer() {
  document.body.classList.add("drawer-open");
}

/** Close the nav drawer. */
function closeDrawer() {
  document.body.classList.remove("drawer-open");
}

/**
 * Toggle the expandable search bar (mobile only).
 * On expand, wires the mobile search input to the same applyFilters() path.
 * On collapse, clears both inputs and returns to filtered state.
 */
function toggleSearch() {
  const row   = document.getElementById("search-bar-row");
  const chips = document.getElementById("search-chips-row");
  const input = document.getElementById("search-expanded");
  const isOpen = row.classList.contains("expanded");
  if (isOpen) {
    const hadQuery = input.value.trim() !== "";
    row.classList.remove("expanded");
    chips.classList.remove("expanded");
    input.value = "";
    document.getElementById("search").value = "";
    // Only navigate home if a search was actually in progress — otherwise stay on current pane.
    if (hadQuery) {
      _applyHome();
    }
  } else {
    row.classList.add("expanded");
    chips.classList.add("expanded");
    input.focus();
  }
}

/**
 * Update the mobile topbar for a given pane state.
 * title: string shown as the page title (empty = show logo).
 * showBack: whether the ← arrow is visible.
 */
function updateMobileTopbar(title, showBack) {
  const back  = document.getElementById("mobile-back");
  const logo  = document.getElementById("topbar-logo");
  const label = document.getElementById("mobile-title");
  if (!back) return;
  if (showBack) {
    back.classList.add("visible");
    logo.classList.add("hidden");
    label.textContent = title || "";
  } else {
    back.classList.remove("visible");
    logo.classList.remove("hidden");
    label.textContent = "";
  }
}

/**
 * Mobile back button handler.
 * If detail is visible → go back to list.
 * If list is visible → go back to home.
 */
function mobilePaneBack() {
  const panes = document.getElementById("panes");
  if (panes.classList.contains("detail-active")) {
    panes.classList.remove("detail-active");
    // Return to the pane we came from (stored in dataset.detailFrom by _applyEntry)
    if (panes.dataset.detailFrom === "releases") {
      panes.classList.add("releases-active");
      updateMobileTopbar("Recent Releases", true);
    } else {
      panes.classList.add("list-active");
      const title = document.getElementById("list-title").textContent;
      updateMobileTopbar(title, true);
    }
    document.querySelectorAll(".entry-row, .release-row").forEach(r => r.classList.remove("active"));
    document.getElementById("detail-empty").style.display = "";
    document.querySelectorAll(".detail-card").forEach(c => c.classList.remove("visible"));
    activeEntryId = null;
    // Update URL to remove the entry param so refresh/share lands on the list, not the detail
    if (panes.dataset.detailFrom === "releases") {
      pushUrl({ releases: activeReleasesView });
    } else if (activeCategory) {
      pushUrl({ cat: activeCategory });
    } else if (activeAuthorFilter) {
      pushUrl({ author: activeAuthorFilter });
    } else {
      pushUrl({});
    }
  } else {
    showHome();
  }
}

/**
 * Sync active class on all mobile chip copies to match the canonical topbar chips.
 * Called after any chip toggle so all three chip sets stay in sync.
 */
function syncMobileChips() {
  document.querySelectorAll(".mobile-chips .chip, #search-chips-row .chip").forEach(chip => {
    const f = chip.dataset.filter;
    chip.classList.toggle("active",
      f === "all" ? activeFilters.size === 3 : activeFilters.has(f)
    );
  });
}

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

  const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;
  document.querySelectorAll("[data-ts]").forEach(el => {
    if (!el.dataset.ts) return;
    el.textContent = relativeTime(el.dataset.ts);
    if (Date.now() - new Date(el.dataset.ts).getTime() < THIRTY_DAYS) {
      el.classList.add("fresh");
    }
  });

  // Search — always switch to global (cross-category) search when a query is typed,
  // regardless of which pane is active. When cleared, return home.
  document.getElementById("search").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (q) {
      _applySearchAll();
    } else {
      _applyHome();
      return;
    }
    applyFilters(q);
  });

  // Filter chips — this selector covers ALL .chip elements including mobile chip
  // copies, so a single registration is sufficient for all chip sets.
  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => toggleChip(chip))
  );

  // Mobile expandable search — always global search, same as desktop.
  const mobileInput = document.getElementById("search-expanded");
  if (mobileInput) {
    mobileInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.getElementById("search").value = e.target.value;
      if (q) {
        _applySearchAll();
        if (isMobile()) {
          const panes = document.getElementById("panes");
          panes.classList.remove("detail-active");
          panes.classList.add("list-active");
          updateMobileTopbar("All", true);
        }
      } else {
        _applyHome();
        return;
      }
      applyFilters(q);
    });
  }

  // Browser back / forward
  window.addEventListener("popstate", restoreFromUrl);

  // Sync pane state when viewport crosses the mobile/desktop boundary.
  window.matchMedia("(max-width: 767px)").addEventListener("change", (e) => {
    const panes = document.getElementById("panes");
    if (!e.matches) {
      // Desktop: remove mobile-only pane classes
      panes.classList.remove("list-active", "detail-active");
      updateMobileTopbar("", false);
      closeDrawer();
    } else {
      // Mobile: derive which pane to show from current desktop state
      if (activeEntryId) {
        panes.classList.remove("list-active");
        panes.classList.add("detail-active");
        const title = activeCategory
          ? document.getElementById("list-title").textContent
          : (activeAuthorFilter || "Releases");
        updateMobileTopbar(title, true);
      } else if (panes.classList.contains("releases-active")) {
        updateMobileTopbar("Recent Releases", true);
      } else if (activeCategory || activeAuthorFilter) {
        panes.classList.add("list-active");
        const title = document.getElementById("list-title").textContent;
        updateMobileTopbar(title, true);
      } else if (!panes.classList.contains("home-active")) {
        // Fallback: cross-category search or unknown state — show list
        panes.classList.add("list-active");
        updateMobileTopbar("All", true);
      }
      // home-active is already handled by CSS — no class addition needed
    }
  });
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
  // Bare ?entry= with no cat/releases/author — find the entry's category and open it.
  if (entryId) {
    const row = document.querySelector(`.entry-row[data-id="${CSS.escape(entryId)}"]`);
    if (row) {
      const cat = (row.dataset.categories || "").split(/[\s,]+/)[0];
      const sidebarEl = cat && document.querySelector(`.sidebar-item[data-category="${CSS.escape(cat)}"]`);
      if (sidebarEl) _applyCategory(cat, sidebarEl);
      _applyEntry(entryId, row);
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
  const panes = document.getElementById("panes");
  panes.classList.add("home-active");
  panes.classList.remove("releases-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("home-item").classList.add("active");
  if (isMobile()) {
    panes.classList.remove("list-active");
    panes.classList.remove("detail-active");
    delete panes.dataset.detailFrom;
    updateMobileTopbar("", false);
    closeDrawer();
  }
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

/** Navigate to a related entry by id, opening its category sidebar first. */
function navigateToEntry(id) {
  const row = document.querySelector(`.entry-row[data-id="${CSS.escape(id)}"]`);
  if (!row) return;
  const cat = (row.dataset.categories || "").split(/[\s,]+/)[0];
  const sidebarEl = cat && document.querySelector(`.sidebar-item[data-category="${CSS.escape(cat)}"]`);
  if (sidebarEl) _applyCategory(cat, sidebarEl);
  _applyEntry(id, row);
  pushUrl({ cat, entry: id });
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
  if (isMobile()) {
    panes.classList.remove("detail-active");
    panes.classList.add("list-active");
    updateMobileTopbar(name, true);
    closeDrawer();
  }
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
  if (isMobile()) {
    panes.classList.remove("list-active");
    panes.classList.remove("detail-active");
    updateMobileTopbar("Recent Releases", true);
    closeDrawer();
  }
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
  if (isMobile()) {
    panes.classList.remove("detail-active");
    panes.classList.add("list-active");
    updateMobileTopbar(el.textContent.trim(), true);
    closeDrawer();
  }
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
  if (isMobile()) {
    const panes = document.getElementById("panes");
    const fromReleases = panes.classList.contains("releases-active");
    panes.classList.remove("list-active", "releases-active");
    panes.classList.add("detail-active");
    // Store origin so mobilePaneBack() can return to the correct pane
    panes.dataset.detailFrom = fromReleases ? "releases" : "list";
    const title = fromReleases
      ? "Releases"
      : (activeCategory
          ? document.getElementById("list-title").textContent
          : (activeAuthorFilter || ""));
    updateMobileTopbar(title, true);
  }
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
  syncMobileChips();
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
