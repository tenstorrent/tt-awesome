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
    if data.get("affiliation") and data.get("affiliation") not in VALID_AFFILIATIONS:
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
        if eid is None:
            continue
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
