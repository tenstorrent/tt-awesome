# Awesome Tenstorrent — Design Spec
**Date:** 2026-05-08  
**Author:** Taylor Singletary  
**Status:** Approved

---

## Overview

A curated, community-first awesome list for the Tenstorrent ecosystem that functions simultaneously as:

1. **A JSON database** — `entries/*.json` is the single source of truth
2. **A skimmable README** — generated from JSON, lives at the repo root
3. **A full-featured website** — built with Eleventy, three-pane layout, deployed to GitHub Pages

The pipeline is one-directional: edit JSON → generate everything else. No bidirectional sync needed.

---

## Goals

- Feature community and affiliated projects *above* official Tenstorrent repos wherever possible
- Make it trivially easy to add an entry (one JSON file, or a CLI helper)
- Keep star counts and metadata fresh without noisy commits to entry files
- Support entries with multiple link types (repo, article, talk, video, paper, demo, lesson)
- Categorize by use case, not by tool

---

## Repository Structure

```
tt-awesome/
├── entries/                        ← source of truth, one .json per entry
│   ├── tt-boltz.json
│   ├── tt-metal.json
│   └── ...
├── scripts/
│   ├── generate_readme.py          ← entries/*.json → README.md
│   ├── validate.py                 ← JSON schema validation (run in CI)
│   ├── add_entry.py                ← interactive CLI: prompts and writes new .json
│   └── fetch_github_meta.py        ← nightly: fetch stars/updated → _data cache
├── src/                            ← Eleventy source
│   ├── _data/
│   │   ├── entries.js              ← loads all entries/*.json, sorts, merges github_meta
│   │   ├── categories.js           ← category slug→label map
│   │   └── github_meta.json        ← auto-generated, do not edit
│   ├── _includes/
│   │   ├── base.njk                ← HTML shell, CSS/JS links
│   │   ├── sidebar.njk             ← category nav
│   │   ├── entry-list.njk          ← middle pane, compact rows
│   │   └── entry-detail.njk        ← right pane template (rendered server-side, toggled client-side)
│   ├── index.njk                   ← three-pane shell page
│   └── assets/
│       ├── main.js                 ← pane switching, search, affiliation filter
│       └── style.css               ← Tenstorrent dark theme (#0F2A35 / #4FD1C5)
├── README.md                       ← GENERATED — do not edit by hand
├── .eleventy.js
├── package.json
├── CONTRIBUTING.md
└── .github/
    └── workflows/
        ├── validate.yml            ← runs validate.py on every PR
        ├── deploy.yml              ← build + push _site/ to gh-pages on merge to main
        └── nightly.yml             ← fetch_github_meta.py, commit if changed
```

`README.md` and `src/_data/github_meta.json` are the only committed generated files. Everything else in `_site/` is built at deploy time and never committed.

---

## JSON Entry Schema

Every file in `entries/` must be valid against this schema:

```json
{
  "id": "tt-boltz",
  "name": "tt-boltz",
  "description": "Boltz-2 biomolecular model for drug discovery on Tenstorrent Blackhole. Supports single-card and multi-card configurations (QuietBox 4×, Galaxy 32×).",
  "affiliation": "community",
  "categories": ["ai-models", "research"],
  "tags": ["drug-discovery", "blackhole", "inference", "biology", "multi-card"],
  "links": [
    { "type": "repo",  "url": "https://github.com/moritztng/tt-boltz" },
    { "type": "talk",  "url": "https://fosdem.org/2026/schedule/event/AJLNVH-tt-boltz/", "label": "FOSDEM 2026 — Drug Discovery on Tenstorrent Hardware" }
  ],
  "hardware": ["blackhole", "quietbox", "galaxy"],
  "featured": true,
  "author": "moritztng",
  "language": "Python",
  "license": "MIT"
}
```

### Field Reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Kebab-case, unique, matches filename |
| `name` | string | yes | Display name |
| `description` | string | yes | 1–3 sentences, plain text |
| `affiliation` | enum | yes | `official` · `affiliated` · `community` |
| `categories` | string[] | yes | At least one; see category slugs below |
| `tags` | string[] | no | Freeform, lowercase, hyphenated |
| `links` | object[] | yes | At least one; first `repo` link is the canonical URL |
| `links[].type` | enum | yes | `repo` · `article` · `talk` · `video` · `website` · `demo` · `lesson` · `paper` |
| `links[].url` | string | yes | Must be a valid HTTPS URL |
| `links[].label` | string | no | Human label; defaults to type if omitted |
| `hardware` | string[] | no | `grayskull` · `wormhole` · `blackhole` · `quietbox` · `galaxy` · `ttsim` |
| `featured` | boolean | no | Elevates entry visually in list; use sparingly |
| `author` | string | no | GitHub username or "Firstname Lastname" |
| `language` | string | no | Primary language |
| `license` | string | no | SPDX identifier |

### Affiliation Definitions

> **Superseded 2026-08-11.** `official` now covers a repo in *any*
> Tenstorrent-owned GitHub org, not just `tenstorrent`. See the affiliation
> policy in `CONTRIBUTING.md` for the current rule and the list of orgs;
> `scripts/validate.py` enforces it. The definitions below are the original
> 2026-05-08 text, kept as the design record.

- **`official`** — lives in the `tenstorrent` GitHub org
- **`affiliated`** — authored by a Tenstorrent employee or close contributor working in a personal capacity (e.g. `tsingletaryTT`, `zoecarver`, `moritztng`)
- **`community`** — everyone else; shown first in every category

### Not in the entry JSON

`stars` and `updatedAt` are intentionally absent. A nightly GitHub Action (`fetch_github_meta.py`) pulls these from the GitHub API and writes `src/_data/github_meta.json`. Eleventy merges them at build time by matching on the first `repo`-type link. Entries with no `repo`-type link (e.g. research papers) simply have no GitHub metadata and display without star counts. This keeps entry files clean and PR diffs meaningful.

---

## Categories

| Slug | Label | Description |
|---|---|---|
| `ai-models` | 🤖 AI & Models | Running, serving, and experimenting with AI models |
| `agents` | 🕵️ AI Agents | Agentic systems and AI assistants running on TT hardware |
| `kernels` | ⚙️ Custom Kernels & Low-Level | Metalium/tt-lang kernel authoring; anything sub-compiler |
| `compilers` | 🔨 Compilers & Frontends | Getting PyTorch/JAX/ONNX/CUDA models onto TT hardware |
| `dev-tools` | 🛠 Dev Tools & Debugging | Profiling, visualization, and debugging workloads |
| `hw-system` | 🖥 Hardware & System | Drivers, firmware, monitoring, and hardware management |
| `cloud-infra` | ☁️ Cloud & Orchestration | Kubernetes, cloud deployment, and multi-node infrastructure |
| `riscv-arch` | 🔩 RISC-V & Architecture | ISA, simulation, and running Linux on TT silicon |
| `research` | 🔬 Research & Papers | Academic papers, theses, and HPC experiments |
| `games-demos` | 🎮 Games & Demos | Creative, playful, and proof-of-concept projects |
| `guides` | 📚 Guides, Tutorials & Education | Getting-started content, blog posts, lessons, courses |

Entries may belong to multiple categories. The `tt-vscode-toolkit` lesson library maps to `guides` entries with link type `lesson`.

---

## Website Layout

Three-pane layout, Tenstorrent dark theme throughout (`#0F2A35` background, `#4FD1C5` teal accent).

```
┌─ top bar ──────────────────────────────────────────────────────────┐
║ ⚡ Awesome Tenstorrent        [search…]  All  community  affiliated ║
╠══════════╦═══════════════════════╦═══════════════════════════════════╣
║          ║ 🤖 AI & Models        ║                                   ║
║ Sidebar  ║ 17 entries            ║   Detail pane                     ║
║          ║ ─────────────────     ║   (loads on click)                ║
║ Category ║ ● tt-boltz community  ║                                   ║
║ nav      ║   tt-lang-models aff. ║                                   ║
║          ║   tt-inference-… off. ║                                   ║
║          ║   …                   ║                                   ║
╚══════════╩═══════════════════════╩═══════════════════════════════════╝
```

**Sidebar (pane 1):** Category nav, always visible. Active category highlighted. "Submit entry" link at bottom.

**List (pane 2):** Compact rows, wider than sidebar. Sorted community → affiliated → official, then stars descending within each tier. Each row shows: name, affiliation badge, star count, one-line description. Clicking a row loads the detail pane; does not navigate away.

**Detail (pane 3):** Full entry view. Name, affiliation badge, author, language, license, star count, last updated. Full description. All links rendered by type (repo gets a GitHub icon, talk gets a microphone, paper gets 📄, etc.). Tags. Hardware compatibility badges. Rendered server-side by Eleventy as hidden `<div>` elements; `main.js` shows/hides on click — no page navigation, no fetch needed.

**Search:** Client-side, filters middle pane in real time. Matches on name, description, tags, author.

**Affiliation filter:** Chip toggles in the top bar. Multi-select — community+affiliated is the default active state (official repos are secondary).

---

## Build Pipeline

```
entries/*.json
    ├── eleventy build  →  _site/          (GitHub Pages)
    └── generate_readme.py  →  README.md   (committed to main)

Nightly:
    fetch_github_meta.py  →  src/_data/github_meta.json  (committed)
```

### `generate_readme.py`

Reads all entries, groups by first listed category, sorts community-first within each group, emits a standard awesome-list markdown structure with inline badges and all typed links listed per entry. Output is committed to `README.md`. The script is idempotent — running it twice produces the same file.

### `validate.py`

Checks every entry in `entries/`:
- Required fields present and correct types
- `affiliation` is one of the three valid values
- All `categories` are valid slugs from the category list
- `id` matches filename (minus `.json`)
- All URLs are valid HTTPS URLs (format check only, no HTTP request)
- No duplicate `id` values across the directory

Exits non-zero on any failure. Run in CI on every PR before merge.

### `add_entry.py`

Interactive CLI. Prompts for each required field, offers multi-select for categories and hardware, lets you add multiple links, validates inline, and writes the final `.json` to `entries/`. Prints the git command to open a PR.

### GitHub Actions

**`validate.yml`** — triggers on PR: runs `validate.py`. Blocks merge on failure.

**`deploy.yml`** — triggers on push to `main`: runs `generate_readme.py`, commits README if changed, runs `eleventy build`, pushes `_site/` to `gh-pages` branch.

**`nightly.yml`** — runs at 02:00 UTC daily: runs `fetch_github_meta.py`, commits `github_meta.json` if changed.

---

## Sorting & Featured Logic

Within each category, the middle pane sorts entries:

1. Community entries: `featured: true` first, then by stars descending
2. Affiliated entries: `featured: true` first, then by stars descending
3. Official entries: `featured: true` first, then by stars descending

Affiliation tier always takes precedence over featured status — a featured official repo never outranks a non-featured community entry. `featured` is an ordering hint within a tier, not a way to bypass the community-first philosophy.

The README follows the same order. `featured` should be used for genuinely exceptional entries — typically community projects that represent the best of what the ecosystem has produced.

---

## Initial Entries (first pass)

Enough content exists to populate the list on day one. Key entries identified during research:

**Community highlights (featured candidates):**
- `moritztng/tt-boltz` — Boltz-2 drug discovery (87⭐, FOSDEM 2026 talk)
- `geohot/tt-tiny` — George Hotz pokes at Blackhole (64⭐)
- `moritztng/grayskull-attention` — FlashAttention in SRAM (38⭐)
- `geohot/tt-twitch` — live Twitch kernel (28⭐)
- `dstackai/dstack` — orchestration with TT support (2130⭐)
- `Zaneham/BarraCUDA` — CUDA → TT compiler (1672⭐)

**Affiliated (tsingletaryTT / zoecarver):**
- `tt-zork-and-more`, `tensix-viz`, `tt-forge-compiletron`, `tt-model-runner`, `tt-qb-lights`, `tt-jukebox`, `tt-warp`
- `tt-lang-models`, `open-oasis`, `dflash`, `diamond`, `gemma4`, `Engram`, `qwen-image-tt-xla`

**Research & Papers:**
- FFT on Wormhole (arXiv:2506.15437) — Brown, Davies, LeClair (Edinburgh/EPCC)
- N-Body Simulations on Wormhole (arXiv:2509.19294)
- Numerical Kernels on Wormhole (arXiv:2603.23343)
- Stencils on Grayskull (arXiv:2409.18835)
- SwiftNPU — multi-tenant NPU allocation for Blackhole (ACM)
- Sapienza University Rome — allreduce on Wormhole n150 (thesis)

**Guides & Tutorials:**
- Martin Chang (clehaxze.tw) — three blog posts, 2024–2025
- `changh95/tt-tutorial` — Korean TT tutorials
- `marty1885/ttnn-helloworld-cpp` — minimal C++ TTNN example
- tt-vscode-toolkit lesson library (48 lessons, `lesson` link type)

**Official TT repos (secondary):**
- All major repos from the `tenstorrent` org, categorized by use case

---

## CONTRIBUTING.md Summary

The contributing guide will explain:
1. Edit or create a file in `entries/` following the schema
2. Run `python scripts/validate.py` locally
3. Optionally run `python scripts/generate_readme.py` to preview README changes
4. Open a PR — CI will validate automatically

Alternatively, run `python scripts/add_entry.py` for an interactive prompt.

The guide will also describe the affiliation policy (who qualifies as `affiliated` vs `community`).

---

## Open Questions (resolved)

- **Source of truth:** JSON ✓
- **Website generator:** Eleventy ✓  
- **Layout:** Three-pane, wider middle column ✓
- **Affiliation tiers:** 3 tiers (official / affiliated / community) ✓
- **Categories:** 11 use-case categories ✓
- **Multiple links per entry:** Supported via typed `links` array ✓
- **tt-vscode-toolkit lessons:** Entries with `lesson` link type in `guides` category ✓
- **Star count freshness:** Nightly GitHub Action, not in entry JSON ✓
