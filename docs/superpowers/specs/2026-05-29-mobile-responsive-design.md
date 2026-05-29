# Mobile-Responsive & Delightful UI — Design Spec

**Date:** 2026-05-29
**Branch:** feat/mobile
**Original prompt:** "Make the website for this project more mobile friendly and delightful"

---

## Overview

The tt-awesome site is a curated directory of Tenstorrent ecosystem projects. Currently it renders as a fixed three-pane desktop layout (sidebar + list + detail) with `overflow: hidden` on `html, body` — completely unusable on mobile. This spec describes making it fully mobile-responsive using a CSS-breakpoint approach, with smooth transitions as the "delight" layer.

---

## Decisions Made

| Question | Decision |
|---|---|
| Mobile navigation pattern | Hamburger (☰) drawer + stack navigation |
| Search on mobile | 🔍 icon in topbar, expands to full-width input |
| Delight level | Functional polish (smooth transitions, 44px tap targets) — no gimmicks |
| Implementation approach | CSS `@media (max-width: 767px)` block + minimal JS additions to `main.js` |

---

## Architecture

No new files. All changes go to:
- `src/assets/style.css` — mobile breakpoint block + new mobile-only classes
- `src/assets/main.js` — drawer open/close, back-button logic, search expand/collapse
- `src/_includes/base.njk` or `src/index.njk` — add hamburger and back-arrow elements to the topbar HTML

---

## Mobile Breakpoint: ≤767px

### Layout rewire

The three-pane flex row becomes a full-viewport stack. Only one "pane" is visible at a time, determined by CSS classes on `#panes`.

```
Desktop: [sidebar | list-pane | detail-pane]  (all visible simultaneously)
Mobile:  One pane fills 100vw/100vh at a time, stacked via show/hide classes
```

Classes that drive mobile visibility:
- `.panes.home-active` → show `.home-view` only
- `.panes.list-active` → show `.list-pane` only  
- `.panes.detail-active` → show `.detail-pane` only
- `.panes.releases-active` → show `.releases-pane` only

The existing JS already sets `home-active` and `releases-active`; we add `list-active` and `detail-active` for mobile pane tracking.

### Topbar

On mobile the topbar shows:
- **Default (home):** `⚡ tt-awesome` logo | spacer | 🔍 icon | ☰ icon
- **List/detail view:** `← Back` button | category name | spacer | 🔍 icon | ☰ icon

The back arrow and title are new elements added to the topbar HTML, hidden on desktop via CSS, shown/updated by JS on mobile.

Filter chips move from the topbar into the list pane header on mobile (they're only relevant when viewing a list). The chips stay in the same DOM position inside `.topbar`; on mobile, CSS hides them from the topbar and a duplicate set is rendered inside `.list-head` using `display: none` toggling — or alternatively the existing chips are repositioned via absolute/flex ordering. To avoid duplicating the JS toggle logic, the simplest approach is to render a second `.chips` container inside `.list-head` in the HTML and hide one set per breakpoint.

### Drawer

- Full-height left overlay (`position: fixed`, `z-index: 200`, `width: 280px`)
- Dark backdrop (`position: fixed`, full viewport, `rgba(0,0,0,0.55)`, `z-index: 199`)
- Slides in with `transform: translateX(-100%)` → `translateX(0)`, `transition: transform 200ms ease-out`
- Closes on: backdrop tap, category select, home select, releases select
- Contains the full sidebar nav (categories + community links)

### Search expand

- 🔍 icon always visible in topbar right
- Tap expands topbar into a full-width search input row (slides down, `max-height` transition)
- Filter chips appear below the search input when expanded
- ✕ button collapses search; clearing the input also collapses after 300ms
- On expand, `input.focus()` is called automatically

### Transitions (the "delight" layer)

| Interaction | Animation |
|---|---|
| Drawer open/close | `translateX` 200ms `ease-out` |
| Pane navigation (list/detail push) | `translateX(100%)` → `0` on push, reverse on back, 220ms `ease-out` |
| Search bar expand | `max-height` 0 → 52px, 180ms `ease-out` |
| Entry row tap | `background` transition already in CSS (keep as-is) |
| Cat card hover | Existing `translateY(-2px)` (keep, skip on touch) |

Touch targets: all tappable elements on mobile get `min-height: 44px` and `min-width: 44px`.

### Category card grid

On mobile, `cat-grid` goes from `repeat(auto-fill, minmax(260px, 1fr))` to `1fr 1fr` (two columns). Below 400px it goes to a single column.

### Detail pane

Full-width, scrollable. The `detail-pane` gets `overflow-y: auto` and normal document flow (no fixed height). `padding: 16px` on mobile.

---

## JS Changes (`main.js`)

### New state variable
```js
let isMobileDetailVisible = false; // tracks whether detail pane is stacked on top
```

### New functions
- `openDrawer()` / `closeDrawer()` — add/remove `.drawer-open` class on `#sidebar`, toggle backdrop
- `toggleSearch()` — add/remove `.search-expanded` on `.topbar`
- `updateMobileTopbar(title)` — show/hide back arrow, set category title text
- Mobile media query listener (`matchMedia('(max-width: 767px)')`) to reset state when resizing back to desktop

### Hooks into existing functions
- `_applyCategory()` → on mobile, also add `.list-active` to `#panes`, call `updateMobileTopbar()`
- `_applyEntry()` → on mobile, also add `.detail-active` to `#panes`
- `_applyHome()` → on mobile, remove `.list-active`, `.detail-active`
- Back arrow click → if `.detail-active`, go back to list; if `.list-active`, go back to home

---

## What Does NOT Change

- Desktop layout — zero impact, the breakpoint block is mobile-only
- URL routing / history — works identically on mobile
- All existing JS state (activeCategory, activeEntryId, etc.)
- The Eleventy build pipeline

---

## Out of Scope

- Pull-to-refresh
- Swipe gestures
- PWA / offline support
- Dark/light mode toggle
