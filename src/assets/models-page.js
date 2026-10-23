// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

/* Models pages: Copy buttons, the list filter and the phone menu. Pages are plain HTML and work without this.
 * Nothing here builds HTML. Text is read with textContent and set with textContent. */
(function () {
  "use strict";

  // Copy buttons: <button data-copy="text">
  function copyText(text, btn) {
    const done = () => { const old = btn.textContent; btn.textContent = "Copied"; setTimeout(() => { btn.textContent = old; }, 1400); };
    const fallback = () => {
      const ta = document.createElement("textarea"); ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.append(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { btn.textContent = "Select and copy"; }
      ta.remove();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-copy]");
    if (b) copyText(b.getAttribute("data-copy"), b);
  });

  // List filter on collection pages: hides cards whose data-search text lacks every typed word.
  const input = document.getElementById("m-filter");
  if (input) {
    const cards = Array.from(document.querySelectorAll("#m-grid .m-card"));
    const count = document.getElementById("m-count");
    const none = document.getElementById("m-none");
    input.addEventListener("input", () => {
      const words = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      let shown = 0;
      cards.forEach((c) => {
        const hay = c.getAttribute("data-search") || "";
        const ok = words.every((w) => hay.includes(w));
        c.hidden = !ok;
        if (ok) shown += 1;
      });
      count.textContent = shown + (shown === 1 ? " model" : " models");
      none.hidden = shown !== 0;
    });
  }

  // Phone menu: the sidebar is a drawer (style.css shows it when body has drawer-open).
  const burger = document.getElementById("hamburger");
  const backdrop = document.getElementById("drawer-backdrop");
  if (burger) burger.addEventListener("click", () => document.body.classList.add("drawer-open"));
  if (backdrop) backdrop.addEventListener("click", () => document.body.classList.remove("drawer-open"));
})();
