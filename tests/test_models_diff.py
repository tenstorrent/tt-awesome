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
             hardware=[], bundles=[])
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
                               hardware=["BH QuietBox 2"], owners=["x"])]
    assert [m["id"] for m in d["removed"]] == ["gone"]


def test_status_change_and_entering_spec():
    old = doc([model("m", bundles=[bundle("o/m")])])
    new = doc([model("m", source="tt-inference-server", inSpec=True, status="Functional", bundles=[bundle("o/m")])])
    d = md.diff_models(old, new)
    assert d["status"] == [dict(id="m", name="m", old=None, new="Functional")]
    assert d["entered_spec"] == [dict(id="m", name="m", status="Functional")]
    assert d["added"] == [] and d["removed"] == []


def test_leaving_spec_is_a_status_change_not_a_removal():
    old = doc([model("m", source="tt-inference-server", inSpec=True, status="Complete", bundles=[bundle("o/m")])])
    new = doc([model("m", bundles=[bundle("o/m")])])
    d = md.diff_models(old, new)
    assert d["removed"] == []
    assert d["status"] == [dict(id="m", name="m", old="Complete", new=None)]
    assert d["entered_spec"] == []


def test_bundle_added_and_removed_on_an_existing_model():
    old = doc([model("m", bundles=[bundle("o/m-v1")])])
    new = doc([model("m", bundles=[bundle("o/m-v2"), bundle("p/m-fast")])])
    d = md.diff_models(old, new)
    assert d["bundles_added"] == [dict(model="m", id="m", repo="o/m-v2"), dict(model="m", id="m", repo="p/m-fast")]
    assert d["bundles_removed"] == [dict(model="m", id="m", repo="o/m-v1")]


def test_kind_and_hardware_changes():
    old = doc([model("m", kind="LLM", hardware=["BH QuietBox 2"])])
    new = doc([model("m", kind="VLM", hardware=["BH QuietBox 2", "Galaxy"])])
    d = md.diff_models(old, new)
    assert d["kind"] == [dict(id="m", name="m", old="LLM", new="VLM")]
    assert d["hardware"] == [dict(id="m", name="m", added=["Galaxy"])]


def test_unreadable_bundles_both_ways():
    old = doc([], unreadable=["o/broken", "o/fixed"])
    new = doc([], unreadable=["o/broken", "o/new-break"])
    d = md.diff_models(old, new)
    assert d["unreadable"] == dict(now_unreadable=["o/new-break"], now_readable=["o/fixed"])


def test_missing_keys_in_the_old_document_are_empty():
    # A week-old file from before a schema change: no unreadableBundles, a model with no hardware or bundles key.
    old = dict(models=[dict(id="m", name="m", source="tt-model bundle", kind="LLM", status=None, inSpec=False)],
               spec=dict(release="0.25.0", commit="2db98e38c"))
    new = doc([model("m", hardware=["Galaxy"], bundles=[bundle("o/m")])])
    d = md.diff_models(old, new)
    assert d["hardware"] == [dict(id="m", name="m", added=["Galaxy"])]
    assert d["bundles_added"] == [dict(model="m", id="m", repo="o/m")]
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
