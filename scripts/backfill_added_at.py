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

JSON is written with ensure_ascii=False to preserve UTF-8 characters (em-dashes,
multiplication signs, accented names, etc.) as literal Unicode rather than \\uXXXX
escape sequences.
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


def _run_git_log_for(path: Path) -> str | None:
    """Run git log --follow --diff-filter=A for a single path; return raw stdout or None on error."""
    result = subprocess.run(
        ["git", "log", "--follow", "--diff-filter=A", "--format=%ai", "--reverse", "--", str(path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        print(f"  WARN: git error for {path.name}: {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout or None


def get_added_date(path: Path) -> str | None:
    """Return the YYYY-MM-DD date when path was first committed, or None.

    For files that were reorganised from a flat entries/<name>.json path into a
    category subdirectory (entries/<category>/<name>.json), git --follow may not
    traverse the rename because the reorganisation was done as a copy rather than
    a tracked rename.  We therefore fall back to checking the legacy flat path
    entries/<basename> when the subdir path yields no history.
    """
    raw = _run_git_log_for(path)
    if raw:
        return parse_git_date(raw)

    # Fallback: check the original flat path entries/<basename> that existed
    # before the category-subdirectory reorganisation commit.
    flat_path = ENTRIES_DIR / path.name
    if flat_path != path:
        raw = _run_git_log_for(flat_path)
        if raw:
            return parse_git_date(raw)

    return None


def backfill_entries(files: list, dry_run: bool = False) -> tuple[int, int]:
    """Backfill added_at on each file. Returns (updated_count, skipped_count)."""
    updated = skipped = 0
    for f in files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            print(f"  SKIP (invalid JSON): {f.name}: {e}", file=sys.stderr)
            skipped += 1
            continue
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
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
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
