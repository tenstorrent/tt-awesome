#!/usr/bin/env python3
"""
Parse a GitHub issue form submission into an entry JSON file.

Reads ISSUE_BODY, ISSUE_NUMBER, and ISSUE_USER from the environment.
Writes the entry to entries/{primary-category}/{id}.json.
Writes the output path to /tmp/entry_file.txt and the entry name to
/tmp/entry_name.txt so the calling workflow can reference them.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_sections(body: str) -> dict[str, str]:
    """Split a GitHub issue form body into {section_label: raw_value} pairs.

    GitHub renders each form field as:
        ### Field Label
        (blank line)
        value text

    This function splits on '### ' headings and returns a dict where keys
    are the heading text and values are the trimmed content below them.
    """
    sections: dict[str, str] = {}
    # Normalise line endings
    body = body.replace("\r\n", "\n").replace("\r", "\n")

    # Split on lines that start with '### '
    parts = re.split(r"\n(?=### )", "\n" + body)
    for part in parts:
        part = part.strip()
        if not part.startswith("### "):
            continue
        newline_pos = part.find("\n")
        if newline_pos == -1:
            # heading with no content
            heading = part[4:].strip()
            sections[heading] = ""
        else:
            heading = part[4:newline_pos].strip()
            value = part[newline_pos:].strip()
            sections[heading] = value

    return sections


def parse_checkboxes(text: str) -> list[str]:
    """Return the labels of checked items from a markdown checkbox list."""
    checked: list[str] = []
    for line in text.splitlines():
        # Matches both '- [x]' and '- [X]'
        m = re.match(r"-\s*\[x\]\s*(.*)", line, re.IGNORECASE)
        if m:
            checked.append(m.group(1).strip())
    return checked


def is_blank(value: str) -> bool:
    """True if value is empty or the GitHub 'no response' placeholder."""
    return not value or value.strip() in ("", "_No response_")


def slugify(text: str) -> str:
    """Convert a string to a kebab-case identifier suitable for a filename."""
    text = text.lower()
    # Replace non-alphanumeric characters (except hyphens) with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    body = os.environ.get("ISSUE_BODY", "")
    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    issue_user = os.environ.get("ISSUE_USER", "")

    if not body:
        print("ERROR: ISSUE_BODY is empty", file=sys.stderr)
        sys.exit(1)

    sections = parse_sections(body)

    # ------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------
    name = sections.get("Name", "").strip()
    description = sections.get("Description", "").strip()
    affiliation = sections.get("Affiliation", "").strip().lower()
    repo_url = sections.get("Repository URL", "").strip()
    categories_raw = sections.get("Categories", "")

    errors: list[str] = []
    if not name:
        errors.append("Name is required")
    if not description:
        errors.append("Description is required")
    if affiliation not in ("community", "affiliated", "official"):
        errors.append(f"Affiliation must be community/affiliated/official, got: {affiliation!r}")
    if not repo_url or not repo_url.startswith("https://"):
        errors.append(f"Repository URL must be an HTTPS URL, got: {repo_url!r}")

    # ------------------------------------------------------------------
    # Parse categories (checkboxes)
    # ------------------------------------------------------------------
    # Each checked label looks like "ai-models — AI & Models"
    # Extract the slug from the part before ' — '
    category_items = parse_checkboxes(categories_raw)
    categories: list[str] = []
    for item in category_items:
        # Split on em dash (—) or plain dash ( - ) with surrounding spaces
        slug = re.split(r"\s+[—\-]\s+", item)[0].strip()
        if slug:
            categories.append(slug)

    if not categories:
        errors.append("At least one category must be selected")

    if errors:
        print("ERROR: Submission is missing required information:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    primary_category = categories[0]
    entry_id = slugify(name)

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    links: list[dict] = [{"type": "repo", "url": repo_url}]

    extra_raw = sections.get("Additional Links", "")
    if not is_blank(extra_raw):
        for line in extra_raw.splitlines():
            line = line.strip().lstrip("- ").strip()
            if not line or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue
            link_type, link_url = parts[0], parts[1]
            if not link_url.startswith("https://"):
                continue  # skip malformed URLs silently
            link: dict = {"type": link_type, "url": link_url}
            if len(parts) >= 3 and parts[2]:
                link["label"] = parts[2]
            links.append(link)

    # ------------------------------------------------------------------
    # Hardware (checkboxes)
    # ------------------------------------------------------------------
    hardware_raw = sections.get("Hardware", "")
    hardware = parse_checkboxes(hardware_raw)  # labels are already the slugs

    # ------------------------------------------------------------------
    # Optional scalar fields
    # ------------------------------------------------------------------
    tags_raw = sections.get("Tags", "")
    tags: list[str] = []
    if not is_blank(tags_raw):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    author = sections.get("Author", "").strip()
    if is_blank(author):
        # Fall back to the submitter's GitHub username
        author = issue_user

    language = sections.get("Language", "").strip()
    if is_blank(language):
        language = ""

    license_val = sections.get("License", "").strip()
    if is_blank(license_val):
        license_val = ""

    # ------------------------------------------------------------------
    # Build the entry dict (only include optional keys when non-empty)
    # ------------------------------------------------------------------
    entry: dict = {
        "id": entry_id,
        "name": name,
        "description": description,
        "affiliation": affiliation,
        "categories": categories,
        "links": links,
    }

    if tags:
        entry["tags"] = tags
    if hardware:
        entry["hardware"] = hardware
    if author:
        entry["author"] = author
    if language:
        entry["language"] = language
    if license_val:
        entry["license"] = license_val

    # ------------------------------------------------------------------
    # Write entry file
    # ------------------------------------------------------------------
    entry_dir = ROOT / "entries" / primary_category
    entry_dir.mkdir(parents=True, exist_ok=True)
    entry_path = entry_dir / f"{entry_id}.json"

    if entry_path.exists():
        print(
            f"WARNING: {entry_path} already exists — it will be overwritten.",
            file=sys.stderr,
        )

    with entry_path.open("w", encoding="utf-8") as fh:
        json.dump(entry, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"Entry written: {entry_path}")
    print(json.dumps(entry, indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------
    # Signal outputs to the workflow via temp files
    # ------------------------------------------------------------------
    Path("/tmp/entry_file.txt").write_text(str(entry_path.relative_to(ROOT)))
    Path("/tmp/entry_name.txt").write_text(name)


if __name__ == "__main__":
    main()
