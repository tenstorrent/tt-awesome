# Mobile-Responsive & Delightful UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make tt-awesome fully usable on mobile via a hamburger drawer, stacked pane navigation, tucked search icon, and smooth CSS transitions — with zero impact on the desktop layout.

**Architecture:** A single `@media (max-width: 767px)` block in `style.css` rewires the three-pane flex layout to single-pane stacked views controlled by CSS classes (`list-active`, `detail-active`) on `#panes`. A small addition to `main.js` handles drawer open/close, back-button logic, and search expand/collapse. One topbar HTML change adds the back-arrow and hamburger elements.

**Tech Stack:** Vanilla CSS (media queries, CSS transitions), vanilla JS (matchMedia, classList), Eleventy (Nunjucks templates), no new dependencies.

---

## File Map

| File | What changes |
|---|---|
| `src/index.njk` | Add `#mobile-back` button and `#hamburger` button to `.topbar`; add second `.chips` block inside `.list-head` for mobile chip display |
| `src/_includes/entry-list.njk` | Add duplicate `.chips` container inside `.list-head` for mobile filter chips |
| `src/_includes/releases-list.njk` | No change needed (releases-pane already has its own toggle buttons) |
| `src/assets/style.css` | Add mobile breakpoint block at end of file; add `.drawer-open`, `.search-expanded`, `.mobile-back`, `.hamburger`, `.drawer-backdrop`, `list-active`, `detail-active` rules |
| `src/assets/main.js` | Add `openDrawer()`, `closeDrawer()`, `toggleSearch()`, `updateMobileTopbar()`, back-button click handler, mobile media query listener; hook into existing `_applyCategory()`, `_applyEntry()`, `_applyHome()`, `_applyReleases()` |

---

## Task 1: Add mobile topbar HTML elements

**Files:**
- Modify: `src/index.njk`

The topbar currently has: logo | search input | chips. We need to add a back button (hidden by default, shown on mobile when in list/detail) and a hamburger button (hidden on desktop, shown on mobile).

- [ ] **Step 1: Update `src/index.njk` topbar**

Replace the current topbar content:
```html
<header class="topbar">
  <span class="logo">⚡ tt-awesome</span>
  <input class="search" id="search" type="text" placeholder="Search {{ entries | length }} entries…" autocomplete="off">
  <div class="chips">
    <button class="chip active" data-filter="all">All</button>
    <button class="chip active" data-filter="community">community</button>
    <button class="chip active" data-filter="affiliated">affiliated</button>
    <button class="chip active" data-filter="official">official</button>
  </div>
</header>
```

With:
```html
<header class="topbar">
  <button class="mobile-back" id="mobile-back" aria-label="Go back" onclick="mobilePaneBack()">←</button>
  <span class="logo" id="topbar-logo" onclick="showHome(); return false;" style="cursor:pointer;">⚡ tt-awesome</span>
  <span class="mobile-title" id="mobile-title"></span>
  <input class="search" id="search" type="text" placeholder="Search {{ entries | length }} entries…" autocomplete="off">
  <button class="search-toggle" id="search-toggle" aria-label="Search" onclick="toggleSearch()">🔍</button>
  <div class="chips" id="topbar-chips">
    <button class="chip active" data-filter="all">All</button>
    <button class="chip active" data-filter="community">community</button>
    <button class="chip active" data-filter="affiliated">affiliated</button>
    <button class="chip active" data-filter="official">official</button>
  </div>
  <button class="hamburger" id="hamburger" aria-label="Open menu" onclick="openDrawer()">☰</button>
</header>
```

- [ ] **Step 2: Add mobile chips to entry-list.njk list-head**

Open `src/_includes/entry-list.njk`. Change `.list-head` from:
```html
<div class="list-head">
  <div class="list-title" id="list-title">{{ categories[0].label }}</div>
  <div class="list-count" id="list-count"></div>
</div>
```
To:
```html
<div class="list-head">
  <div class="list-title-row">
    <div class="list-title" id="list-title">{{ categories[0].label }}</div>
    <div class="list-count" id="list-count"></div>
  </div>
  <div class="chips mobile-chips" id="list-chips">
    <button class="chip active" data-filter="all">All</button>
    <button class="chip active" data-filter="community">community</button>
    <button class="chip active" data-filter="affiliated">affiliated</button>
    <button class="chip active" data-filter="official">official</button>
  </div>
</div>
```

- [ ] **Step 3: Build and verify no desktop breakage**

```bash
npm run build
```
Expected: build succeeds, `_site/index.html` exists. Open in a desktop browser and confirm it looks identical to before (new elements are invisible on desktop — we haven't written CSS yet, so they may be briefly visible; that's fine for now).

- [ ] **Step 4: Commit**

```bash
git add src/index.njk src/_includes/entry-list.njk
git commit -m "feat(mobile): add back button, hamburger, search toggle to topbar HTML"
```

---

## Task 2: Desktop-hide new elements + drawer HTML

**Files:**
- Modify: `src/assets/style.css`

We need to hide the new mobile-only elements on desktop, and add the drawer + backdrop markup to the sidebar.

- [ ] **Step 1: Add desktop-hide rules to style.css**

Append to the end of `src/assets/style.css`:

```css
/* ── Mobile-only elements (hidden on desktop) ──────────────────────────── */
.mobile-back   { display: none; }
.mobile-title  { display: none; }
.search-toggle { display: none; }
.hamburger     { display: none; }
.mobile-chips  { display: none; }
.drawer-backdrop { display: none; }
```

- [ ] **Step 2: Add drawer backdrop element to sidebar.njk**

Open `src/_includes/sidebar.njk`. Add a backdrop div just before the closing `</nav>` tag:

```html
  <div class="drawer-backdrop" id="drawer-backdrop" onclick="closeDrawer()"></div>
</nav>
```

Wait — the backdrop needs to be *outside* the `<nav>` so it covers the whole viewport. Add it to `src/index.njk` instead, directly after `<div class="panes home-active" id="panes">`:

Actually the backdrop must be a sibling of `.panes`, not inside it. In `src/index.njk`, add it as a direct child of `.app`, just before the closing `</div>` of `.app`:

```html
<div class="app">
  <header class="topbar">
    ...
  </header>
  <div class="panes home-active" id="panes">
    ...
  </div>
  <div class="drawer-backdrop" id="drawer-backdrop" onclick="closeDrawer()"></div>
</div>
```

- [ ] **Step 3: Add backdrop CSS**

Append to `src/assets/style.css`:

```css
/* ── Drawer backdrop ────────────────────────────────────────────────────── */
.drawer-backdrop {
  position: fixed; inset: 0; z-index: 199;
  background: rgba(0,0,0,0); pointer-events: none;
  transition: background 200ms ease-out;
}
.drawer-open .drawer-backdrop {
  background: rgba(0,0,0,0.55); pointer-events: auto;
}
```

The `.drawer-open` class will be applied to `body` when the drawer is open.

- [ ] **Step 4: Build and confirm**

```bash
npm run build
```
Expected: no errors. Desktop layout still looks identical.

- [ ] **Step 5: Commit**

```bash
git add src/assets/style.css src/index.njk src/_includes/sidebar.njk
git commit -m "feat(mobile): desktop-hide mobile elements, add drawer backdrop"
```

---

## Task 3: Mobile breakpoint — layout rewire

**Files:**
- Modify: `src/assets/style.css`

This is the core CSS task. At ≤767px, rewrite the layout so only one pane is visible at a time.

- [ ] **Step 1: Add the mobile breakpoint block to style.css**

Append to the end of `src/assets/style.css`:

```css
/* ════════════════════════════════════════════════════════════════════════
   MOBILE  (≤767px)
   ════════════════════════════════════════════════════════════════════════ */
@media (max-width: 767px) {
  /* Allow page to scroll normally on mobile */
  html, body { overflow: auto; height: auto; }
  .app { height: auto; min-height: 100vh; flex-direction: column; }

  /* ── Topbar ──────────────────────────────────────────────────────────── */
  .topbar { padding: 0 10px; gap: 8px; position: sticky; top: 0; z-index: 100; }
  .logo   { font-size: 14px; }
  /* Hide desktop search input and chips from topbar */
  .search      { display: none; }
  #topbar-chips { display: none; }
  /* Show mobile-only elements */
  .mobile-back  { display: flex; align-items: center; justify-content: center;
                  background: none; border: none; color: var(--teal);
                  font-size: 20px; min-width: 44px; min-height: 44px;
                  cursor: pointer; padding: 0; visibility: hidden; }
  .mobile-back.visible { visibility: visible; }
  .mobile-title { display: block; font-size: 13px; font-weight: 600;
                  color: var(--text); flex: 1; overflow: hidden;
                  text-overflow: ellipsis; white-space: nowrap; }
  .logo.hidden  { display: none; }
  .search-toggle { display: flex; align-items: center; justify-content: center;
                   background: none; border: none; font-size: 16px;
                   min-width: 44px; min-height: 44px; cursor: pointer; padding: 0; }
  .hamburger   { display: flex; align-items: center; justify-content: center;
                 background: none; border: none; color: var(--text);
                 font-size: 18px; min-width: 44px; min-height: 44px;
                 cursor: pointer; padding: 0; flex-shrink: 0; }

  /* ── Expandable search bar ───────────────────────────────────────────── */
  .search-bar-row { display: none; background: var(--bg3);
                    padding: 0 10px; overflow: hidden; max-height: 0;
                    transition: max-height 180ms ease-out, padding 180ms ease-out;
                    border-bottom: 1px solid rgba(79,209,197,0.1); }
  .search-bar-row.expanded { display: flex; max-height: 52px; padding: 8px 10px; }
  .search-bar-row .search { display: flex; flex: 1; max-width: none; }
  .search-close { background: none; border: none; color: var(--muted);
                  font-size: 18px; min-width: 44px; min-height: 44px;
                  cursor: pointer; display: flex; align-items: center;
                  justify-content: center; }
  /* Chips row shown below search when expanded */
  .search-chips-row { display: none; background: var(--bg3);
                      padding: 0 10px; overflow: hidden; max-height: 0;
                      transition: max-height 180ms ease-out;
                      border-bottom: 1px solid rgba(79,209,197,0.1); }
  .search-chips-row.expanded { display: flex; max-height: 44px;
                                padding: 6px 10px; gap: 6px; flex-wrap: nowrap;
                                overflow-x: auto; }

  /* ── Panes — stacked single column ──────────────────────────────────── */
  .panes { flex-direction: column; overflow: visible; flex: unset; }
  /* By default hide all panes on mobile — JS adds active classes */
  .sidebar     { display: none; }
  .home-view   { display: none; }
  .list-pane   { display: none; width: 100%; border-right: none; }
  .releases-pane { display: none; width: 100%; border-right: none; }
  .detail-pane { display: none; width: 100%; padding: 16px; }

  /* Show the right pane based on state class */
  .panes.home-active    .home-view      { display: block; }
  .panes.list-active    .list-pane      { display: flex; }
  .panes.detail-active  .detail-pane    { display: block; }
  .panes.releases-active .releases-pane { display: flex; }

  /* ── Home view ───────────────────────────────────────────────────────── */
  .home-view  { padding: 20px 16px 32px; }
  .home-title { font-size: 24px; }
  .home-sub   { font-size: 13px; margin-bottom: 20px; }
  .home-stats { gap: 24px; }
  .home-stat-n { font-size: 24px; }
  .cat-grid   { grid-template-columns: 1fr 1fr; gap: 10px; }
  @media (max-width: 400px) {
    .cat-grid { grid-template-columns: 1fr; }
  }

  /* ── List pane ───────────────────────────────────────────────────────── */
  .list-head  { padding: 8px 12px; }
  .mobile-chips { display: flex; gap: 4px; flex-wrap: nowrap;
                  overflow-x: auto; padding: 6px 0 2px;
                  /* hide scrollbar */ scrollbar-width: none; }
  .mobile-chips::-webkit-scrollbar { display: none; }
  .entry-row  { padding: 10px 12px; }
  .row-name   { font-size: 13px; }
  .row-desc   { font-size: 12px; }

  /* ── Detail pane ─────────────────────────────────────────────────────── */
  .detail-name { font-size: 18px; }
  .detail-desc { font-size: 13px; }

  /* ── Pane slide transition ───────────────────────────────────────────── */
  .list-pane, .detail-pane, .releases-pane, .home-view {
    transition: opacity 180ms ease-out;
    animation: pane-in 220ms ease-out;
  }
  @keyframes pane-in {
    from { opacity: 0; transform: translateX(18px); }
    to   { opacity: 1; transform: translateX(0); }
  }

  /* ── Drawer (sidebar as overlay) ─────────────────────────────────────── */
  .sidebar {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: 280px; z-index: 200;
    transform: translateX(-100%);
    transition: transform 200ms ease-out;
    padding-top: 56px; /* clear topbar */
  }
  body.drawer-open .sidebar { transform: translateX(0); display: flex; }
  .drawer-backdrop           { display: block; }
  body.drawer-open .drawer-backdrop {
    background: rgba(0,0,0,0.55); pointer-events: auto;
  }

  /* ── Touch targets ───────────────────────────────────────────────────── */
  .sidebar-item { min-height: 44px; display: flex; align-items: center; }
  .chip         { min-height: 36px; padding: 4px 12px; }
  .entry-row    { min-height: 56px; }
  .release-row  { min-height: 56px; }
}
```

- [ ] **Step 2: Add the expandable search bar HTML to index.njk**

The `.search-bar-row` needs to be a sibling of `.topbar` in `.app`. In `src/index.njk`, after the `</header>` closing tag and before `<div class="panes...">`, add:

```html
<div class="search-bar-row" id="search-bar-row">
  <input class="search" id="search-expanded" type="text" placeholder="Search {{ entries | length }} entries…" autocomplete="off">
  <button class="search-close" onclick="toggleSearch()">✕</button>
</div>
<div class="search-chips-row" id="search-chips-row">
  <button class="chip active" data-filter="all">All</button>
  <button class="chip active" data-filter="community">community</button>
  <button class="chip active" data-filter="affiliated">affiliated</button>
  <button class="chip active" data-filter="official">official</button>
</div>
```

- [ ] **Step 3: Build and check mobile layout**

```bash
npm run build
```

Open `_site/index.html` in a browser. Use DevTools → Toggle device toolbar → iPhone (375px wide). Verify:
- Home view shows with category grid
- Sidebar is hidden
- Hamburger (☰) is visible in topbar right
- 🔍 icon is visible
- Back arrow is hidden (correct — we're on home)

Desktop (1280px): layout still identical to before.

- [ ] **Step 4: Commit**

```bash
git add src/assets/style.css src/index.njk
git commit -m "feat(mobile): add mobile breakpoint CSS — stacked panes, drawer, search expand"
```

---

## Task 4: Mobile JS — drawer + back button + search toggle

**Files:**
- Modify: `src/assets/main.js`

Add the mobile interaction logic. Key principle: all of this is additive — existing desktop functions are unchanged. A `isMobile()` helper gates mobile-specific behavior.

- [ ] **Step 1: Add mobile helpers at the top of main.js, after the state variables**

After the existing state declarations (around line 10), add:

```js
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
    row.classList.remove("expanded");
    chips.classList.remove("expanded");
    input.value = "";
    applyFilters("");
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
  if (!back) return; // desktop — elements not present, nothing to do
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
    panes.classList.add("list-active");
    const title = document.getElementById("list-title").textContent;
    updateMobileTopbar(title, true);
    // Clear active entry highlight
    document.querySelectorAll(".entry-row, .release-row").forEach(r => r.classList.remove("active"));
    document.getElementById("detail-empty").style.display = "";
    document.querySelectorAll(".detail-card").forEach(c => c.classList.remove("visible"));
    activeEntryId = null;
  } else {
    showHome();
  }
}
```

- [ ] **Step 2: Wire the mobile search input to applyFilters**

In `DOMContentLoaded`, after the existing search listener block (around line 50), add:

```js
  // Mobile expandable search input mirrors the desktop search
  const mobileInput = document.getElementById("search-expanded");
  if (mobileInput) {
    mobileInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      // Keep desktop input in sync
      document.getElementById("search").value = e.target.value;
      if (q && isHomeActive()) {
        _applySearchAll();
        if (isMobile()) {
          const panes = document.getElementById("panes");
          panes.classList.add("list-active");
          updateMobileTopbar("All", true);
        }
      } else if (!q && activeCategory === null && activeAuthorFilter === null && !isHomeActive()) {
        _applyHome();
        return;
      }
      applyFilters(q);
    });
  }
```

- [ ] **Step 3: Wire mobile chip copies to toggleChip**

The `.mobile-chips` in `entry-list.njk` and `.search-chips-row` in `index.njk` need to trigger the same `toggleChip()` logic. In `DOMContentLoaded`, after the existing chip listener block, add:

```js
  // Mobile chip copies (list-head + search-chips-row) use the same toggleChip logic.
  // We sync their active state by re-applying all chip active classes after any toggle.
  document.querySelectorAll(".mobile-chips .chip, #search-chips-row .chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      toggleChip(chip);
      syncMobileChips();
    })
  );
```

Then add this function alongside the other helpers (after `mobilePaneBack`):

```js
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
```

Also call `syncMobileChips()` at the end of the existing `toggleChip()` function:

```js
function toggleChip(chip) {
  // ... existing code ...
  applyFilters(document.getElementById("search").value.toLowerCase().trim());
  syncMobileChips(); // keep mobile copies in sync
}
```

- [ ] **Step 4: Hook into _applyCategory to set mobile pane state**

In `_applyCategory()`, add at the end of the function:

```js
  // Mobile: switch to list pane and update topbar
  if (isMobile()) {
    const panes = document.getElementById("panes");
    panes.classList.remove("detail-active");
    panes.classList.add("list-active");
    updateMobileTopbar(el.textContent.trim(), true);
    closeDrawer();
  }
```

- [ ] **Step 5: Hook into _applyEntry to set mobile pane state**

In `_applyEntry()`, add at the end of the function:

```js
  // Mobile: switch to detail pane and update topbar
  if (isMobile()) {
    const panes = document.getElementById("panes");
    panes.classList.remove("list-active");
    panes.classList.add("detail-active");
    const title = activeCategory
      ? document.getElementById("list-title").textContent
      : (activeAuthorFilter || "Releases");
    updateMobileTopbar(title, true);
  }
```

- [ ] **Step 6: Hook into _applyHome to reset mobile pane state**

In `_applyHome()`, add at the end of the function:

```js
  // Mobile: reset to home pane
  if (isMobile()) {
    const panes = document.getElementById("panes");
    panes.classList.remove("list-active");
    panes.classList.remove("detail-active");
    updateMobileTopbar("", false);
    closeDrawer();
  }
```

- [ ] **Step 7: Hook into _applyReleases to set mobile pane state**

In `_applyReleases()`, add at the end of the function:

```js
  // Mobile: switch to releases pane
  if (isMobile()) {
    const panes = document.getElementById("panes");
    panes.classList.remove("list-active");
    panes.classList.remove("detail-active");
    updateMobileTopbar("Recent Releases", true);
    closeDrawer();
  }
```

- [ ] **Step 8: Hook into _applyAuthorFilter to set mobile pane state**

In `_applyAuthorFilter()`, add at the end of the function:

```js
  // Mobile: switch to list pane
  if (isMobile()) {
    const panes = document.getElementById("panes");
    panes.classList.remove("detail-active");
    panes.classList.add("list-active");
    updateMobileTopbar(name, true);
    closeDrawer();
  }
```

- [ ] **Step 9: Reset on resize to desktop**

In `DOMContentLoaded`, add after the `window.addEventListener("popstate", ...)` line:

```js
  // When resizing from mobile to desktop, remove mobile-only pane classes
  window.matchMedia("(max-width: 767px)").addEventListener("change", (e) => {
    if (!e.matches) {
      const panes = document.getElementById("panes");
      panes.classList.remove("list-active", "detail-active");
      updateMobileTopbar("", false);
      closeDrawer();
    }
  });
```

- [ ] **Step 10: Build and smoke-test**

```bash
npm run build
```

Open `_site/index.html` in DevTools mobile view (375px). Verify:
1. Home shows category grid, ☰ and 🔍 visible, logo visible, back arrow hidden
2. Tapping a category card → list pane slides in, back arrow visible, drawer category highlighted
3. Tapping ☰ → drawer slides in from left, backdrop visible
4. Tapping backdrop → drawer closes
5. Tapping a list entry → detail pane slides in
6. Tapping ← → returns to list pane
7. Tapping ← again → returns to home
8. Tapping 🔍 → search bar expands below topbar, chips appear
9. Typing in search while on home → switches to list pane with results
10. Desktop at 1280px: zero visual change

- [ ] **Step 11: Commit**

```bash
git add src/assets/main.js
git commit -m "feat(mobile): drawer, back-button, search toggle, pane routing JS"
```

---

## Task 5: Polish — transitions, touch targets, home pane on mobile init

**Files:**
- Modify: `src/assets/style.css`
- Modify: `src/assets/main.js`

Ensure the home view actually shows on mobile page load (the existing `home-active` class shows `.home-view` but our new mobile CSS requires it to be explicitly triggered) and add the final polish touches.

- [ ] **Step 1: Verify home-active shows home-view on mobile**

The existing CSS rule `.panes.home-active .home-view` hides it on desktop (via the pane layout), but our mobile block overrides this. Check that `_applyHome()` is correctly setting the `home-active` class on `#panes`.

In `src/assets/style.css`, in the mobile breakpoint block, ensure the existing desktop rule is overridden correctly. The rule:

```css
.panes.home-active    .home-view      { display: block; }
```

is already in the mobile block from Task 3. No change needed — this is a verification step.

- [ ] **Step 2: On mobile initial load, set list-active if URL has ?cat=**

`restoreFromUrl()` calls `_applyCategory()` for `?cat=` URLs, which already sets `list-active` via our hook. This is already handled — verification only.

- [ ] **Step 3: Cat card grid — ensure two-column on mobile doesn't truncate featured entry preview**

In the mobile breakpoint block, add:

```css
  /* Cat cards: hide featured entry preview on smallest screens to save space */
  @media (max-width: 480px) {
    .cat-card-feature { display: none; }
  }
```

- [ ] **Step 4: Detail pane — preview image on mobile**

The `detail-preview img` has `max-height: 220px`. On mobile this is fine but the top-padding on detail-pane needs to account for no sticky header offset. Verify `padding: 16px` from Task 3 is sufficient. Already handled in Task 3 — verification only.

- [ ] **Step 5: Reduce topbar height on mobile to 44px (matches min touch target)**

In the mobile breakpoint block, add:

```css
  .topbar { height: 44px; }
```

- [ ] **Step 6: Build final check**

```bash
npm run build
```

Resize DevTools between 375px and 1280px multiple times. Verify:
- No layout flashing or jumps on resize
- Desktop layout pixel-identical to before all changes (open a pre-changes screenshot or side-by-side if possible)
- All tap targets comfortably hittable with a finger

- [ ] **Step 7: Final commit**

```bash
git add src/assets/style.css
git commit -m "feat(mobile): polish — touch targets, hide card previews on smallest screens"
```

---

## Task 6: Add `.superpowers/` to .gitignore

The visual companion server writes mockup files to `.superpowers/brainstorm/` — these shouldn't be committed.

- [ ] **Step 1: Check if .gitignore exists and add entry**

```bash
grep -q ".superpowers" .gitignore 2>/dev/null || echo ".superpowers/" >> .gitignore
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore .superpowers/ brainstorm files"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Hamburger drawer, slides from left, backdrop | Task 3 CSS + Task 4 JS |
| 🔍 tucked icon, expands to full-width | Task 3 CSS + Task 4 JS |
| Back arrow in topbar, contextual | Task 1 HTML + Task 4 JS |
| Stacked single-pane navigation | Task 3 CSS |
| `list-active` / `detail-active` CSS classes | Task 3 CSS + Task 4 JS |
| Filter chips in list pane header on mobile | Task 1 HTML + Task 3 CSS |
| Chip sync across three chip sets | Task 4 JS `syncMobileChips()` |
| 44px tap targets | Task 3 CSS |
| Smooth transitions (pane-in keyframe, drawer slide) | Task 3 CSS |
| Category card grid 2-col on mobile | Task 3 CSS |
| Cat card feature preview hidden on smallest | Task 5 CSS |
| Zero desktop impact | All tasks — gated by media query or `isMobile()` |
| `.superpowers/` gitignored | Task 6 |

**No placeholders found.** All steps contain exact code.

**Type consistency check:** `isMobile()`, `openDrawer()`, `closeDrawer()`, `toggleSearch()`, `updateMobileTopbar()`, `mobilePaneBack()`, `syncMobileChips()` — all defined in Task 4 Step 1 and referenced consistently across subsequent steps. `activeFilters`, `activeCategory`, `activeAuthorFilter`, `activeEntryId` — all pre-existing state variables, used consistently.
