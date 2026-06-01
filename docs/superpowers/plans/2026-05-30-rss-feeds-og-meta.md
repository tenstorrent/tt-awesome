# RSS Feeds & Open Graph Meta Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Atom + JSON Feed syndication feeds and improved Open Graph/Twitter/JSON-LD meta tags to the tt-awesome Eleventy site, backed by a git-blame backfill of `added_at` dates on all 106 existing entries.

**Architecture:** Eleventy Nunjucks templates in `src/feeds/` output XML and JSON feed files during `npm run build`. A one-time Python script backfills `added_at` from git history into every entry JSON. The existing `recentReleases.js` data layer feeds the releases Atom feed without modification; `added_at` is used for new-entries and articles feeds. `base.njk` gains richer OG tags, `summary_large_image` Twitter card, a static social card image, feed autodiscovery `<link>` tags, and a JSON-LD `WebSite` block.

**Tech Stack:** Eleventy 3 (11ty), Nunjucks templates, Python 3, git CLI (for backfill), no new npm dependencies.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `scripts/backfill_added_at.py` | Create | One-time: write `added_at` to all entry JSONs via git blame |
| `scripts/validate.py` | Modify | Soft-warn on missing `added_at`; validate format |
| `scripts/add_entry.py` | Modify | Auto-populate `added_at` = today on new entries |
| `src/feeds/releases.njk` | Create | Atom 1.0 feed for recent releases |
| `src/feeds/new-entries.njk` | Create | Atom 1.0 feed for entries sorted by `added_at` |
| `src/feeds/articles.njk` | Create | Atom 1.0 feed for article-type links |
| `src/feeds/feed.njk` | Create | JSON Feed 1.1 combined feed |
| `src/assets/og-card.svg` | Create | 1200×630 social card (SVG, committed asset) |
| `src/_includes/base.njk` | Modify | Richer OG/Twitter, JSON-LD, feed autodiscovery |
| `tests/test_backfill.py` | Create | Tests for backfill script |
| `tests/test_validate_added_at.py` | Create | Tests for new validate.py warning |

---

## Task 1: Backfill script — write failing tests

**Files:**
- Create: `tests/test_backfill.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_backfill.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import backfill_added_at as baa


def test_parse_git_date_extracts_date():
    assert baa.parse_git_date("2026-05-08 16:24:50 -0700") == "2026-05-08"


def test_parse_git_date_returns_none_for_empty():
    assert baa.parse_git_date("") is None
    assert baa.parse_git_date(None) is None


def test_get_added_date_calls_git(tmp_path):
    fake_file = tmp_path / "test-entry.json"
    fake_file.write_text("{}")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="2026-03-15 10:00:00 -0800\n", returncode=0
        )
        result = baa.get_added_date(fake_file)
    assert result == "2026-03-15"
    args = mock_run.call_args[0][0]
    assert "git" in args[0]
    assert "--diff-filter=A" in args


def test_get_added_date_returns_none_when_git_empty(tmp_path):
    fake_file = tmp_path / "test-entry.json"
    fake_file.write_text("{}")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = baa.get_added_date(fake_file)
    assert result is None


def test_backfill_writes_added_at(tmp_path):
    entry = {"id": "my-entry", "name": "My Entry"}
    f = tmp_path / "my-entry.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date", return_value="2026-01-10"):
        updated, skipped = baa.backfill_entries([f])
    data = json.loads(f.read_text())
    assert data["added_at"] == "2026-01-10"
    assert updated == 1
    assert skipped == 0


def test_backfill_skips_existing_added_at(tmp_path):
    entry = {"id": "my-entry", "added_at": "2025-12-01"}
    f = tmp_path / "my-entry.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date") as mock_get:
        updated, skipped = baa.backfill_entries([f])
    mock_get.assert_not_called()
    assert updated == 0
    assert skipped == 1


def test_backfill_skips_when_git_returns_nothing(tmp_path):
    entry = {"id": "my-entry"}
    f = tmp_path / "my-entry.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date", return_value=None):
        updated, skipped = baa.backfill_entries([f])
    data = json.loads(f.read_text())
    assert "added_at" not in data
    assert updated == 0
    assert skipped == 1


def test_backfill_preserves_field_order(tmp_path):
    entry = {"id": "x", "name": "X", "description": "Desc", "affiliation": "official"}
    f = tmp_path / "x.json"
    f.write_text(json.dumps(entry, indent=2))
    with patch("backfill_added_at.get_added_date", return_value="2026-02-01"):
        baa.backfill_entries([f])
    result = json.loads(f.read_text())
    keys = list(result.keys())
    # added_at should appear — we don't mandate position but all original keys survive
    assert set(keys) == {"id", "name", "description", "affiliation", "added_at"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 -m pytest tests/test_backfill.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backfill_added_at'`

---

## Task 2: Backfill script — implementation

**Files:**
- Create: `scripts/backfill_added_at.py`

- [ ] **Step 1: Write the implementation**

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""One-time script: backfill added_at from git history into all entry JSON files.

Usage:
    python3 scripts/backfill_added_at.py [--dry-run]

For each entry JSON under entries/ that does not already have added_at, runs
  git log --follow --diff-filter=A --format="%ai" -- <file>
to find the commit date when the file was first added, then writes
  "added_at": "YYYY-MM-DD"
into the JSON. Files that already have the field, or for which git returns
nothing (untracked), are skipped with a warning.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"


def parse_git_date(output: str) -> str | None:
    """Extract YYYY-MM-DD from a git %ai date string like '2026-05-08 16:24:50 -0700'."""
    if not output or not output.strip():
        return None
    return output.strip().split()[0]


def get_added_date(path: Path) -> str | None:
    """Return the YYYY-MM-DD date when path was first committed, or None."""
    result = subprocess.run(
        ["git", "log", "--follow", "--diff-filter=A", "--format=%ai", "--", str(path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return parse_git_date(result.stdout)


def backfill_entries(files: list, dry_run: bool = False) -> tuple[int, int]:
    """Backfill added_at on each file. Returns (updated_count, skipped_count)."""
    updated = skipped = 0
    for f in files:
        data = json.loads(f.read_text())
        if "added_at" in data:
            skipped += 1
            continue
        date = get_added_date(f)
        if date is None:
            print(f"  SKIP (no git history): {f.name}", file=sys.stderr)
            skipped += 1
            continue
        data["added_at"] = date
        if not dry_run:
            f.write_text(json.dumps(data, indent=2) + "\n")
        updated += 1
    return updated, skipped


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("DRY RUN — no files will be modified\n")

    files = sorted(ENTRIES_DIR.rglob("*.json"))
    if not files:
        print("No entry JSON files found.")
        sys.exit(0)

    print(f"Processing {len(files)} entries…")
    updated, skipped = backfill_entries(files, dry_run=dry_run)
    print(f"\nDone. Updated: {updated}  Skipped: {skipped}")
    if dry_run and updated:
        print("(dry run — no writes performed)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the tests and verify they pass**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 -m pytest tests/test_backfill.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 3: Run a dry-run against real entries**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 scripts/backfill_added_at.py --dry-run
```

Expected output ends with `Updated: 106  Skipped: 0` (or similar — any skips with warnings for files git doesn't know about).

- [ ] **Step 4: Commit**

```bash
git add scripts/backfill_added_at.py tests/test_backfill.py
git commit -m "feat: add backfill_added_at script with tests"
```

---

## Task 3: Run the backfill for real

**Files:**
- Modify: `entries/**/*.json` (adds `added_at` field to all 106 files)

- [ ] **Step 1: Run the backfill**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 scripts/backfill_added_at.py
```

Expected: `Updated: 106  Skipped: 0` (any SKIP lines are for untracked files — acceptable).

- [ ] **Step 2: Spot-check a few entries**

```bash
python3 -c "
import json, glob
for f in list(sorted(glob.glob('entries/**/*.json', recursive=True)))[:5]:
    d = json.load(open(f))
    print(f, d.get('added_at', 'MISSING'))
"
```

Expected: Each shows a `YYYY-MM-DD` date.

- [ ] **Step 3: Confirm no entry has invalid added_at format**

```bash
python3 -c "
import json, glob, re
bad = []
for f in glob.glob('entries/**/*.json', recursive=True):
    d = json.load(open(f))
    v = d.get('added_at','')
    if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
        bad.append((f, v))
print('Bad dates:', bad if bad else 'none')
"
```

Expected: `Bad dates: none`

- [ ] **Step 4: Commit**

```bash
git add entries/
git commit -m "chore: backfill added_at from git history on all entries"
```

---

## Task 4: Update validate.py — warn on missing added_at

**Files:**
- Modify: `scripts/validate.py`
- Create: `tests/test_validate_added_at.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate_added_at.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate import validate_entry, validate_entry_warnings


def p(stem="test-entry"):
    return Path(f"/fake/entries/{stem}.json")


def valid():
    return {
        "id": "test-entry",
        "name": "Test Entry",
        "description": "A test.",
        "affiliation": "community",
        "categories": ["ai-models"],
        "links": [{"type": "repo", "url": "https://github.com/foo/bar"}],
        "added_at": "2026-01-01",
    }


def test_no_warning_when_added_at_present():
    warnings = validate_entry_warnings(p(), valid())
    assert not any("added_at" in w for w in warnings)


def test_warns_when_added_at_missing():
    e = valid()
    del e["added_at"]
    warnings = validate_entry_warnings(p(), e)
    assert any("added_at" in w for w in warnings)


def test_error_when_added_at_invalid_format():
    errors = validate_entry(p(), valid({"added_at": "01/01/2026"}))
    assert any("added_at" in e for e in errors)


def test_error_when_added_at_not_string():
    errors = validate_entry(p(), valid({"added_at": 20260101}))
    assert any("added_at" in e for e in errors)
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 -m pytest tests/test_validate_added_at.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'validate_entry_warnings'`

- [ ] **Step 3: Add validate_entry_warnings and added_at validation to validate.py**

In `validate.py`, after the existing `validate_entry` function, add:

```python
def validate_entry_warnings(path: Path, data: dict) -> list:
    """Return soft warnings (non-fatal) for an entry."""
    warnings = []
    if not data.get("added_at"):
        warnings.append("missing added_at (run scripts/backfill_added_at.py)")
    return warnings
```

Also, inside the existing `validate_entry` function, after the existing `"date"` check block (around line 88), add:

```python
    # added_at: optional ISO 8601 date string (YYYY-MM-DD) — when the entry was first listed
    if "added_at" in data:
        if not isinstance(data["added_at"], str) or not DATE_RE.match(data["added_at"]):
            errors.append(f"added_at must be a YYYY-MM-DD string, got '{data.get('added_at')}'")
```

In the `main()` function, after the `if errors:` block, add the warnings printout. Replace the existing `main()` body loop logic. The full updated loop looks like:

```python
    all_ids, total_errors, total_warnings = [], 0, 0
    for fpath in json_files:
        try:
            data = json.loads(fpath.read_text())
        except json.JSONDecodeError as e:
            print(f"FAIL {fpath.name}: invalid JSON — {e}")
            total_errors += 1
            continue
        errors = validate_entry(fpath, data)
        warnings = validate_entry_warnings(fpath, data)
        all_ids.append(data.get("id"))
        if errors:
            print(f"FAIL {fpath.name}:")
            for e in errors:
                print(f"  - {e}")
            total_errors += len(errors)
        elif warnings:
            print(f"  WARN {fpath.name}:")
            for w in warnings:
                print(f"    ~ {w}")
            total_warnings += len(warnings)
        else:
            print(f"  OK {fpath.name}")
```

Also update the final summary lines in `main()`:

```python
    seen = set()
    for eid in all_ids:
        if eid is None:
            continue
        if eid in seen:
            print(f"FAIL: duplicate id '{eid}'")
            total_errors += 1
        seen.add(eid)
    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        sys.exit(1)
    if total_warnings:
        print(f"\nAll {len(json_files)} entries valid ({total_warnings} warning(s)).")
    else:
        print(f"\nAll {len(json_files)} entries valid.")
```

- [ ] **Step 4: Run the tests and verify they pass**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 -m pytest tests/test_validate_added_at.py tests/test_validate.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Run validate against real entries (should show all OK now)**

```bash
python3 scripts/validate.py 2>&1 | tail -5
```

Expected: `All 106 entries valid.` (no warnings, since backfill ran in Task 3).

- [ ] **Step 6: Commit**

```bash
git add scripts/validate.py tests/test_validate_added_at.py
git commit -m "feat: add validate_entry_warnings and added_at validation"
```

---

## Task 5: Update add_entry.py — auto-populate added_at

**Files:**
- Modify: `scripts/add_entry.py`

- [ ] **Step 1: Add `import datetime` at the top of add_entry.py**

At line 5, after the existing imports block, add:

```python
import datetime
```

- [ ] **Step 2: Add added_at to the entry dict in main()**

In `add_entry.py` `main()`, in the `entry = { ... }` block (around line 106), add `added_at` after the initial fields:

```python
    entry = {
        "id": entry_id, "name": name, "description": description,
        "affiliation": affiliation, "categories": categories, "links": links,
        "added_at": datetime.date.today().isoformat(),
    }
```

- [ ] **Step 3: Verify the change manually**

```bash
python3 -c "
import datetime, json
# Simulate what add_entry.py now produces
entry = {
    'id': 'test', 'name': 'Test', 'description': 'Desc',
    'affiliation': 'community', 'categories': ['ai-models'],
    'links': [{'type': 'repo', 'url': 'https://github.com/x/y'}],
    'added_at': datetime.date.today().isoformat(),
}
print(entry['added_at'])
"
```

Expected: today's date in `YYYY-MM-DD` format.

- [ ] **Step 4: Commit**

```bash
git add scripts/add_entry.py
git commit -m "feat: auto-populate added_at in add_entry.py"
```

---

## Task 6: Releases Atom feed template

**Files:**
- Create: `src/feeds/releases.njk`

The `recentReleases` data collection (already in `src/_data/recentReleases.js`) provides: `entryId`, `entryName`, `affiliation`, `tagName`, `publishedAt`, `url`, `repoUrl`.

- [ ] **Step 1: Create src/feeds/releases.njk**

```xml
---
permalink: /feeds/releases.xml
eleventyExcludeFromCollections: true
---
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>tt-awesome — Recent Releases</title>
  <subtitle>Latest stable releases from Tenstorrent ecosystem projects</subtitle>
  <link href="https://tenstorrent.github.io/tt-awesome/feeds/releases.xml" rel="self"/>
  <link href="https://tenstorrent.github.io/tt-awesome/"/>
  <id>https://tenstorrent.github.io/tt-awesome/feeds/releases.xml</id>
  <updated>{{ recentReleases[0].publishedAt if recentReleases.length else "1970-01-01T00:00:00Z" }}</updated>
  {%- for rel in recentReleases %}
  <entry>
    <id>{{ rel.url }}</id>
    <title>{{ rel.entryName }} {{ rel.tagName }}</title>
    <link href="{{ rel.url }}"/>
    <updated>{{ rel.publishedAt }}</updated>
    <summary>{{ rel.entryName }} released {{ rel.tagName }}. Repository: {{ rel.repoUrl }}</summary>
    <category term="{{ rel.affiliation }}"/>
    <category term="release"/>
  </entry>
  {%- endfor %}
</feed>
```

- [ ] **Step 2: Build and verify the file is generated**

```bash
cd /Users/tsingletary/code/tt-awesome
npm run build 2>&1 | tail -5
cat _site/feeds/releases.xml | head -20
```

Expected: Valid XML starting with `<?xml version="1.0"` and at least one `<entry>` block.

- [ ] **Step 3: Validate well-formed XML**

```bash
python3 -c "
import xml.etree.ElementTree as ET
ET.parse('_site/feeds/releases.xml')
print('releases.xml is well-formed XML')
"
```

Expected: `releases.xml is well-formed XML`

- [ ] **Step 4: Commit**

```bash
git add src/feeds/releases.njk
git commit -m "feat: add Atom feed for recent releases"
```

---

## Task 7: New Entries Atom feed template

**Files:**
- Create: `src/feeds/new-entries.njk`

The `entries` data collection (from `src/_data/entries.js`) is available. Each entry has: `id`, `name`, `description`, `categories`, `affiliation`, `added_at` (after backfill), `links` (with `type` and `url`).

- [ ] **Step 1: Create src/feeds/new-entries.njk**

```xml
---
permalink: /feeds/new-entries.xml
eleventyExcludeFromCollections: true
---
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>tt-awesome — New Entries</title>
  <subtitle>Newly added projects, tools, and resources in the Tenstorrent ecosystem</subtitle>
  <link href="https://tenstorrent.github.io/tt-awesome/feeds/new-entries.xml" rel="self"/>
  <link href="https://tenstorrent.github.io/tt-awesome/"/>
  <id>https://tenstorrent.github.io/tt-awesome/feeds/new-entries.xml</id>
  {%- set sortedEntries = entries | sort(true, false, "added_at") | first(50) %}
  <updated>{{ sortedEntries[0].added_at + "T00:00:00Z" if sortedEntries.length else "1970-01-01T00:00:00Z" }}</updated>
  {%- for entry in sortedEntries %}
  {%- set repoLink = entry.links | selectattr("type", "equalto", "repo") | first %}
  <entry>
    <id>{{ repoLink.url if repoLink else "https://tenstorrent.github.io/tt-awesome/#" + entry.id }}</id>
    <title>{{ entry.name }}</title>
    <link href="{{ repoLink.url if repoLink else "https://tenstorrent.github.io/tt-awesome/" }}"/>
    <updated>{{ entry.added_at + "T00:00:00Z" if entry.added_at else "1970-01-01T00:00:00Z" }}</updated>
    <summary>{{ entry.description }}</summary>
    <category term="{{ entry.affiliation }}"/>
    {%- for cat in entry.categories %}
    <category term="{{ cat }}"/>
    {%- endfor %}
  </entry>
  {%- endfor %}
</feed>
```

- [ ] **Step 2: Build and verify**

```bash
cd /Users/tsingletary/code/tt-awesome
npm run build 2>&1 | tail -5
cat _site/feeds/new-entries.xml | head -25
```

Expected: Valid XML with `<entry>` blocks containing `<title>` and `<updated>` with `T00:00:00Z` timestamps.

- [ ] **Step 3: Validate well-formed XML**

```bash
python3 -c "
import xml.etree.ElementTree as ET
ET.parse('_site/feeds/new-entries.xml')
print('new-entries.xml is well-formed XML')
"
```

Expected: `new-entries.xml is well-formed XML`

- [ ] **Step 4: Check entry count is capped at 50**

```bash
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('_site/feeds/new-entries.xml')
ns = {'atom': 'http://www.w3.org/2005/Atom'}
entries = tree.findall('atom:entry', ns)
print(f'Entry count: {len(entries)} (should be <= 50)')
assert len(entries) <= 50
"
```

- [ ] **Step 5: Commit**

```bash
git add src/feeds/new-entries.njk
git commit -m "feat: add Atom feed for new entries"
```

---

## Task 8: Articles Atom feed template

**Files:**
- Create: `src/feeds/articles.njk`

Article link types: `article`, `lesson`, `paper`, `talk`, `video`, `demo`. This feed collects all such links across all entries, deduplicates by URL, and sorts by parent entry's `added_at` (entries without `added_at` sort last, using entry position as tiebreaker).

Nunjucks lacks a built-in dedup filter, so deduplication is handled via a macro-style accumulation approach using a namespace object (Nunjucks scoping workaround).

- [ ] **Step 1: Create src/feeds/articles.njk**

```xml
---
permalink: /feeds/articles.xml
eleventyExcludeFromCollections: true
---
<?xml version="1.0" encoding="utf-8"?>
{%- set articleTypes = ["article", "lesson", "paper", "talk", "video", "demo"] %}
{%- set ns = namespace(seen=[], items=[]) %}
{%- set sortedByDate = entries | sort(true, false, "added_at") %}
{%- for entry in sortedByDate %}
  {%- for link in entry.links %}
    {%- if link.type in articleTypes and link.url not in ns.seen %}
      {%- set ns.seen = ns.seen.concat([link.url]) %}
      {%- set ns.items = ns.items.concat([{
        "entryId": entry.id,
        "entryName": entry.name,
        "entryDesc": entry.description,
        "affiliation": entry.affiliation,
        "categories": entry.categories,
        "linkType": link.type,
        "linkUrl": link.url,
        "linkLabel": link.label if link.label else (link.type | title),
        "added_at": entry.added_at if entry.added_at else "1970-01-01"
      }]) %}
    {%- endif %}
  {%- endfor %}
{%- endfor %}
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>tt-awesome — Articles &amp; Resources</title>
  <subtitle>Articles, papers, lessons, talks, videos, and demos from the Tenstorrent ecosystem</subtitle>
  <link href="https://tenstorrent.github.io/tt-awesome/feeds/articles.xml" rel="self"/>
  <link href="https://tenstorrent.github.io/tt-awesome/"/>
  <id>https://tenstorrent.github.io/tt-awesome/feeds/articles.xml</id>
  <updated>{{ ns.items[0].added_at + "T00:00:00Z" if ns.items.length else "1970-01-01T00:00:00Z" }}</updated>
  {%- for item in ns.items | first(50) %}
  <entry>
    <id>{{ item.linkUrl }}</id>
    <title>{{ item.entryName }} — {{ item.linkLabel }}</title>
    <link href="{{ item.linkUrl }}"/>
    <updated>{{ item.added_at + "T00:00:00Z" }}</updated>
    <summary>{{ item.entryDesc }}</summary>
    <category term="{{ item.linkType }}"/>
    <category term="{{ item.affiliation }}"/>
    {%- for cat in item.categories %}
    <category term="{{ cat }}"/>
    {%- endfor %}
  </entry>
  {%- endfor %}
</feed>
```

- [ ] **Step 2: Build and verify**

```bash
cd /Users/tsingletary/code/tt-awesome
npm run build 2>&1 | tail -5
cat _site/feeds/articles.xml | head -30
```

Expected: Valid XML with `<entry>` blocks. No duplicate `<id>` values.

- [ ] **Step 3: Validate well-formed XML and check for duplicate IDs**

```bash
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('_site/feeds/articles.xml')
ns = {'atom': 'http://www.w3.org/2005/Atom'}
ids = [e.find('atom:id', ns).text for e in tree.findall('atom:entry', ns)]
dupes = [i for i in ids if ids.count(i) > 1]
print(f'Entries: {len(ids)}, Dupes: {len(dupes)}')
assert not dupes, f'Duplicate IDs: {dupes}'
print('articles.xml is well-formed with no duplicate IDs')
"
```

- [ ] **Step 4: Commit**

```bash
git add src/feeds/articles.njk
git commit -m "feat: add Atom feed for articles and resources"
```

---

## Task 9: JSON Feed 1.1 combined feed

**Files:**
- Create: `src/feeds/feed.njk`

JSON Feed 1.1 spec: https://www.jsonfeed.org/version/1.1/. Each item needs: `id`, `url`, `title`, `summary`, `date_published` (RFC 3339), `tags`.

- [ ] **Step 1: Create src/feeds/feed.njk**

```json
---
permalink: /feeds/feed.json
eleventyExcludeFromCollections: true
---
{%- set articleTypes = ["article", "lesson", "paper", "talk", "video", "demo"] %}
{%- set ns = namespace(items=[]) %}

{%- for rel in recentReleases %}
{%- set ns.items = ns.items.concat([{
  "id": rel.url,
  "url": rel.url,
  "title": rel.entryName + " " + rel.tagName,
  "summary": rel.entryName + " released " + rel.tagName + ". Repository: " + rel.repoUrl,
  "date_published": rel.publishedAt,
  "tags": [rel.affiliation, "release"]
}]) %}
{%- endfor %}

{%- set seenUrls = namespace(seen=[]) %}
{%- set sortedEntries = entries | sort(true, false, "added_at") %}
{%- for entry in sortedEntries | first(50) %}
{%- set repoLink = entry.links | selectattr("type", "equalto", "repo") | first %}
{%- set entryUrl = repoLink.url if repoLink else "https://tenstorrent.github.io/tt-awesome/#" + entry.id %}
{%- set ns.items = ns.items.concat([{
  "id": entryUrl,
  "url": entryUrl,
  "title": entry.name,
  "summary": entry.description,
  "date_published": (entry.added_at + "T00:00:00Z") if entry.added_at else "1970-01-01T00:00:00Z",
  "tags": entry.categories.concat([entry.affiliation, "entry"])
}]) %}
{%- for link in entry.links %}
  {%- if link.type in articleTypes and link.url not in seenUrls.seen %}
    {%- set seenUrls.seen = seenUrls.seen.concat([link.url]) %}
    {%- set ns.items = ns.items.concat([{
      "id": link.url,
      "url": link.url,
      "title": entry.name + " — " + (link.label if link.label else (link.type | title)),
      "summary": entry.description,
      "date_published": (entry.added_at + "T00:00:00Z") if entry.added_at else "1970-01-01T00:00:00Z",
      "tags": entry.categories.concat([entry.affiliation, link.type, "article"])
    }]) %}
  {%- endif %}
{%- endfor %}
{%- endfor %}
{{ {
  "version": "https://jsonfeed.org/version/1.1",
  "title": "tt-awesome",
  "home_page_url": "https://tenstorrent.github.io/tt-awesome/",
  "feed_url": "https://tenstorrent.github.io/tt-awesome/feeds/feed.json",
  "description": "Projects, releases, articles, and resources from the Tenstorrent ecosystem",
  "icon": "https://tenstorrent.github.io/tt-awesome/assets/og-card.png",
  "items": ns.items
} | dump(2) }}
```

- [ ] **Step 2: Build and verify valid JSON**

```bash
cd /Users/tsingletary/code/tt-awesome
npm run build 2>&1 | tail -5
python3 -c "
import json
d = json.load(open('_site/feeds/feed.json'))
print('version:', d['version'])
print('item count:', len(d['items']))
first = d['items'][0]
print('first item keys:', list(first.keys()))
assert all(k in first for k in ['id','url','title','summary','date_published','tags'])
print('JSON Feed is valid')
"
```

Expected: `version: https://jsonfeed.org/version/1.1` and item count > 0.

- [ ] **Step 3: Commit**

```bash
git add src/feeds/feed.njk
git commit -m "feat: add JSON Feed 1.1 combined feed"
```

---

## Task 10: Social card image

**Files:**
- Create: `src/assets/og-card.svg`

A static SVG social card (1200×630) committed to the repo. GitHub Pages serves it; it's referenced by OG tags. We use SVG so it's text-based (no binary blob) — social crawlers accept SVG for og:image.

- [ ] **Step 1: Create src/assets/og-card.svg**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <rect width="1200" height="630" fill="#0d1117"/>
  <!-- subtle grid lines -->
  <line x1="0" y1="315" x2="1200" y2="315" stroke="#21262d" stroke-width="1"/>
  <line x1="600" y1="0" x2="600" y2="630" stroke="#21262d" stroke-width="1"/>
  <!-- accent bar -->
  <rect x="0" y="0" width="8" height="630" fill="#ff6600"/>
  <!-- logo text -->
  <text x="80" y="260" font-family="ui-monospace,SFMono-Regular,Menlo,monospace"
        font-size="96" font-weight="700" fill="#f0f6fc">⚡ tt-awesome</text>
  <!-- tagline -->
  <text x="80" y="330" font-family="ui-monospace,SFMono-Regular,Menlo,monospace"
        font-size="36" fill="#8b949e">A curated list of Tenstorrent awesomeness</text>
  <!-- sub-tagline -->
  <text x="80" y="390" font-family="ui-monospace,SFMono-Regular,Menlo,monospace"
        font-size="28" fill="#484f58">tenstorrent.github.io/tt-awesome</text>
</svg>
```

- [ ] **Step 2: Verify the file renders in a browser**

Open the file in a browser or check the SVG is well-formed:

```bash
python3 -c "
import xml.etree.ElementTree as ET
ET.parse('src/assets/og-card.svg')
print('SVG is well-formed XML')
"
```

- [ ] **Step 3: Build to confirm it's copied to _site**

```bash
npm run build 2>&1 | tail -3
ls _site/assets/og-card.svg
```

Expected: file exists at `_site/assets/og-card.svg`.

- [ ] **Step 4: Commit**

```bash
git add src/assets/og-card.svg
git commit -m "feat: add og-card.svg social card image"
```

---

## Task 11: Update base.njk — OG tags, Twitter card, JSON-LD, feed autodiscovery

**Files:**
- Modify: `src/_includes/base.njk`

Replace the static `<head>` meta block with a richer version. The `entries` and `categories` globals are available in all 11ty templates.

- [ ] **Step 1: Replace the existing OG/Twitter block in base.njk**

The current block (lines 10–20 of `src/_includes/base.njk`) is:

```html
  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="tt-awesome">
  <meta property="og:title" content="tt-awesome — A curated list of Tenstorrent awesomeness">
  <meta property="og:description" content="Community projects, tools, AI models, research papers, and tutorials for Tenstorrent hardware — curated by the community.">
  <meta property="og:url" content="https://tenstorrent.github.io/tt-awesome/">
  <!-- Twitter / X Card -->
  <meta name="twitter:card" content="summary">
  <meta name="twitter:site" content="@tenstorrent">
  <meta name="twitter:title" content="tt-awesome — A curated list of Tenstorrent awesomeness">
  <meta name="twitter:description" content="Community projects, tools, AI models, research papers, and tutorials for Tenstorrent hardware — curated by the community.">
```

Replace it with:

```html
  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="tt-awesome">
  <meta property="og:title" content="tt-awesome — A curated list of Tenstorrent awesomeness">
  <meta property="og:description" content="Discover {{ entries | length }} projects across {{ categories | length }} categories — tools, AI models, kernels, compilers, and more for Tenstorrent hardware.">
  <meta property="og:url" content="https://tenstorrent.github.io/tt-awesome/">
  <meta property="og:image" content="https://tenstorrent.github.io/tt-awesome/assets/og-card.svg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <!-- Twitter / X Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@tenstorrent">
  <meta name="twitter:title" content="tt-awesome — A curated list of Tenstorrent awesomeness">
  <meta name="twitter:description" content="Discover {{ entries | length }} projects across {{ categories | length }} categories — tools, AI models, kernels, compilers, and more for Tenstorrent hardware.">
  <meta name="twitter:image" content="https://tenstorrent.github.io/tt-awesome/assets/og-card.svg">
  <!-- Feed autodiscovery -->
  <link rel="alternate" type="application/atom+xml" title="tt-awesome — Recent Releases" href="https://tenstorrent.github.io/tt-awesome/feeds/releases.xml">
  <link rel="alternate" type="application/atom+xml" title="tt-awesome — New Entries" href="https://tenstorrent.github.io/tt-awesome/feeds/new-entries.xml">
  <link rel="alternate" type="application/atom+xml" title="tt-awesome — Articles &amp; Resources" href="https://tenstorrent.github.io/tt-awesome/feeds/articles.xml">
  <link rel="alternate" type="application/feed+json" title="tt-awesome — JSON Feed" href="https://tenstorrent.github.io/tt-awesome/feeds/feed.json">
  <!-- Structured data -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "tt-awesome",
    "url": "https://tenstorrent.github.io/tt-awesome/",
    "description": "Discover {{ entries | length }} projects across {{ categories | length }} categories — tools, AI models, kernels, compilers, and more for Tenstorrent hardware.",
    "potentialAction": {
      "@type": "SearchAction",
      "target": "https://tenstorrent.github.io/tt-awesome/?q={search_term_string}",
      "query-input": "required name=search_term_string"
    }
  }
  </script>
```

- [ ] **Step 2: Build and verify the head block**

```bash
cd /Users/tsingletary/code/tt-awesome
npm run build 2>&1 | tail -5
grep -A2 'og:image' _site/index.html
grep 'twitter:card' _site/index.html
grep 'application/atom' _site/index.html | head -4
grep 'application/ld+json' _site/index.html
```

Expected:
- `og:image` tag with `og-card.svg` URL
- `twitter:card` = `summary_large_image`
- Four feed autodiscovery `<link>` tags
- `application/ld+json` script tag present

- [ ] **Step 3: Verify entry count in meta description is not zero**

```bash
python3 -c "
from pathlib import Path
html = Path('_site/index.html').read_text()
import re
m = re.search(r'Discover (\d+) projects across (\d+) categories', html)
assert m, 'Dynamic description not found'
entries, cats = int(m.group(1)), int(m.group(2))
assert entries > 50, f'Expected >50 entries, got {entries}'
assert cats > 5, f'Expected >5 categories, got {cats}'
print(f'OK: {entries} projects, {cats} categories in meta description')
"
```

- [ ] **Step 4: Commit**

```bash
git add src/_includes/base.njk
git commit -m "feat: upgrade OG/Twitter meta tags, add feed autodiscovery and JSON-LD"
```

---

## Task 12: Final build verification

- [ ] **Step 1: Run all Python tests**

```bash
cd /Users/tsingletary/code/tt-awesome
python3 -m pytest tests/ -v --ignore=tests/__pycache__
```

Expected: All tests PASS.

- [ ] **Step 2: Run JS tests**

```bash
node tests/test_data_files.js
```

Expected: `All tests passed ✓`

- [ ] **Step 3: Full build**

```bash
npm run build 2>&1
```

Expected: Build completes with no errors.

- [ ] **Step 4: Verify all four feed files exist**

```bash
ls -lh _site/feeds/
```

Expected: `releases.xml`, `new-entries.xml`, `articles.xml`, `feed.json` all present.

- [ ] **Step 5: Validate all XML feeds are well-formed**

```bash
python3 -c "
import xml.etree.ElementTree as ET
for name in ['releases.xml', 'new-entries.xml', 'articles.xml']:
    ET.parse(f'_site/feeds/{name}')
    print(f'{name}: well-formed')
import json
d = json.load(open('_site/feeds/feed.json'))
assert d['version'] == 'https://jsonfeed.org/version/1.1'
print('feed.json: valid JSON Feed 1.1')
"
```

- [ ] **Step 6: Validate entries (no errors, no warnings)**

```bash
python3 scripts/validate.py 2>&1 | tail -3
```

Expected: `All 106 entries valid.`

- [ ] **Step 7: Commit final verification**

No code changes needed here — just confirm clean state.

```bash
git status
```

Expected: `nothing to commit, working tree clean`
