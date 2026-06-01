#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Interactive CLI to add a new entry to entries/."""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"

AFFILIATIONS = ["community", "affiliated", "official"]
CATEGORIES = [
    "getting-started",
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
    entry_id = ask("ID (slug)", default=slugify(name))
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
        "added_at": datetime.date.today().isoformat(),
    }
    if hardware:   entry["hardware"] = hardware
    if tags:       entry["tags"] = tags
    if author:     entry["author"] = author
    if language:   entry["language"] = language
    if license_id: entry["license"] = license_id
    if featured:   entry["featured"] = True

    # Write the new entry into a subdirectory named by its first category slug.
    out_dir = ENTRIES_DIR / categories[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{entry_id}.json"
    if dest.exists():
        print(f"ERROR: {dest} already exists.")
        sys.exit(1)
    dest.write_text(json.dumps(entry, indent=2) + "\n")
    print(f"\n✅  Written to {dest}")
    print(f"\nNext steps:")
    print(f"  python3 scripts/validate.py")
    print(f"  git add {dest} && git commit -m 'feat: add {name}'")
    print(f"  gh pr create --title 'Add {name}'")


if __name__ == "__main__":
    main()
