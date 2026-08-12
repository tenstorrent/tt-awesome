#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Validate all entries in entries/*.json against the schema."""
import json
import re
import sys
from pathlib import Path

VALID_AFFILIATIONS = {"official", "affiliated", "community"}
VALID_CATEGORY_SLUGS = {
    "getting-started",
    "ai-models", "agents", "kernels", "compilers", "dev-tools",
    "hw-system", "cloud-infra", "riscv-arch", "research", "games-demos", "guides", "blogs",
}
VALID_LINK_TYPES = {"repo", "article", "talk", "video", "website", "demo", "lesson", "paper"}
VALID_HARDWARE = {"grayskull", "wormhole", "blackhole", "quietbox", "galaxy", "ttsim"}
VALID_PACKAGE_TYPES = {"pypi", "apt", "cargo"}
URL_RE  = re.compile(r"^https://.+")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_entry(path: Path, data: dict) -> list:
    errors = []
    expected_id = path.stem
    if data.get("id") != expected_id:
        errors.append(f"id '{data.get('id')}' must match filename '{expected_id}'")
    for field in ("id", "name", "description", "affiliation"):
        if not data.get(field) or not isinstance(data[field], str):
            errors.append(f"missing or invalid required field: {field}")
    entry_id = data.get("id")
    if entry_id and isinstance(entry_id, str) and not re.match(r'^[a-z0-9][a-z0-9\-]*$', entry_id):
        errors.append(f"id must be a lowercase slug, got '{entry_id}'")
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
    pkgs = data.get("packages")
    if pkgs is not None:
        if not isinstance(pkgs, list):
            errors.append("packages must be a list")
        else:
            for i, pkg in enumerate(pkgs):
                if not isinstance(pkg, dict):
                    errors.append(f"packages[{i}] must be an object")
                    continue
                if pkg.get("type") not in VALID_PACKAGE_TYPES:
                    errors.append(f"packages[{i}].type must be one of {sorted(VALID_PACKAGE_TYPES)}")
                if not pkg.get("name") or not isinstance(pkg.get("name"), str):
                    errors.append(f"packages[{i}].name must be a non-empty string")
                if "ppa" in pkg and not isinstance(pkg["ppa"], str):
                    errors.append(f"packages[{i}].ppa must be a string")
                if "url" in pkg:
                    if not isinstance(pkg["url"], str) or not URL_RE.match(pkg["url"]):
                        errors.append(f"packages[{i}].url must be a valid https:// URL, got '{pkg.get('url')}'")
    author_url = data.get("author_url")
    if author_url is not None:
        if not isinstance(author_url, str) or not URL_RE.match(author_url):
            errors.append(f"author_url must be a valid https:// URL, got '{author_url}'")
    related = data.get("related")
    if related is not None:
        if not isinstance(related, list):
            errors.append("related must be a list")
        else:
            for i, rel in enumerate(related):
                if not isinstance(rel, str) or not re.match(r'^[a-z0-9][a-z0-9\-]*$', rel):
                    errors.append(f"related[{i}] must be a lowercase slug, got '{rel}'")
    if "tags" in data and not isinstance(data["tags"], list):
        errors.append("tags must be a list")
    if "featured" in data and not isinstance(data["featured"], bool):
        errors.append("featured must be a boolean")
    # home_pinned: optional boolean — when true the entry always gets a home-page
    # showcase slot in the first category card it belongs to (see .eleventy.js)
    if "home_pinned" in data and not isinstance(data["home_pinned"], bool):
        errors.append("home_pinned must be a boolean")
    # hidden: optional boolean — when true the entry is excluded from the README and website
    if "hidden" in data and not isinstance(data["hidden"], bool):
        errors.append("hidden must be a boolean")
    # date: optional ISO 8601 date string (YYYY-MM-DD) — publication / submission date
    if "date" in data:
        if not isinstance(data["date"], str) or not DATE_RE.match(data["date"]):
            errors.append(f"date must be a YYYY-MM-DD string, got '{data.get('date')}'")
    # added_at: optional ISO 8601 date string (YYYY-MM-DD) — when the entry was first listed
    if "added_at" in data:
        if not isinstance(data["added_at"], str) or not DATE_RE.match(data["added_at"]):
            errors.append(f"added_at must be a YYYY-MM-DD string, got '{data.get('added_at')}'")
    return errors


def validate_entry_warnings(path: Path, data: dict) -> list:
    """Return soft warnings (non-fatal) for an entry."""
    warnings = []
    if not data.get("added_at"):
        warnings.append("missing added_at (run scripts/backfill_added_at.py)")
    return warnings


def main():
    entries_dir = Path(__file__).parent.parent / "entries"
    if not entries_dir.is_dir():
        print(f"ERROR: entries/ not found at {entries_dir}")
        sys.exit(1)
    json_files = sorted(entries_dir.rglob("*.json"))
    if not json_files:
        print("No entries found — nothing to validate.")
        sys.exit(0)
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
        if warnings:
            print(f"WARN {fpath.name}:")
            for w in warnings:
                print(f"  ~ {w}")
            total_warnings += len(warnings)
        if not errors and not warnings:
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
    if total_warnings:
        print(f"\nNo errors. {len(json_files)} entries checked ({total_warnings} warning(s)).")
    else:
        print(f"\nAll {len(json_files)} entries valid.")


if __name__ == "__main__":
    main()
