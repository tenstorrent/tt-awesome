// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

/* ── Models section ─────────────────────────────────────────────────────────
 * Loaded before main.js. Exposes the four entry points main.js calls:
 *   showModels(viewKey?, modelId?)  public: navigate and push a history entry
 *   _applyModels(viewKey, modelId)  internal: navigate without touching history (URL restore)
 *   leaveModels()                   called by every other pane switch
 *   modelsBack()                    the mobile top bar's back arrow while Models is open
 * URL: ?models=index (the Models index), ?models=<view key> (a list), plus &model=<id>.
 *
 * Data is src/_data/models.json (scripts/build_models_data.py), embedded as JSON. Status, context and
 * users are copied from tt-inference-server's release spec; nothing is measured. All data-derived text
 * reaches the DOM through textContent.
 */
(function () {
  "use strict";
  const DATA = JSON.parse(document.getElementById("models-data").textContent);
  const MODELS = DATA.models;
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const byId = Object.fromEntries(MODELS.map((m) => [m.id, m]));

  /* A view is {key, group, label, blurb, test(model)}. The groups are computed from the data. */
  const uniq = (f) => [...new Set(MODELS.flatMap(f))].sort();
  const SRC = "Source of every status and limit: the tt-inference-server release spec (" + DATA.spec.commit + "). Bundles come from tt-model's catalog.";
  const views = [{ key: "all", group: "", label: "All models", test: () => true,
    blurb: "Models listed in tt-inference-server or published as a tt-model bundle. Models in tt-inference-server come first." }];
  [["c:single", "Runs on a single card", "Models with a supported single-chip device in tt-inference-server.", (m) => m.singleCard],
   ["c:multi", "Needs a multi-chip system", "Models whose supported devices all have more than one chip.", (m) => m.inSpec && m.multiOnly],
   ["c:bundle", "Has a tt-model bundle", "Models that also have a published tt-model bundle.", (m) => m.bundles.length > 0],
   ["c:fresh", "Bundles from the last 14 days", "Models with a tt-model bundle pushed in the last 14 days.",
     (m) => m.newest >= FRESH_CUTOFF()]
  ].forEach(([key, label, blurb, test]) => views.push({ key, group: "Collections", label, blurb, test }));
  function FRESH_CUTOFF() {
    const base = new Date();
    base.setDate(base.getDate() - 14);
    return base.toISOString().slice(0, 10);
  }
  uniq((m) => [m.kind]).forEach((kd) => views.push({ key: "k:" + kd, group: "By kind of model", label: kd,
    blurb: kd === "Unclassified" ? "The name did not say what these are." : "", test: (m) => m.kind === kd }));
  uniq((m) => m.devices).forEach((h) => views.push({ key: "h:" + h, group: "By hardware", label: h, blurb: "", test: (m) => m.devices.includes(h) }));
  ["Complete", "Functional", "Experimental"].forEach((st) => views.push({ key: "t:" + st, group: "By status", label: st,
    blurb: "Best status the model has in tt-inference-server.", test: (m) => m.status === st }));
  views.push({ key: "t:none", group: "By status", label: "Not in tt-inference-server", blurb: "Published as tt-model bundles only.", test: (m) => !m.inSpec });
  const GROUPS = ["Collections", "By kind of model", "By hardware", "By status"];
  const viewByKey = Object.fromEntries(views.map((v) => [v.key, v]));
  const inView = (v) => MODELS.filter(v.test);

  let current = null;            // null is the Models index, otherwise a view
  let query = "";
  let selectedId = MODELS.length ? MODELS[0].id : null;
  const scrollAt = {};          // browse-area scroll per view key, restored when Back returns to a view
  let viaPop = false;           // true while a Back or Forward is being applied
  window.addEventListener("popstate", () => { viaPop = true; setTimeout(() => { viaPop = false; }, 0); });
  const openGroups = new Set(["Collections", "By kind of model"]);   // sidebar groups the visitor has open

  function matches(m) {
    if (!query) return true;
    const hay = [m.name, m.upstream || "", m.kind, m.devices.join(" "), m.bundles.map((b) => b.repo).join(" ")].join(" ").toLowerCase();
    return query.split(/\s+/).every((w) => hay.includes(w));
  }

  /* tt launch's rule (tt-cli launchers/base.py, commands/launch.py): a client needs chat completions, which tt
     serves through vLLM, and the terminal clients also need a published tool-call parser. A model outside the
     catalog is not checked: tt warns and carries on. */
  const CLIENTS = [["opencode", "Terminal", true], ["pi", "Terminal", true], ["aider", "Terminal", true],
    ["qwencode", "Terminal", true], ["openwebui", "Web service", false], ["anythingllm", "Web service", false]];
  function clientFit(m, needsTools) {
    if (m.inSpec) {
      if (!m.chat) return ["no", "Not a chat model"];
      if (needsTools && !m.parser) return ["no", "No tool-call parser published"];
      return ["yes", needsTools ? "Tool calling: " + m.parser : "Any chat model"];
    }
    if (m.kind !== "Language model") return ["no", "Not a chat model"];
    return ["maybe", needsTools ? "tt cannot confirm tool calling" : "Not checked by tt"];
  }
  const cmdFor = (m, id) => "tt launch " + id + " --model " + m.serve;

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
  function cmdBlock(label, text) {
    const w = el("div", "m-cmd"); w.append(el("div", "lbl", label), el("code", null, text));
    const b = el("button", "m-copy", "Copy"); b.type = "button"; b.setAttribute("aria-label", "Copy: " + text);
    b.addEventListener("click", () => copyText(text, b)); w.append(b); return w;
  }

  /* ── Navigation ── */
  function modelsParams(view, id) {
    const p = { models: view ? view.key : "index" };
    if (view && id) p.model = id;
    return p;
  }
  function enter() {
    const panes = $("panes");
    panes.classList.remove("home-active", "releases-active", "list-active", "detail-active");
    panes.classList.add("models-active");
    delete panes.dataset.detailFrom;
    document.querySelectorAll(".sidebar-item").forEach((i) => i.classList.remove("active"));
    $("models-item").classList.add("active");
    $("models-sub").hidden = false;
    if (isMobile()) { updateMobileTopbar("Models", true); closeDrawer(); }
  }
  function _applyModels(key, modelId) {
    activeCategory = null; activeEntryId = null; activeAuthorFilter = null;
    const prev = current, prevId = selectedId;
    scrollAt[prev ? prev.key : "index"] = $("models-main").scrollTop;
    current = viewByKey[key] || null;       // "index" and unknown keys both land on the index
    if (modelId && byId[modelId]) selectedId = modelId;
    if (current) openGroups.add(current.group);
    enter();
    $("models-view").classList.toggle("detail-open", !!(current && modelId && byId[modelId]));
    render();
    // Keep the reader's place: only a change of view returns the browse area to the top, and picking a
    // model in the same list leaves the list where it is. A different model starts its panel at the top.
    if (current !== prev) {
      window.scrollTo(0, 0);
      $("models-main").scrollTop = viaPop ? (scrollAt[current ? current.key : "index"] || 0) : 0;
    }
    if (selectedId !== prevId || current !== prev) $("models-panel").scrollTop = 0;
  }
  function showModels(key, modelId) {
    const view = key ? viewByKey[key] : null;
    const params = modelsParams(view, modelId), url = "?" + new URLSearchParams(params).toString();
    // Picking a model inside the list you are already in replaces the history entry on a wide screen, so Back
    // leaves the list instead of stepping through every card. A repeat of the current URL adds nothing.
    const sameList = $("panes").classList.contains("models-active") && current && view === current && !isMobile();
    if (location.search === url) { /* already here */ }
    else if (sameList) history.replaceState(params, "", url);
    else pushUrl(params);
    _applyModels(key || "index", modelId);
  }
  function leaveModels() {
    $("panes").classList.remove("models-active");
    $("models-sub").hidden = true;
    $("models-view").classList.remove("detail-open");
  }
  function modelsBack() {
    const v = $("models-view");
    if (v.classList.contains("detail-open")) { showModels(current && current.key); return; }
    if (current) { showModels(); return; }
    showHome();
  }
  window.showModels = showModels; window._applyModels = _applyModels; window.leaveModels = leaveModels; window.modelsBack = modelsBack;

  /* ── Sidebar subtree ── */
  function buildNav() {
    const nav = $("models-nav"), side = $("sidebar"), keep = side.scrollTop;
    nav.replaceChildren();
    const group = (label, items) => {
      const wrap = label ? el("details") : el("div");
      if (label) {
        wrap.open = openGroups.has(label);
        wrap.addEventListener("toggle", () => { if (wrap.open) openGroups.add(label); else openGroups.delete(label); });
        wrap.appendChild(el("summary", null, label));
      }
      const ul = el("ul");
      items.forEach((v) => {
        const li = el("li"), b = el("button", "models-nav-btn"); b.type = "button";
        b.setAttribute("aria-current", String(!!current && current.key === v.key));
        b.append(el("span", null, v.label), el("span", "n", String(inView(v).filter(matches).length)));
        b.addEventListener("click", () => showModels(v.key));
        li.appendChild(b); ul.appendChild(li);
      });
      wrap.appendChild(ul); nav.appendChild(wrap);
    };
    group("", [views[0]]);
    GROUPS.forEach((g) => group(g, views.filter((v) => v.group === g)));
    side.scrollTop = keep;
  }

  /* ── Browse area ── */
  function card(m) {
    const b = el("button", "m-card"); b.type = "button";
    const kind = el("div", "kind"); kind.append(el("span", null, m.kind), el("span", "m-pill" + (m.inSpec ? " tt" : ""), m.source));
    const top = el("div"); top.append(el("h3", null, m.name), el("div", "upstream", m.upstream || m.bundles[0].repo));
    const facts = el("dl", "m-facts");
    const row = (k, v, cls) => { facts.append(el("dt", null, k), el("dd", cls, v)); };
    const shown = m.devices.slice(0, 3).join(", ") + (m.devices.length > 3 ? " +" + (m.devices.length - 3) : "");
    row("Runs on", m.devices.length ? shown : "Not stated", m.devices.length ? "" : "none");
    row("Status", m.status || "Not in the release spec", m.status ? "" : "none");
    const ok = CLIENTS.filter((c) => clientFit(m, c[2])[0] === "yes").length;
    const maybe = CLIENTS.filter((c) => clientFit(m, c[2])[0] === "maybe").length;
    row("tt launch", ok ? ok + " of " + CLIENTS.length + " clients" : maybe ? "Not confirmed" : "None", ok ? "" : "none");
    row("tt-studio", m.studio || "Not confirmed", m.studio ? "" : "none");
    const foot = el("div", "m-foot");
    if (m.params) foot.append(el("span", null, m.params + " parameters"));
    const engines = [...new Set(m.rows.map((r) => r.engine))];
    if (engines.length) foot.append(el("span", null, engines.join(", ")));
    if (m.newest) foot.append(el("span", null, "newest bundle " + m.newest));
    b.setAttribute("aria-pressed", String(m.id === selectedId));
    b.append(kind, top, el("p", "sum", m.summary), facts, foot);
    b.addEventListener("click", () => showModels(current.key, m.id));
    return b;
  }

  function crumbs(parts) {
    const c = $("models-crumb"); c.replaceChildren();
    parts.forEach((p, i) => {
      if (i) c.append(el("span", null, "/"));
      if (p.go) { const b = el("button", null, p.label); b.type = "button"; b.addEventListener("click", p.go); c.append(b); }
      else { const s = el("span", null, p.label); s.setAttribute("aria-current", "page"); c.append(s); }
    });
  }
  const tile = (label, n, blurb, onClick, cls) => {
    const b = el("button", "m-tile" + (cls ? " " + cls : "")); b.type = "button";
    const t = el("span", "t"); t.append(el("span", null, label), el("span", "n", n)); b.append(t, el("span", "d", blurb));
    b.addEventListener("click", onClick); return b;
  };

  function render() {
    buildNav();
    const index = !current;
    $("models-tiles").hidden = !index; $("models-list").hidden = index;
    if (index) {
      crumbs([{ label: "tt-awesome", go: () => showHome() }, { label: "Models" }]);
      $("models-title").textContent = "Models";
      $("models-blurb").textContent = "Pick a collection or a way to slice the list. Models in tt-inference-server come first inside every list.";
      const t = $("models-tiles"); t.replaceChildren();
      const g0 = el("div", "m-tilegroup"), r0 = el("div", "m-tilerow");
      r0.append(tile(views[0].label, String(MODELS.length), views[0].blurb, () => showModels(views[0].key), "hero")); g0.append(r0); t.append(g0);
      GROUPS.forEach((gn) => {
        const g = el("div", "m-tilegroup"), r = el("div", "m-tilerow"); g.append(el("h3", null, gn), r);
        views.filter((v) => v.group === gn).forEach((v) => r.append(tile(v.label, String(inView(v).length), v.blurb || " ", () => showModels(v.key))));
        t.append(g);
      });
      quickStart();
      return;
    }
    crumbs([{ label: "tt-awesome", go: () => showHome() }, { label: "Models", go: () => showModels() }, { label: current.label }]);
    $("models-title").textContent = current.label;
    $("models-blurb").textContent = current.blurb;
    const list = inView(current).filter(matches);
    const s = $("models-sort").value;
    if (s === "name") list.sort((a, b) => a.name.localeCompare(b.name));
    else if (s === "newest") list.sort((a, b) => b.newest.localeCompare(a.newest) || a.name.localeCompare(b.name));
    else list.sort((a, b) => (a.inSpec === b.inSpec ? 0 : a.inSpec ? -1 : 1) || a.name.localeCompare(b.name));
    $("models-count").textContent = list.length + (list.length === 1 ? " model" : " models");
    if (list.length && !list.some((m) => m.id === selectedId)) selectedId = list[0].id;
    const g = $("models-grid"); g.replaceChildren(...list.map(card));
    if (!list.length) g.append(el("p", "none", "No models match this search in this view."));
    renderPanel(list.length ? byId[selectedId] : null);
  }

  /* ── Details panel ── */
  function quickStart() {
    const d = $("models-panel"); d.replaceChildren();
    d.append(el("div", "kind", "Quick start"), el("h2", null, "Run any model with tt"));
    d.append(el("p", null, "Open a collection and pick a model. Its page has the exact commands. The three steps are the same for every model."));
    d.append(el("h4", null, "1. Download"), cmdBlock("Weights, and the bundle if there is one", "tt model pull <model>"));
    d.append(el("h4", null, "2. Serve"), cmdBlock("Starts an OpenAI-compatible server on this machine", "tt serve <model>"));
    d.append(el("h4", null, "3. Connect a client"), cmdBlock("opencode, pi, aider, qwencode, Open WebUI or AnythingLLM", "tt launch <client> --model <model>"));
    d.append(el("p", "note", "tt-studio gives chat, image, video, speech and embedding models a web page of their own."));
    d.append(el("h4", null, "Find a model from the terminal"), cmdBlock("Lists published tt-model bundles", "tt model search"));
  }

  function renderPanel(m) {
    const d = $("models-panel"); d.replaceChildren();
    if (!m) { d.append(el("p", "none", "Select a model to see its details.")); return; }
    const back = el("button", "back", "Back to list"); back.type = "button";
    back.addEventListener("click", () => showModels(current.key));
    d.append(back, el("div", "kind", m.kind), el("h2", null, m.name));
    if (m.upstream) {
      const w = el("div", "upstream"); const a = el("a", null, m.upstream);
      a.href = "https://huggingface.co/" + m.upstream; a.target = "_blank"; a.rel = "noopener noreferrer"; w.append(a); d.append(w);
    }
    d.append(el("p", null, m.summary));

    d.append(el("h4", null, "Install and run"));
    d.append(cmdBlock("Download the weights" + (m.inSpec ? "" : " and the bundle"), "tt model pull " + m.serve));
    d.append(cmdBlock("Serve it on this machine", "tt serve " + m.serve));
    if (!m.inSpec) d.append(el("p", "note", "A tt-model bundle, so tt serve runs it through tt-model. If a bundle needs a board you do not have, tt says so."));

    /* Only the clients that work are listed. */
    d.append(el("h4", null, "Works with tt launch"));
    const fits = CLIENTS.map((c) => [c, clientFit(m, c[2])]).filter((x) => x[1][0] !== "no");
    if (!fits.length) {
      d.append(el("p", "none", m.inSpec && !m.chat ? "None. tt launch connects chat models, and this is not one." : "None."));
    } else {
      const lw = el("div", "m-scroll"), lt = el("table");
      const lh = el("tr"); ["Client", "Type", "Notes", ""].forEach((h) => lh.append(el("th", null, h))); lt.append(lh);
      fits.forEach(([[id, type], [fit, why]]) => {
        const tr = el("tr"), f = el("td");
        if (fit === "maybe") f.append(el("span", "m-fit", "Not confirmed"), document.createTextNode(" "));
        f.append(document.createTextNode(why));
        const c = el("td"), b = el("button", "m-copy sm", "Copy"); b.type = "button"; b.setAttribute("aria-label", "Copy: " + cmdFor(m, id));
        b.addEventListener("click", () => copyText(cmdFor(m, id), b)); c.append(b);
        tr.append(el("td", null, id), el("td", null, type), f, c); lt.append(tr);
      });
      lw.append(lt); d.append(lw, el("p", "note", "Serve the model first, then run the copied command."));
    }

    d.append(el("h4", null, "In tt-studio"));
    d.append(m.studio ? el("p", null, m.studio + ". tt-studio picks the page from the model type.")
      : el("p", "none", "Not confirmed. tt-studio picks a page from the model type, and a bundle outside tt-inference-server has no type here."));

    d.append(el("h4", null, "In tt-inference-server"));
    if (m.rows.length) {
      const wrap = el("div", "m-scroll"), t = el("table");
      const hr = el("tr"); ["Device", "Engine", "Status", "Context", "Users"].forEach((h) => hr.append(el("th", null, h))); t.append(hr);
      m.rows.forEach((r) => {
        const tr = el("tr");
        tr.append(el("td", null, r.device), el("td", null, r.engine), el("td", null, r.status),
          el("td", "num", r.context || "-"), el("td", "num", r.users == null ? "-" : String(r.users)));
        t.append(tr);
      });
      wrap.append(t); d.append(wrap, el("p", "note", SRC + " Context is the longest prompt plus reply the entry allows. Users is its highest concurrency."));
    } else d.append(el("p", "none", "Not in the release spec. tt-inference-server does not list this model."));

    d.append(el("h4", null, "In tt-model"));
    if (m.bundles.length) {
      const wrap = el("div", "m-scroll"), t = el("table");
      const hr = el("tr"); ["Bundle", "Boards", "Pushed", ""].forEach((h) => hr.append(el("th", null, h))); t.append(hr);
      m.bundles.slice().sort((a, b) => b.updated.localeCompare(a.updated)).forEach((b) => {
        const tr = el("tr"), c = el("td"), a = el("a", null, b.repo);
        a.href = "https://huggingface.co/" + b.repo; a.target = "_blank"; a.rel = "noopener noreferrer"; c.append(a);
        const cc = el("td"), cb = el("button", "m-copy sm", "Copy serve"); cb.type = "button"; cb.setAttribute("aria-label", "Copy: tt serve " + b.repo);
        cb.addEventListener("click", () => copyText("tt serve " + b.repo, cb)); cc.append(cb);
        tr.append(c, el("td", null, b.boards.join(", ") || "Not in the name"), el("td", "num", b.updated), cc); t.append(tr);
      });
      wrap.append(t); d.append(wrap);
    } else d.append(el("p", "none", "No tt-model bundle has been published."));

    d.append(el("h4", null, "Details"));
    const t2 = el("table");
    [["Kind", m.kind + (m.kindGuess ? " (guessed from the name)" : "")], ["Parameters", m.params], ["Listed by", m.source]]
      .filter((r) => r[1]).forEach((r) => { const tr = el("tr"); tr.append(el("td", null, r[0]), el("td", null, r[1])); t2.append(tr); });
    d.append(t2);
  }

  $("models-q").addEventListener("input", (e) => {
    query = e.target.value.trim().toLowerCase();
    if (!current) { showModels("all"); } else { render(); }
  });
  $("models-sort").addEventListener("change", render);
})();
