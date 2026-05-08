# Awesome Tenstorrent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a JSON-driven, community-first awesome list with a generated README and an Eleventy three-pane website deployed to GitHub Pages.

**Architecture:** `entries/*.json` is the single source of truth. Python scripts generate `README.md` and validate entries. Eleventy reads the JSON data and renders a three-pane site (sidebar / list / detail) with Tenstorrent dark theme. Client-side JS handles pane switching, search, and affiliation filtering without page navigation.

**Tech Stack:** Eleventy 3.x (Nunjucks templates), vanilla JS, Python 3.11+, GitHub Actions, GitHub Pages.

---

## File Map

```
entries/                          Task 9-11  (one .json per entry)
scripts/
  validate.py                     Task 2
  generate_readme.py              Task 3
  fetch_github_meta.py            Task 4
  add_entry.py                    Task 5
tests/
  test_validate.py                Task 2
  test_generate_readme.py         Task 3
src/
  _data/
    categories.js                 Task 1
    entries.js                    Task 1
    github_meta.json              Task 1  (empty seed)
  _includes/
    base.njk                      Task 6
    sidebar.njk                   Task 6
    entry-list.njk                Task 6
    entry-detail.njk              Task 6
  index.njk                       Task 6
  assets/
    style.css                     Task 6
    main.js                       Task 7
.eleventy.js                      Task 1
package.json                      Task 1
CONTRIBUTING.md                   Task 12
.github/workflows/
  validate.yml                    Task 8
  deploy.yml                      Task 8
  nightly.yml                     Task 8
```

---

## Task 1: Repo scaffolding + Eleventy setup

**Files:**
- Create: `package.json`
- Create: `.eleventy.js`
- Create: `src/_data/categories.js`
- Create: `src/_data/entries.js`
- Create: `src/_data/github_meta.json`
- Create: `entries/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p entries src/_data src/_includes src/assets scripts tests .github/workflows
touch entries/.gitkeep
```

- [ ] **Step 2: Write `package.json`**

```json
{
  "name": "tt-awesome",
  "version": "1.0.0",
  "description": "Awesome Tenstorrent — community-first ecosystem list",
  "scripts": {
    "build": "eleventy",
    "serve": "eleventy --serve",
    "validate": "python3 scripts/validate.py",
    "generate": "python3 scripts/generate_readme.py"
  },
  "devDependencies": {
    "@11ty/eleventy": "^3.0.0"
  }
}
```

- [ ] **Step 3: Install Eleventy**

```bash
npm install
```

Expected: `node_modules/@11ty/eleventy` exists.

- [ ] **Step 4: Write `.eleventy.js`**

```js
module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addFilter("truncate", (str, len) =>
    str && str.length > len ? str.slice(0, len) + "…" : str
  );
  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
  };
};
```

- [ ] **Step 5: Write `src/_data/categories.js`**

```js
module.exports = [
  { slug: "ai-models",   label: "🤖 AI & Models",                   description: "Running, serving, and experimenting with AI models" },
  { slug: "agents",      label: "🕵️ AI Agents",                     description: "Agentic systems and AI assistants running on TT hardware" },
  { slug: "kernels",     label: "⚙️ Custom Kernels & Low-Level",     description: "Metalium/tt-lang kernel authoring; anything sub-compiler" },
  { slug: "compilers",   label: "🔨 Compilers & Frontends",          description: "Getting PyTorch/JAX/ONNX/CUDA models onto TT hardware" },
  { slug: "dev-tools",   label: "🛠 Dev Tools & Debugging",          description: "Profiling, visualization, and debugging workloads" },
  { slug: "hw-system",   label: "🖥 Hardware & System",              description: "Drivers, firmware, monitoring, and hardware management" },
  { slug: "cloud-infra", label: "☁️ Cloud & Orchestration",          description: "Kubernetes, cloud deployment, and multi-node infrastructure" },
  { slug: "riscv-arch",  label: "🔩 RISC-V & Architecture",          description: "ISA, simulation, and running Linux on TT silicon" },
  { slug: "research",    label: "🔬 Research & Papers",               description: "Academic papers, theses, and HPC experiments" },
  { slug: "games-demos", label: "🎮 Games & Demos",                  description: "Creative, playful, and proof-of-concept projects" },
  { slug: "guides",      label: "📚 Guides, Tutorials & Education",  description: "Getting-started content, blog posts, lessons, courses" },
];
```

- [ ] **Step 6: Write `src/_data/entries.js`**

```js
const fs = require("fs");
const path = require("path");
const meta = require("./github_meta.json");

const metaByUrl = {};
for (const [url, data] of Object.entries(meta)) {
  metaByUrl[url] = data;
}

const AFFILIATION_ORDER = { community: 0, affiliated: 1, official: 2 };

module.exports = function () {
  const entriesDir = path.join(__dirname, "../../entries");
  const files = fs.readdirSync(entriesDir).filter((f) => f.endsWith(".json"));

  const entries = files.map((f) => {
    const entry = JSON.parse(
      fs.readFileSync(path.join(entriesDir, f), "utf8")
    );
    const repoLink = (entry.links || []).find((l) => l.type === "repo");
    if (repoLink && metaByUrl[repoLink.url]) {
      Object.assign(entry, metaByUrl[repoLink.url]);
    }
    return entry;
  });

  return entries.sort((a, b) => {
    const tierDiff =
      (AFFILIATION_ORDER[a.affiliation] ?? 2) -
      (AFFILIATION_ORDER[b.affiliation] ?? 2);
    if (tierDiff !== 0) return tierDiff;
    const featDiff = (a.featured ? 0 : 1) - (b.featured ? 0 : 1);
    if (featDiff !== 0) return featDiff;
    return (b.stars || 0) - (a.stars || 0);
  });
};
```

- [ ] **Step 7: Seed `src/_data/github_meta.json`**

```json
{}
```

- [ ] **Step 8: Verify Eleventy can start with minimal template**

Create `src/index.njk` temporarily:

```njk
---
title: Awesome Tenstorrent
---
<h1>{{ title }}</h1>
<p>{{ entries | length }} entries loaded.</p>
```

Run:
```bash
npm run build
```

Expected: `_site/index.html` contains `0 entries loaded.` (entries dir is empty). No errors.

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json .eleventy.js src/ entries/.gitkeep
git commit -m "feat: scaffold Eleventy site with data layer"
```

---

## Task 2: `validate.py` + tests

**Files:**
- Create: `scripts/validate.py`
- Create: `tests/test_validate.py`

- [ ] **Step 1: Write `tests/test_validate.py`**

```python
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate import validate_entry


def valid(overrides=None):
    e = {
        "id": "test-entry",
        "name": "Test Entry",
        "description": "A test entry.",
        "affiliation": "community",
        "categories": ["ai-models"],
        "links": [{"type": "repo", "url": "https://github.com/foo/bar"}],
    }
    if overrides:
        e.update(overrides)
    return e


def p(stem="test-entry"):
    return Path(f"/fake/entries/{stem}.json")


def test_valid_entry_has_no_errors():
    assert validate_entry(p(), valid()) == []


def test_id_must_match_filename():
    errors = validate_entry(p("other"), valid())
    assert any("must match filename" in e for e in errors)


def test_missing_name():
    e = valid()
    del e["name"]
    assert any("name" in err for err in validate_entry(p(), e))


def test_missing_description():
    e = valid()
    del e["description"]
    assert any("description" in err for err in validate_entry(p(), e))


def test_invalid_affiliation():
    errors = validate_entry(p(), valid({"affiliation": "partner"}))
    assert any("affiliation" in e for e in errors)


def test_empty_categories():
    errors = validate_entry(p(), valid({"categories": []}))
    assert any("categories" in e for e in errors)


def test_unknown_category():
    errors = validate_entry(p(), valid({"categories": ["unknown-cat"]}))
    assert any("unknown category" in e for e in errors)


def test_empty_links():
    errors = validate_entry(p(), valid({"links": []}))
    assert any("links" in e for e in errors)


def test_invalid_link_type():
    e = valid({"links": [{"type": "podcast", "url": "https://example.com"}]})
    assert any("type" in err for err in validate_entry(p(), e))


def test_http_url_rejected():
    e = valid({"links": [{"type": "repo", "url": "http://github.com/foo/bar"}]})
    assert any("https://" in err for err in validate_entry(p(), e))


def test_invalid_hardware():
    errors = validate_entry(p(), valid({"hardware": ["rtx4090"]}))
    assert any("hardware" in e for e in errors)


def test_valid_hardware():
    e = valid({"hardware": ["blackhole", "wormhole", "ttsim"]})
    assert validate_entry(p(), e) == []


def test_featured_must_be_bool():
    errors = validate_entry(p(), valid({"featured": "yes"}))
    assert any("featured" in e for e in errors)


def test_multiple_valid_categories_and_links():
    e = valid({
        "categories": ["ai-models", "research"],
        "links": [
            {"type": "repo", "url": "https://github.com/foo/bar"},
            {"type": "talk", "url": "https://fosdem.org/talk", "label": "FOSDEM 2026"},
        ],
    })
    assert validate_entry(p(), e) == []
```

- [ ] **Step 2: Run tests — expect ImportError (validate.py doesn't exist yet)**

```bash
python3 -m pytest tests/test_validate.py -v 2>&1 | head -20
```

Expected: `ImportError: No module named 'validate'`

- [ ] **Step 3: Write `scripts/validate.py`**

```python
#!/usr/bin/env python3
"""Validate all entries in entries/*.json against the schema."""
import json
import re
import sys
from pathlib import Path

VALID_AFFILIATIONS = {"official", "affiliated", "community"}
VALID_CATEGORY_SLUGS = {
    "ai-models", "agents", "kernels", "compilers", "dev-tools",
    "hw-system", "cloud-infra", "riscv-arch", "research", "games-demos", "guides",
}
VALID_LINK_TYPES = {"repo", "article", "talk", "video", "website", "demo", "lesson", "paper"}
VALID_HARDWARE = {"grayskull", "wormhole", "blackhole", "quietbox", "galaxy", "ttsim"}
URL_RE = re.compile(r"^https://.+")


def validate_entry(path: Path, data: dict) -> list:
    errors = []
    expected_id = path.stem
    if data.get("id") != expected_id:
        errors.append(f"id '{data.get('id')}' must match filename '{expected_id}'")
    for field in ("id", "name", "description", "affiliation"):
        if not data.get(field) or not isinstance(data[field], str):
            errors.append(f"missing or invalid required field: {field}")
    if data.get("affiliation") not in VALID_AFFILIATIONS:
        errors.append(f"affiliation must be one of {sorted(VALID_AFFILIATIONS)}, got '{data.get('affiliation')}'")
    cats = data.get("categories")
    if not cats or not isinstance(cats, list) or len(cats) == 0:
        errors.append("categories must be a non-empty list")
    else:
        for c in cats:
            if c not in VALID_CATEGORY_SLUGS:
                errors.append(f"unknown category slug: '{c}'")
    links = data.get("links")
    if not links or not isinstance(links, list) or len(links) == 0:
        errors.append("links must be a non-empty list")
    else:
        for i, link in enumerate(links):
            if link.get("type") not in VALID_LINK_TYPES:
                errors.append(f"links[{i}].type must be one of {sorted(VALID_LINK_TYPES)}")
            url = link.get("url", "")
            if not URL_RE.match(url):
                errors.append(f"links[{i}].url must be a valid https:// URL, got '{url}'")
    hw = data.get("hardware")
    if hw is not None:
        if not isinstance(hw, list):
            errors.append("hardware must be a list")
        else:
            for h in hw:
                if h not in VALID_HARDWARE:
                    errors.append(f"unknown hardware value: '{h}'")
    if "tags" in data and not isinstance(data["tags"], list):
        errors.append("tags must be a list")
    if "featured" in data and not isinstance(data["featured"], bool):
        errors.append("featured must be a boolean")
    return errors


def main():
    entries_dir = Path(__file__).parent.parent / "entries"
    if not entries_dir.is_dir():
        print(f"ERROR: entries/ not found at {entries_dir}")
        sys.exit(1)
    json_files = sorted(entries_dir.glob("*.json"))
    if not json_files:
        print("No entries found — nothing to validate.")
        sys.exit(0)
    all_ids, total_errors = [], 0
    for fpath in json_files:
        try:
            data = json.loads(fpath.read_text())
        except json.JSONDecodeError as e:
            print(f"FAIL {fpath.name}: invalid JSON — {e}")
            total_errors += 1
            continue
        errors = validate_entry(fpath, data)
        all_ids.append(data.get("id"))
        if errors:
            print(f"FAIL {fpath.name}:")
            for e in errors:
                print(f"  - {e}")
            total_errors += len(errors)
        else:
            print(f"  OK {fpath.name}")
    seen = set()
    for eid in all_ids:
        if eid in seen:
            print(f"FAIL: duplicate id '{eid}'")
            total_errors += 1
        seen.add(eid)
    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        sys.exit(1)
    print(f"\nAll {len(json_files)} entries valid.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_validate.py -v
```

Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/validate.py tests/test_validate.py
git commit -m "feat: add validate.py with full schema checks"
```

---

## Task 3: `generate_readme.py` + tests

**Files:**
- Create: `scripts/generate_readme.py`
- Create: `tests/test_generate_readme.py`

- [ ] **Step 1: Write `tests/test_generate_readme.py`**

```python
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_readme import sort_entries, render_entry, AFFILIATION_ORDER

COMM = {
    "id": "cool-proj", "name": "cool-proj",
    "description": "A cool community project.",
    "affiliation": "community", "categories": ["ai-models"],
    "links": [{"type": "repo", "url": "https://github.com/foo/cool-proj"}],
    "stars": 50, "featured": True,
}
AFFIL = {**COMM, "id": "affil-proj", "name": "affil-proj", "affiliation": "affiliated", "featured": False}
OFFICIAL = {**COMM, "id": "official-proj", "name": "official-proj", "affiliation": "official", "featured": True, "stars": 9999}


def test_community_always_before_official():
    result = sort_entries([OFFICIAL, COMM])
    assert result[0]["affiliation"] == "community"


def test_featured_first_within_tier():
    plain = {**COMM, "id": "plain", "name": "plain", "featured": False, "stars": 1000}
    result = sort_entries([plain, COMM])
    assert result[0]["name"] == "cool-proj"


def test_stars_desc_within_same_tier_and_featured():
    high = {**COMM, "id": "high", "name": "high", "featured": False, "stars": 200}
    low  = {**COMM, "id": "low",  "name": "low",  "featured": False, "stars": 5}
    result = sort_entries([low, high])
    assert result[0]["name"] == "high"


def test_affiliated_between_community_and_official():
    result = sort_entries([OFFICIAL, AFFIL, COMM])
    affiliations = [e["affiliation"] for e in result]
    assert affiliations == ["community", "affiliated", "official"]


def test_render_entry_contains_name_description_badge():
    md = render_entry(COMM)
    assert "cool-proj" in md
    assert "community" in md
    assert "A cool community project." in md


def test_render_entry_includes_all_links():
    entry = {**COMM, "links": [
        {"type": "repo", "url": "https://github.com/foo/cool-proj"},
        {"type": "talk", "url": "https://fosdem.org/talk", "label": "FOSDEM 2026"},
    ]}
    md = render_entry(entry)
    assert "FOSDEM 2026" in md
    assert "🎤" in md


def test_render_entry_no_repo_link():
    entry = {**COMM, "links": [{"type": "paper", "url": "https://arxiv.org/abs/1234.56789"}]}
    md = render_entry(entry)
    assert "cool-proj" in md
    assert "arxiv.org" in md
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python3 -m pytest tests/test_generate_readme.py -v 2>&1 | head -5
```

- [ ] **Step 3: Write `scripts/generate_readme.py`**

```python
#!/usr/bin/env python3
"""Generate README.md from entries/*.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"

CATEGORIES = [
    ("ai-models",   "🤖 AI & Models"),
    ("agents",      "🕵️ AI Agents"),
    ("kernels",     "⚙️ Custom Kernels & Low-Level"),
    ("compilers",   "🔨 Compilers & Frontends"),
    ("dev-tools",   "🛠 Dev Tools & Debugging"),
    ("hw-system",   "🖥 Hardware & System"),
    ("cloud-infra", "☁️ Cloud & Orchestration"),
    ("riscv-arch",  "🔩 RISC-V & Architecture"),
    ("research",    "🔬 Research & Papers"),
    ("games-demos", "🎮 Games & Demos"),
    ("guides",      "📚 Guides, Tutorials & Education"),
]

AFFILIATION_ORDER = {"community": 0, "affiliated": 1, "official": 2}

LINK_ICONS = {
    "repo": "📦", "article": "📝", "talk": "🎤", "video": "🎥",
    "website": "🌐", "demo": "🚀", "lesson": "📖", "paper": "📄",
}

SHIELDS = {
    "community": "![community](https://img.shields.io/badge/community-27AE60?style=flat-square)",
    "affiliated": "![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)",
    "official":   "![official](https://img.shields.io/badge/official-607D8B?style=flat-square)",
}


def load_entries():
    return [json.loads(f.read_text()) for f in sorted(ENTRIES_DIR.glob("*.json"))]


def sort_entries(entries):
    def key(e):
        tier = AFFILIATION_ORDER.get(e.get("affiliation", "community"), 2)
        feat = 0 if e.get("featured") else 1
        return (tier, feat, -(e.get("stars", 0)))
    return sorted(entries, key=key)


def render_entry(e):
    name = e["name"]
    desc = e["description"]
    badge = SHIELDS.get(e.get("affiliation", "community"), "")
    links = e.get("links", [])
    repo = next((l for l in links if l["type"] == "repo"), None)
    name_md = f"[{name}]({repo['url']})" if repo else name
    link_parts = [
        f"[{LINK_ICONS.get(l['type'], '🔗')} {l.get('label') or l['type']}]({l['url']})"
        for l in links
    ]
    return f"- **{name_md}** {badge}\n  {desc}\n  {' · '.join(link_parts)}"


def generate():
    entries = sort_entries(load_entries())
    lines = [
        "# ⚡ Awesome Tenstorrent", "",
        "> A curated, community-first collection of awesome demos, tools, projects, and resources "
        "built by and for the Tenstorrent ecosystem.", "",
        "> **This file is auto-generated from `entries/*.json`. Do not edit directly — "
        "see [CONTRIBUTING.md](CONTRIBUTING.md) to add an entry.**", "",
        "## Contents", "",
    ]
    for slug, label in CATEGORIES:
        if any(slug in e.get("categories", []) for e in entries):
            anchor = label.lower().replace(" ", "-").replace("&", "").replace("️", "").strip("-")
            lines.append(f"- [{label}](#{anchor})")
    lines.append("")
    for slug, label in CATEGORIES:
        cat_entries = [e for e in entries if slug in e.get("categories", [])]
        if not cat_entries:
            continue
        lines += [f"## {label}", ""]
        for e in cat_entries:
            lines += [render_entry(e), ""]
    lines += ["---", "", "*Generated by `scripts/generate_readme.py`.*", ""]
    return "\n".join(lines)


def main():
    readme = generate()
    out = ROOT / "README.md"
    out.write_text(readme)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_generate_readme.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_readme.py tests/test_generate_readme.py
git commit -m "feat: add generate_readme.py with community-first sorting"
```

---

## Task 4: `fetch_github_meta.py`

**Files:**
- Create: `scripts/fetch_github_meta.py`

No automated tests — this calls an external API. Tested manually.

- [ ] **Step 1: Write `scripts/fetch_github_meta.py`**

```python
#!/usr/bin/env python3
"""Fetch stars + updatedAt for all repo-linked entries. Writes src/_data/github_meta.json."""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"
META_OUT = ROOT / "src" / "_data" / "github_meta.json"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_RE = re.compile(r"https://github\.com/([^/?#]+/[^/?#]+?)(?:\.git)?$")


def fetch_repo(repo: str) -> dict:
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return {"stars": d.get("stargazers_count", 0), "updatedAt": d.get("updated_at", "")}
    except urllib.error.HTTPError as e:
        print(f"  WARN {repo}: HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"  WARN {repo}: {e}", file=sys.stderr)
    return {}


def main():
    entries = [json.loads(f.read_text()) for f in sorted(ENTRIES_DIR.glob("*.json"))]
    meta = {}
    for entry in entries:
        repo_link = next((l for l in entry.get("links", []) if l["type"] == "repo"), None)
        if not repo_link:
            continue
        m = REPO_RE.match(repo_link["url"])
        if not m:
            continue
        repo = m.group(1)
        print(f"Fetching {repo}…")
        result = fetch_repo(repo)
        if result:
            meta[repo_link["url"]] = result
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {len(meta)} entries to {META_OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/fetch_github_meta.py
git commit -m "feat: add fetch_github_meta.py for nightly star counts"
```

---

## Task 5: `add_entry.py`

**Files:**
- Create: `scripts/add_entry.py`

- [ ] **Step 1: Write `scripts/add_entry.py`**

```python
#!/usr/bin/env python3
"""Interactive CLI to add a new entry to entries/."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"

AFFILIATIONS = ["community", "affiliated", "official"]
CATEGORIES = [
    "ai-models", "agents", "kernels", "compilers", "dev-tools",
    "hw-system", "cloud-infra", "riscv-arch", "research", "games-demos", "guides",
]
LINK_TYPES = ["repo", "article", "talk", "video", "website", "demo", "lesson", "paper"]
HARDWARE = ["grayskull", "wormhole", "blackhole", "quietbox", "galaxy", "ttsim"]
URL_RE = re.compile(r"^https://.+")


def ask(prompt, required=True, default=None):
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"{prompt}{suffix}: ").strip()
        if not val and default:
            return default
        if val:
            return val
        if not required:
            return None
        print("  (required — please enter a value)")


def pick(prompt, options, multi=False):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    label = "number(s), comma-separated" if multi else "number"
    while True:
        raw = input(f"Enter {label}: ").strip()
        try:
            indices = [int(x) - 1 for x in raw.split(",") if x.strip()]
            chosen = [options[i] for i in indices if 0 <= i < len(options)]
            if chosen:
                return chosen if multi else chosen[0]
        except (ValueError, IndexError):
            pass
        print("  (invalid — try again)")


def collect_links():
    links = []
    print("\nLinks — enter at least one repo link.")
    while True:
        n = len(links) + 1
        print(f"\n  Link {n}:")
        ltype = pick("  Type", LINK_TYPES)
        url = ask("  URL (https://…)")
        if not URL_RE.match(url):
            print("  Invalid URL, skipping.")
            continue
        label = ask("  Label (optional)", required=False)
        link = {"type": ltype, "url": url}
        if label:
            link["label"] = label
        links.append(link)
        if input("  Add another link? [y/N] ").strip().lower() != "y":
            break
    return links


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    print("⚡ Add an Awesome Tenstorrent entry\n")
    name = ask("Name (e.g. tt-boltz)")
    entry_id = slugify(name)
    dest = ENTRIES_DIR / f"{entry_id}.json"
    if dest.exists():
        print(f"ERROR: {dest} already exists.")
        sys.exit(1)
    description = ask("Description (1–3 sentences)")
    affiliation = pick("Affiliation", AFFILIATIONS)
    categories = pick("Categories (multi-select OK)", CATEGORIES, multi=True)
    links = collect_links()

    hw_raw = input("\nHardware (comma-separated numbers, or blank):\n  " +
                   " ".join(f"{i+1}.{h}" for i, h in enumerate(HARDWARE)) + "\n> ").strip()
    hardware = []
    if hw_raw:
        for x in hw_raw.split(","):
            try:
                hardware.append(HARDWARE[int(x.strip()) - 1])
            except (ValueError, IndexError):
                pass

    tags_raw = input("Tags (comma-separated, or blank): ").strip()
    tags = [t.strip().lower().replace(" ", "-") for t in tags_raw.split(",") if t.strip()]
    author = ask("Author (GitHub username or name)", required=False)
    language = ask("Language (e.g. Python)", required=False)
    license_id = ask("License (SPDX, e.g. MIT)", required=False)
    featured = input("Featured? [y/N] ").strip().lower() == "y"

    entry = {
        "id": entry_id, "name": name, "description": description,
        "affiliation": affiliation, "categories": categories, "links": links,
    }
    if hardware:   entry["hardware"] = hardware
    if tags:       entry["tags"] = tags
    if author:     entry["author"] = author
    if language:   entry["language"] = language
    if license_id: entry["license"] = license_id
    if featured:   entry["featured"] = True

    dest.write_text(json.dumps(entry, indent=2) + "\n")
    print(f"\n✅  Written to {dest}")
    print(f"\nNext steps:")
    print(f"  python3 scripts/validate.py")
    print(f"  git add entries/{entry_id}.json && git commit -m 'feat: add {name}'")
    print(f"  gh pr create --title 'Add {name}'")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/add_entry.py
git commit -m "feat: add interactive add_entry.py CLI"
```

---

## Task 6: Eleventy templates + CSS

**Files:**
- Create: `src/_includes/base.njk`
- Create: `src/_includes/sidebar.njk`
- Create: `src/_includes/entry-list.njk`
- Create: `src/_includes/entry-detail.njk`
- Replace: `src/index.njk`
- Create: `src/assets/style.css`

- [ ] **Step 1: Write `src/_includes/base.njk`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚡ Awesome Tenstorrent</title>
  <meta name="description" content="A curated, community-first collection of projects and resources for the Tenstorrent ecosystem.">
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  {{ content | safe }}
  <script src="/assets/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `src/index.njk`**

```njk
---
layout: base.njk
---
<div class="app">
  <header class="topbar">
    <span class="logo">⚡ Awesome Tenstorrent</span>
    <input class="search" id="search" type="text" placeholder="search entries…" autocomplete="off">
    <div class="chips">
      <button class="chip active" data-filter="all">All</button>
      <button class="chip active" data-filter="community">community</button>
      <button class="chip active" data-filter="affiliated">affiliated</button>
      <button class="chip" data-filter="official">official</button>
    </div>
  </header>
  <div class="panes">
    {%- include "sidebar.njk" -%}
    {%- include "entry-list.njk" -%}
    {%- include "entry-detail.njk" -%}
  </div>
</div>
```

- [ ] **Step 3: Write `src/_includes/sidebar.njk`**

```njk
<nav class="sidebar" id="sidebar">
  <div class="sidebar-label">Use Cases</div>
  {%- for cat in categories %}
  <a class="sidebar-item{% if loop.first %} active{% endif %}"
     href="#"
     data-category="{{ cat.slug }}"
     onclick="selectCategory('{{ cat.slug }}', this); return false;">
    {{ cat.label }}
  </a>
  {%- endfor %}
  <hr class="sidebar-hr">
  <a class="sidebar-item sidebar-muted" href="CONTRIBUTING.md">+ Submit entry</a>
</nav>
```

- [ ] **Step 4: Write `src/_includes/entry-list.njk`**

```njk
<div class="list-pane">
  <div class="list-head">
    <div class="list-title" id="list-title">{{ categories[0].label }}</div>
    <div class="list-count" id="list-count"></div>
  </div>
  <div class="list-rows" id="list-rows">
    {%- for entry in entries %}
    <div class="entry-row"
         data-id="{{ entry.id }}"
         data-categories="{{ entry.categories | join(',') }}"
         data-affiliation="{{ entry.affiliation }}"
         data-search="{{ entry.name | lower }} {{ entry.description | lower }} {{ entry.tags | join(' ') if entry.tags else '' }} {{ entry.author | lower if entry.author else '' }}"
         onclick="selectEntry('{{ entry.id }}', this)">
      <div class="row-top">
        <span class="row-name">{{ entry.name }}</span>
        <span class="badge badge--{{ entry.affiliation }}">{{ entry.affiliation }}</span>
        {%- if entry.stars %}<span class="row-stars">{{ entry.stars }}⭐</span>{%- endif %}
      </div>
      <div class="row-desc">{{ entry.description | truncate(90) }}</div>
    </div>
    {%- endfor %}
  </div>
</div>
```

- [ ] **Step 5: Write `src/_includes/entry-detail.njk`**

```njk
<div class="detail-pane" id="detail-pane">
  <div class="detail-empty" id="detail-empty">
    <p>Select an entry to see details</p>
  </div>
  {%- for entry in entries %}
  <div class="detail-card" id="detail-{{ entry.id }}">
    <div class="detail-head">
      <div class="detail-title-row">
        <h1 class="detail-name">{{ entry.name }}</h1>
        <span class="badge badge--{{ entry.affiliation }}">{{ entry.affiliation }}</span>
        {%- if entry.featured %}<span class="featured-star">★ featured</span>{%- endif %}
      </div>
      <div class="detail-meta">
        {%- if entry.author %}by {{ entry.author }} · {% endif -%}
        {%- if entry.language %}{{ entry.language }} · {% endif -%}
        {%- if entry.license %}{{ entry.license }} · {% endif -%}
        {%- if entry.stars %}{{ entry.stars }}⭐{%- endif %}
      </div>
    </div>
    <p class="detail-desc">{{ entry.description }}</p>
    {%- if entry.links %}
    <div class="detail-section">
      <div class="section-label">Links</div>
      {%- for link in entry.links %}
      <a class="detail-link link--{{ link.type }}" href="{{ link.url }}" target="_blank" rel="noopener noreferrer">
        {%- if link.type == "repo" %}📦
        {%- elif link.type == "article" %}📝
        {%- elif link.type == "talk" %}🎤
        {%- elif link.type == "video" %}🎥
        {%- elif link.type == "paper" %}📄
        {%- elif link.type == "lesson" %}📖
        {%- elif link.type == "demo" %}🚀
        {%- else %}🌐
        {%- endif %}
        {{ link.label if link.label else link.type | title }}
      </a>
      {%- endfor %}
    </div>
    {%- endif %}
    {%- if entry.tags %}
    <div class="detail-section detail-tags">
      {%- for tag in entry.tags %}
      <span class="tag">{{ tag }}</span>
      {%- endfor %}
    </div>
    {%- endif %}
    {%- if entry.hardware %}
    <div class="detail-section">
      <div class="section-label">Works on</div>
      {%- for hw in entry.hardware %}
      <span class="hw-badge">{{ hw }}</span>
      {%- endfor %}
    </div>
    {%- endif %}
  </div>
  {%- endfor %}
</div>
```

- [ ] **Step 6: Write `src/assets/style.css`**

```css
:root {
  --bg0: #0F2A35; --bg1: #1A3C47; --bg2: #2D3142; --bg3: #0a1e28;
  --teal: #4FD1C5; --teal-lt: #81E6D9;
  --pink: #EC96B8; --green: #27AE60; --muted: #607D8B; --gold: #F4C471;
  --text: #E8F0F2; --text2: #B0C4DE;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: var(--bg0); color: var(--text); font-size: 14px; }
.app { display: flex; flex-direction: column; height: 100vh; }

/* Topbar */
.topbar { display: flex; align-items: center; gap: 12px; padding: 7px 16px;
          background: var(--bg0); border-bottom: 1px solid var(--bg2); flex-shrink: 0; }
.logo { font-weight: 800; font-size: 15px; color: var(--teal); white-space: nowrap; }
.search { flex: 1; max-width: 280px; background: var(--bg1); border: 1px solid var(--bg2);
          color: var(--text); padding: 5px 10px; border-radius: 4px; font-size: 13px; outline: none; }
.search:focus { border-color: var(--teal); }
.chips { display: flex; gap: 5px; }
.chip { font-size: 11px; padding: 3px 10px; border-radius: 12px; border: none;
        cursor: pointer; background: var(--bg1); color: var(--muted); transition: 0.15s; }
.chip.active[data-filter="all"]       { background: var(--bg2); color: var(--text); }
.chip.active[data-filter="community"] { background: var(--green); color: #fff; }
.chip.active[data-filter="affiliated"]{ background: var(--pink);  color: #fff; }
.chip.active[data-filter="official"]  { background: var(--muted); color: #fff; }

/* Three panes */
.panes { display: flex; flex: 1; overflow: hidden; }

/* Sidebar */
.sidebar { width: 160px; flex-shrink: 0; background: var(--bg3);
           border-right: 1px solid var(--bg2); padding: 10px 6px; overflow-y: auto; }
.sidebar-label { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase;
                 color: var(--muted); padding: 0 8px 8px; }
.sidebar-item { display: block; font-size: 12px; color: var(--muted); padding: 5px 8px;
                border-radius: 4px; text-decoration: none; margin-bottom: 1px;
                transition: 0.1s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sidebar-item:hover  { color: var(--text); background: var(--bg1); }
.sidebar-item.active { color: var(--teal); background: var(--bg1); font-weight: 600; }
.sidebar-muted       { font-size: 11px; opacity: 0.6; }
.sidebar-hr          { border: none; border-top: 1px solid var(--bg2); margin: 8px 6px; }

/* List pane */
.list-pane { width: 300px; flex-shrink: 0; border-right: 1px solid var(--bg2);
             display: flex; flex-direction: column; overflow: hidden; }
.list-head { padding: 10px 12px 8px; border-bottom: 1px solid var(--bg2); flex-shrink: 0; }
.list-title { font-size: 13px; font-weight: 700; color: var(--text); }
.list-count { font-size: 10px; color: var(--muted); margin-top: 1px; }
.list-rows  { overflow-y: auto; flex: 1; }
.entry-row  { padding: 8px 12px; border-bottom: 1px solid var(--bg1); cursor: pointer;
              transition: background 0.1s; border-left: 3px solid transparent; }
.entry-row:hover  { background: var(--bg1); }
.entry-row.active { background: var(--bg1); border-left-color: var(--teal); }
.entry-row.hidden { display: none; }
.row-top  { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.row-name { font-size: 12px; font-weight: 600; color: var(--text); }
.row-stars{ font-size: 10px; color: var(--teal-lt); margin-left: auto; white-space: nowrap; }
.row-desc { font-size: 11px; color: var(--muted); line-height: 1.4; }

/* Badges */
.badge { font-size: 9px; padding: 1px 6px; border-radius: 8px; color: #fff; white-space: nowrap; }
.badge--community { background: var(--green); }
.badge--affiliated{ background: var(--pink); }
.badge--official  { background: var(--muted); }
.featured-star    { font-size: 10px; color: var(--gold); }

/* Detail pane */
.detail-pane  { flex: 1; overflow-y: auto; padding: 20px 24px; }
.detail-empty { display: flex; align-items: center; justify-content: center;
                height: 100%; color: var(--muted); font-size: 13px; }
.detail-card  { display: none; }
.detail-card.visible { display: block; }
.detail-head  { margin-bottom: 14px; }
.detail-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
.detail-name  { font-size: 22px; font-weight: 800; color: var(--teal); }
.detail-meta  { font-size: 11px; color: var(--muted); }
.detail-desc  { font-size: 13px; color: var(--text); line-height: 1.65; margin-bottom: 16px; }
.detail-section { margin-bottom: 16px; }
.section-label  { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase;
                  color: var(--muted); margin-bottom: 6px; }
.detail-link { display: inline-block; font-size: 12px; color: var(--teal); text-decoration: none;
               background: var(--bg1); padding: 4px 10px; border-radius: 4px; margin: 2px 4px 2px 0;
               border: 1px solid var(--bg2); transition: border-color 0.1s; }
.detail-link:hover { border-color: var(--teal); }
.detail-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.tag         { font-size: 10px; background: var(--bg1); color: var(--teal-lt);
               padding: 2px 8px; border-radius: 10px; }
.hw-badge    { display: inline-block; font-size: 11px; background: var(--bg1); color: var(--text);
               padding: 3px 10px; border-radius: 4px; border: 1px solid var(--bg2); margin: 2px 4px 2px 0; }
```

- [ ] **Step 7: Verify build with templates**

```bash
npm run build 2>&1 | tail -5
```

Expected: `[11ty] Wrote 1 file in … (Eleventy)` with no errors.

- [ ] **Step 8: Commit**

```bash
git add src/
git commit -m "feat: add Eleventy templates and Tenstorrent dark theme CSS"
```

---

## Task 7: Client-side JS

**Files:**
- Create: `src/assets/main.js`

- [ ] **Step 1: Write `src/assets/main.js`**

```js
// State
let activeCategory = null;
let activeFilters = new Set(["community", "affiliated"]);
let activeEntryId = null;

document.addEventListener("DOMContentLoaded", () => {
  // Auto-select first category
  const first = document.querySelector(".sidebar-item[data-category]");
  if (first) selectCategory(first.dataset.category, first);

  // Search
  document.getElementById("search").addEventListener("input", (e) => {
    applyFilters(e.target.value.toLowerCase().trim());
  });

  // Filter chips
  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => toggleChip(chip))
  );
});

function selectCategory(slug, el) {
  activeCategory = slug;
  activeEntryId = null;
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
  // If active entry is now hidden, clear detail
  if (activeEntryId) {
    const row = document.querySelector(`.entry-row[data-id="${activeEntryId}"]`);
    if (row && row.classList.contains("hidden")) clearDetail();
  }
}
```

- [ ] **Step 2: Build and smoke-test manually**

```bash
npm run build && open _site/index.html
```

Verify: three panes render, sidebar categories show, no JS errors in console.

- [ ] **Step 3: Commit**

```bash
git add src/assets/main.js
git commit -m "feat: add three-pane JS (category select, search, filter)"
```

---

## Task 8: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/validate.yml`
- Create: `.github/workflows/deploy.yml`
- Create: `.github/workflows/nightly.yml`

- [ ] **Step 1: Write `.github/workflows/validate.yml`**

```yaml
name: Validate entries
on:
  pull_request:
    paths: ["entries/**", "scripts/validate.py"]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python3 scripts/validate.py
```

- [ ] **Step 2: Write `.github/workflows/deploy.yml`**

```yaml
name: Build and deploy
on:
  push:
    branches: [main]
permissions:
  contents: write
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Generate README
        run: python3 scripts/generate_readme.py
      - name: Commit README if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add README.md
          git diff --staged --quiet || git commit -m "chore: regenerate README [skip ci]"
          git push
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm run build
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./_site
```

- [ ] **Step 3: Write `.github/workflows/nightly.yml`**

```yaml
name: Fetch GitHub metadata
on:
  schedule:
    - cron: "17 2 * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Fetch metadata
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python3 scripts/fetch_github_meta.py
      - name: Commit if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add src/_data/github_meta.json
          git diff --staged --quiet || git commit -m "chore: update GitHub metadata [skip ci]"
          git push
```

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "feat: add CI/CD workflows (validate, deploy, nightly)"
```

---

## Task 9: Community + affiliated entries

**Files:** One `.json` per entry in `entries/`

- [ ] **Step 1: Write community featured entries**

`entries/tt-boltz.json`:
```json
{
  "id": "tt-boltz",
  "name": "tt-boltz",
  "description": "Boltz-2 biomolecular model for drug discovery on Tenstorrent Blackhole. Supports single-card and multi-card configurations — QuietBox (4×) and Galaxy (32×). Approaches physics-based FEP accuracy at 1000× the speed.",
  "affiliation": "community",
  "categories": ["ai-models", "research"],
  "tags": ["drug-discovery", "blackhole", "inference", "biology", "multi-card"],
  "links": [
    { "type": "repo", "url": "https://github.com/moritztng/tt-boltz" },
    { "type": "talk", "url": "https://fosdem.org/2026/schedule/event/AJLNVH-tt-boltz/", "label": "FOSDEM 2026 — Drug Discovery on Tenstorrent Hardware" }
  ],
  "hardware": ["blackhole", "quietbox", "galaxy"],
  "featured": true,
  "author": "moritztng",
  "language": "Python",
  "license": "MIT"
}
```

`entries/grayskull-attention.json`:
```json
{
  "id": "grayskull-attention",
  "name": "grayskull-attention",
  "description": "FlashAttention-style attention kernel implemented entirely in on-chip SRAM on the Tenstorrent Grayskull chip using TT-Metalium. Pioneering work in low-level attention on TT hardware.",
  "affiliation": "community",
  "categories": ["kernels", "ai-models"],
  "tags": ["attention", "grayskull", "metalium", "sram", "kernel"],
  "links": [
    { "type": "repo", "url": "https://github.com/moritztng/grayskull-attention" }
  ],
  "hardware": ["grayskull"],
  "featured": true,
  "author": "moritztng",
  "language": "TeX",
  "license": "MIT"
}
```

`entries/tt-tiny.json`:
```json
{
  "id": "tt-tiny",
  "name": "tt-tiny",
  "description": "Minimal Python code to access and program the Tenstorrent Blackhole chip directly — George Hotz's exploration of TT hardware programmability with pointed commentary on the architecture.",
  "affiliation": "community",
  "categories": ["kernels"],
  "tags": ["blackhole", "low-level", "exploration"],
  "links": [
    { "type": "repo", "url": "https://github.com/geohot/tt-tiny" }
  ],
  "hardware": ["blackhole"],
  "featured": true,
  "author": "geohot",
  "language": "Python"
}
```

`entries/tt-twitch.json`:
```json
{
  "id": "tt-twitch",
  "name": "tt-twitch",
  "description": "A Tenstorrent Grayskull kernel written live on Twitch by George Hotz. 120-core grid demonstration of live kernel programming.",
  "affiliation": "community",
  "categories": ["kernels", "games-demos"],
  "tags": ["grayskull", "kernel", "live-coding", "demo"],
  "links": [
    { "type": "repo", "url": "https://github.com/geohot/tt-twitch" }
  ],
  "hardware": ["grayskull"],
  "featured": true,
  "author": "geohot",
  "language": "C++"
}
```

`entries/dstack.json`:
```json
{
  "id": "dstack",
  "name": "dstack",
  "description": "Vendor-agnostic orchestration for training, inference, and agentic workloads across NVIDIA, AMD, TPU, and Tenstorrent on clouds, Kubernetes, and bare metal.",
  "affiliation": "community",
  "categories": ["cloud-infra", "agents"],
  "tags": ["orchestration", "kubernetes", "cloud", "multi-vendor"],
  "links": [
    { "type": "repo", "url": "https://github.com/dstackai/dstack" },
    { "type": "website", "url": "https://dstack.ai" }
  ],
  "featured": true,
  "author": "dstackai",
  "language": "Python",
  "license": "MPL-2.0"
}
```

`entries/barracuda.json`:
```json
{
  "id": "barracuda",
  "name": "BarraCUDA",
  "description": "Open-source CUDA compiler targeting multiple GPU architectures including Tenstorrent. Compiles .cu files to run on AMD and Tenstorrent hardware without modification.",
  "affiliation": "community",
  "categories": ["compilers"],
  "tags": ["cuda", "compiler", "cross-platform", "blackhole"],
  "links": [
    { "type": "repo", "url": "https://github.com/Zaneham/BarraCUDA" }
  ],
  "hardware": ["blackhole"],
  "featured": true,
  "author": "Zaneham",
  "language": "C"
}
```

`entries/ttnn-helloworld-cpp.json`:
```json
{
  "id": "ttnn-helloworld-cpp",
  "name": "ttnn-helloworld-cpp",
  "description": "Minimal working example of using Tenstorrent TTNN in C++. The simplest possible starting point for C++ developers targeting TT hardware with TTNN.",
  "affiliation": "community",
  "categories": ["kernels", "guides"],
  "tags": ["c++", "ttnn", "hello-world", "template"],
  "links": [
    { "type": "repo", "url": "https://github.com/marty1885/ttnn-helloworld-cpp" }
  ],
  "hardware": ["wormhole", "blackhole"],
  "author": "marty1885",
  "language": "C++"
}
```

`entries/tt-tutorial-korean.json`:
```json
{
  "id": "tt-tutorial-korean",
  "name": "tt-tutorial (Korean)",
  "description": "Comprehensive tutorials for the Tenstorrent software stack in Korean. Jupyter notebooks covering the full developer path from hardware setup to model inference.",
  "affiliation": "community",
  "categories": ["guides"],
  "tags": ["tutorial", "korean", "jupyter", "getting-started"],
  "links": [
    { "type": "repo", "url": "https://github.com/changh95/tt-tutorial" }
  ],
  "hardware": ["wormhole"],
  "author": "changh95",
  "language": "Jupyter Notebook"
}
```

`entries/bhx.json`:
```json
{
  "id": "bhx",
  "name": "bhx",
  "description": "Boot stock Linux cloud images on the SiFive X280 RISC-V cores inside Tenstorrent Blackhole AI accelerators. Per-card Rust daemon with virtio-mmio block/net/console and U-Boot/EFI support.",
  "affiliation": "community",
  "categories": ["riscv-arch"],
  "tags": ["blackhole", "risc-v", "linux", "boot", "virtio"],
  "links": [
    { "type": "repo", "url": "https://github.com/olofj/bhx" }
  ],
  "hardware": ["blackhole"],
  "featured": true,
  "author": "olofj",
  "language": "Rust"
}
```

`entries/koyeb-tenstorrent-examples.json`:
```json
{
  "id": "koyeb-tenstorrent-examples",
  "name": "koyeb/tenstorrent-examples",
  "description": "Example applications and deployment configurations for running AI workloads on Tenstorrent hardware via Koyeb's cloud platform.",
  "affiliation": "community",
  "categories": ["cloud-infra", "ai-models"],
  "tags": ["cloud", "koyeb", "deployment", "examples"],
  "links": [
    { "type": "repo", "url": "https://github.com/koyeb/tenstorrent-examples" },
    { "type": "website", "url": "https://www.koyeb.com/blog/tenstorrent-cloud-instances-unveiling-next-gen-ai-accelerators", "label": "Koyeb blog post" }
  ],
  "author": "koyeb",
  "language": "Dockerfile"
}
```

- [ ] **Step 2: Write affiliated entries — tsingletaryTT**

`entries/tt-zork-and-more.json`:
```json
{
  "id": "tt-zork-and-more",
  "name": "tt-zork-and-more",
  "description": "A Tenstorrent fork of Infocom's Zork I (and more!), running a Z-machine interpreter at least four different ways on TT hardware. The most fun you can have with an AI accelerator.",
  "affiliation": "affiliated",
  "categories": ["games-demos"],
  "tags": ["zork", "z-machine", "interactive-fiction", "demo", "fun"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tt-zork-and-more" }
  ],
  "featured": true,
  "author": "tsingletaryTT",
  "language": "Python"
}
```

`entries/tensix-viz.json`:
```json
{
  "id": "tensix-viz",
  "name": "tensix-viz",
  "description": "Hardware topology visualizer for Tenstorrent chips — from individual chip to full cluster. Interactive JavaScript visualization of Tensix core layout and NoC connections.",
  "affiliation": "affiliated",
  "categories": ["dev-tools"],
  "tags": ["visualization", "topology", "noc", "hardware"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tensix-viz" }
  ],
  "hardware": ["wormhole", "blackhole"],
  "featured": true,
  "author": "tsingletaryTT",
  "language": "JavaScript"
}
```

`entries/tt-forge-compiletron.json`:
```json
{
  "id": "tt-forge-compiletron",
  "name": "tt-forge-compiletron",
  "description": "Compile more than 100 models on tt-forge in a display format suitable for demos. Comprehensive showcase of tt-forge model compatibility.",
  "affiliation": "affiliated",
  "categories": ["compilers", "games-demos"],
  "tags": ["tt-forge", "models", "demo", "compilation"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tt-forge-compiletron" }
  ],
  "author": "tsingletaryTT",
  "language": "Python"
}
```

`entries/tt-model-runner.json`:
```json
{
  "id": "tt-model-runner",
  "name": "tt-model-runner",
  "description": "Discover, load, and benchmark models with a GUI and TUI for tt-inference-server. Makes exploring available models on Tenstorrent hardware as easy as browsing a catalog.",
  "affiliation": "affiliated",
  "categories": ["dev-tools", "ai-models"],
  "tags": ["gui", "tui", "models", "inference", "benchmark"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tt-model-runner" }
  ],
  "hardware": ["wormhole", "blackhole", "quietbox"],
  "author": "tsingletaryTT",
  "language": "Python"
}
```

`entries/tt-qb-lights.json`:
```json
{
  "id": "tt-qb-lights",
  "name": "tt-qb-lights",
  "description": "Sync your Tenstorrent Quietbox's RGB lighting to accelerator utilization status. Visual feedback for hardware activity in real time.",
  "affiliation": "affiliated",
  "categories": ["hw-system", "games-demos"],
  "tags": ["quietbox", "rgb", "hardware", "fun"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tt-qb-lights" }
  ],
  "hardware": ["quietbox"],
  "author": "tsingletaryTT",
  "language": "Rust"
}
```

`entries/tt-jukebox.json`:
```json
{
  "id": "tt-jukebox",
  "name": "tt-jukebox",
  "description": "Play models on Tenstorrent hardware as easily as choosing songs on a jukebox. Simple model selection and playback interface.",
  "affiliation": "affiliated",
  "categories": ["ai-models", "dev-tools"],
  "tags": ["models", "inference", "ux", "jukebox"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tt-jukebox" }
  ],
  "hardware": ["wormhole", "blackhole"],
  "author": "tsingletaryTT",
  "language": "Python"
}
```

`entries/tt-warp.json`:
```json
{
  "id": "tt-warp",
  "name": "tt-warp",
  "description": "Warp terminal plugin for Tenstorrent — integrates hardware status, model management, and developer workflows directly into the Warp terminal.",
  "affiliation": "affiliated",
  "categories": ["dev-tools"],
  "tags": ["warp", "terminal", "plugin", "developer-experience"],
  "links": [
    { "type": "repo", "url": "https://github.com/tsingletaryTT/tt-warp" }
  ],
  "author": "tsingletaryTT",
  "language": "Python"
}
```

- [ ] **Step 3: Write affiliated entries — zoecarver**

`entries/tt-lang-models.json`:
```json
{
  "id": "tt-lang-models",
  "name": "tt-lang-models",
  "description": "A growing collection of models that use tt-lang for some or all of their implementation. Reference implementations for bringing modern models to the tt-lang DSL.",
  "affiliation": "affiliated",
  "categories": ["ai-models", "kernels"],
  "tags": ["tt-lang", "models", "dsl", "reference"],
  "links": [
    { "type": "repo", "url": "https://github.com/zoecarver/tt-lang-models" }
  ],
  "author": "zoecarver",
  "language": "Python"
}
```

`entries/open-oasis.json`:
```json
{
  "id": "open-oasis",
  "name": "open-oasis",
  "description": "tt-lang inference script for Oasis 500M — an interactive video world model running on Tenstorrent hardware via the tt-lang DSL.",
  "affiliation": "affiliated",
  "categories": ["ai-models"],
  "tags": ["video", "world-model", "oasis", "tt-lang", "inference"],
  "links": [
    { "type": "repo", "url": "https://github.com/zoecarver/open-oasis" }
  ],
  "hardware": ["blackhole"],
  "author": "zoecarver",
  "language": "Python"
}
```

`entries/dflash.json`:
```json
{
  "id": "dflash",
  "name": "dflash",
  "description": "DFlash: Block Diffusion for Flash Speculative Decoding on Tenstorrent hardware using tt-lang. Combines block diffusion with speculative decoding for faster inference.",
  "affiliation": "affiliated",
  "categories": ["ai-models", "kernels"],
  "tags": ["speculative-decoding", "diffusion", "tt-lang", "inference"],
  "links": [
    { "type": "repo", "url": "https://github.com/zoecarver/dflash" }
  ],
  "author": "zoecarver",
  "language": "Python"
}
```

`entries/diamond-tt.json`:
```json
{
  "id": "diamond-tt",
  "name": "diamond",
  "description": "DIAMOND: Atari game-playing agent implemented on Tenstorrent hardware via tt-lang. Diffusion-based world model for reinforcement learning.",
  "affiliation": "affiliated",
  "categories": ["ai-models", "games-demos"],
  "tags": ["atari", "reinforcement-learning", "world-model", "tt-lang"],
  "links": [
    { "type": "repo", "url": "https://github.com/zoecarver/diamond" }
  ],
  "author": "zoecarver",
  "language": "Python"
}
```

`entries/gemma4-tt.json`:
```json
{
  "id": "gemma4-tt",
  "name": "gemma4",
  "description": "Gemma 4 language model implemented in tt-lang (e4b variant) for direct execution on Tenstorrent hardware.",
  "affiliation": "affiliated",
  "categories": ["ai-models"],
  "tags": ["gemma", "llm", "tt-lang", "inference"],
  "links": [
    { "type": "repo", "url": "https://github.com/zoecarver/gemma4" }
  ],
  "hardware": ["blackhole"],
  "author": "zoecarver",
  "language": "Python"
}
```

`entries/engram-tt.json`:
```json
{
  "id": "engram-tt",
  "name": "Engram",
  "description": "A Tenstorrent port of the DeepSeek Engram model using tt-lang. Brings DeepSeek's memory-efficient architecture to TT hardware.",
  "affiliation": "affiliated",
  "categories": ["ai-models"],
  "tags": ["deepseek", "engram", "tt-lang", "inference"],
  "links": [
    { "type": "repo", "url": "https://github.com/zoecarver/Engram" }
  ],
  "hardware": ["blackhole"],
  "author": "zoecarver",
  "language": "Python"
}
```

- [ ] **Step 4: Validate all entries written so far**

```bash
python3 scripts/validate.py
```

Expected: all OK, no errors.

- [ ] **Step 5: Commit**

```bash
git add entries/
git commit -m "feat: add community and affiliated entries (22 entries)"
```

---

## Task 10: Research papers + blog posts

**Files:** More `entries/*.json`

- [ ] **Step 1: Write research paper entries**

`entries/paper-fft-wormhole.json`:
```json
{
  "id": "paper-fft-wormhole",
  "name": "Exploring Fast Fourier Transforms on the Tenstorrent Wormhole",
  "description": "Ports the Cooley-Tukey FFT algorithm to the Wormhole n300 RISC-V accelerator. The Wormhole draws 8× less power and consumes 2.8× less energy than a 24-core Xeon Platinum for a 2D FFT. ISC 2025.",
  "affiliation": "community",
  "categories": ["research", "kernels"],
  "tags": ["fft", "wormhole", "hpc", "risc-v", "energy-efficiency", "epcc"],
  "links": [
    { "type": "paper", "url": "https://arxiv.org/abs/2506.15437", "label": "arXiv:2506.15437" },
    { "type": "article", "url": "https://www.research.ed.ac.uk/en/publications/exploring-fast-fourier-transforms-on-the-tenstorrent-wormhole/", "label": "University of Edinburgh" }
  ],
  "hardware": ["wormhole"],
  "author": "Nick Brown, Jake Davies, Felix LeClair"
}
```

`entries/paper-nbody-wormhole.json`:
```json
{
  "id": "paper-nbody-wormhole",
  "name": "Accelerating Gravitational N-Body Simulations on Tenstorrent Wormhole",
  "description": "Accelerates an astrophysical N-body simulation on the Wormhole n300. Achieves 2× speedup and 2× energy savings over a highly optimized CPU implementation. SC '25 Workshop.",
  "affiliation": "community",
  "categories": ["research"],
  "tags": ["n-body", "astrophysics", "hpc", "wormhole", "risc-v", "simulation"],
  "links": [
    { "type": "paper", "url": "https://arxiv.org/abs/2509.19294", "label": "arXiv:2509.19294" },
    { "type": "article", "url": "https://dl.acm.org/doi/10.1145/3731599.3767528", "label": "ACM SC '25" }
  ],
  "hardware": ["wormhole"]
}
```

`entries/paper-numerical-kernels-wormhole.json`:
```json
{
  "id": "paper-numerical-kernels-wormhole",
  "name": "Numerical Kernels on a Spatial Accelerator: Tenstorrent Wormhole",
  "description": "Implements three numerical kernels and composes them into a conjugate gradient solver on Wormhole. Demonstrates AI accelerators merit consideration for HPC workloads traditionally dominated by CPUs and GPUs. 2026.",
  "affiliation": "community",
  "categories": ["research"],
  "tags": ["numerical-methods", "hpc", "conjugate-gradient", "wormhole", "sparse"],
  "links": [
    { "type": "paper", "url": "https://arxiv.org/abs/2603.23343", "label": "arXiv:2603.23343" }
  ],
  "hardware": ["wormhole"]
}
```

`entries/paper-stencils-grayskull.json`:
```json
{
  "id": "paper-stencils-grayskull",
  "name": "Accelerating Stencils on the Tenstorrent Grayskull RISC-V Accelerator",
  "description": "Explores stencil computation on the Grayskull PCIe RISC-V accelerator. Early academic work examining TT hardware for HPC stencil workloads. 2024.",
  "affiliation": "community",
  "categories": ["research"],
  "tags": ["stencil", "hpc", "grayskull", "risc-v"],
  "links": [
    { "type": "paper", "url": "https://arxiv.org/abs/2409.18835", "label": "arXiv:2409.18835" }
  ],
  "hardware": ["grayskull"]
}
```

`entries/paper-swiftnpu.json`:
```json
{
  "id": "paper-swiftnpu",
  "name": "SwiftNPU: Scalable Shape-Flexible Allocation for Inter-Core Connected NPUs",
  "description": "Makes multi-tenant NPU sharing practical for Blackhole-class hardware using polynomial-time allocation algorithms. Delivers up to 1.37× higher utilization and 1.14× faster workload completion. Up to 890,000× faster than NP-hard baselines.",
  "affiliation": "community",
  "categories": ["research", "hw-system"],
  "tags": ["multi-tenant", "allocation", "blackhole", "npu", "scheduling"],
  "links": [
    { "type": "paper", "url": "https://dl.acm.org/doi/10.1145/3805621.3807614", "label": "ACM DL" }
  ],
  "hardware": ["blackhole"]
}
```

`entries/paper-sapienza-allreduce.json`:
```json
{
  "id": "paper-sapienza-allreduce",
  "name": "Collective Operations on Wormhole n150 (Sapienza University of Rome)",
  "description": "Master's thesis implementing and benchmarking five allreduce algorithms (Swing, Recursive Doubling, Bandwidth Optimal, Latency Optimal, Shared Memory) on the Wormhole n150. Bandwidth Optimal achieved best performance, approaching within 2× of theoretical optimal.",
  "affiliation": "community",
  "categories": ["research"],
  "tags": ["allreduce", "collective-ops", "wormhole", "mpi", "bandwidth"],
  "links": [
    { "type": "repo", "url": "https://github.com/EngineerCharlie/TenstorrentAllreduce" }
  ],
  "hardware": ["wormhole"],
  "author": "Charles Heron (Sapienza University of Rome)"
}
```

- [ ] **Step 2: Write blog post entries**

`entries/blog-martin-chang-grayskull.json`:
```json
{
  "id": "blog-martin-chang-grayskull",
  "name": "Thoughts and Logs After Messing with Tenstorrent Grayskull",
  "description": "Honest field notes from getting a Grayskull card running and writing first Metalium kernels. Covers setup pitfalls, processor hangs, memory protection quirks, and what makes Metalium compelling despite early rough edges.",
  "affiliation": "community",
  "categories": ["guides"],
  "tags": ["grayskull", "metalium", "getting-started", "blog", "honest-review"],
  "links": [
    { "type": "article", "url": "https://clehaxze.tw/gemlog/2024/06-02-thoughts-and-logs-after-messing-with-tenstorrent-grayskull.gmi", "label": "clehaxze.tw — June 2024" }
  ],
  "hardware": ["grayskull"],
  "author": "Martin Chang"
}
```

`entries/blog-martin-chang-arch-linux.json`:
```json
{
  "id": "blog-martin-chang-arch-linux",
  "name": "A Gentle Guide: Tenstorrent Card on Arch Linux with Metalium",
  "description": "Step-by-step guide to getting a Tenstorrent card running on Arch Linux with the full Metalium stack. Practical troubleshooting from someone who did it the hard way first.",
  "affiliation": "community",
  "categories": ["guides"],
  "tags": ["arch-linux", "metalium", "installation", "blog", "getting-started"],
  "links": [
    { "type": "article", "url": "https://clehaxze.tw/gemlog/2024/07-07-a-gentle-guide-on-getting-your-tenstorrent-card-running-on-arch-linux-with-the-metalium-stack.gmi", "label": "clehaxze.tw — July 2024" }
  ],
  "hardware": ["grayskull", "wormhole"],
  "author": "Martin Chang"
}
```

`entries/blog-martin-chang-programming.json`:
```json
{
  "id": "blog-martin-chang-programming",
  "name": "Programming Tenstorrent Processors",
  "description": "Deep-dive into the Tenstorrent architecture and Metalium programming model — circular buffers, kernel synchronization, NoC routing, and where the footguns are. The honest guide to thinking in Tensix.",
  "affiliation": "community",
  "categories": ["guides", "kernels"],
  "tags": ["metalium", "programming-model", "tensix", "noc", "circular-buffers", "blog"],
  "links": [
    { "type": "article", "url": "https://clehaxze.tw/gemlog/2025/04-21-programming-tensotrrent-processors.gmi", "label": "clehaxze.tw — April 2025" }
  ],
  "hardware": ["wormhole", "blackhole"],
  "featured": true,
  "author": "Martin Chang"
}
```

- [ ] **Step 3: Validate + commit**

```bash
python3 scripts/validate.py
git add entries/
git commit -m "feat: add research papers and community blog posts (9 entries)"
```

---

## Task 11: Official Tenstorrent org entries

**Files:** More `entries/*.json`

- [ ] **Step 1: Write core SDK and compiler entries**

`entries/tt-metal.json`:
```json
{
  "id": "tt-metal",
  "name": "tt-metal",
  "description": "TT-NN operator library and TT-Metalium low-level kernel programming model. The primary SDK for developing on Tenstorrent hardware — from high-level tensor ops to bare-metal RISC-V kernels.",
  "affiliation": "official",
  "categories": ["kernels", "compilers"],
  "tags": ["metalium", "ttnn", "sdk", "kernels", "core"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-metal" }],
  "hardware": ["grayskull", "wormhole", "blackhole", "ttsim"],
  "language": "C++", "license": "Apache-2.0"
}
```

`entries/tt-forge.json`:
```json
{
  "id": "tt-forge",
  "name": "tt-forge",
  "description": "Tenstorrent's MLIR-based compiler frontend. Enables running AI workloads from PyTorch, ONNX, and other frameworks on all Tenstorrent hardware configurations through an open-source, general, and performant compiler.",
  "affiliation": "official",
  "categories": ["compilers"],
  "tags": ["mlir", "compiler", "pytorch", "onnx", "frontend"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-forge" },
    { "type": "website", "url": "https://tenstorrent.com" }
  ],
  "hardware": ["wormhole", "blackhole", "ttsim"],
  "language": "JavaScript", "license": "Apache-2.0"
}
```

`entries/tt-mlir.json`:
```json
{
  "id": "tt-mlir",
  "name": "tt-mlir",
  "description": "Tenstorrent MLIR compiler — the core compiler infrastructure shared by tt-forge and other frontends. Handles graph optimization, lowering, and code generation for Tensix hardware.",
  "affiliation": "official",
  "categories": ["compilers"],
  "tags": ["mlir", "compiler", "backend", "optimization"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-mlir" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "MLIR", "license": "Apache-2.0"
}
```

`entries/tt-lang.json`:
```json
{
  "id": "tt-lang",
  "name": "tt-lang",
  "description": "Python-based domain-specific language for authoring custom operations on Tenstorrent hardware. Expresses concurrent compute and data-movement programs that compile directly to Tensix kernels.",
  "affiliation": "official",
  "categories": ["kernels"],
  "tags": ["dsl", "python", "kernels", "tt-lang"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-lang" },
    { "type": "lesson", "url": "https://docs.tenstorrent.com/tt-vscode-toolkit/lessons", "label": "Introduction to tt-lang (VSCode Toolkit)" }
  ],
  "hardware": ["wormhole", "blackhole", "ttsim"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-xla.json`:
```json
{
  "id": "tt-xla",
  "name": "tt-xla",
  "description": "PJRT device plugin for Tenstorrent hardware. Enables JAX, PyTorch/XLA, and other XLA-based frameworks to target TT accelerators.",
  "affiliation": "official",
  "categories": ["compilers"],
  "tags": ["xla", "pjrt", "jax", "pytorch"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-xla" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-torch.json`:
```json
{
  "id": "tt-torch",
  "name": "tt-torch",
  "description": "Frontend integration for PyTorch with tt-mlir. Compile PyTorch models directly to Tenstorrent hardware via torch.compile integration.",
  "affiliation": "official",
  "categories": ["compilers"],
  "tags": ["pytorch", "torch-compile", "frontend"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-torch" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-tvm.json`:
```json
{
  "id": "tt-tvm",
  "name": "tt-tvm",
  "description": "TVM for Tenstorrent ASICs. Brings the Apache TVM compiler stack to Tenstorrent hardware, enabling model compilation from TensorFlow, PyTorch, ONNX, and more.",
  "affiliation": "official",
  "categories": ["compilers"],
  "tags": ["tvm", "compiler", "tensorflow", "onnx"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-tvm" }],
  "hardware": ["grayskull", "wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

- [ ] **Step 2: Write inference + serving entries**

`entries/tt-inference-server.json`:
```json
{
  "id": "tt-inference-server",
  "name": "tt-inference-server",
  "description": "Production-ready model serving for Tenstorrent hardware with OpenAI-compatible REST API. Supports continuous batching, multiple models, and all TT hardware configurations.",
  "affiliation": "official",
  "categories": ["ai-models", "cloud-infra"],
  "tags": ["serving", "openai-compatible", "production", "rest-api"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-inference-server" },
    { "type": "lesson", "url": "https://docs.tenstorrent.com/tt-vscode-toolkit/lessons", "label": "Production Inference lesson (VSCode Toolkit)" }
  ],
  "hardware": ["wormhole", "blackhole", "quietbox", "galaxy"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-studio.json`:
```json
{
  "id": "tt-studio",
  "name": "TT-Studio",
  "description": "Web-based GUI for deploying and chatting with AI models on Tenstorrent hardware. Handles all technical setup automatically — deploy models, run inference, and explore capabilities through a simple browser interface.",
  "affiliation": "official",
  "categories": ["ai-models", "dev-tools"],
  "tags": ["web-ui", "gui", "models", "chat", "deployment"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-studio" }],
  "hardware": ["wormhole", "blackhole", "quietbox"],
  "language": "TypeScript", "license": "Apache-2.0"
}
```

`entries/tt-blacksmith.json`:
```json
{
  "id": "tt-blacksmith",
  "name": "tt-blacksmith",
  "description": "Optimized training recipes for a variety of ML models on Tenstorrent hardware, powered by the TT-Forge compiler stack. Reference implementations for fine-tuning and training from scratch.",
  "affiliation": "official",
  "categories": ["ai-models"],
  "tags": ["training", "fine-tuning", "recipes", "pytorch"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-blacksmith" },
    { "type": "lesson", "url": "https://docs.tenstorrent.com/tt-vscode-toolkit/lessons", "label": "Custom Training lessons (VSCode Toolkit)" }
  ],
  "hardware": ["wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-buda.json`:
```json
{
  "id": "tt-buda",
  "name": "tt-buda",
  "description": "TT-BUDA: Tenstorrent's original Python compiler and runtime for AI workloads. Legacy stack — tt-forge is the recommended successor, but tt-buda has the largest model demo library.",
  "affiliation": "official",
  "categories": ["compilers"],
  "tags": ["legacy", "compiler", "pytorch", "buda"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-buda" }
  ],
  "hardware": ["grayskull", "wormhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-buda-demos.json`:
```json
{
  "id": "tt-buda-demos",
  "name": "tt-buda-demos",
  "description": "Repository of model demos using TT-Buda. The largest collection of pre-compiled model examples for Tenstorrent hardware — BERT, ResNet, YOLO, GPT-2, Whisper, and many more.",
  "affiliation": "official",
  "categories": ["ai-models"],
  "tags": ["demos", "models", "bert", "resnet", "yolo", "gpt2"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-buda-demos" }],
  "hardware": ["grayskull", "wormhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-example-apps.json`:
```json
{
  "id": "tt-example-apps",
  "name": "tt-example-apps",
  "description": "End-to-end AI applications running on Tenstorrent AI accelerators. Complete application examples from retrieval-augmented generation to image generation pipelines.",
  "affiliation": "official",
  "categories": ["ai-models", "agents"],
  "tags": ["rag", "applications", "end-to-end", "examples"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-example-apps" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "Jupyter Notebook", "license": "Apache-2.0"
}
```

`entries/tt-local-generator.json`:
```json
{
  "id": "tt-local-generator",
  "name": "tt-local-generator",
  "description": "Generate infinite videos and images (and imaginative prompts to inspire them) on Tenstorrent's Quietbox 2. Fully local generative media pipeline.",
  "affiliation": "official",
  "categories": ["ai-models"],
  "tags": ["video-generation", "image-generation", "quietbox", "generative"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-local-generator" }],
  "hardware": ["quietbox"],
  "language": "Python", "license": "Apache-2.0"
}
```

- [ ] **Step 3: Write hardware + system entries**

`entries/tt-smi.json`:
```json
{
  "id": "tt-smi",
  "name": "tt-smi",
  "description": "Tenstorrent System Management Interface — monitor device telemetry, issue board-level resets, and inspect hardware health. The nvidia-smi equivalent for Tenstorrent hardware.",
  "affiliation": "official",
  "categories": ["hw-system", "dev-tools"],
  "tags": ["monitoring", "telemetry", "smi", "hardware-management"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-smi" }],
  "hardware": ["grayskull", "wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-toplike.json`:
```json
{
  "id": "tt-toplike",
  "name": "tt-toplike",
  "description": "A vibrant htop-style visualizer for Tenstorrent hardware written in Rust. Real-time process and utilization view for TT accelerators.",
  "affiliation": "official",
  "categories": ["hw-system", "dev-tools"],
  "tags": ["monitoring", "htop", "rust", "real-time"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-toplike" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "Rust", "license": "Apache-2.0"
}
```

`entries/tt-kmd.json`:
```json
{
  "id": "tt-kmd",
  "name": "tt-kmd",
  "description": "Tenstorrent kernel module driver. The Linux kernel module required to interface with Tenstorrent PCIe accelerator cards.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["kernel-module", "driver", "linux", "pcie"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-kmd" }],
  "hardware": ["grayskull", "wormhole", "blackhole"],
  "language": "C", "license": "GPL-2.0"
}
```

`entries/tt-umd.json`:
```json
{
  "id": "tt-umd",
  "name": "tt-umd",
  "description": "User-mode driver for Tenstorrent hardware. The userspace layer that sits between the kernel module and higher-level SDKs.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["user-mode-driver", "umd", "hardware-interface"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-umd" }],
  "hardware": ["grayskull", "wormhole", "blackhole"],
  "language": "C++", "license": "Apache-2.0"
}
```

`entries/luwen.json`:
```json
{
  "id": "luwen",
  "name": "luwen",
  "description": "Tenstorrent system interface library written in Rust. Low-level Rust bindings for communicating with and managing TT hardware.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["rust", "system-interface", "low-level", "bindings"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/luwen" }],
  "hardware": ["grayskull", "wormhole", "blackhole"],
  "language": "Rust", "license": "Apache-2.0"
}
```

`entries/tt-firmware.json`:
```json
{
  "id": "tt-firmware",
  "name": "tt-firmware",
  "description": "Tenstorrent firmware repository. Board management and control firmware for Tenstorrent accelerator cards.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["firmware", "bmc", "board-management"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-firmware" }],
  "hardware": ["wormhole", "blackhole"],
  "license": "Apache-2.0"
}
```

`entries/tt-system-firmware.json`:
```json
{
  "id": "tt-system-firmware",
  "name": "tt-system-firmware",
  "description": "System firmware for Tenstorrent hardware. Low-level system initialization and control firmware that runs on-device.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["firmware", "system", "embedded"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-system-firmware" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "C", "license": "Apache-2.0"
}
```

`entries/wallabmc.json`:
```json
{
  "id": "wallabmc",
  "name": "WallaBMC",
  "description": "Lightweight BMC (Baseboard Management Controller) for STM32 and similar MCUs, with Web UI, Redfish API, and HTTPS support. Built on Zephyr RTOS. Used in Tenstorrent systems.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["bmc", "stm32", "redfish", "zephyr", "embedded"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/wallabmc" }],
  "language": "C", "license": "Apache-2.0"
}
```

`entries/tt-flash.json`:
```json
{
  "id": "tt-flash",
  "name": "tt-flash",
  "description": "Tenstorrent firmware update utility. Flash new firmware onto Tenstorrent accelerator cards from the command line.",
  "affiliation": "official",
  "categories": ["hw-system"],
  "tags": ["firmware-update", "flash", "utility"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-flash" }],
  "hardware": ["grayskull", "wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-topology.json`:
```json
{
  "id": "tt-topology",
  "name": "tt-topology",
  "description": "Configure Ethernet routing on multi-card Tenstorrent systems. Flash NB cards to use specific ETH routing configurations for scale-out deployments.",
  "affiliation": "official",
  "categories": ["hw-system", "cloud-infra"],
  "tags": ["topology", "ethernet", "multi-card", "routing"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-topology" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-installer.json`:
```json
{
  "id": "tt-installer",
  "name": "tt-installer",
  "description": "Install the complete Tenstorrent software stack with one command. Handles drivers, firmware, Python environment, and SDK setup automatically.",
  "affiliation": "official",
  "categories": ["hw-system", "guides"],
  "tags": ["installation", "setup", "one-command", "getting-started"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-installer" },
    { "type": "lesson", "url": "https://docs.tenstorrent.com/tt-vscode-toolkit/lessons", "label": "Modern Setup lesson (VSCode Toolkit)" }
  ],
  "hardware": ["wormhole", "blackhole"],
  "language": "Shell", "license": "Apache-2.0"
}
```

- [ ] **Step 4: Write dev tools + debugging entries**

`entries/ttnn-visualizer.json`:
```json
{
  "id": "ttnn-visualizer",
  "name": "ttnn-visualizer",
  "description": "Comprehensive tool for visualizing and analyzing model execution on Tenstorrent hardware. Interactive graphs, memory plots, tensor details, buffer overviews, operation flow graphs, and multi-instance support.",
  "affiliation": "official",
  "categories": ["dev-tools"],
  "tags": ["visualization", "profiling", "memory", "operations", "graphs"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/ttnn-visualizer" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "TypeScript", "license": "Apache-2.0"
}
```

`entries/tt-exalens.json`:
```json
{
  "id": "tt-exalens",
  "name": "tt-exalens",
  "description": "Low-level hardware debugger for Tenstorrent devices. Inspect register state, memory contents, and kernel execution at the hardware level.",
  "affiliation": "official",
  "categories": ["dev-tools"],
  "tags": ["debugger", "low-level", "hardware", "registers"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-exalens" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/tt-npe.json`:
```json
{
  "id": "tt-npe",
  "name": "tt-npe",
  "description": "Network-on-chip Performance Estimator for Tenstorrent Tensix-based devices. Model and estimate NoC utilization before running kernels on hardware.",
  "affiliation": "official",
  "categories": ["dev-tools"],
  "tags": ["noc", "performance", "estimator", "profiling"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-npe" }],
  "hardware": ["wormhole", "blackhole"],
  "language": "C++", "license": "Apache-2.0"
}
```

`entries/tt-vscode-toolkit.json`:
```json
{
  "id": "tt-vscode-toolkit",
  "name": "tt-vscode-toolkit",
  "description": "48 interactive lessons covering the full Tenstorrent developer path — from hardware detection to custom training — with click-to-run commands and hardware auto-detection. Available in VSCode and code-server.",
  "affiliation": "official",
  "categories": ["guides", "dev-tools"],
  "tags": ["vscode", "lessons", "interactive", "getting-started", "code-server"],
  "links": [
    { "type": "repo", "url": "https://github.com/tenstorrent/tt-vscode-toolkit" },
    { "type": "lesson", "url": "https://docs.tenstorrent.com/tt-vscode-toolkit/lessons", "label": "All 48 lessons" }
  ],
  "hardware": ["wormhole", "blackhole", "quietbox", "ttsim"],
  "language": "TypeScript", "license": "Apache-2.0"
}
```

- [ ] **Step 5: Write RISC-V + simulation entries**

`entries/ttsim.json`:
```json
{
  "id": "ttsim",
  "name": "ttsim",
  "description": "Fast full-system simulator of Tenstorrent Wormhole and Blackhole hardware. Runs TT-Metalium workloads on any Linux/x86_64 system without physical silicon. Bit-exact results relative to hardware.",
  "affiliation": "official",
  "categories": ["riscv-arch", "dev-tools"],
  "tags": ["simulator", "no-hardware", "bit-exact", "wormhole", "blackhole"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/ttsim" }],
  "hardware": ["ttsim"],
  "language": "N/A", "license": "Apache-2.0"
}
```

`entries/tt-bh-linux.json`:
```json
{
  "id": "tt-bh-linux",
  "name": "tt-bh-linux",
  "description": "Linux demo for the Tenstorrent Blackhole P100/P150 card RISC-V cores. Boot a real Linux kernel on the 16 high-performance RISC-V cores built into the Blackhole chip.",
  "affiliation": "official",
  "categories": ["riscv-arch"],
  "tags": ["linux", "risc-v", "blackhole", "bare-metal", "boot"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tt-bh-linux" }],
  "hardware": ["blackhole"],
  "featured": true,
  "language": "C", "license": "GPL-2.0"
}
```

`entries/riscv-ocelot.json`:
```json
{
  "id": "riscv-ocelot",
  "name": "riscv-ocelot",
  "description": "The Berkeley Out-of-Order Machine with V-EXT (RISC-V Vector Extension) support. Tenstorrent's research-grade out-of-order RISC-V core with vector extension.",
  "affiliation": "official",
  "categories": ["riscv-arch"],
  "tags": ["risc-v", "out-of-order", "vector-extension", "processor-design"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/riscv-ocelot" }],
  "language": "SystemVerilog", "license": "Apache-2.0"
}
```

`entries/riescue.json`:
```json
{
  "id": "riescue",
  "name": "RiESCUE",
  "description": "RISC-V Directed Test Framework and Compliance Suite. Comprehensive test infrastructure for verifying RISC-V processor implementations against the specification.",
  "affiliation": "official",
  "categories": ["riscv-arch"],
  "tags": ["risc-v", "testing", "compliance", "verification"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/riescue" }],
  "language": "Python", "license": "Apache-2.0"
}
```

`entries/whisper-iss.json`:
```json
{
  "id": "whisper-iss",
  "name": "whisper",
  "description": "RISC-V Instruction Set Simulator (ISS) used by Tenstorrent for processor verification. Powers the co-simulation architecture checker.",
  "affiliation": "official",
  "categories": ["riscv-arch"],
  "tags": ["risc-v", "iss", "simulator", "verification"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/whisper" }],
  "language": "C++", "license": "Apache-2.0"
}
```

`entries/tensix-isa-simulator.json`:
```json
{
  "id": "tensix-isa-simulator",
  "name": "tensix-isa-simulator",
  "description": "ISA-level simulator for the Tensix compute engine. Simulates the matrix, vector, and scalar units inside each Tensix core.",
  "affiliation": "official",
  "categories": ["riscv-arch", "dev-tools"],
  "tags": ["tensix", "isa", "simulator", "compute-engine"],
  "links": [{ "type": "repo", "url": "https://github.com/tenstorrent/tensix-isa-simulator" }],
  "hardware": ["ttsim"],
  "language": "C++", "license": "Apache-2.0"
}
```

- [ ] **Step 6: Validate all entries**

```bash
python3 scripts/validate.py
```

Expected: All entries OK, 0 errors.

- [ ] **Step 7: Run generate_readme.py and inspect output**

```bash
python3 scripts/generate_readme.py
head -60 README.md
```

Expected: README with community entries at the top of each section.

- [ ] **Step 8: Rebuild Eleventy and verify entry count**

```bash
npm run build
grep -c "entry-row" _site/index.html
```

Expected: count matches total number of entries written.

- [ ] **Step 9: Commit**

```bash
git add entries/ README.md
git commit -m "feat: add official TT org entries (28 entries, total ~50)"
```

---

## Task 12: CONTRIBUTING.md + final wiring

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Write `CONTRIBUTING.md`**

```markdown
# Contributing to Awesome Tenstorrent

Thanks for helping grow this list! There are two ways to add an entry.

---

## Option 1 — Interactive CLI (easiest)

```bash
python3 scripts/add_entry.py
```

Follow the prompts. The script writes `entries/<id>.json`, validates it inline, and prints the git commands to open a PR.

---

## Option 2 — Write the JSON directly

Create `entries/<id>.json` where `<id>` is a kebab-case slug matching the project name:

```json
{
  "id": "your-project",
  "name": "your-project",
  "description": "One to three sentences. What does it do, and why does it matter for TT hardware?",
  "affiliation": "community",
  "categories": ["ai-models"],
  "links": [
    { "type": "repo", "url": "https://github.com/you/your-project" }
  ]
}
```

See the [full schema](docs/superpowers/specs/2026-05-08-awesome-tenstorrent-design.md#json-entry-schema) for all fields.

### Validate locally

```bash
python3 scripts/validate.py
```

---

## Affiliation policy

| Value | When to use |
|---|---|
| `community` | Your project — you're not a Tenstorrent employee |
| `affiliated` | You work at Tenstorrent and this is your personal project |
| `official` | The project lives in the `tenstorrent` GitHub org |

Community entries appear **first** in every category. That's by design — this list celebrates the ecosystem, not the company.

---

## Opening a PR

1. Fork this repo
2. Add your entry to `entries/`
3. Run `python3 scripts/validate.py` — fix any errors
4. Open a PR with title `feat: add <project-name>`

CI will validate automatically. On merge, the README and website update within minutes.

---

## Link types

| Type | Use for |
|---|---|
| `repo` | GitHub / GitLab / source code |
| `article` | Blog posts, write-ups |
| `talk` | Conference talks, presentations |
| `video` | YouTube, recorded demos |
| `paper` | arXiv, ACM, IEEE |
| `lesson` | tt-vscode-toolkit lessons |
| `demo` | Live demos, playgrounds |
| `website` | Project homepage |
```

- [ ] **Step 2: Run full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Final build check**

```bash
npm run build 2>&1 | tail -3
```

Expected: Eleventy reports success, no template errors.

- [ ] **Step 4: Run generate_readme.py one final time**

```bash
python3 scripts/generate_readme.py
```

- [ ] **Step 5: Commit everything**

```bash
git add CONTRIBUTING.md README.md
git commit -m "feat: add CONTRIBUTING.md and final README generation"
```

- [ ] **Step 6: Push branch and open PR**

```bash
git push -u origin list-some-awesome
gh pr create \
  --title "feat: awesome-tenstorrent full system — JSON database, generated README, Eleventy three-pane site" \
  --body "$(cat <<'EOF'
## Summary
- `entries/*.json` as single source of truth (~50 initial entries)
- `scripts/validate.py` with full test suite
- `scripts/generate_readme.py` — idempotent README generation, community-first
- `scripts/add_entry.py` — interactive CLI for new entries
- `scripts/fetch_github_meta.py` — nightly star count refresh
- Eleventy three-pane website: sidebar / list / detail, Tenstorrent dark theme
- Client-side search + affiliation filter chips
- GitHub Actions: validate on PR, deploy on merge, nightly metadata refresh

## Test plan
- [ ] `python3 -m pytest tests/ -v` passes
- [ ] `python3 scripts/validate.py` passes on all entries
- [ ] `npm run build` succeeds
- [ ] Open `_site/index.html` — three panes render, sidebar works, click an entry shows detail
- [ ] Search filters list in real-time
- [ ] Community entries appear above official entries in every category
EOF
)"
```
