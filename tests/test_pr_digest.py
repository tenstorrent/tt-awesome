# tests/test_pr_digest.py
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""Tests for scripts/pr_digest.py — the markdown digest that opens the
automated metadata-refresh PRs.

Every test here is offline: the one LLM call the module makes is either
monkeypatched or exercised through its degradation path, because the digest
must still render when the summarization backend is unreachable.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import pr_digest as pd


# ── Fixtures ────────────────────────────────────────────────────────────────

def rel(title, date, description="Summary text.", **kw):
    """Build a release-shaped planet item."""
    item = {
        "type": "release",
        "title": title,
        "url": f"https://github.com/tenstorrent/{title.split()[0]}/releases/tag/{title.split()[-1]}",
        "description": description,
        "date": date,
        "dateISO": f"{date}T12:00:00Z",
        "projectName": title.split()[0],
        "affiliation": "official",
        "approved": True,
    }
    item.update(kw)
    return item


# ── group_by_project ────────────────────────────────────────────────────────

def test_group_by_project_collapses_same_project():
    items = [
        rel("tt-bio v0.3.0", "2026-08-18"),
        rel("tt-metal v0.77.0", "2026-08-18"),
        rel("tt-bio v0.4.0", "2026-08-19"),
    ]
    groups = pd.group_by_project(items)
    names = [g["project"] for g in groups]
    assert names.count("tt-bio") == 1, "tt-bio's two releases must share one group"
    tt_bio = next(g for g in groups if g["project"] == "tt-bio")
    assert len(tt_bio["items"]) == 2


def test_group_by_project_orders_groups_newest_first():
    items = [
        rel("old-proj v1.0", "2026-08-01"),
        rel("new-proj v2.0", "2026-08-20"),
    ]
    groups = pd.group_by_project(items)
    assert groups[0]["project"] == "new-proj"


def test_group_by_project_orders_items_within_group_oldest_first():
    """Inside a project's group the releases read as a chronological run."""
    items = [
        rel("tt-bio v0.4.0", "2026-08-19"),
        rel("tt-bio v0.3.0", "2026-08-18"),
    ]
    groups = pd.group_by_project(items)
    titles = [i["title"] for i in groups[0]["items"]]
    assert titles == ["tt-bio v0.3.0", "tt-bio v0.4.0"]


def test_group_by_project_falls_back_to_title_when_project_missing():
    """Planet items (talks, papers) may carry no projectName — never crash."""
    items = [{"type": "paper", "title": "A Paper", "date": "2026-08-01",
              "dateISO": "2026-08-01T00:00:00Z", "description": "d",
              "url": "https://arxiv.org/abs/1", "approved": True}]
    groups = pd.group_by_project(items)
    assert groups[0]["project"] == "A Paper"


# ── build_digest ────────────────────────────────────────────────────────────

def test_build_digest_returns_empty_string_for_no_items():
    """No items means the caller keeps its static PR body."""
    assert pd.build_digest([], kind="release", lede="anything") == ""


def test_build_digest_includes_count_heading():
    out = pd.build_digest([rel("tt-bio v0.3.0", "2026-08-18")], kind="release", lede="")
    assert "1 new release" in out


def test_build_digest_pluralizes_count():
    items = [rel("tt-bio v0.3.0", "2026-08-18"), rel("tt-metal v0.77.0", "2026-08-18")]
    out = pd.build_digest(items, kind="release", lede="")
    assert "2 new releases" in out


def test_build_digest_includes_lede_when_present():
    out = pd.build_digest([rel("tt-bio v0.3.0", "2026-08-18")],
                          kind="release", lede="The headline is tt-bio.")
    assert "The headline is tt-bio." in out


def test_build_digest_omits_lede_section_when_lede_empty():
    """A dead summarization backend must not leave an empty paragraph behind."""
    out = pd.build_digest([rel("tt-bio v0.3.0", "2026-08-18")], kind="release", lede="")
    # No blank-line-surrounded empty stretch where the lede would have gone.
    assert "\n\n\n" not in out


def test_build_digest_lists_every_summary():
    items = [
        rel("tt-bio v0.3.0", "2026-08-18", description="First summary here."),
        rel("tt-bio v0.4.0", "2026-08-19", description="Second summary here."),
    ]
    out = pd.build_digest(items, kind="release", lede="")
    assert "First summary here." in out
    assert "Second summary here." in out


def test_build_digest_groups_multiple_releases_under_one_project_heading():
    items = [
        rel("tt-bio v0.3.0", "2026-08-18"),
        rel("tt-bio v0.4.0", "2026-08-19"),
    ]
    out = pd.build_digest(items, kind="release", lede="")
    assert out.count("#### tt-bio") == 1, "one heading per project, not per release"
    assert "v0.3.0" in out and "v0.4.0" in out


def test_build_digest_renders_date_range_for_a_multi_day_run():
    items = [
        rel("tt-bio v0.3.0", "2026-08-18"),
        rel("tt-bio v0.4.0", "2026-08-19"),
    ]
    out = pd.build_digest(items, kind="release", lede="")
    assert "Aug 18–19" in out


def test_build_digest_renders_single_date_when_run_is_same_day():
    items = [rel("tt-bio v0.3.0", "2026-08-18"), rel("tt-bio v0.4.0", "2026-08-18")]
    out = pd.build_digest(items, kind="release", lede="")
    assert "Aug 18" in out
    assert "–" not in out.split("#### tt-bio")[1].splitlines()[0]


def test_build_digest_links_each_item_to_its_url():
    item = rel("tt-bio v0.3.0", "2026-08-18")
    out = pd.build_digest([item], kind="release", lede="")
    assert item["url"] in out


def test_build_digest_flags_items_awaiting_approval():
    """The planet-feeds PR exists to collect approval decisions — surface them."""
    items = [
        rel("tt-bio v0.3.0", "2026-08-18"),
        rel("some-blog Post", "2026-08-18", approved=False),
    ]
    out = pd.build_digest(items, kind="planet", lede="")
    assert "awaiting approval" in out.lower()


def test_build_digest_omits_approval_section_when_all_approved():
    out = pd.build_digest([rel("tt-bio v0.3.0", "2026-08-18")], kind="planet", lede="")
    assert "awaiting approval" not in out.lower()


def test_build_digest_escapes_nothing_that_breaks_markdown_headings():
    """A '#' inside a title must not turn into a heading of its own."""
    item = rel("tt-bio v0.3.0", "2026-08-18")
    item["title"] = "### not a heading"
    item["projectName"] = "### not a heading"
    out = pd.build_digest([item], kind="release", lede="")
    assert "\n### not a heading" not in out


def test_build_digest_stays_under_the_github_body_limit():
    """GitHub 422s a body over 65536 chars — the digest must trim itself."""
    items = [rel(f"proj-{i} v1.0", "2026-08-18", description="y" * 1200)
             for i in range(200)]
    out = pd.build_digest(items, kind="release", lede="A lede.")
    assert len(out) <= pd.BODY_MAX_CHARS


def test_build_digest_says_when_it_truncated():
    items = [rel(f"proj-{i} v1.0", "2026-08-18", description="y" * 1200)
             for i in range(200)]
    out = pd.build_digest(items, kind="release", lede="")
    assert "truncated" in out.lower()


def test_build_digest_truncation_keeps_the_header_and_lede():
    items = [rel(f"proj-{i} v1.0", "2026-08-18", description="y" * 1200)
             for i in range(200)]
    out = pd.build_digest(items, kind="release", lede="Keep me.")
    assert "200 new releases" in out
    assert "Keep me." in out


def test_build_digest_truncation_keeps_the_newest_projects():
    """Trimming drops the least-recent projects, not the most-recent ones."""
    items = [rel("newest v1.0", "2026-08-20", description="n" * 1200)] + [
        rel(f"old-{i} v1.0", "2026-01-01", description="y" * 1200) for i in range(200)
    ]
    out = pd.build_digest(items, kind="release", lede="")
    assert "#### newest" in out


def test_build_digest_does_not_truncate_a_normal_run():
    """A realistic batch must come through whole, notice-free."""
    items = [rel(f"proj-{i} v1.0", "2026-08-18", description="y" * 900)
             for i in range(20)]
    out = pd.build_digest(items, kind="release", lede="A lede.")
    assert "truncated" not in out.lower()


# ── build_manifest (the LLM's input) ────────────────────────────────────────

def test_build_manifest_lists_items_with_metadata():
    items = [rel("tt-bio v0.3.0", "2026-08-18", description="A summary.")]
    manifest = pd.build_manifest(items)
    assert "tt-bio v0.3.0" in manifest
    assert "official" in manifest
    assert "A summary." in manifest


def test_build_manifest_marks_unapproved_items():
    items = [rel("blog Post", "2026-08-18", approved=False)]
    assert "AWAITING APPROVAL" in pd.build_manifest(items)


def test_build_manifest_truncates_long_descriptions():
    items = [rel("tt-bio v0.3.0", "2026-08-18", description="x" * 5000)]
    manifest = pd.build_manifest(items)
    assert len(manifest) < 2000


def test_build_manifest_caps_item_count_and_says_so():
    items = [rel(f"proj-{i} v1.0", "2026-08-18") for i in range(pd.MANIFEST_MAX_ITEMS + 10)]
    manifest = pd.build_manifest(items)
    assert "more" in manifest.lower()


# ── request_lede ────────────────────────────────────────────────────────────

def test_request_lede_returns_model_text(monkeypatch):
    monkeypatch.setattr(pd.llm_client, "complete", lambda *a, **k: "  A lede.  ")
    assert pd.request_lede([rel("tt-bio v0.3.0", "2026-08-18")]) == "A lede."


def test_request_lede_returns_empty_string_on_provider_failure(monkeypatch):
    """llm_client.complete() returns '' on any API error; we degrade, not crash."""
    monkeypatch.setattr(pd.llm_client, "complete", lambda *a, **k: "")
    assert pd.request_lede([rel("tt-bio v0.3.0", "2026-08-18")]) == ""


def test_request_lede_returns_empty_string_when_complete_raises(monkeypatch):
    """A malformed prompt file or missing PyYAML must not fail the whole job."""
    def boom(*a, **k):
        raise RuntimeError("prompt file is broken")
    monkeypatch.setattr(pd.llm_client, "complete", boom)
    assert pd.request_lede([rel("tt-bio v0.3.0", "2026-08-18")]) == ""


def test_request_lede_skips_the_call_entirely_for_no_items(monkeypatch):
    called = []
    monkeypatch.setattr(pd.llm_client, "complete", lambda *a, **k: called.append(1) or "x")
    assert pd.request_lede([]) == ""
    assert not called, "no items means no reason to spend a model call"


def test_request_lede_strips_a_heading_the_model_added_anyway(monkeypatch):
    monkeypatch.setattr(pd.llm_client, "complete", lambda *a, **k: "## Summary\nReal text.")
    assert pd.request_lede([rel("tt-bio v0.3.0", "2026-08-18")]) == "Real text."


# ── write_pr_body ───────────────────────────────────────────────────────────

def test_write_pr_body_writes_digest_then_boilerplate(tmp_path):
    out = tmp_path / "pr-body.md"
    pd.write_pr_body(
        [rel("tt-bio v0.3.0", "2026-08-18")],
        kind="release", lede="A lede.", boilerplate="Standard footer.", path=out,
    )
    text = out.read_text()
    assert text.index("A lede.") < text.index("Standard footer.")


def test_write_pr_body_skips_the_file_when_nothing_was_added(tmp_path):
    """No file means create-pull-request falls back to its static body."""
    out = tmp_path / "pr-body.md"
    pd.write_pr_body([], kind="release", lede="", boilerplate="Footer.", path=out)
    assert not out.exists()


def test_write_pr_body_returns_the_markdown_it_wrote(tmp_path):
    out = tmp_path / "pr-body.md"
    written = pd.write_pr_body(
        [rel("tt-bio v0.3.0", "2026-08-18")],
        kind="release", lede="", boilerplate="Footer.", path=out,
    )
    assert written == out.read_text()


def test_write_pr_body_creates_parent_directories(tmp_path):
    out = tmp_path / "nested" / "dir" / "pr-body.md"
    pd.write_pr_body([rel("tt-bio v0.3.0", "2026-08-18")],
                     kind="release", lede="", boilerplate="F.", path=out)
    assert out.exists()


# ── append_step_summary ─────────────────────────────────────────────────────

def test_append_step_summary_appends_to_the_actions_file(tmp_path, monkeypatch):
    f = tmp_path / "step-summary.md"
    f.write_text("existing\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(f))
    pd.append_step_summary("new digest")
    text = f.read_text()
    assert "existing" in text and "new digest" in text


def test_append_step_summary_is_a_noop_outside_actions(monkeypatch):
    """Local runs have no GITHUB_STEP_SUMMARY; this must not raise."""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    pd.append_step_summary("anything")  # must not raise


def test_append_step_summary_survives_an_unwritable_path(tmp_path, monkeypatch):
    """A bad path is not worth failing a green run over."""
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "no" / "such" / "dir" / "f.md"))
    pd.append_step_summary("anything")  # must not raise


def test_append_step_summary_ignores_empty_markdown(tmp_path, monkeypatch):
    f = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(f))
    pd.append_step_summary("")
    assert not f.exists()
