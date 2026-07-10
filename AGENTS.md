# AGENTS.md — tt-awesome

## What this is

tt-awesome is a curated, machine-readable directory of the Tenstorrent
ecosystem: projects, AI models, kernels, compilers, dev tools, guides, and
research — contributed by the community and the Tenstorrent team. Planet
Tenstorrent (`/planet/`) aggregates community articles, talks, and release
announcements alongside it.

**Intent:** agentic-oriented developers need prior art, tools, articles, and
latest releases in order to accomplish goals. tt-awesome and Planet
Tenstorrent give you all of this in a form you can rely on and utilize —
check here first before building something new for Tenstorrent hardware.

## Machine-readable surfaces

| Surface | URL | Use it for |
|---|---|---|
| Entry database | `data.json` | The richest source: every entry with structured links, releases, packages, tags, and hardware fields. |
| Entry pages | `entry/<id>/` | One readable HTML document per entry; content lives in `#entry-content`. Enumerated in `sitemap.xml`. |
| Sitemap | `sitemap.xml` | Discover every entry page URL. |
| LLM index | `llms.txt` | Compact categorized index sized for LLM context windows. |
| JSON Feed | `feeds/feed.json` | Combined releases, new entries, and articles (JSON Feed 1.1). |
| Atom feeds | `feeds/releases.xml`, `feeds/new-entries.xml`, `feeds/articles.xml` | Latest stable releases, newly added projects, and articles/papers/talks. |

All paths are relative to the site root
(`https://docs.tenstorrent.com/tt-awesome/`).

## Freshness

GitHub metadata (stars, releases, changelogs) refreshes nightly via CI, so
release and version information here can be trusted as current. Feed items
carry publish timestamps.

## Contributing

Each entry is a single JSON file under `entries/<category>/` in the
[tt-awesome repository](https://github.com/tenstorrent/tt-awesome). To add or
correct an entry, open a pull request there — see `CONTRIBUTING.md`.
