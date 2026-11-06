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
    models_diff.py roundup --old OLD.json --new NEW.json --week-end YYYY-MM-DD [--feeds F] [--dry-run] [--replace]
    models_diff.py carry-forward --from BRANCH_FEEDS.json [--feeds F]
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import llm_client
import pr_digest


# ── The change set ──────────────────────────────────────────────────────────

def _by_id(document: dict) -> dict:
    return {m["id"]: m for m in document.get("models") or [] if m.get("id")}


def _sorted_by_name(rows: list) -> list:
    return sorted(rows, key=lambda r: (str(r.get("name") or r.get("model") or "").lower(), r.get("repo") or ""))


HF_URL = "https://huggingface.co/"


def _model_url(m: dict) -> str:
    """Where a model's name links: the original model's Hugging Face card (its weights repo), which credits
    the authors and is where a reader learns what the model is; the tt-awesome page only when the record
    has no weights repo (a decision model named after its bundle)."""
    return HF_URL + m["weights"] if m.get("weights") else f"{MODELS_URL}{m['id']}/"


def _card(m: dict) -> dict:
    """The fields of a model that the digest and roundup quote for an added or removed model."""
    bundles = [b["repo"] for b in m.get("bundles") or [] if b.get("repo")]
    return dict(id=m["id"], name=m.get("name") or m["id"], source=m.get("source") or "",
                kind=m.get("kind") or "", status=m.get("status"), hardware=list(m.get("hardware") or []),
                owners=sorted({b.get("owner") or b.get("repo", "").split("/")[0] for b in m.get("bundles") or []}),
                # Models are grouped by weights repo, so one new model can arrive as several bundles
                # (gpt-oss-20b has four). Kept so the roundup can count and name each one.
                bundles=sorted(bundles), weights=m.get("weights"), purpose=m.get("purpose"), url=_model_url(m))


def diff_models(old: dict, new: dict) -> dict:
    """The change set from `old` to `new`, two models.json documents.

    Returns a dict with these keys; every list is sorted by model name.
      spec            {"old": {release, commit}, "new": {release, commit}}
      added, removed  [{id, name, source, kind, status, hardware, owners, bundles, weights, purpose, url}]
      status          [{id, name, old, new, url}]  best status changed, None on either side allowed
      entered_spec    [{id, name, status, kind, hardware, purpose, url}]  was bundle-only, now in the release
                                                   spec; kind and hardware seat it in the roundup's spec table
      bundles_added, bundles_removed  [{model, id, repo, url}]
      kind            [{id, name, old, new, url}]
      hardware        [{id, name, added: [...], url}]  hardware names the model gained
    `url` is the model's Hugging Face card, or its tt-awesome page when it has no weights repo.
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
        name, url = m.get("name") or mid, _model_url(m)
        if o.get("status") != m.get("status"):
            d["status"].append(dict(id=mid, name=name, old=o.get("status"), new=m.get("status"), url=url))
        if m.get("inSpec") and not o.get("inSpec"):
            # kind, hardware and purpose ride along so the roundup can seat it in the tt-inference-server table.
            d["entered_spec"].append(dict(id=mid, name=name, status=m.get("status"), kind=m.get("kind") or "",
                                          hardware=list(m.get("hardware") or []), purpose=m.get("purpose"), url=url))
        ob = {b["repo"] for b in o.get("bundles") or [] if b.get("repo")}
        nb = {b["repo"] for b in m.get("bundles") or [] if b.get("repo")}
        d["bundles_added"] += [dict(model=name, id=mid, repo=r, url=url) for r in sorted(nb - ob)]
        d["bundles_removed"] += [dict(model=name, id=mid, repo=r, url=url) for r in sorted(ob - nb)]
        if (o.get("kind") or "") != (m.get("kind") or ""):
            d["kind"].append(dict(id=mid, name=name, old=o.get("kind"), new=m.get("kind"), url=url))
        gained = sorted(set(m.get("hardware") or []) - set(o.get("hardware") or []))
        if gained:
            d["hardware"].append(dict(id=mid, name=name, added=gained, url=url))

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


# ── The nightly PR body ─────────────────────────────────────────────────────

# The marker the workflow's comment step strips from (sed '/tt-awesome-digest-boilerplate/,$d'), so the
# comment is just this run's changes. It is the first line of .github/pr-templates/models.md, and
# nightly.yml's pr_digest.py uses the same marker for the metadata PR.
BOILERPLATE_MARKER = "<!-- tt-awesome-digest-boilerplate -->"


def _plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _card_line(m: dict) -> str:
    """One bullet for an added or removed model: name, source, kind, status when it has one, then where it runs."""
    facts = [m["source"], m["kind"]] + ([m["status"]] if m.get("status") else [])
    where = ", ".join(m.get("hardware") or [])
    if not where and m.get("owners"):
        where = "bundles by " + ", ".join(m["owners"])
    return f"- **{m['name']}** ({', '.join(f for f in facts if f)})" + (f" — {where}" if where else "")


def render_pr_body(diff: dict, boilerplate: str) -> str:
    """The PR body for a nightly refresh: one `###` section per kind of change, then the boilerplate.

    "" when nothing changed, so the workflow falls back to the bare template. The boilerplate is
    passed in (the template file's text) rather than read here, so tests need no file.
    """
    if is_empty(diff):
        return ""
    sections = []

    def section(title, lines):
        if lines:
            sections.append(f"### {title}\n" + "\n".join(lines))

    section(f"🆕 {_plural(len(diff['added']), 'new model')}", [_card_line(m) for m in diff["added"]])
    section(f"➖ {_plural(len(diff['removed']), 'model removed', 'models removed')}", [_card_line(m) for m in diff["removed"]])
    section(f"🚀 {_plural(len(diff['entered_spec']), 'model entered the spec', 'models entered the spec')}",
            [f"- **{m['name']}** ({m['status']})" for m in diff["entered_spec"]])
    section(f"📈 {_plural(len(diff['status']), 'status change')}",
            [f"- **{m['name']}**: {m['old'] or 'not in spec'} → {m['new'] or 'not in spec'}" for m in diff["status"]])
    section(f"📦 {_plural(len(diff['bundles_added']), 'new bundle')}",
            [f"- **{b['model']}**: {b['repo']}" for b in diff["bundles_added"]])
    section(f"📦 {_plural(len(diff['bundles_removed']), 'bundle withdrawn', 'bundles withdrawn')}",
            [f"- **{b['model']}**: {b['repo']}" for b in diff["bundles_removed"]])
    section(f"🔁 {_plural(len(diff['kind']), 'kind change')}",
            [f"- **{m['name']}**: {m['old']} → {m['new']}" for m in diff["kind"]])
    section(f"🖥 {_plural(len(diff['hardware']), 'hardware addition')}",
            [f"- **{m['name']}**: {', '.join(m['added'])}" for m in diff["hardware"]])
    unreadable = diff["unreadable"]
    section("⚠ Unreadable bundles",
            [f"- now unreadable: {r}" for r in unreadable["now_unreadable"]]
            + [f"- readable again: {r}" for r in unreadable["now_readable"]])

    old_rel, new_rel = diff["spec"]["old"].get("release"), diff["spec"]["new"].get("release")
    if old_rel != new_rel:
        sections.append(f"tt-inference-server spec: {old_rel} → {new_rel}")

    body = "\n\n".join(sections) + "\n\n"
    return body + (boilerplate if boilerplate.lstrip().startswith(BOILERPLATE_MARKER)
                   else BOILERPLATE_MARKER + "\n" + boilerplate)


def write_pr_body(diff: dict, out, template) -> bool:
    """Write the PR body to `out` and return True; write nothing and return False when nothing changed.

    No file on an empty diff is deliberate: peter-evans/create-pull-request then falls back to the
    template the workflow copies into place, exactly as nightly.yml does.
    """
    body = render_pr_body(diff, Path(template).read_text())
    if not body:
        return False
    Path(out).write_text(body)
    return True


# ── The Thursday Planet roundup ─────────────────────────────────────────────

# Where a model's page lives; the planet item and its links point here. The site's canonical host,
# see src/_data/site.js. The week fragment makes each roundup's URL unique, which is what the
# planet's URL dedup and write_roundup key on.
SITE = "https://docs.tenstorrent.com/tt-awesome/"
MODELS_URL = SITE + "models/"

MODEL = "claude-haiku-4-5-20251001"  # Anthropic-direct default; the foundry path uses llm_client's default
MANIFEST_CAP = 40                    # lines of the change list handed to the model


def _kind_text(m: dict) -> str:
    """What a model is: "VLM, deep-research agent" for the two families (LLM, VLM), where the purpose says
    what this member is for; the purpose alone for a specific kind, since "Embedding, multimodal embedding"
    says it twice; the kind alone when the builder inferred no purpose."""
    kind, purpose = m.get("kind") or "", m.get("purpose")
    if not purpose:
        return kind
    return f"{kind}, {purpose}" if kind in ("LLM", "VLM") else purpose


def week_fragment(week_end: date) -> str:
    """"week-2026-W45": the ISO week the roundup covers, named by its last day."""
    year, week, _ = week_end.isocalendar()
    return f"week-{year}-W{week:02d}"


def _new_spec_models(diff: dict) -> list:
    return [m for m in diff["added"] if m["source"] == "tt-inference-server"] + [
        dict(m, source="tt-inference-server") for m in diff["entered_spec"]]


def _new_bundles(diff: dict) -> int:
    """Bundles that are new this week: every bundle of a brand-new bundle-only model, plus bundles added to
    models already listed."""
    return (sum(max(1, len(m.get("bundles") or [])) for m in diff["added"] if m["source"] != "tt-inference-server")
            + len(diff["bundles_added"]))


def _count_changes(diff: dict) -> int:
    lists = ("added", "removed", "status", "entered_spec", "bundles_added", "bundles_removed", "kind", "hardware")
    return sum(len(diff[k]) for k in lists) + sum(len(v) for v in diff["unreadable"].values())


def roundup_title(diff: dict) -> str:
    """"Models this week: 8 new on tt-inference-server, 7 new tt-model bundles"; zero counts are left out."""
    parts = []
    n_spec, n_bundles = len(_new_spec_models(diff)), _new_bundles(diff)
    if n_spec:
        parts.append(f"{n_spec} new on tt-inference-server")
    if n_bundles:
        parts.append(f"{_plural(n_bundles, 'new tt-model bundle')}")
    if not parts:
        parts.append(_plural(_count_changes(diff), "change"))
    return "Models this week: " + ", ".join(parts)


def _manifest_lines(diff: dict) -> list:
    lines = []
    for m in diff["added"]:
        if m["source"] == "tt-inference-server":
            where = (" on " + ", ".join(m["hardware"])) if m["hardware"] else ""
            lines.append(f"new on tt-inference-server: {m['name']} ({_kind_text(m)}, {m['status']}){where}")
        else:
            # No owners and no repo ids: the paragraph is about models, and Taylor asked that it never
            # single out who published a bundle. The table under the paragraph carries the repo ids.
            n_b = len(m.get("bundles") or [])
            lines.append(f"new tt-model {'bundles' if n_b > 1 else 'bundle'}: {m['name']} ({_kind_text(m)})"
                         + (f", {n_b} bundles" if n_b > 1 else ""))
    for m in diff["entered_spec"]:
        lines.append(f"now on tt-inference-server: {m['name']} ({m['status']})")
    for m in diff["status"]:
        if not any(e["id"] == m["id"] for e in diff["entered_spec"]):
            lines.append(f"status: {m['name']} {m['old'] or 'not in spec'} → {m['new'] or 'not in spec'}")
    # Bundle changes to a listed model: counted per model, never by repo id, for the same reason as above.
    for model_name, n in _per_model(diff["bundles_added"]).items():
        lines.append(f"new bundle for {model_name}" if n == 1 else f"{n} new bundles for {model_name}")
    for model_name, n in _per_model(diff["bundles_removed"]).items():
        lines.append(f"bundle withdrawn from {model_name}" if n == 1 else f"{n} bundles withdrawn from {model_name}")
    for m in diff["removed"]:
        lines.append(f"removed: {m['name']}")
    for m in diff["kind"]:
        lines.append(f"kind: {m['name']} {m['old']} → {m['new']}")
    for m in diff["hardware"]:
        lines.append(f"new hardware for {m['name']}: {', '.join(m['added'])}")
    old_rel, new_rel = diff["spec"]["old"].get("release"), diff["spec"]["new"].get("release")
    if old_rel != new_rel:
        lines.append(f"tt-inference-server spec: {old_rel} → {new_rel}")
    return lines


def _per_model(changes: list) -> dict:
    """{model name: how many bundle entries}, in the order the diff lists them."""
    counts: dict = {}
    for b in changes:
        counts[b["model"]] = counts.get(b["model"], 0) + 1
    return counts


def build_manifest(diff: dict, cap: int = MANIFEST_CAP) -> str:
    """The change list as plain text for the model, one line per change, cut at `cap` lines."""
    lines = _manifest_lines(diff)
    if len(lines) > cap:
        lines = lines[:cap] + [f"… and {len(lines) - cap} more"]
    return "\n".join(lines)


def request_roundup_paragraph(manifest: str, *, week: str, anthropic_api_key: str = "",
                              github_token: str = "", foundry_api_key: str = "") -> str:
    """The one model call: the roundup paragraph, or "" on any failure. Never raises."""
    try:
        text = llm_client.complete(
            "models-roundup", {"week": week, "manifest": manifest},
            anthropic_model=MODEL, anthropic_api_key=anthropic_api_key,
            github_token=github_token, foundry_api_key=foundry_api_key,
        )
    except Exception as e:  # noqa: BLE001 — the item ships with the fallback paragraph instead
        print(f"  WARN models_diff: roundup paragraph unavailable ({e})", file=sys.stderr)
        return ""
    if not text:
        print("  WARN models_diff: provider returned no paragraph; using the fallback", file=sys.stderr)
        return ""
    # Strip a leading heading the prompt forbade, as pr_digest does with its lede.
    return pr_digest._LEADING_HEADING_RE.sub("", text, count=1).strip()


def _join(names: list) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def fallback_paragraph(diff: dict) -> str:
    """One sentence per kind of change, for a week whose model call failed. Plain prose, one line."""
    sentences = []
    spec = [m["name"] for m in _new_spec_models(diff)]
    if spec:
        sentences.append(f"New on tt-inference-server: {_join(spec)}.")
    # Names only: the bundle table under the paragraph carries the repo ids, and the prose never names a
    # publisher (see _manifest_lines).
    bundled = [m["name"] for m in diff["added"] if m["source"] != "tt-inference-server"]
    if bundled:
        sentences.append(f"New as tt-model bundles: {_join(bundled)}.")
    more = list(_per_model(diff["bundles_added"]))
    if more:
        sentences.append(f"New bundles for {_join(more)}.")
    promoted = [f"{m['name']} to {m['new']}" for m in diff["status"]
                if m["new"] and not any(e["id"] == m["id"] for e in diff["entered_spec"])]
    if promoted:
        sentences.append(f"Status changes: {_join(promoted)}.")
    left = [m["name"] for m in diff["status"] if m["old"] and not m["new"]]
    if left:
        sentences.append(f"{_join(left)} left tt-inference-server but {'stays' if len(left) == 1 else 'stay'} listed as "
                         f"{'a bundle' if len(left) == 1 else 'bundles'}.")
    withdrawn = list(_per_model(diff["bundles_removed"]))
    if withdrawn:
        sentences.append(f"Bundles withdrawn from {_join(withdrawn)}.")
    removed = [m["name"] for m in diff["removed"]]
    if removed:
        sentences.append(f"Removed: {_join(removed)}.")
    kinds = [f"{m['name']} from {m['old']} to {m['new']}" for m in diff["kind"]]
    if kinds:
        sentences.append(f"Reclassified: {_join(kinds)}.")
    hardware = [f"{m['name']} on {_join(m['added'])}" for m in diff["hardware"]]
    if hardware:
        sentences.append(f"Now also runs: {_join(hardware)}.")
    unreadable = diff["unreadable"]
    if unreadable["now_unreadable"]:
        sentences.append(f"Manifests that could not be read this week: {_join(unreadable['now_unreadable'])}.")
    if unreadable["now_readable"]:
        sentences.append(f"Readable again: {_join(unreadable['now_readable'])}.")
    old_rel, new_rel = diff["spec"]["old"].get("release"), diff["spec"]["new"].get("release")
    if old_rel != new_rel:
        sentences.append(f"tt-inference-server moved from {old_rel} to {new_rel}.")
    return " ".join(sentences)


def link_models(text: str, models: list) -> str:
    """The first whole-word mention of each model's name becomes a link to its page.

    Longest names first, so "Qwen3.5-27B-Instruct" is linked as itself and not as "Qwen3.5-27B"
    plus a suffix. A mention already inside a markdown link is left alone.
    """
    for m in sorted(models, key=lambda m: -len(m["name"])):
        name = m["name"]
        # Not preceded by a word character, "[" (link text) or "/" (inside a URL); not followed by a word
        # character or "-" (a longer name) or "/" or "]" (a URL or link text). A period after the name is a
        # sentence end and must still match.
        pattern = re.compile(r"(?<![\w\[/-])" + re.escape(name) + r"(?![\w\]/-])")
        pos = 0
        while True:
            hit = pattern.search(text, pos)
            if not hit:
                break
            # Inside "[...](...)" already? Then this mention is link text or a URL; look further.
            open_br = text.rfind("[", 0, hit.start())
            if open_br != -1 and "]" not in text[open_br:hit.start()] and "](" in text[hit.end():hit.end() + 2]:
                pos = hit.end()
                continue
            if text[hit.end():hit.end() + 2] == "](":
                pos = hit.end()
                continue
            text = text[:hit.start()] + _link(m) + text[hit.end():]
            break
    return text


def _link(m: dict) -> str:
    return f"[{m['name']}]({m.get('url') or MODELS_URL + m['id'] + '/'})"


def _bundle_link(repo: str) -> str:
    """A bundle id linked to its own Hugging Face card: the thing `tt model pull` takes."""
    return f"[{repo}]({HF_URL}{repo})"


def _cell(text: str) -> str:
    """A table cell: never empty (an em dash stands for "none"), never a stray pipe."""
    return (text or "—").replace("|", "\\|")


def _spec_table(models: list) -> str:
    rows = [f"| {_link(m)} | {_cell(_kind_text(m))} | {_cell(m.get('status'))} | {_cell(', '.join(m.get('hardware') or []))} |"
            for m in models]
    return "| Model | Kind | Status | Hardware |\n|---|---|---|---|\n" + "\n".join(rows)


def _bundle_table(models: list) -> str:
    rows = [f"| {_link(m)} | {_cell(_kind_text(m))} | {_cell(', '.join(_bundle_link(r) for r in m.get('bundles') or []))} "
            f"| {_cell(', '.join(m.get('hardware') or []))} |" for m in models]
    return "| Model | Kind | Bundle | Hardware |\n|---|---|---|---|\n" + "\n".join(rows)


def _also_bullets(diff: dict) -> list:
    """Everything that is neither a new model nor a model entering the spec, one bullet each."""
    entered = {e["id"] for e in diff["entered_spec"]}
    bullets = []
    for m in diff["status"]:
        if m["id"] not in entered:
            bullets.append(f"- {_link(m)}: {m['old'] or 'not in spec'} → {m['new'] or 'not in spec'}")
    for b in diff["bundles_added"]:
        bullets.append(f"- {_link(dict(id=b['id'], name=b['model'], url=b.get('url')))}: new bundle {_bundle_link(b['repo'])}")
    for b in diff["bundles_removed"]:
        bullets.append(f"- {_link(dict(id=b['id'], name=b['model'], url=b.get('url')))}: bundle {b['repo']} withdrawn")
    for m in diff["removed"]:
        bullets.append(f"- {m['name']}: removed from the list")
    for m in diff["kind"]:
        bullets.append(f"- {_link(m)}: reclassified {m['old']} → {m['new']}")
    for m in diff["hardware"]:
        if m["id"] not in entered:   # the table row of a model entering the spec already shows its hardware
            bullets.append(f"- {_link(m)}: now also on {', '.join(m['added'])}")
    for r in diff["unreadable"]["now_unreadable"]:
        bullets.append(f"- Bundle manifest now unreadable: {r}")
    for r in diff["unreadable"]["now_readable"]:
        bullets.append(f"- Bundle manifest readable again: {r}")
    old_rel, new_rel = diff["spec"]["old"].get("release"), diff["spec"]["new"].get("release")
    if old_rel != new_rel:
        bullets.append(f"- tt-inference-server spec {old_rel} → {new_rel}")
    return bullets


def build_roundup(diff: dict, week_end: date, paragraph: str, now: datetime) -> dict:
    """The Planet item for the week ending `week_end`, written as block markdown.

    The body is `paragraph` (the model's reply or the fallback) with model names linked, then the
    mechanical part that makes the item complete whatever the paragraph said: a table of the models
    new on tt-inference-server (kind, status, hardware), a table of the new tt-model bundles (kind,
    bundle repo, hardware), and an "Also this week" bullet list for status, bundle, kind, hardware and
    spec changes. Empty sections are left out. The item carries body: "markdown" so planet-item.njk
    renders it with block markdown instead of the one-paragraph inline filter.
    """
    spec_new = _new_spec_models(diff)
    bundle_new = [m for m in diff["added"] if m["source"] != "tt-inference-server"]
    mentioned = (spec_new + bundle_new + diff["status"] + diff["kind"] + diff["hardware"]
                 + [dict(id=b["id"], name=b["model"], url=b.get("url")) for b in diff["bundles_added"] + diff["bundles_removed"]])
    sections = []
    if paragraph.strip():
        sections.append(link_models(paragraph.strip(), mentioned))
    if spec_new:
        sections += ["**New on tt-inference-server**", _spec_table(spec_new)]
    if bundle_new:
        sections += ["**New tt-model bundles**", _bundle_table(bundle_new)]
    bullets = _also_bullets(diff)
    if bullets:
        sections += ["**Also this week**", "\n".join(bullets)]
    return dict(
        type="article",
        source="models-roundup",
        approved=True,
        title=roundup_title(diff),
        url=f"{MODELS_URL}#{week_fragment(week_end)}",
        description="\n\n".join(sections),
        body="markdown",
        date=week_end.isoformat(),
        dateISO=now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        label="Models this week",
        projectName="Models",
        projectId=None,
        affiliation="official",
    )


def _declined_urls(feeds_path: Path) -> set:
    """URLs in planet_declined.json, kept next to the feed file by scripts/decline_planet_item.py.

    A maintainer who declined a week's roundup moved its URL there, and the item must stay gone: a
    forced rerun of the roundup, or a stale PR branch handed to carry_forward, would otherwise put it
    back with approved: true. Same rule as fetch_planet_feeds.load_declined_urls.
    """
    path = feeds_path.with_name("planet_declined.json")
    if not path.exists():
        return set()
    try:
        rows = json.loads(path.read_text())
    except ValueError as e:
        print(f"  WARN models_diff: could not read {path}: {e}", file=sys.stderr)
        return set()
    return {r["url"] for r in rows if isinstance(r, dict) and r.get("url")}


def write_roundup(item: dict, feeds_path, replace: bool = False) -> bool:
    """Insert the item into planet_feeds.json in dateISO order.

    False, and no write, when its URL is on the declined list, or already in the feed unless
    `replace` is set (a dispatch with roundup=true regenerates the week after a prompt change)."""
    path = Path(feeds_path)
    if item["url"] in _declined_urls(path):
        print(f"  SKIP roundup {item['url']}: declined by a maintainer (planet_declined.json)")
        return False
    items = json.loads(path.read_text()) if path.exists() else []
    if any(i.get("url") == item["url"] for i in items):
        if not replace:
            return False
        items = [i for i in items if i.get("url") != item["url"]]
    items.append(item)
    items.sort(key=lambda i: i.get("dateISO") or "", reverse=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    return True


def carry_forward(branch_feeds, feeds_path) -> int:
    """Copy the roundup items an unmerged PR branch holds into `feeds_path`; returns how many were added.

    peter-evans/create-pull-request rebuilds the PR branch from main plus the run's own tree on every
    run, so a Thursday item that has not been merged by Friday would vanish from the PR. The Friday
    run therefore reads the branch's planet_feeds.json first and keeps every "models-roundup" item
    whose URL main does not have. Only roundup items are carried: anything else on the branch is
    the previous run's models.json business, which this run rebuilds itself.
    """
    branch_path = Path(branch_feeds)
    if not branch_path.exists():
        return 0
    added = 0
    for item in json.loads(branch_path.read_text()):
        if item.get("source") == "models-roundup" and item.get("url") and write_roundup(item, feeds_path):
            added += 1
    return added


# ── CLI ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
FEEDS_DEFAULT = ROOT / "src" / "_data" / "planet_feeds.json"
TEMPLATE_DEFAULT = ROOT / ".github" / "pr-templates" / "models.md"


def _load(path) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list | None = None) -> int:
    """`pr-body` writes the nightly PR body; `roundup` adds the week's Planet item. See the module docstring."""
    import argparse
    ap = argparse.ArgumentParser(description="What changed between two models.json documents.")
    sub = ap.add_subparsers(dest="command", required=True)

    pb = sub.add_parser("pr-body", help="write the nightly PR body, or nothing when the files are the same")
    pb.add_argument("--old", required=True, help="models.json as committed")
    pb.add_argument("--new", required=True, help="models.json the run just built")
    pb.add_argument("--out", required=True, help="where to write the body (left absent when nothing changed)")
    pb.add_argument("--template", default=str(TEMPLATE_DEFAULT), help="the boilerplate appended under the digest")

    ru = sub.add_parser("roundup", help="add the week's 'Models this week' item to planet_feeds.json")
    ru.add_argument("--old", required=True, help="models.json as of a week ago")
    ru.add_argument("--new", required=True, help="models.json the run just built")
    ru.add_argument("--week-end", required=True, help="the Thursday the week ends on, YYYY-MM-DD")
    ru.add_argument("--feeds", default=str(FEEDS_DEFAULT))
    ru.add_argument("--dry-run", action="store_true", help="print the item instead of writing it")
    ru.add_argument("--replace", action="store_true", help="overwrite the week's item if the feed already has one")

    cf = sub.add_parser("carry-forward", help="keep the roundup items of an unmerged PR branch in planet_feeds.json")
    cf.add_argument("--from", dest="branch_feeds", required=True, help="planet_feeds.json as on the PR branch")
    cf.add_argument("--feeds", default=str(FEEDS_DEFAULT))

    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if args.command == "carry-forward":
        n = carry_forward(args.branch_feeds, args.feeds)
        print(f"carried {n} roundup item{'s' if n != 1 else ''} forward from the PR branch")
        return 0

    diff = diff_models(_load(args.old), _load(args.new))

    if args.command == "pr-body":
        if write_pr_body(diff, args.out, args.template):
            print(f"wrote {args.out}")
        else:
            print("no changes; no PR body written")
        return 0

    # roundup
    if is_empty(diff):
        print("no changes this week; no roundup item")
        return 0
    week_end = date.fromisoformat(args.week_end)
    paragraph = request_roundup_paragraph(
        build_manifest(diff), week=f"the week ending {week_end.isoformat()}",
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        foundry_api_key=os.environ.get("FOUNDRY_API_KEY", ""),
    ) or fallback_paragraph(diff)
    item = build_roundup(diff, week_end, paragraph, datetime.now(timezone.utc))
    if args.dry_run:
        print(f"--- DRY RUN: roundup item for {week_fragment(week_end)} ---")
        print(json.dumps(item, indent=2, ensure_ascii=False))
        return 0
    if write_roundup(item, args.feeds, replace=args.replace):
        print(f"{'replaced' if args.replace else 'added'} roundup {item['url']} in {args.feeds}")
    else:
        print(f"roundup {item['url']} already in {args.feeds}; nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
