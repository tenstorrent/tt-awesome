# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.
"""The one-line blurb on a Models card: blurb() and split_first_sentence() in scripts/build_models_data.py.

Card descriptions are long single sentences (median 776 characters over the 31 bundle cards read on
2026-11-06), so a fixed-width cut always landed mid-clause and ended with "…". The rule under test
keeps whole sentences: the first sentence when it fits, else that sentence without its parenthetical
asides, else a cut at the last clause boundary, always ending with a period.

The builder is a script, so its helper block is read out of the file and run on its own, as
tests/test_models_perf.py does for the speed figures."""
import json
import pathlib
import re

SRC = (pathlib.Path(__file__).parent.parent / "scripts/build_models_data.py").read_text()
block = SRC[SRC.index("# ---- Card blurbs"):SRC.index("\n# A decision model")]
ns = {"re": re}
exec(block, ns)
blurb, split_first_sentence = ns["blurb"], ns["split_first_sentence"]

# The 24 real card descriptions whose first sentence runs past 240 characters (Hugging Face, 2026-11-06).
FIXTURE = pathlib.Path(__file__).parent / "fixtures/model_card_descriptions.json"


def test_short_first_sentence_is_kept_whole():
    assert blurb("Short one. Then more.") == "Short one."


def test_decimal_and_version_do_not_end_the_sentence():
    assert split_first_sentence("Planner v5.0 on 0.17 m voxels. Next.") == "Planner v5.0 on 0.17 m voxels."


def test_parentheticals_are_dropped_when_too_long():
    long = "BEVFormer-small, a detector (" + "x" * 300 + "), run on six inputs. Next."
    assert blurb(long) == "BEVFormer-small, a detector, run on six inputs."


def test_nested_parentheticals_are_dropped_whole():
    long = "Name, a thing (outer (inner) more " + "y" * 300 + ") that works. Next."
    assert blurb(long) == "Name, a thing that works."


def test_clause_cut_ends_with_a_period():
    long = "Name, a thing: " + ", ".join(f"part{i}" for i in range(80)) + ". Next."
    out = blurb(long)
    assert len(out) <= 241 and out.endswith(".") and "…" not in out
    assert out.startswith("Name, a thing: part0, part1")


def test_real_cards_never_end_in_an_ellipsis():
    for d in json.loads(FIXTURE.read_text()):
        out = blurb(d)
        assert not out.endswith("…") and not out.endswith("..."), out
        assert out[-1] in ".!?" and len(out) <= 241, out


def test_markdown_is_stripped():
    assert blurb("**Bold** [link](https://x) `code`. Next.") == "Bold link code."


def test_empty_description_gives_empty_blurb():
    assert blurb(None) == "" and blurb("") == ""


def test_a_bullet_list_after_the_first_sentence_is_not_part_of_it():
    # The Pi-0.5 card: a one-sentence opener, then a markdown list. Collapsing whitespace used to glue
    # "- Supports ..." onto the sentence, because the splitter wanted a capital after the period.
    card = ("This package runs the [Pi-0.5](https://huggingface.co/lerobot/pi05_base) VLA model of Physical "
            "Intelligence on one Tenstorrent Blackhole p150a.\n\n- Supports the following configurations:\n"
            "  - num_cameras: 1/2/3/4\n  - Prompt bucket: 32/64/128/224\n")
    assert blurb(card) == "This package runs the Pi-0.5 VLA model of Physical Intelligence on one Tenstorrent Blackhole p150a."
