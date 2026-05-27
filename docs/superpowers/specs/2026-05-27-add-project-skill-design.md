# Design: tt-awesome plugin + /tt-awesome:add-project skill

**Date:** 2026-05-27  
**Status:** Approved

## Overview

Two changes to the tt-awesome repo:

1. **Sidebar**: Replace the Forum link with a TT Console link.
2. **Plugin**: Add a `tt-awesome` Claude Code plugin with an `add-project` skill that guides contributors through submitting a new entry — via GitHub issue, local JSON file, or PR.

---

## 1. Sidebar change

**File:** `src/_includes/sidebar.njk:25`

Replace:
```html
<a class="sidebar-item sidebar-ext" href="https://community.tenstorrent.com" target="_blank" rel="noopener noreferrer">🌐 Forum</a>
```

With:
```html
<a class="sidebar-item sidebar-ext" href="https://console.tenstorrent.com" target="_blank" rel="noopener noreferrer">🚀 TT Console</a>
```

No other sidebar changes.

---

## 2. Plugin structure

New files added to the repo root:

```
.claude-plugin/
  plugin.json
skills/
  add-project/
    SKILL.md
```

### `.claude-plugin/plugin.json`

```json
{
  "name": "tt-awesome",
  "description": "Claude Code plugin for the Awesome Tenstorrent list. Provides /tt-awesome:add-project to guide contributors through submitting new entries.",
  "author": {
    "name": "Tenstorrent"
  }
}
```

### `skills/add-project/SKILL.md`

Frontmatter:
```yaml
---
name: add-project
description: Guide the user through submitting a new entry to the Awesome Tenstorrent list. Use when the user wants to add, submit, or propose a project, library, tool, or resource to tt-awesome.
argument-hint: [project name or URL]
allowed-tools: [Bash, Read, Write]
---
```

---

## 3. Skill behavior

The skill runs in three sequential phases.

### Phase 1 — Gather

Ask one question at a time. Fields and order:

| Field | Required | Notes |
|---|---|---|
| Project name | yes | Pre-fill from `$ARGUMENTS` if provided |
| Repo URL | yes | Must be HTTPS GitHub/GitLab |
| Description | yes | Auto-fetch from GitHub API via `gh api repos/{owner}/{repo}` — show fetched value, let user confirm or override |
| Language | no | Auto-fetched from GitHub meta |
| License | no | Auto-fetched from GitHub meta (SPDX id) |
| Categories | yes | Multi-select from the 12 slugs; first selection determines subdirectory |
| Affiliation | yes | `community` / `affiliated` / `official` |
| Hardware | no | Multi-select: grayskull, wormhole, blackhole, quietbox, galaxy, ttsim |
| Tags | no | Comma-separated, lowercase, hyphenated |
| Extra links | no | Format: `type \| url \| label` one per line |

**GitHub meta fetch:** Run `gh api repos/{owner}/{repo} --jq '{description:.description, language:.language, license:.license.spdx_id}'`. If the URL is not a GitHub URL or the fetch fails, skip silently and ask the user to fill in manually.

**Entry ID generation:** Derive from the **project name** (not the repo name), matching `scripts/issue_to_entry.py`'s `slugify(name)` logic: lowercase, strip non-word characters except hyphens, replace whitespace/underscores with `-`, collapse consecutive `-`, strip leading/trailing `-`. Show the proposed ID to the user and let them override. This ensures the ID the contributor confirms in the preview matches the ID in the auto-generated PR for Path A.

### Phase 2 — Preview

Render the complete JSON that would be written, using the gathered fields. Example:

```json
{
  "id": "my-project",
  "name": "My Project",
  "description": "A tool that does X using TT-Metalium.",
  "affiliation": "community",
  "categories": ["dev-tools"],
  "tags": ["inference", "llm"],
  "links": [
    { "type": "repo", "url": "https://github.com/user/my-project" }
  ],
  "hardware": ["wormhole"],
  "language": "Python",
  "license": "MIT"
}
```

Ask: "Does this look right? Any fields to change?" Loop until the user confirms.

### Phase 3 — Choose path

Present three options:

**A — File a GitHub issue** *(for anyone; no local repo access needed)*  
- Constructs issue body matching the `### Field` heading format expected by `scripts/issue_to_entry.py`
- Runs: `gh issue create --repo tenstorrent/tt-awesome --title "[Entry] {name}" --label submission --body "..."`
- Reports the issue URL on success
- Notes: a maintainer must add the `approved` label to trigger the auto-PR

**B — Write JSON locally** *(for contributors with a local checkout)*  
- Writes `entries/{primary-category}/{id}.json`
- Runs `python3 scripts/validate.py` and shows output
- Prints the git commands to create a branch and PR:
  ```
  git checkout -b entry/{id}
  git add entries/{category}/{id}.json
  git commit -m "feat: add {name}"
  gh pr create --title "feat: add {name}" --base main
  ```

**C — Write JSON + open PR** *(for maintainers / contributors with push access)*  
- Same as B, but also runs the git commands and `gh pr create` automatically
- Reports the PR URL on success

---

## 4. Category slugs (reference)

| Slug | Label |
|---|---|
| `getting-started` | Getting Started |
| `ai-models` | AI & Models |
| `agents` | AI Agents |
| `kernels` | Custom Kernels & Low-Level |
| `compilers` | Compilers & Frontends |
| `dev-tools` | Dev Tools & Debugging |
| `hw-system` | Hardware & System |
| `cloud-infra` | Cloud & Orchestration |
| `riscv-arch` | RISC-V & Architecture |
| `research` | Research & Papers |
| `games-demos` | Games & Demos |
| `guides` | Guides, Tutorials & Education |

---

## 5. Out of scope

- No changes to CI workflows
- No changes to `scripts/add_entry.py` (the existing interactive CLI remains)
- No auto-detection of whether the user has push access (user selects path)
- No GUI/TUI — plain conversational interface only
