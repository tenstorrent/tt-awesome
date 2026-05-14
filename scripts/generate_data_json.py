#!/usr/bin/env python3
"""Generate data.json — machine-readable API export of all entries.

Output structure:
  {
    "meta": { generated, schema_version, total_entries, categories },
    "categories": {
      "<slug>": { "label": "...", "count": N, "entries": [...] },
      ...
    }
  }

Each top-level key under "categories" is self-contained so callers can
select only the group(s) they care about and discard the rest.
"""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"

# Category order and display labels (emoji stripped for API cleanliness;
# the HTML site uses its own label from src/_data/categories.js).
CATEGORIES = [
    ("getting-started", "Getting Started"),
    ("ai-models",       "AI & Models"),
    ("agents",          "AI Agents"),
    ("kernels",         "Custom Kernels & Low-Level"),
    ("compilers",       "Compilers & Frontends"),
    ("dev-tools",       "Dev Tools & Debugging"),
    ("hw-system",       "Hardware & System"),
    ("cloud-infra",     "Cloud & Orchestration"),
    ("riscv-arch",      "RISC-V & Architecture"),
    ("research",        "Research & Papers"),
    ("games-demos",     "Games & Demos"),
    ("guides",          "Guides, Tutorials & Education"),
]

# Same tier ordering as generate_readme.py so both outputs are consistent.
AFFILIATION_ORDER = {"community": 0, "affiliated": 1, "official": 2}


def load_entries():
    """Load all non-hidden entries from entries/**/*.json, sorted by filename."""
    entries = [json.loads(f.read_text()) for f in sorted(ENTRIES_DIR.rglob("*.json"))]
    return [e for e in entries if not e.get("hidden") is True]


def sort_entries(entries):
    """Sort community-first, then featured, then by star count descending."""
    def key(e):
        tier = AFFILIATION_ORDER.get(e.get("affiliation", "community"), 2)
        feat = 0 if e.get("featured") else 1
        return (tier, feat, -(e.get("stars", 0)))
    return sorted(entries, key=key)


def generate():
    """Build the full data structure."""
    entries = sort_entries(load_entries())

    categories_out = {}
    for slug, label in CATEGORIES:
        cat_entries = [e for e in entries if slug in e.get("categories", [])]
        if not cat_entries:
            continue
        categories_out[slug] = {
            "label": label,
            "count": len(cat_entries),
            "entries": cat_entries,
        }

    return {
        "meta": {
            # ISO-8601 UTC timestamp so consumers know how fresh the data is.
            "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "1",
            "total_entries": len(entries),
            # Ordered list of category slugs present in this file.
            "categories": [slug for slug, _ in CATEGORIES if slug in categories_out],
        },
        "categories": categories_out,
    }


def main():
    """Write data.json to the repository root."""
    data = generate()
    out = ROOT / "data.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {out}  ({data['meta']['total_entries']} entries, "
          f"{len(data['categories'])} categories)")


if __name__ == "__main__":
    main()
