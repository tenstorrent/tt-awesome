# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.
"""Tests for scripts/models_diff.py: the change set between two models.json documents and the two
things rendered from it, the nightly PR body and the Thursday Planet roundup.

Every test is offline. The one LLM call the module makes is monkeypatched or exercised through its
degradation path, because the roundup must still ship with its mechanical paragraph when the
summarization backend is unreachable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import models_diff as md  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────────

def model(id, **kw):
    """A models.json model record with the keys the diff reads, in the shape build_models_data.py writes."""
    m = dict(id=id, name=id, source="tt-model bundle", kind="LLM", status=None, inSpec=False,
             hardware=[], bundles=[], weights=f"org/{id}", purpose=None)
    m.update(kw)
    return m


def bundle(repo, updated="2026-11-01"):
    return dict(repo=repo, owner=repo.split("/")[0], updated=updated)


def doc(models, release="0.26.1", commit="0ad0f4be9", unreadable=()):
    return dict(models=models, spec=dict(release=release, commit=commit), unreadableBundles=list(unreadable),
                hardware=[], unclassified=[])


# ── diff_models ─────────────────────────────────────────────────────────────

def test_added_and_removed_models():
    old = doc([model("a"), model("gone", source="tt-inference-server", inSpec=True, status="Complete")])
    new = doc([model("a"), model("b", source="tt-inference-server", kind="VLM", status="Functional", inSpec=True,
                                hardware=["BH QuietBox 2"], bundles=[bundle("x/b-p300")])])
    d = md.diff_models(old, new)
    assert d["added"] == [dict(id="b", name="b", source="tt-inference-server", kind="VLM", status="Functional",
                               hardware=["BH QuietBox 2"], owners=["x"], bundles=["x/b-p300"],
                               weights="org/b", purpose=None, url="https://huggingface.co/org/b")]
    assert [m["id"] for m in d["removed"]] == ["gone"]


def test_status_change_and_entering_spec():
    old = doc([model("m", bundles=[bundle("o/m")])])
    new = doc([model("m", source="tt-inference-server", inSpec=True, status="Functional", bundles=[bundle("o/m")])])
    d = md.diff_models(old, new)
    assert d["status"] == [dict(id="m", name="m", old=None, new="Functional", url="https://huggingface.co/org/m")]
    assert d["entered_spec"] == [dict(id="m", name="m", status="Functional", kind="LLM", hardware=[], purpose=None,
                                      url="https://huggingface.co/org/m")]
    assert d["added"] == [] and d["removed"] == []


def test_leaving_spec_is_a_status_change_not_a_removal():
    old = doc([model("m", source="tt-inference-server", inSpec=True, status="Complete", bundles=[bundle("o/m")])])
    new = doc([model("m", bundles=[bundle("o/m")])])
    d = md.diff_models(old, new)
    assert d["removed"] == []
    assert d["status"] == [dict(id="m", name="m", old="Complete", new=None, url="https://huggingface.co/org/m")]
    assert d["entered_spec"] == []


def test_bundle_added_and_removed_on_an_existing_model():
    old = doc([model("m", bundles=[bundle("o/m-v1")])])
    new = doc([model("m", bundles=[bundle("o/m-v2"), bundle("p/m-fast")])])
    d = md.diff_models(old, new)
    u = "https://huggingface.co/org/m"
    assert d["bundles_added"] == [dict(model="m", id="m", repo="o/m-v2", url=u), dict(model="m", id="m", repo="p/m-fast", url=u)]
    assert d["bundles_removed"] == [dict(model="m", id="m", repo="o/m-v1", url=u)]


def test_kind_and_hardware_changes():
    old = doc([model("m", kind="LLM", hardware=["BH QuietBox 2"])])
    new = doc([model("m", kind="VLM", hardware=["BH QuietBox 2", "Galaxy"])])
    d = md.diff_models(old, new)
    assert d["kind"] == [dict(id="m", name="m", old="LLM", new="VLM", url="https://huggingface.co/org/m")]
    assert d["hardware"] == [dict(id="m", name="m", added=["Galaxy"], url="https://huggingface.co/org/m")]


def test_unreadable_bundles_both_ways():
    old = doc([], unreadable=["o/broken", "o/fixed"])
    new = doc([], unreadable=["o/broken", "o/new-break"])
    d = md.diff_models(old, new)
    assert d["unreadable"] == dict(now_unreadable=["o/new-break"], now_readable=["o/fixed"])


def test_missing_keys_in_the_old_document_are_empty():
    # A week-old file from before a schema change: no unreadableBundles, a model with no hardware or bundles key.
    old = dict(models=[dict(id="m", name="m", source="tt-model bundle", kind="LLM", status=None, inSpec=False)],
               spec=dict(release="0.25.0", commit="2db98e38c"))
    new = doc([model("m", hardware=["Galaxy"], bundles=[bundle("o/m")], weights=None)])
    d = md.diff_models(old, new)
    # A model with no weights repo falls back to its tt-awesome page.
    assert d["hardware"] == [dict(id="m", name="m", added=["Galaxy"], url="https://docs.tenstorrent.com/tt-awesome/models/m/")]
    assert d["bundles_added"] == [dict(model="m", id="m", repo="o/m", url="https://docs.tenstorrent.com/tt-awesome/models/m/")]
    assert d["unreadable"] == dict(now_unreadable=[], now_readable=[])
    assert d["spec"] == dict(old=dict(release="0.25.0", commit="2db98e38c"), new=dict(release="0.26.1", commit="0ad0f4be9"))


def test_lists_are_sorted_by_model_name():
    new = doc([model("zeta"), model("Alpha"), model("mid")])
    d = md.diff_models(doc([]), new)
    assert [m["name"] for m in d["added"]] == ["Alpha", "mid", "zeta"]


def test_spec_bump_alone_is_not_empty_but_no_lists_is_empty():
    same = doc([model("m")])
    assert md.is_empty(md.diff_models(same, same))
    bumped = doc([model("m")], release="0.27.0", commit="abcdef012")
    assert not md.is_empty(md.diff_models(same, bumped))


# ── render_pr_body / write_pr_body ──────────────────────────────────────────

BOILERPLATE = "<!-- tt-awesome-digest-boilerplate -->\nNightly rebuild of `src/_data/models.json`.\n"


def rich_diff():
    old = doc([model("Kept", source="tt-inference-server", inSpec=True, status="Functional", kind="LLM",
                     hardware=["Galaxy"], bundles=[bundle("o/kept-v1")]),
               model("Dropped")],
              release="0.25.0", commit="2db98e38c", unreadable=["o/fixed"])
    new = doc([model("Kept", source="tt-inference-server", inSpec=True, status="Complete", kind="VLM",
                     hardware=["Galaxy", "BH QuietBox 2"], bundles=[bundle("o/kept-v2")]),
               model("Fresh", source="tt-inference-server", inSpec=True, status="Experimental", kind="LLM",
                     hardware=["Galaxy"]),
               model("Bundled", bundles=[bundle("u/bundled-p150")])],
              release="0.26.1", commit="0ad0f4be9", unreadable=["o/broken"])
    return md.diff_models(old, new)


def test_render_pr_body_is_empty_for_no_changes():
    same = doc([model("m")])
    assert md.render_pr_body(md.diff_models(same, same), BOILERPLATE) == ""


def test_render_pr_body_sections_and_boilerplate_marker():
    body = md.render_pr_body(rich_diff(), BOILERPLATE)
    assert "### 🆕 2 new models" in body
    assert "- **Bundled** (tt-model bundle, LLM) — bundles by u" in body
    assert "- **Fresh** (tt-inference-server, LLM, Experimental) — Galaxy" in body
    assert "### ➖ 1 model removed" in body and "- **Dropped**" in body
    assert "### 📈 1 status change" in body and "- **Kept**: Functional → Complete" in body
    assert "### 📦 1 new bundle" in body and "- **Kept**: o/kept-v2" in body
    assert "### 📦 1 bundle withdrawn" in body and "- **Kept**: o/kept-v1" in body
    assert "### 🔁 1 kind change" in body and "- **Kept**: LLM → VLM" in body
    assert "### 🖥 1 hardware addition" in body and "- **Kept**: BH QuietBox 2" in body
    assert "### ⚠ Unreadable bundles" in body and "- now unreadable: o/broken" in body and "- readable again: o/fixed" in body
    assert "tt-inference-server spec: 0.25.0 → 0.26.1" in body
    assert body.count("<!-- tt-awesome-digest-boilerplate -->") == 1
    assert body.rstrip().endswith("Nightly rebuild of `src/_data/models.json`.")
    # Headings appear only for non-empty sections.
    assert "entered the spec" not in body


def test_render_pr_body_entered_spec_section():
    old = doc([model("m", bundles=[bundle("o/m")])])
    new = doc([model("m", source="tt-inference-server", inSpec=True, status="Functional", bundles=[bundle("o/m")])])
    body = md.render_pr_body(md.diff_models(old, new), BOILERPLATE)
    assert "### 🚀 1 model entered the spec" in body and "- **m** (Functional)" in body


def test_write_pr_body_leaves_no_file_when_empty(tmp_path):
    same = doc([model("m")])
    template = tmp_path / "models.md"
    template.write_text(BOILERPLATE)
    out = tmp_path / "pr-body.md"
    assert md.write_pr_body(md.diff_models(same, same), out, template) is False
    assert not out.exists()
    assert md.write_pr_body(rich_diff(), out, template) is True
    assert out.read_text().startswith("### ")


# ── The weekly roundup ──────────────────────────────────────────────────────

import json  # noqa: E402
from datetime import date, datetime, timezone  # noqa: E402

import llm_client  # noqa: E402

WEEK_END = date(2026, 11, 5)   # a Thursday
NOW = datetime(2026, 11, 5, 7, 50, 0, tzinfo=timezone.utc)


def test_week_fragment_uses_iso_week():
    assert md.week_fragment(date(2026, 11, 5)) == "week-2026-W45"
    assert md.week_fragment(date(2027, 1, 1)) == "week-2026-W53"   # ISO year differs from the calendar year


def test_title_counts_both_sources_and_omits_zero():
    d = rich_diff()   # Fresh on tt-inference-server, Bundled as a bundle, plus Kept's new bundle o/kept-v2
    assert md.roundup_title(d) == "Models this week: 1 new on tt-inference-server, 2 new tt-model bundles"
    only_spec = md.diff_models(doc([]), doc([model("A", source="tt-inference-server", inSpec=True, status="Complete")]))
    assert md.roundup_title(only_spec) == "Models this week: 1 new on tt-inference-server"
    only_status = md.diff_models(doc([model("m", status="Functional", inSpec=True, source="tt-inference-server")]),
                                 doc([model("m", status="Complete", inSpec=True, source="tt-inference-server")]))
    assert md.roundup_title(only_status) == "Models this week: 1 change"


def test_build_manifest_is_capped():
    d = md.diff_models(doc([]), doc([model(f"m{i:02}") for i in range(50)]))
    text = md.build_manifest(d, cap=10)
    assert text.count("\n") == 10 and text.endswith("… and 40 more")


def test_fallback_paragraph_names_models_per_section():
    p = md.fallback_paragraph(rich_diff())
    assert "Fresh" in p and "tt-inference-server" in p
    assert "Bundled" in p and "New bundles for Kept." in p and "o/kept-v2" not in p
    assert "Kept" in p and "Complete" in p
    assert p.endswith(".") and "\n" not in p


def test_link_models_links_whole_names_longest_first():
    models = [dict(id="qwen3-5-27b", name="Qwen3.5-27B"), dict(id="qwen3-5-27b-instruct", name="Qwen3.5-27B-Instruct")]
    out = md.link_models("Qwen3.5-27B-Instruct joins Qwen3.5-27B this week; Qwen3.5-27B again.", models)
    assert out == ("[Qwen3.5-27B-Instruct](https://docs.tenstorrent.com/tt-awesome/models/qwen3-5-27b-instruct/) joins "
                   "[Qwen3.5-27B](https://docs.tenstorrent.com/tt-awesome/models/qwen3-5-27b/) this week; Qwen3.5-27B again.")


def test_link_models_skips_text_already_inside_a_link():
    models = [dict(id="laya", name="Laya")]
    text = "See [Laya](https://example.com/laya) and Laya."
    assert md.link_models(text, models) == "See [Laya](https://example.com/laya) and [Laya](https://docs.tenstorrent.com/tt-awesome/models/laya/)."


def test_build_roundup_item_shape():
    d = rich_diff()
    item = md.build_roundup(d, WEEK_END, "A paragraph.", NOW)
    assert item["type"] == "article" and item["source"] == "models-roundup" and item["approved"] is True
    assert item["body"] == "markdown"            # planet-item.njk renders this one with block markdown
    assert item["title"] == md.roundup_title(d)
    assert item["url"] == "https://docs.tenstorrent.com/tt-awesome/models/#week-2026-W45"
    assert item["date"] == "2026-11-05" and item["dateISO"] == "2026-11-05T07:50:00Z"
    assert item["label"] == "Models this week" and item["projectName"] == "Models" and item["projectId"] is None
    assert item["affiliation"] == "official"


def test_build_roundup_body_has_paragraph_tables_and_bullets():
    # The lede is the model's (or fallback) paragraph; everything else is mechanical and complete, so the
    # paragraph never needs a "New: ..." tail and a reader can scan kind, status and hardware in a table.
    d = rich_diff()
    body = md.build_roundup(d, WEEK_END, "Fresh landed on tt-inference-server.", NOW)["description"]
    sections = body.split("\n\n")
    # Every model name links to the original model's Hugging Face card; a bundle id links to the bundle's card.
    assert sections[0] == "[Fresh](https://huggingface.co/org/Fresh) landed on tt-inference-server."
    assert "**New on tt-inference-server**" in sections
    assert ("| Model | Kind | Status | Hardware |\n|---|---|---|---|\n"
            "| [Fresh](https://huggingface.co/org/Fresh) | LLM | Experimental | Galaxy |") in body
    assert "**New tt-model bundles**" in sections
    assert ("| Model | Kind | Bundle | Hardware |\n|---|---|---|---|\n"
            "| [Bundled](https://huggingface.co/org/Bundled) | LLM | [u/bundled-p150](https://huggingface.co/u/bundled-p150) | — |") in body
    assert "**Also this week**" in sections
    bullets = sections[sections.index("**Also this week**") + 1].splitlines()
    kept = "[Kept](https://huggingface.co/org/Kept)"
    assert f"- {kept}: Functional → Complete" in bullets
    assert f"- {kept}: new bundle [o/kept-v2](https://huggingface.co/o/kept-v2)" in bullets
    assert f"- {kept}: bundle o/kept-v1 withdrawn" in bullets
    assert f"- {kept}: reclassified LLM → VLM" in bullets
    assert f"- {kept}: now also on BH QuietBox 2" in bullets
    assert "- tt-inference-server spec 0.25.0 → 0.26.1" in bullets
    assert "- Bundle manifest now unreadable: o/broken" in bullets and "- Bundle manifest readable again: o/fixed" in bullets
    assert "New:" not in body


def test_build_roundup_omits_empty_sections_and_lists_several_bundles():
    new = doc([model("Solo", source="tt-inference-server", inSpec=True, status="Complete", kind="VLM", hardware=["Galaxy"]),
               model("Multi", kind="LLM", hardware=["p150"], bundles=[bundle("a/multi-p150"), bundle("b/multi-qb2")])])
    body = md.build_roundup(md.diff_models(doc([]), new), WEEK_END, "", NOW)["description"]
    assert "**Also this week**" not in body
    assert body.startswith("**New on tt-inference-server**")   # an empty paragraph leaves no blank lead
    assert ("| [Multi](https://huggingface.co/org/Multi) | LLM | [a/multi-p150](https://huggingface.co/a/multi-p150), "
            "[b/multi-qb2](https://huggingface.co/b/multi-qb2) | p150 |") in body


def test_kind_cell_carries_the_inferred_purpose():
    new = doc([model("MIRA", kind="VLM", purpose="deep-research agent", hardware=["p150"], bundles=[bundle("r/mira")])])
    body = md.build_roundup(md.diff_models(doc([]), new), WEEK_END, "", NOW)["description"]
    assert "| [MIRA](https://huggingface.co/org/MIRA) | VLM, deep-research agent | [r/mira](https://huggingface.co/r/mira) | p150 |" in body
    manifest = md.build_manifest(md.diff_models(doc([]), new))
    assert "new tt-model bundle: MIRA (VLM, deep-research agent)" in manifest


def test_entered_spec_models_sit_in_the_spec_table():
    old = doc([model("Gem", kind="LLM", bundles=[bundle("o/gem")])])
    new = doc([model("Gem", source="tt-inference-server", inSpec=True, status="Functional", kind="LLM",
                     hardware=["BH QuietBox 2"], bundles=[bundle("o/gem")])])
    body = md.build_roundup(md.diff_models(old, new), WEEK_END, "", NOW)["description"]
    assert "| [Gem](https://huggingface.co/org/Gem) | LLM | Functional | BH QuietBox 2 |" in body
    assert "**Also this week**" not in body     # entering the spec is the table row, not a second bullet


def test_build_roundup_links_a_model_that_only_gained_a_bundle():
    old = doc([model("Elyza", bundles=[bundle("o/elyza-v1")])])
    new = doc([model("Elyza", bundles=[bundle("o/elyza-v1"), bundle("t/elyza-fast")])])
    body = md.build_roundup(md.diff_models(old, new), WEEK_END, "", NOW)["description"]
    assert "- [Elyza](https://huggingface.co/org/Elyza): new bundle [t/elyza-fast](https://huggingface.co/t/elyza-fast)" in body


def test_manifest_and_paragraph_inputs_name_no_publishers():
    # Taylor: the prose must not single out who published a bundle. Owners stay out of what the model sees.
    manifest = md.build_manifest(rich_diff())
    assert " by u" not in manifest and "u/bundled-p150" not in manifest
    assert "new tt-model bundle: Bundled (LLM)" in manifest


def test_request_paragraph_degrades_to_empty(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("backend down")
    monkeypatch.setattr(llm_client, "complete", boom)
    assert md.request_roundup_paragraph("manifest", week="the week ending 2026-11-05") == ""
    monkeypatch.setattr(llm_client, "complete", lambda *a, **k: "## Heading\nThe paragraph.")
    assert md.request_roundup_paragraph("manifest", week="the week ending 2026-11-05") == "The paragraph."


def test_request_paragraph_passes_the_prompt_file_and_variables(monkeypatch):
    seen = {}
    def fake(name, variables, **kw):
        seen.update(name=name, variables=variables)
        return "Text."
    monkeypatch.setattr(llm_client, "complete", fake)
    md.request_roundup_paragraph("the manifest", week="the week ending 2026-11-05")
    assert seen["name"] == "models-roundup"
    assert seen["variables"] == {"week": "the week ending 2026-11-05", "manifest": "the manifest"}
    # The prompt file exists and renders without PyYAML errors.
    prompt = llm_client.load_prompt("models-roundup")
    assert any("{{ manifest }}" in m["content"] for m in prompt["messages"])


def test_write_roundup_inserts_in_date_order_and_dedups_by_url(tmp_path):
    feeds = tmp_path / "planet_feeds.json"
    feeds.write_text(json.dumps([
        dict(url="https://a", dateISO="2026-11-06T00:00:00Z"),
        dict(url="https://b", dateISO="2026-11-01T00:00:00Z"),
    ]))
    item = md.build_roundup(rich_diff(), WEEK_END, "Paragraph.", NOW)
    assert md.write_roundup(item, feeds) is True
    urls = [i["url"] for i in json.loads(feeds.read_text())]
    assert urls == ["https://a", item["url"], "https://b"]
    assert md.write_roundup(item, feeds) is False            # same Thursday again: nothing written twice
    assert len(json.loads(feeds.read_text())) == 3


# ── CLI ─────────────────────────────────────────────────────────────────────

def _write_docs(tmp_path):
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    old.write_text(json.dumps(doc([model("m")], release="0.25.0")))
    new.write_text(json.dumps(doc([model("m"), model("Fresh", source="tt-inference-server", inSpec=True,
                                                         status="Complete", hardware=["Galaxy"])])))
    return old, new


def test_cli_pr_body_writes_file(tmp_path):
    old, new = _write_docs(tmp_path)
    template = tmp_path / "models.md"
    template.write_text(BOILERPLATE)
    out = tmp_path / "pr-body.md"
    assert md.main(["pr-body", "--old", str(old), "--new", str(new), "--out", str(out), "--template", str(template)]) == 0
    assert "### 🆕 1 new model" in out.read_text()


def test_cli_roundup_dry_run_prints_item_and_writes_nothing(tmp_path, monkeypatch, capsys):
    old, new = _write_docs(tmp_path)
    feeds = tmp_path / "planet_feeds.json"
    feeds.write_text("[]")
    monkeypatch.setattr(md, "request_roundup_paragraph", lambda *a, **k: "A paragraph naming Fresh.")
    rc = md.main(["roundup", "--old", str(old), "--new", str(new), "--week-end", "2026-11-05",
                  "--feeds", str(feeds), "--dry-run"])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out.split("--- DRY RUN", 1)[1].split("\n", 1)[1])
    assert printed["url"].endswith("#week-2026-W45") and printed["description"].startswith("A paragraph naming [Fresh](https://huggingface.co/org/Fresh)")
    assert feeds.read_text() == "[]"


def test_cli_roundup_writes_the_item(tmp_path, monkeypatch):
    old, new = _write_docs(tmp_path)
    feeds = tmp_path / "planet_feeds.json"
    feeds.write_text("[]")
    monkeypatch.setattr(md, "request_roundup_paragraph", lambda *a, **k: "")   # backend down: fallback paragraph
    assert md.main(["roundup", "--old", str(old), "--new", str(new), "--week-end", "2026-11-05",
                    "--feeds", str(feeds)]) == 0
    items = json.loads(feeds.read_text())
    assert len(items) == 1 and items[0]["description"].startswith("New on tt-inference-server: [Fresh]")


def test_cli_roundup_no_changes(tmp_path, capsys):
    same = tmp_path / "same.json"
    same.write_text(json.dumps(doc([model("m")])))
    feeds = tmp_path / "planet_feeds.json"
    assert md.main(["roundup", "--old", str(same), "--new", str(same), "--week-end", "2026-11-05",
                    "--feeds", str(feeds)]) == 0
    assert "no changes this week" in capsys.readouterr().out
    assert not feeds.exists()


# ── Fix pass after the whole-branch review (2026-11-06) ─────────────────────

def test_fallback_paragraph_covers_every_kind_of_change():
    # A week with only a demotion, a withdrawn bundle, a kind change, a hardware addition and a manifest
    # flip is not empty, so an item is built; its fallback must say something for each.
    old = doc([model("Gone", source="tt-inference-server", inSpec=True, status="Complete", kind="LLM",
                     hardware=["Galaxy"], bundles=[bundle("o/gone-v1")])], unreadable=["o/fixed"])
    new = doc([model("Gone", kind="VLM", hardware=["Galaxy", "p150"], bundles=[])], unreadable=["o/broken"])
    p = md.fallback_paragraph(md.diff_models(old, new))
    assert "Gone" in p and "left tt-inference-server" in p
    assert "Bundles withdrawn from Gone." in p and "o/gone-v1" not in p   # repo ids live in the bullets
    assert "LLM to VLM" in p
    assert "p150" in p
    assert "o/broken" in p and "o/fixed" in p
    assert p.endswith(".")


def test_carry_forward_keeps_an_unmerged_roundup(tmp_path):
    # Friday's run rebuilds the PR branch from main plus its own tree; Thursday's item lives only on the
    # branch until merged. Carrying it forward keeps it (and its one paid-for paragraph) in the PR.
    branch = tmp_path / "branch_feeds.json"
    main_feeds = tmp_path / "planet_feeds.json"
    thursday = dict(url="https://docs.tenstorrent.com/tt-awesome/models/#week-2026-W45", source="models-roundup",
                    dateISO="2026-11-05T07:50:00Z", title="Models this week: 1 change")
    other = dict(url="https://x/branch-only-release", source="github", dateISO="2026-11-05T00:00:00Z")
    branch.write_text(json.dumps([thursday, other]))
    main_feeds.write_text(json.dumps([dict(url="https://a", dateISO="2026-11-06T00:00:00Z")]))
    assert md.carry_forward(branch, main_feeds) == 1
    urls = [i["url"] for i in json.loads(main_feeds.read_text())]
    assert urls == ["https://a", thursday["url"]]           # the roundup only, in dateISO order
    assert md.carry_forward(branch, main_feeds) == 0         # idempotent


def test_cli_carry_forward(tmp_path, capsys):
    branch = tmp_path / "branch_feeds.json"
    feeds = tmp_path / "planet_feeds.json"
    branch.write_text(json.dumps([dict(url="https://docs.tenstorrent.com/tt-awesome/models/#week-2026-W45",
                                       source="models-roundup", dateISO="2026-11-05T07:50:00Z")]))
    feeds.write_text("[]")
    assert md.main(["carry-forward", "--from", str(branch), "--feeds", str(feeds)]) == 0
    assert "carried 1 roundup" in capsys.readouterr().out
    assert len(json.loads(feeds.read_text())) == 1


def test_a_new_model_with_several_bundles_counts_each_bundle():
    # Models are grouped by weights repo, so a bundle-only model can arrive with several bundles at once
    # (gpt-oss-20b has four). The title counts bundles, and the manifest and fallback name each repo.
    new = doc([model("gpt-oss-20b", kind="LLM", bundles=[bundle("a/gpt-oss-20b-p150"), bundle("b/gpt-oss-20b-qb2"),
                                                          bundle("b/gpt-oss-20b-galaxy")])])
    d = md.diff_models(doc([]), new)
    assert d["added"][0]["bundles"] == ["a/gpt-oss-20b-p150", "b/gpt-oss-20b-galaxy", "b/gpt-oss-20b-qb2"]
    assert md.roundup_title(d) == "Models this week: 3 new tt-model bundles"
    manifest = md.build_manifest(d)
    assert "new tt-model bundles: gpt-oss-20b (LLM), 3 bundles" in manifest
    assert "a/gpt-oss-20b-p150" not in md.fallback_paragraph(d)   # repo ids live in the table, publishers never in prose
    assert "[a/gpt-oss-20b-p150](https://huggingface.co/a/gpt-oss-20b-p150)" in md.build_roundup(d, WEEK_END, "", NOW)["description"]


def test_write_roundup_honours_a_declined_url(tmp_path):
    # decline_planet_item.py moves a rejected item's URL to planet_declined.json next to the feed file.
    # A forced rerun, or a stale PR branch handed to carry_forward, must not bring the week back.
    feeds = tmp_path / "planet_feeds.json"
    feeds.write_text("[]")
    item = md.build_roundup(rich_diff(), WEEK_END, "Paragraph.", NOW)
    (tmp_path / "planet_declined.json").write_text(json.dumps([
        dict(url=item["url"], title=item["title"], date="2026-11-05", source="models-roundup", reason="quiet week")]))
    assert md.write_roundup(item, feeds) is False
    assert json.loads(feeds.read_text()) == []
    branch = tmp_path / "branch_feeds.json"
    branch.write_text(json.dumps([item]))
    assert md.carry_forward(branch, feeds) == 0
    assert json.loads(feeds.read_text()) == []


def test_write_roundup_replace_overwrites_the_week(tmp_path):
    # A dispatch with roundup=true is how a week gets regenerated after a prompt change; it replaces.
    feeds = tmp_path / "planet_feeds.json"
    first = md.build_roundup(rich_diff(), WEEK_END, "First paragraph.", NOW)
    feeds.write_text(json.dumps([first, dict(url="https://b", dateISO="2026-11-01T00:00:00Z")]))
    second = dict(first, description="Second paragraph.")
    assert md.write_roundup(second, feeds) is False
    assert md.write_roundup(second, feeds, replace=True) is True
    items = json.loads(feeds.read_text())
    assert [i["url"] for i in items] == [first["url"], "https://b"]
    assert items[0]["description"] == "Second paragraph."


def test_cli_roundup_replace_flag(tmp_path, monkeypatch):
    old, new = _write_docs(tmp_path)
    feeds = tmp_path / "planet_feeds.json"
    feeds.write_text("[]")
    monkeypatch.setattr(md, "request_roundup_paragraph", lambda *a, **k: "One.")
    md.main(["roundup", "--old", str(old), "--new", str(new), "--week-end", "2026-11-05", "--feeds", str(feeds)])
    monkeypatch.setattr(md, "request_roundup_paragraph", lambda *a, **k: "Two.")
    md.main(["roundup", "--old", str(old), "--new", str(new), "--week-end", "2026-11-05", "--feeds", str(feeds), "--replace"])
    items = json.loads(feeds.read_text())
    assert len(items) == 1 and items[0]["description"].startswith("Two.")


def test_kind_cell_shows_only_the_purpose_when_the_kind_is_already_specific():
    # "Embedding, multimodal embedding" says it twice; "VLM, deep-research agent" does not, since LLM and VLM
    # are families and the purpose says what this member is for.
    assert md._kind_text(dict(kind="Embedding", purpose="multimodal embedding")) == "multimodal embedding"
    assert md._kind_text(dict(kind="Text ranking", purpose="text reranker for 100+ languages and code")) == "text reranker for 100+ languages and code"
    assert md._kind_text(dict(kind="VLM", purpose="deep-research agent")) == "VLM, deep-research agent"
    assert md._kind_text(dict(kind="LLM", purpose=None)) == "LLM"
    assert md._kind_text(dict(kind="Object detection", purpose=None)) == "Object detection"


# ── Copilot review on PR #314 (2026-11-06) ──────────────────────────────────

def test_bundle_changes_reach_the_model_and_the_fallback_without_repo_ids():
    # A bundle gained or lost by a model already listed used to go into the manifest and the fallback
    # paragraph as "owner/name", so the prose could still single out a publisher. Names only, both places;
    # the "Also this week" bullets carry the repo ids.
    old = doc([model("Kept", bundles=[bundle("o/kept-v1")]), model("Lost", bundles=[bundle("p/lost-a"), bundle("p/lost-b")])])
    new = doc([model("Kept", bundles=[bundle("o/kept-v1"), bundle("t/kept-fast"), bundle("t/kept-slow")]),
               model("Lost", bundles=[bundle("p/lost-a")])])
    d = md.diff_models(old, new)
    manifest = md.build_manifest(d)
    assert "2 new bundles for Kept" in manifest and "bundle withdrawn from Lost" in manifest
    assert "/" not in manifest
    p = md.fallback_paragraph(d)
    assert "New bundles for Kept." in p and "Bundles withdrawn from Lost." in p
    assert "/" not in p
    body = md.build_roundup(d, WEEK_END, "", NOW)["description"]
    assert "[t/kept-fast](https://huggingface.co/t/kept-fast)" in body and "p/lost-b withdrawn" in body


def test_prompt_test_data_carries_no_repo_ids():
    # The prompt's own example manifest is what a maintainer reads to learn the contract; it must show
    # the shape the code produces, which names no bundle repo.
    import re, yaml
    spec = yaml.safe_load((Path(__file__).parent.parent / "prompts" / "models-roundup.prompt.yml").read_text())
    for case in spec["testData"]:
        for line in case["manifest"].splitlines():
            assert not re.search(r"\S+/\S+", line), line


# ── First forced run on main (2026-11-06, run 42314783741) ──────────────────

def test_request_paragraph_keeps_only_the_lede(monkeypatch):
    # The first real reply opened with four sentences, then wrote its own table with a "Delivery" column
    # that maxTokens cut off mid-row. build_roundup adds the tables itself, so anything after the first
    # block of prose is dropped: a blank line, or a line that starts a table, heading, bullet or label.
    reply = ("Qwen2.5-VL arrives through tt-inference-server. Three agents arrive as bundles.\n\n"
             "| Model | Kind | Status | Hardware | Delivery |\n|---|---|---|---|---|\n| granite | LLM | Functional")
    monkeypatch.setattr(llm_client, "complete", lambda *a, **k: reply)
    assert md.request_roundup_paragraph("m", week="w") == \
        "Qwen2.5-VL arrives through tt-inference-server. Three agents arrive as bundles."
    monkeypatch.setattr(llm_client, "complete", lambda *a, **k: "One sentence.\n| a | b |\n**Also**\n- bullet")
    assert md.request_roundup_paragraph("m", week="w") == "One sentence."


def test_request_paragraph_replaces_em_dashes(monkeypatch):
    # House style forbids em-dashes; the model used a pair to set off a list. Each becomes a comma.
    reply = "Three agents arrive as bundles—MIRA, QUEST and Tongyi—alongside Qwen3 tools. A dash — here too."
    monkeypatch.setattr(llm_client, "complete", lambda *a, **k: reply)
    assert md.request_roundup_paragraph("m", week="w") == \
        "Three agents arrive as bundles, MIRA, QUEST and Tongyi, alongside Qwen3 tools. A dash, here too."


def test_link_models_matches_a_name_regardless_of_case():
    # The model wrote "Gemma-4-26B-A4B-it" for gemma-4-26B-A4B-it and the mention went unlinked. The link
    # keeps the model's own spelling as its text.
    models = [dict(id="g", name="gemma-4-26B-A4B-it", url="https://huggingface.co/google/gemma-4-26B-A4B-it")]
    assert md.link_models("Gemma-4-26B-A4B-it advances to Functional.", models) == \
        "[Gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it) advances to Functional."
