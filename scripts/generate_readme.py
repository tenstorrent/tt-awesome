#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Generate README.md from entries/*.json."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "entries"

CATEGORIES = [
    ("getting-started", "🚀 Getting Started"),
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

# Ordering for affiliation tiers: lower value = higher in the list
# community (0) → affiliated (1) → official (2)
AFFILIATION_ORDER = {"community": 0, "affiliated": 1, "official": 2}

# Icons for each recognized link type
LINK_ICONS = {
    "repo": "📦", "article": "📝", "talk": "🎤", "video": "🎥",
    "website": "🌐", "demo": "🚀", "lesson": "📖", "paper": "📄",
}

# Icons and install commands for package registry types
PKG_ICONS = {"pypi": "🐍", "apt": "🐧", "cargo": "🦀", "conda": "⚗️"}
PKG_INSTALL = {"pypi": "pip install", "apt": "apt install", "cargo": "cargo add",
               "conda": "conda install"}
# Channel assumed when a conda package omits an explicit one.
DEFAULT_CONDA_CHANNEL = "conda-forge"


def pkg_url(pkg):
    """Derive a registry URL for a package entry."""
    t = pkg.get("type")
    name = pkg.get("name", "")
    if t == "pypi":
        return f"https://pypi.org/project/{name}/"
    if t == "cargo":
        return f"https://crates.io/crates/{name}"
    if t == "conda":
        channel = pkg.get("channel") or DEFAULT_CONDA_CHANNEL
        return f"https://anaconda.org/{channel}/{name}"
    if t == "apt":
        ppa = pkg.get("ppa", "")
        if ppa.startswith("ppa:"):
            # ppa:owner/name → https://launchpad.net/~owner/+archive/ubuntu/name
            rest = ppa[4:]
            owner, _, ppa_name = rest.partition("/")
            if ppa_name:
                return f"https://launchpad.net/~{owner}/+archive/ubuntu/{ppa_name}"
        # Archives that aren't Launchpad PPAs (ppa.tenstorrent.com, for one)
        # carry a plain `url` instead. Every apt entry in the list currently
        # uses this form, so without it the README linked none of them.
        if pkg.get("url"):
            return pkg["url"]
    return None

# Shields.io badges for each affiliation tier
SHIELDS = {
    "community": "![community](https://img.shields.io/badge/community-27AE60?style=flat-square)",
    "affiliated": "![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)",
    "official":   "![official](https://img.shields.io/badge/official-607D8B?style=flat-square)",
}


def load_entries():
    """Load all entry JSON files from ENTRIES_DIR, sorted by filename.

    Entries with ``"hidden": true`` are excluded so they remain in the JSON
    database for historical reference but do not appear in the generated README.
    """
    entries = [json.loads(f.read_text()) for f in sorted(ENTRIES_DIR.rglob("*.json"))]
    return [e for e in entries if not e.get("hidden") is True]


def sort_entries(entries):
    """Sort entries with community-first ordering.

    Primary key:   affiliation tier (community < affiliated < official)
    Secondary key: featured flag (featured entries come first within a tier)
    Tertiary key:  star count descending (more stars = higher rank)
    """
    def key(e):
        tier = AFFILIATION_ORDER.get(e.get("affiliation", "community"), 2)
        feat = 0 if e.get("featured") else 1
        return (tier, feat, -(e.get("stars", 0)))
    return sorted(entries, key=key)


def format_author(author_str):
    """Return Markdown for an author field.

    GitHub-style handles (no spaces, alphanumeric / - / _ / .) are linked to
    their GitHub profile.  Full names and multi-person strings are returned as
    plain text so nothing is silently mis-linked.
    """
    if not author_str:
        return None
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_./-]*$', author_str):
        return f"[@{author_str}](https://github.com/{author_str})"
    return author_str


def render_entry(e):
    """Render a single entry as a Markdown list item.

    Produces a block like:
        - **[name](repo_url)** ![badge]
          by [@author](https://github.com/author) — Description text.
          [📦 repo](url) · [🎤 FOSDEM 2026](url)
    """
    name = e["name"]
    desc = e["description"]
    badge = SHIELDS.get(e.get("affiliation", "community"), "")
    links = e.get("links", [])
    author_md = format_author(e.get("author"))

    # Use the first repo link (if any) to hyperlink the project name
    repo = next((l for l in links if l["type"] == "repo"), None)
    name_md = f"[{name}]({repo['url']})" if repo else name

    # Build the inline link list; fall back to generic link icon for unknown types
    link_parts = [
        f"[{LINK_ICONS.get(l['type'], '🔗')} {l.get('label') or l['type']}]({l['url']})"
        for l in links
    ]

    # Build package install links (appended after regular links)
    pkg_parts = []
    for pkg in e.get("packages", []):
        icon = PKG_ICONS.get(pkg.get("type", ""), "📦")
        cmd = f"{PKG_INSTALL.get(pkg.get('type', ''), 'install')} {pkg.get('name', '')}"
        url = pkg_url(pkg)
        pkg_parts.append(f"[{icon} `{cmd}`]({url})" if url else f"{icon} `{cmd}`")

    # Combine author + description on the same line when author is present
    desc_line = f"by {author_md} — {desc}" if author_md else desc

    result = f"- **{name_md}** {badge}\n  {desc_line}"
    all_parts = link_parts + pkg_parts
    if all_parts:
        result += f"\n  {' · '.join(all_parts)}"
    return result


def generate():
    """Build the full README string from all entries."""
    entries = sort_entries(load_entries())

    lines = [
        "# tt-awesome", "",
        "## A hidden dimension of Tenstorrent awesomeness", "",
        "A curated directory of projects, tools, models, and research for Tenstorrent hardware "
        "— contributed by the community and our team.", "",
        "> **This file is auto-generated from `entries/*.json`. Do not edit directly — "
        "[submit an entry via issue](https://github.com/tenstorrent/tt-awesome/issues/new?template=submit-entry.yml) "
        "or see [CONTRIBUTING.md](CONTRIBUTING.md) for other options.**", "",
        "## Contents", "",
    ]

    # Table of contents — only include categories that have at least one entry
    for slug, label in CATEGORIES:
        if any(slug in e.get("categories", []) for e in entries):
            # Derive a GitHub-compatible anchor from the label
            anchor = re.sub(r'[^\w\s-]', '', label.lower()).strip().replace(' ', '-')
            anchor = re.sub(r'-+', '-', anchor)
            lines.append(f"- [{label}](#{anchor})")
    lines.append("")

    # Per-category sections
    for slug, label in CATEGORIES:
        cat_entries = [e for e in entries if e.get("categories", [None])[0] == slug]
        if not cat_entries:
            continue
        lines += [f"## {label}", ""]
        for e in cat_entries:
            lines += [render_entry(e), ""]

    # Feeds & Resources section — hand-authored content kept in generate() so it
    # survives re-generation.  Update this block when feed capabilities change.
    lines += [
        "## Feeds & Resources", "",
        "Subscribe to tt-awesome activity via Atom or JSON Feed:", "",
        "- **[New Entries (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/new-entries.xml)** — "
        "newly added projects and resources.",
        "- **[Articles & Resources (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/articles.xml)** — "
        "articles, papers, lessons, talks, and demos.",
        "- **[Recent Releases (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/releases.xml)** — "
        "latest stable releases. Release items use LLM-generated summaries when available.",
        "- **[JSON Feed](https://tenstorrent.github.io/tt-awesome/feeds/feed.json)** — "
        "combined releases, entries, and articles (JSON Feed 1.1).",
        "- **[data.json](https://tenstorrent.github.io/tt-awesome/data.json)** — "
        "full machine-readable entry database.",
        "- **[llms.txt](https://tenstorrent.github.io/tt-awesome/llms.txt)** — "
        "curated plain-text index for LLM context and AI tooling.", "",
        "Each Atom and JSON Feed item carries both a short `<summary>` and a full rich `<content>` block "
        "containing the project description, all associated links, attribution, and tags — "
        "suitable for feed readers that render HTML content.", "",
    ]

    # Contributing section
    lines += [
        "## Contributing", "",
        "We welcome contributions from the community! Please see [CONTRIBUTING.md](CONTRIBUTING.md) "
        "for guidelines on submitting entries, bug reports, and pull requests.", "",
        "All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).", "",
    ]

    # License section
    lines += [
        "## License", "",
        "- **Code and Software**: Licensed under the [Apache License 2.0](LICENSE), except where specified. "
        "See [LICENSE_understanding.txt](LICENSE_understanding.txt) for clarifications on how this license applies.", "",
        "- **Documentation and Images**: Licensed under [Creative Commons Attribution 4.0 International (CC-BY)](LICENSE-DOCS). "
        "This includes all content in the docs/ directory, README.md content, and generated website output.", "",
    ]

    lines += ["---", "", "*Generated by `scripts/generate_readme.py`.*", ""]
    return "\n".join(lines)


def main():
    """Write the generated README to the repository root."""
    readme = generate()
    out = ROOT / "README.md"
    out.write_text(readme)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
