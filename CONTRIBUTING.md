# Contributing to Awesome Tenstorrent

Thank you for helping build the definitive resource for the Tenstorrent ecosystem!

## Adding an entry

### Option A: Submit via issue (no PR required) — recommended for most contributors

[Open a submission issue →](https://github.com/tenstorrent/tt-awesome/issues/new?template=submit-entry.yml)

Fill in the form fields (name, description, affiliation, links, categories, etc.). A maintainer will review your submission. Once the `approved` label is applied, a pull request is created **automatically** — you don't need to fork the repo or write any JSON.

### Option B: Interactive CLI

```bash
python3 scripts/add_entry.py
```

The CLI prompts for every required field, offers multi-select for categories and hardware, validates inline, and writes the `.json` file to the right `entries/{category}/` subdirectory. It prints the git commands to open a PR when done.

### Option C: Write the JSON directly

1. Create `entries/{primary-category}/your-entry-id.json`
2. Fill in the schema (see below)
3. Run `python3 scripts/validate.py` to check it
4. Optionally preview: `python3 scripts/generate_readme.py`
5. Open a pull request

## JSON schema

Every entry must be valid against this schema:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Kebab-case; must match filename stem |
| `name` | string | yes | Display name |
| `description` | string | yes | 1–3 sentences, plain text |
| `affiliation` | enum | yes | `community` · `affiliated` · `official` |
| `categories` | string[] | yes | At least one; first entry determines subdirectory |
| `tags` | string[] | no | Freeform, lowercase, hyphenated |
| `links` | object[] | yes | At least one; first `repo` link is canonical |
| `links[].type` | enum | yes | `repo` · `article` · `talk` · `video` · `website` · `demo` · `lesson` · `paper` |
| `links[].url` | string | yes | HTTPS URL |
| `links[].label` | string | no | Human label; defaults to type |
| `hardware` | string[] | no | `grayskull` · `wormhole` · `blackhole` · `quietbox` · `galaxy` · `ttsim` |
| `featured` | boolean | no | Elevates entry within its affiliation tier; use sparingly |
| `hidden` | boolean | no | Set `true` to suppress from README and website while keeping the entry in the database |
| `author` | string | no | GitHub username or "Firstname Lastname" |
| `language` | string | no | Primary language |
| `license` | string | no | SPDX identifier |

## Affiliation policy

| Value | Who qualifies |
|---|---|
| `community` | Anyone not employed by Tenstorrent |
| `affiliated` | Tenstorrent employees contributing in a personal capacity (e.g. personal GitHub repos, not under the tenstorrent org) |
| `official` | Repositories in the `tenstorrent` GitHub org |

**Community entries are shown first** in every category. This is intentional — the goal is to surface what the community has built, not to be an index of official repos.

## Category slugs

| Slug | Label |
|---|---|
| `getting-started` | 🚀 Getting Started |
| `ai-models` | 🤖 AI & Models |
| `agents` | 🕵️ AI Agents |
| `kernels` | ⚙️ Custom Kernels & Low-Level |
| `compilers` | 🔨 Compilers & Frontends |
| `dev-tools` | 🛠 Dev Tools & Debugging |
| `hw-system` | 🖥 Hardware & System |
| `cloud-infra` | ☁️ Cloud & Orchestration |
| `riscv-arch` | 🔩 RISC-V & Architecture |
| `research` | 🔬 Research & Papers |
| `games-demos` | 🎮 Games & Demos |
| `guides` | 📚 Guides, Tutorials & Education |

## CI validation

Every pull request touching `entries/` runs `scripts/validate.py` automatically. The PR will not merge if validation fails.

## Star counts

`stars` and `updatedAt` are not in the entry JSON. They are fetched nightly by a GitHub Action and stored in `src/_data/github_meta.json`. Do not add them to your entry file.

## README.md

`README.md` is auto-generated from the entries. Do not edit it by hand — changes will be overwritten on the next deploy.
