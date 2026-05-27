---
name: add-project
description: Guide the user through submitting a new entry to the Awesome Tenstorrent list. Use when the user wants to add, submit, or propose a project, library, tool, or resource to tt-awesome.
argument-hint: [project name or URL]
allowed-tools: [Bash, Read, Write]
---

# /tt-awesome:add-project

Guides a contributor through submitting a new entry to the Awesome Tenstorrent list.
Three exit paths: file a GitHub issue, write JSON locally, or write JSON and open a PR.

## Arguments

The user invoked this with: $ARGUMENTS

If `$ARGUMENTS` contains a URL, treat it as the repo URL and skip that question.
If `$ARGUMENTS` contains a project name (non-URL text), pre-fill the name field.

---

## Phase 1 — Gather fields

Ask **one question at a time** in this order. Never ask multiple fields in one message.

For each optional field, ask only once — if the user says "skip", "none", or leaves it blank, move on.

### Fields and order

1. **Project name** (required)
   - Skip if pre-filled from `$ARGUMENTS`

2. **Repo URL** (required)
   - Must be HTTPS. Accept GitHub or GitLab URLs.
   - Skip if pre-filled from `$ARGUMENTS`
   - After getting the URL, immediately run the GitHub meta fetch (see below) and use the results to pre-fill description, language, and license. Do not ask for those three fields separately yet — just show what was fetched and confirm.

3. **Description** (required)
   - Show the GitHub-fetched description (if any) and ask: "Does this description work, or would you like to change it?"
   - If no description was fetched, ask the user to write one (1–3 sentences, plain text).

4. **Categories** (required, multi-select)
   - Present the full list and ask the user to pick one or more. The **first** selected category determines the entry's subdirectory.
   - Valid slugs:
     - `getting-started` — Getting Started
     - `ai-models` — AI & Models
     - `agents` — AI Agents
     - `kernels` — Custom Kernels & Low-Level
     - `compilers` — Compilers & Frontends
     - `dev-tools` — Dev Tools & Debugging
     - `hw-system` — Hardware & System
     - `cloud-infra` — Cloud & Orchestration
     - `riscv-arch` — RISC-V & Architecture
     - `research` — Research & Papers
     - `games-demos` — Games & Demos
     - `guides` — Guides, Tutorials & Education

5. **Affiliation** (required)
   - `community` — not a Tenstorrent employee
   - `affiliated` — Tenstorrent employee, personal capacity
   - `official` — lives under the `tenstorrent` GitHub org

6. **Hardware tested** (optional)
   - Ask: "Which Tenstorrent hardware has this been tested on? (skip if unsure)"
   - Options: `grayskull`, `wormhole`, `blackhole`, `quietbox`, `galaxy`, `ttsim`

7. **Tags** (optional)
   - Ask: "Any tags? (comma-separated, lowercase, e.g. `inference, llm, transformer` — or skip)"

8. **Extra links** (optional)
   - Ask: "Any additional links? (one per line: `type | url | label` — types: article, talk, video, website, demo, lesson, paper — or skip)"

9. **Author** (optional)
   - Ask: "Author GitHub username or full name? (leave blank to use your GitHub username)"

### GitHub meta fetch

After receiving a GitHub repo URL, run:

```bash
gh api repos/{owner}/{repo} --jq '{description:.description, language:.language, license:.license.spdx_id}'
```

- Extract `owner` and `repo` from the URL path.
- If the fetch succeeds, use `description`, `language`, and `license` as pre-filled values.
- If the URL is not a GitHub URL, or the fetch fails for any reason, skip silently and ask manually.

### Entry ID generation

Derive the entry ID from the **project name** (not the repo name) — this matches how `scripts/issue_to_entry.py` derives the ID from the `Name` field, so Path A (issue) and Paths B/C (local JSON) produce the same ID:
- Lowercase
- Strip non-word characters except hyphens
- Replace whitespace and underscores with `-`
- Collapse multiple consecutive `-` into one
- Strip leading/trailing `-`

Show the proposed ID and let the user override it.

> **Note for Path A:** The auto-generated PR from an approved issue derives its ID the same way — from the `Name` field — so the ID the contributor sees in the preview will match the final file.

---

## Phase 2 — Preview

Once all fields are gathered, render the complete JSON:

```json
{
  "id": "<id>",
  "name": "<name>",
  "description": "<description>",
  "affiliation": "<affiliation>",
  "categories": ["<primary>", ...],
  "tags": [...],
  "links": [
    { "type": "repo", "url": "<repo_url>" },
    ...extra links...
  ],
  "hardware": [...],
  "language": "<language>",
  "license": "<license>",
  "author": "<author>"
}
```

Omit optional fields (`tags`, `hardware`, `language`, `license`, `author`, extra links) if the user skipped them.

Ask: **"Does this look right? Any fields to change?"**

Loop — let the user request any edits — until they confirm. Then move to Phase 3.

---

## Phase 3 — Choose path

Present the three options clearly:

---

**A — File a GitHub issue** *(works for anyone — no local repo access needed)*
A maintainer reviews and adds the `approved` label, which auto-creates a PR.

**B — Write the JSON file locally** *(requires a local checkout of tt-awesome)*
Writes the file, validates it, and prints the git commands to open a PR yourself.

**C — Write JSON + open PR automatically** *(requires push access to tt-awesome)*
Does everything in B and then runs `gh pr create` for you.

---

Wait for the user to pick A, B, or C.

### Path A — File GitHub issue

Construct the issue body in GitHub issue form format (each field as a `### Heading` section):

```
### Name

{name}

### Description

{description}

### Affiliation

{affiliation}

### Repository URL

{repo_url}

### Additional Links

{extra_links or "_No response_"}

### Categories

{each selected category as "- [X] slug — Label" on its own line}

### Hardware

{each selected hardware as "- [X] slug" on its own line, or "_No response_" if none}

### Tags

{tags or "_No response_"}

### Author

{author or "_No response_"}

### Language

{language or "_No response_"}

### License

{license or "_No response_"}
```

Run:
```bash
gh issue create \
  --repo tenstorrent/tt-awesome \
  --title "[Entry] {name}" \
  --label submission \
  --body "{body}"
```

Report the issue URL. Remind the user that a maintainer needs to add the `approved` label before a PR is created automatically.

### Path B — Write JSON locally

1. Write `entries/{primary_category}/{id}.json` with the confirmed JSON.
2. Run `python3 scripts/validate.py` and show the output.
3. If validation fails, show the errors and ask the user to fix them (loop back to Phase 2).
4. If validation passes, print:

```
Entry written to entries/{primary_category}/{id}.json

To open a PR:
  git checkout -b entry/{id}
  git add entries/{primary_category}/{id}.json
  git commit -m "feat: add {name}"
  gh pr create --title "feat: add {name}" --base main
```

### Path C — Write JSON + open PR

1. Write `entries/{primary_category}/{id}.json` with the confirmed JSON.
2. Run `python3 scripts/validate.py`. If it fails, show errors and loop back to Phase 2.
3. Run:

```bash
git checkout -b entry/{id}
git add entries/{primary_category}/{id}.json
git commit -m "feat: add {name}"
gh pr create --title "feat: add {name}" --base main
```

4. Report the PR URL on success.
