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
