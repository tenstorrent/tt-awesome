# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.
"""The speed figures on the Models cards: spec_perf and bundle_perf in scripts/build_models_data.py.

The builder is a script, so its helper block is read out of the file and run on its own."""
import pathlib
import re

SRC = (pathlib.Path(__file__).parent.parent / "scripts/build_models_data.py").read_text()
block = SRC[SRC.index("# ---- Headline speed figures"):SRC.index("\ndef k(n):")]
ns = {"re": re}
exec(block, ns)
spec_perf, bundle_perf = ns["spec_perf"], ns["bundle_perf"]

REFS = [{"isl": 128, "osl": 128, "max_concurrency": 1, "targets": {
    "functional": {"ttft_ms": 510.0, "tput_user": 2.7}, "complete": {"ttft_ms": 102.0, "tput_user": 13.5},
    "target": {"ttft_ms": 51.0, "tput_user": 27.0}}}]


def test_spec_perf_uses_the_tier_for_the_status():
    assert spec_perf(REFS, "COMPLETE") == dict(decode=13.5, ttft=102.0, tier="complete", measured=False)
    assert spec_perf(REFS, "EXPERIMENTAL")["decode"] == 2.7


def test_spec_perf_ignores_other_shapes_and_missing_data():
    assert spec_perf([dict(REFS[0], isl=2048)], "COMPLETE") is None
    assert spec_perf([], "COMPLETE") is None and spec_perf(None, "COMPLETE") is None


TABLE = """### Latency sweep, P150 (one chip)

| Input tokens | Output tokens | Users | N | TTFT (ms) | TPOT (ms) | Decode tok/s/user | Total out tok/s | E2EL (s) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 128 | 2 | 8 | 222 | 167.9 | 6.0 | 12 | 21.55 |
| 1,024 | 256 | 1 | 4 | 196 | 168.0 | 5.9 | 6 | 43.03 |
| 128 | 128 | 1 | 4 | 97 | 167.4 | 6.0 | 6 | 21.35 |
"""


def test_bundle_perf_takes_one_user_at_the_shortest_prompt_and_reads_the_board_from_the_heading():
    p = bundle_perf(TABLE)
    assert (p["decode"], p["ttft"], p["board"], p["chips"]) == (6.0, 97.0, "p150", 1)


def test_bundle_perf_drops_ttft_when_no_128_token_row():
    p = bundle_perf(TABLE.replace("| 128 | 128 | 1 | 4 | 97 | 167.4 | 6.0 | 6 | 21.35 |\n", ""))
    assert p["ttft"] is None and p["decode"] == 5.9


def test_bundle_perf_reads_the_board_from_a_profile_column():
    t = ("| profile | ISL | OSL | concurrency | N | TTFT (ms) | prefill tok/s/u | decode tok/s/u | E2EL (s) |\n"
         "|---|---|---|---|---|---|---|---|---|\n| p150x4 | 128 | 128 | 1 | 4 | 90 | 1,400 | 52.0 | 3 |\n")
    p = bundle_perf(t)
    assert (p["board"], p["chips"], p["decode"]) == ("p150x4", 4, 52.0)


def test_bundle_perf_needs_both_columns():
    assert bundle_perf("| Eval | score |\n|---|---|\n| GSM8K | 0.9 |\n") is None
    assert bundle_perf(None) is None
