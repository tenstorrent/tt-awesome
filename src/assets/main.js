// State
let activeCategory = null;
let activeFilters = new Set(["community", "affiliated", "official"]);
let activeEntryId = null;

document.addEventListener("DOMContentLoaded", () => {
  // Start on the welcome page rather than auto-selecting the first category
  showHome();

  // Search — when typing while on the home view, jump into "all" mode
  document.getElementById("search").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (q && isHomeActive()) {
      // Select the first category to surface results
      const first = document.querySelector(".sidebar-item[data-category]");
      if (first) selectCategory(first.dataset.category, first);
    }
    applyFilters(q);
  });

  // Filter chips
  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => toggleChip(chip))
  );
});

/* ── Home view ──────────────────────────────────────────────────────────── */

function isHomeActive() {
  return document.getElementById("panes").classList.contains("home-active");
}

function showHome() {
  activeCategory = null;
  activeEntryId = null;
  document.getElementById("panes").classList.add("home-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  document.getElementById("home-item").classList.add("active");
}

/** Navigate to a category by slug — used by the home page card clicks. */
function selectCategoryBySlug(slug) {
  const el = document.querySelector(`.sidebar-item[data-category="${slug}"]`);
  if (el) selectCategory(slug, el);
}

/* ── Category / entry selection ─────────────────────────────────────────── */

function selectCategory(slug, el) {
  activeCategory = slug;
  // Leave the home view
  document.getElementById("panes").classList.remove("home-active");
  document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("list-title").textContent = el.textContent.trim();
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
  clearDetail();
}

function selectEntry(id, el) {
  activeEntryId = id;
  document.querySelectorAll(".entry-row").forEach((r) => r.classList.remove("active"));
  el.classList.add("active");
  document.getElementById("detail-empty").style.display = "none";
  document.querySelectorAll(".detail-card").forEach((c) => c.classList.remove("visible"));
  const card = document.getElementById("detail-" + id);
  if (card) card.classList.add("visible");
}

function clearDetail() {
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
  document.querySelectorAll(".entry-row").forEach((row) => {
    const cats  = (row.dataset.categories || "").split(",");
    const aff   = row.dataset.affiliation;
    const text  = row.dataset.search || "";
    const show  =
      (!activeCategory || cats.includes(activeCategory)) &&
      activeFilters.has(aff) &&
      (!query || text.includes(query));
    row.classList.toggle("hidden", !show);
    if (show) visible++;
  });
  document.getElementById("list-count").textContent = `${visible} entr${visible === 1 ? "y" : "ies"}`;
  // If the active entry is now filtered out, clear the detail panel
  if (activeEntryId) {
    const row = document.querySelector(`.entry-row[data-id="${activeEntryId}"]`);
    if (row && row.classList.contains("hidden")) clearDetail();
  }
}
