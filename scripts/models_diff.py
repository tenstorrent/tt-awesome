#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

"""What changed between two models.json documents, and the two things written from that.

src/_data/models.json is rebuilt every night by .github/workflows/nightly-models.yml from
tt-inference-server's release spec and the tt-model catalog (scripts/build_models_data.py). Two
consumers read the change set this module computes:

  1. The nightly PR body. The refresh PR used to carry a fixed paragraph, so a reviewer had to
     read a 1 MB JSON diff to learn what the run changed. `render_pr_body` lists it instead:
     models added and removed, status changes, models entering the spec, new and withdrawn
     bundles, kind and hardware changes, the spec release bump. Mechanical, no model call.

  2. The Thursday Planet roundup. Once a week the same diff, taken over the seven days ending
     that Thursday (models.json on main a week ago against the file the run just built), becomes
     one Planet item: "Models this week: ...". Its paragraph is the one LLM call in this module
     (`request_roundup_paragraph`); `fallback_paragraph` stands in when the call fails, so the
     item ships either way. A week with no changes produces no item and no call.

Design notes:

* Both sides are plain dicts in the shape build_models_data.py writes. Keys that an older file
  lacks (a model with no `hardware`, a document with no `unreadableBundles`) read as empty, so a
  week-old file from before a schema change still diffs.
* A model that leaves the release spec but keeps a bundle is a status change (X -> None), not a
  removal: it is still on the Models pages.
* Lists are sorted by model name so the same change set renders the same text every time.

Usage (CLI, see main()):
    models_diff.py pr-body --old OLD.json --new NEW.json --out pr-body.md [--template T.md]
    models_diff.py roundup --old OLD.json --new NEW.json --week-end YYYY-MM-DD [--feeds F] [--dry-run]
"""

from __future__ import annotations


# ── The change set ──────────────────────────────────────────────────────────

def _by_id(document: dict) -> dict:
    return {m["id"]: m for m in document.get("models") or [] if m.get("id")}


def _sorted_by_name(rows: list) -> list:
    return sorted(rows, key=lambda r: (str(r.get("name") or r.get("model") or "").lower(), r.get("repo") or ""))


def _card(m: dict) -> dict:
    """The fields of a model that the digest and roundup quote for an added or removed model."""
    return dict(id=m["id"], name=m.get("name") or m["id"], source=m.get("source") or "",
                kind=m.get("kind") or "", status=m.get("status"), hardware=list(m.get("hardware") or []),
                owners=sorted({b.get("owner") or b.get("repo", "").split("/")[0] for b in m.get("bundles") or []}))


def diff_models(old: dict, new: dict) -> dict:
    """The change set from `old` to `new`, two models.json documents.

    Returns a dict with these keys; every list is sorted by model name.
      spec            {"old": {release, commit}, "new": {release, commit}}
      added, removed  [{id, name, source, kind, status, hardware, owners}]
      status          [{id, name, old, new}]       best status changed, None on either side allowed
      entered_spec    [{id, name, status}]         was bundle-only, now in the release spec
      bundles_added, bundles_removed  [{model, id, repo}]
      kind            [{id, name, old, new}]
      hardware        [{id, name, added: [...]}]   hardware names the model gained
      unreadable      {"now_unreadable": [...], "now_readable": [...]}  bundle repos whose manifest state flipped
    """
    om, nm = _by_id(old), _by_id(new)
    d = dict(spec=dict(old=dict(old.get("spec") or {}), new=dict(new.get("spec") or {})),
             added=[], removed=[], status=[], entered_spec=[], bundles_added=[], bundles_removed=[],
             kind=[], hardware=[])

    for mid, m in nm.items():
        if mid not in om:
            d["added"].append(_card(m))
            continue
        o = om[mid]
        name = m.get("name") or mid
        if o.get("status") != m.get("status"):
            d["status"].append(dict(id=mid, name=name, old=o.get("status"), new=m.get("status")))
        if m.get("inSpec") and not o.get("inSpec"):
            d["entered_spec"].append(dict(id=mid, name=name, status=m.get("status")))
        ob = {b["repo"] for b in o.get("bundles") or [] if b.get("repo")}
        nb = {b["repo"] for b in m.get("bundles") or [] if b.get("repo")}
        d["bundles_added"] += [dict(model=name, id=mid, repo=r) for r in sorted(nb - ob)]
        d["bundles_removed"] += [dict(model=name, id=mid, repo=r) for r in sorted(ob - nb)]
        if (o.get("kind") or "") != (m.get("kind") or ""):
            d["kind"].append(dict(id=mid, name=name, old=o.get("kind"), new=m.get("kind")))
        gained = sorted(set(m.get("hardware") or []) - set(o.get("hardware") or []))
        if gained:
            d["hardware"].append(dict(id=mid, name=name, added=gained))

    d["removed"] = [_card(m) for mid, m in om.items() if mid not in nm]

    ou, nu = set(old.get("unreadableBundles") or []), set(new.get("unreadableBundles") or [])
    d["unreadable"] = dict(now_unreadable=sorted(nu - ou), now_readable=sorted(ou - nu))

    for key in ("added", "removed", "status", "entered_spec", "bundles_added", "bundles_removed", "kind", "hardware"):
        d[key] = _sorted_by_name(d[key])
    return d


def is_empty(diff: dict) -> bool:
    """True when nothing changed: every list empty, no manifest flipped, and the spec release the same."""
    lists = ("added", "removed", "status", "entered_spec", "bundles_added", "bundles_removed", "kind", "hardware")
    if any(diff.get(key) for key in lists):
        return False
    if any(diff["unreadable"].values()):
        return False
    return diff["spec"]["old"].get("release") == diff["spec"]["new"].get("release")
