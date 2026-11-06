#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.
"""Build src/_data/models.json, the data behind the Models pages of the site.

Every fact comes from one of three sources. Nothing is measured and nothing is taken from anywhere else.

  1. tt-inference-server (a checkout of its main branch). It takes precedence.
       release_model_spec.json            the models, their devices, status, context, users, parsers
       workflows/workflow_types.py        DeviceTypes.to_product_str / to_mesh_device_str: the names of the hardware
       docs/model_support/<kind>/*.md     which per-model support pages exist (linked, never copied)
  2. tt-model (the CLI, from tt-model-manager)
       `tt-model search --catalog --json` the published bundles
       `tt-model info <repo>`             each bundle's manifest: weights repo, kind, hardware profiles,
                                          context length, parsers and the card's Hub task tag
  3. This repo's own scripts/data/model_families.json, a short list of name prefixes that decides a model's family,
     and scripts/data/model_kinds_inferred.json, the kind of a bundle whose card states no task. That file is an
     inference (each entry says why), applied only when no task is stated, and the pages mark the kind as inferred.

A bundle belongs to a model when the weights repo in its manifest is the model's Hugging Face repo, or when the
last part of the two names matches. A bundle that matches no model is a model of its own, named after its weights
repo. Hardware is named the way tt-inference-server names it (DeviceTypes.to_product_str); a name it does not list
keeps the spelling it was found with.

The nightly workflow (.github/workflows/nightly-models.yml) runs this. By hand:
  tt-model search --catalog --json --limit 300 > catalog.json
  python3 scripts/build_models_data.py --isrv <tt-inference-server checkout> --catalog catalog.json

The output is deterministic (sorted, no build date), so a night with no upstream change makes no diff. The script
refuses to write a list that shrank by more than half, so a failed fetch cannot empty the site.
"""
import argparse
import ast
import concurrent.futures as cf
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--isrv", required=True, help="tt-inference-server checkout (release_model_spec.json, workflows/, docs/)")
ap.add_argument("--catalog", required=True, help="JSON from `tt-model search --catalog --json`")
ap.add_argument("--limit", type=int, default=0,
                help="the --limit given to tt-model search; a catalog with exactly this many rows was cut off")
ap.add_argument("--spec-commit", default="", help="commit of the checkout; read from .git/HEAD when left out, and required when --isrv has no .git directory")
ap.add_argument("--manifests", default="", help="JSON cache of `tt-model info` output. Read when it exists; written after a fetch.")
ap.add_argument("--hf-cards", default="", help="JSON cache of each original model's Hugging Face card metadata (pipeline tag, "
                "tags). Read when it exists; written after a fetch. HF_TOKEN is used when set.")
ap.add_argument("--out", default=str(HERE.parent / "src/_data/models.json"))
args = ap.parse_args()
ISRV = pathlib.Path(args.isrv)

KIND = {"LLM": "LLM", "VLM": "VLM", "IMAGE": "Image generation", "VIDEO": "Video generation",
        "AUDIO": "Speech-to-text", "TEXT_TO_SPEECH": "Text-to-speech", "EMBEDDING": "Embedding", "CNN": "CNN"}
# The page tt-studio opens for a model type (tt-studio app/frontend/src/api/modelsDeployedApis.ts, getDestinationFromModelType).
# tt-studio deploys tt-inference-server models, so this is set only for models in the release spec.
STUDIO = {"LLM": "Chat", "VLM": "Chat, with image input", "IMAGE": "Image generation", "VIDEO": "Video generation",
          "AUDIO": "Speech to text", "TEXT_TO_SPEECH": "Text to speech", "EMBEDDING": "Embedding demo", "CNN": "Object detection"}
# Folder under docs/model_support for each model type.
DOCDIR = {"LLM": "llm", "VLM": "vlm", "IMAGE": "image", "VIDEO": "video", "AUDIO": "audio",
          "TEXT_TO_SPEECH": "tts", "EMBEDDING": "embedding", "CNN": "cnn"}
# Hugging Face task tags, in the kind names above. Any other tag is shown as the tag itself.
TAG_KIND = {"text-generation": "LLM", "image-text-to-text": "VLM", "text-to-speech": "Text-to-speech",
            "automatic-speech-recognition": "Speech-to-text", "feature-extraction": "Embedding"}
# A bundle with no task tag is grouped by what its manifest says it is served with.
NOT_STATED = {"vllm-plugin": "Served with vLLM, task not stated", "vllm": "Served with vLLM, task not stated",
              "vllm-fork": "Served with vLLM, task not stated", "tt-dit-server": "Diffusion server, task not stated",
              "http-server": "HTTP server, task not stated"}
NOT_STATED_ANY = "Task not stated"
RANK = {"COMPLETE": 3, "FUNCTIONAL": 2, "EXPERIMENTAL": 1}
# The clients `tt launch` can connect to a served model (tt-cli, src/tenstorrent/launchers/__init__.py), and whether each
# needs tool calling (the launcher's requires_tool_calling). tt-cli's rule (commands/launch.py): a client needs a chat
# model, which tt serves through vLLM, and a client that needs tool calling also needs a tool-call parser. Keep this
# list in step with that registry.
CLIENTS = [("opencode", "Terminal", True), ("pi", "Terminal", True), ("aider", "Terminal", True),
           ("qwencode", "Terminal", True), ("hermes", "Terminal", True),
           ("openwebui", "Web service", False), ("anythingllm", "Web service", False)]
VLLM_BUNDLE_KINDS = {"vllm", "vllm-plugin", "vllm-fork"}
# tt-inference-server lists these products as one card each (workflow_types.py: "Single P300 card (2 dies)").
SINGLE_CARD_KEYS = {"E150", "N150", "N300", "P100", "P150", "P300"}


def die(msg):
    sys.exit("build_models_data: " + msg)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())



# ---- Headline speed figures for the browse cards (LLM and VLM only) ----
TIER_FOR_STATUS = {"COMPLETE": "complete", "FUNCTIONAL": "functional", "EXPERIMENTAL": "functional"}


def spec_perf(refs, status):
    """tt-inference-server's reference entry for 128 in / 128 out at one user: the figure for the row's status tier.
    These are targets the release spec sets for that status, not measurements."""
    for e in refs or []:
        if (e.get("isl"), e.get("osl"), e.get("max_concurrency")) != (128, 128, 1):
            continue
        tgt = e.get("targets") or {}
        tier = TIER_FOR_STATUS.get(status.upper(), "functional")
        t = tgt.get(tier) or (tgt.get("target") if tgt.get("target") and not tgt.get(tier) else None)
        tier = tier if tgt.get(tier) else "target"
        if t and t.get("tput_user") and t.get("ttft_ms"):
            return dict(decode=t["tput_user"], ttft=t["ttft_ms"], tier=tier, measured=False)
    return None


# Board names as a bundle's card writes them, with the number of chips on that board. Hand-kept:
# P300 is one card with two chips; the x2, x4 and x8 names count P150 or P300 boards.
CHIPS = {"p100": 1, "p150": 1, "p150x2": 2, "p150x4": 4, "p150x8": 8, "p300": 2, "p300x2": 4}
BOARD = re.compile(r"\b(p100|p150x8|p150x4|p150x2|p150|p300x2|p300)\b", re.I)


def md_number(cell):
    m = re.search(r"-?\d[\d,]*\.?\d*", cell.replace("**", ""))
    return float(m.group(0).replace(",", "")) if m else None


def bundle_perf(text):
    """Speed at one user for the shortest prompt, read from the latency table in a bundle card's performance text.
    Returns None unless a table gives both time to first token and decode speed per user."""
    heading, lines, best = "", (text or "").split("\n"), None
    i = 0
    while i < len(lines) - 2:
        line = lines[i].strip()
        if line.startswith("#"):
            heading = line
        if line.startswith("|") and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            head = [c.strip().strip("*").lower() for c in line.strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            col = lambda pred: next((n for n, h in enumerate(head) if pred(h)), None)
            c_ttft = col(lambda h: h.startswith("ttft") and "p99" not in h and "(ms)" in h)
            c_dec = col(lambda h: "decode" in h and ("tok/s/u" in h or "/user" in h or h == "decode tok/s"))
            c_isl = col(lambda h: h in ("isl", "input tokens"))
            c_users = col(lambda h: h in ("users", "concurrency", "c"))
            c_prof = col(lambda h: h == "profile")
            if c_ttft is not None and c_dec is not None:
                cands = []
                for r in rows:
                    if len(r) != len(head):
                        continue
                    if c_users is not None and md_number(r[c_users]) != 1:
                        continue
                    isl = md_number(r[c_isl]) if c_isl is not None else 0
                    ttft, dec = md_number(r[c_ttft]), md_number(r[c_dec])
                    if isl is None or not ttft or not dec:
                        continue
                    board = BOARD.search(r[c_prof]) if c_prof is not None else BOARD.search(heading)
                    cands.append((isl != 128, isl, ttft, dec, board.group(0).lower() if board else None))
                if cands:
                    _, isl, ttft, dec, board = min(cands, key=lambda c: c[:2])
                    # Time to first token is only comparable at the shortest prompt; at any other length it is left out.
                    return dict(decode=dec, ttft=ttft if isl in (0, 128) else None, board=board, chips=CHIPS.get(board), measured=True)
            i = j
            continue
        i += 1
    return best


def k(n):
    return f"{n // 1024}K" if n and n >= 1024 else (str(n) if n else None)


def params(p):
    if not p:
        return None
    return f"{p:g}B" if p >= 1 else f"{p * 1000:g}M"


# ---- hardware names, read from tt-inference-server's own code ----
def read_device_tables(path):
    """Enum member names, {ENUM_NAME: product string} and {ENUM_NAME: mesh string}, from DeviceTypes."""
    tree = ast.parse(path.read_text())
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DeviceTypes"), None)
    if not cls:
        die(f"no DeviceTypes class in {path}")
    members = [t.id for n in cls.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)]
    tables = {}
    for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ("to_product_str", "to_mesh_device_str")):
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                tables[fn.name] = {kk.attr: vv.value for kk, vv in zip(node.value.keys, node.value.values)
                                   if isinstance(kk, ast.Attribute) and isinstance(vv, ast.Constant)}
    if "to_product_str" not in tables or "to_mesh_device_str" not in tables:
        die("could not read to_product_str and to_mesh_device_str from DeviceTypes")
    return members, tables["to_product_str"], tables["to_mesh_device_str"]


MEMBERS, PRODUCT, MESH = read_device_tables(ISRV / "workflows/workflow_types.py")
BY_MESH = {v.lower(): kk for kk, v in MESH.items()}
HW_SEEN = {}   # lower-case name -> one spelling, for names tt-inference-server does not list (see choose_spellings)


def hardware(raw):
    """-> {raw, key, product, listed}. `key` is the DeviceTypes member when tt-inference-server lists the name."""
    r = str(raw).strip()
    enum = r.upper() if r.upper() in PRODUCT else BY_MESH.get(r.lower())
    if enum and enum in PRODUCT:
        return dict(raw=r, key=enum, product=PRODUCT[enum], listed=True)
    return dict(raw=r, key=None, product=HW_SEEN.get(r.lower(), r), listed=False)


# ---- tt-inference-server models ----
spec = json.load(open(ISRV / "release_model_spec.json"))
rows = []


def walk(x):
    if isinstance(x, dict):
        if "hf_model_repo" in x:
            rows.append(x)
            return
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(spec["model_specs"])
rows = [r for r in rows if r["model_type"] != "TRAINING"]
DOCS = ISRV / "docs/model_support"

models = {}
for r in rows:
    m = models.setdefault(r["hf_model_repo"], dict(
        name=r["model_name"], upstream=r["hf_model_repo"], weights=r.get("hf_weights_repo"),
        kind=KIND[r["model_type"]], kindFrom="tt-inference-server model type", modelType=r["model_type"],
        kindInferred=False, studio=STUDIO.get(r["model_type"]), params=params(r.get("param_count")), minDiskGb=r.get("min_disk_gb"), minRamGb=r.get("min_ram_gb"),
        modalities=r.get("supported_modalities"), rows=[], bundles=[], inSpec=True,
        serve=r["model_name"], toolParser=None, reasoningParser=None))
    meta = r.get("metadata") or {}
    if r["inference_engine"] == "vLLM":
        m["toolParser"] = m["toolParser"] or meta.get("tool_call_parser_name")
        m["reasoningParser"] = m["reasoningParser"] or meta.get("reasoning_parser_name")
    dm = r["device_model_spec"]
    hw = hardware(r["device_type"])
    doc = f"{DOCDIR[r['model_type']]}/{r['model_name']}_{r['device_type'].lower()}.md"
    impl = r.get("impl") or {}
    m["rows"].append(dict(
        perf=spec_perf(dm.get("perf_reference"), r["status"]),
        hardware=hw["product"], deviceKey=r["device_type"], listed=hw["listed"], engine=r["inference_engine"],
        status=r["status"].title(), context=k(dm.get("max_context")), users=dm.get("max_concurrency"),
        impl=impl.get("impl_name"), codeLink=r.get("code_link"), ttMetal=r.get("tt_metal_commit"),
        vllm=r.get("vllm_commit"), image=r.get("docker_image"), version=r.get("version"),
        doc=doc if (DOCS / doc).exists() else None))
for m in models.values():
    seen, uniq = set(), []
    for x in sorted(m["rows"], key=lambda x: (-RANK[x["status"].upper()], x["hardware"], x["deviceKey"], x["engine"], x["impl"] or "")):
        # Two spec rows can share a product name (GALAXY and GALAXY_T3K are both WH Galaxy) or a device with two
        # implementations, so the key carries the device key and the implementation.
        key = (x["deviceKey"], x["engine"], x["impl"])
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    m["rows"] = uniq
    m["status"] = max((x["status"] for x in uniq), key=lambda s: RANK[s.upper()])
    m["impls"] = sorted({x["impl"] for x in uniq if x["impl"]})

by_repo, by_name = {}, {}
for m in models.values():
    for repo in (m["upstream"], m["weights"]):
        if repo:
            by_repo[repo.lower()] = m
    for nm in (m["name"], m["upstream"].split("/")[-1]):
        by_name[norm(nm)] = m

# ---- tt-model bundles ----
REPO_ID = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
catalog = json.load(open(args.catalog))
# The cut-off check counts the rows the search returned, before any are skipped below.
raw_rows = len(catalog)
if args.limit and raw_rows >= args.limit:
    die(f"catalog has {raw_rows} rows, the search limit: it was cut off. Raise --limit.")
bad_ids = [c["id"] for c in catalog if not REPO_ID.match(c["id"]) or any(set(x) == {"."} for x in c["id"].split("/"))]
if bad_ids:
    print("skipping catalog ids that are not owner/name:", bad_ids, file=sys.stderr)
    catalog = [c for c in catalog if c["id"] not in bad_ids]


def tt_model_info(repo):
    try:
        out = subprocess.run(["tt-model", "info", repo], capture_output=True, text=True, timeout=120, cwd="/tmp").stdout
        return json.JSONDecoder().raw_decode(out[out.index("{"):])[0]
    except Exception as e:  # a bundle whose manifest cannot be read is still listed
        return {"_error": str(e)[:120]}


cache = pathlib.Path(args.manifests) if args.manifests else None
manifests = json.loads(cache.read_text()) if cache and cache.exists() else {}
todo = [c["id"] for c in catalog if c["id"] not in manifests]
if todo:
    with cf.ThreadPoolExecutor(8) as ex:
        for repo, mf in zip(todo, ex.map(tt_model_info, todo)):
            manifests[repo] = mf
    if cache:
        cache.write_text(json.dumps(manifests))
unreadable = sorted(c["id"] for c in catalog if "_error" in manifests[c["id"]])
if len(unreadable) > len(catalog) / 2:
    die(f"{len(unreadable)} of {len(catalog)} manifests could not be read; is tt-model working?")


# ---- Card blurbs
# The one line a Models card shows for a bundle, taken from the card's description. Descriptions are long single
# sentences (median 776 characters over the 31 bundle cards read on 2026-11-06), so a fixed-width cut landed
# mid-clause and ended in "…". The rule keeps whole sentences instead:
#   1. the first sentence, when it fits in n characters;
#   2. else that sentence without its parenthetical asides, which is where the architecture detail lives;
#   3. else a cut at the last clause boundary (": ", "; " or ", ") before n, ended with a period.
# A blurb therefore always ends in sentence punctuation and never in an ellipsis. (Changing this rule rewrites every
# blurb on the next nightly run; models.json is never edited by hand.)

# A sentence ends at ., ! or ? followed by whitespace and a capital, digit, quote or bracket. The lookahead keeps
# "v5.0 planner" and "0.17 m voxels" in one sentence: their period is followed by a digit with no space.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def _clean_markdown(text):
    """Inline markdown and emphasis stripped, whitespace collapsed. Links keep their text.

    A list item that follows the opening sentence ("...p150a.\n\n- Supports ...") is a new sentence, so
    a line-leading bullet marker becomes a sentence break the splitter recognises instead of being
    collapsed onto the period as " - Supports", which the splitter's capital-letter lookahead would skip."""
    t = re.sub(r"(?m)^\s*[-*+•]\s+", "\n", text or "")
    return re.sub(r"\s+", " ", re.sub(r"[`*_#>]|\[([^\]]*)\]\([^)]*\)", r"\1", t)).strip()


def split_first_sentence(text):
    """The first sentence of already-cleaned text, punctuation included; the whole text when it has no end."""
    m = _SENTENCE_END.search(text)
    return text[:m.start()] if m else text


def _drop_parentheticals(text):
    """The text without any (...) group, nested groups included, with the punctuation around the gap tidied."""
    out, depth = [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    t = re.sub(r"\s+", " ", "".join(out))
    t = re.sub(r"\s+([,.;:])", r"\1", t)     # "detector , run" -> "detector, run"
    return re.sub(r",\s*,", ",", t).strip()  # ", ," left by a dropped group between two commas


def _end_sentence(text):
    return text if text.endswith((".", "!", "?")) else text + "."


def blurb(text, n=240):
    """A whole-sentence blurb of at most n characters (plus its final period) from a card description."""
    s = split_first_sentence(_clean_markdown(text))
    if not s:
        return ""
    if len(s) <= n:
        return _end_sentence(s)  # a card with no final stop still gets one
    s = _drop_parentheticals(s)
    if len(s) <= n:
        return _end_sentence(s)
    head = s[:n]
    cut = max(head.rfind(": "), head.rfind("; "), head.rfind(", "))
    if cut < n // 2:  # no clause boundary in the second half: fall back to a word boundary
        cut = head.rfind(" ")
    return head[:cut].rstrip(" ,;:.") + "."


# A decision model answers typed questions (choice, score, noul) with probabilities and generates no text. Its card
# says so by naming the System One / SystemOne API or the "noul" question type. Such a bundle is never joined to the
# language model its weights came from (CLM-v0.1-8B is built on Qwen3-8B but is not a chat model).
DECISION = re.compile(r"system ?one|noul", re.I)


# ---- Purpose inference
# What a model is for, beyond its task tag. A bundle with no task tag used to be listed as "Served with vLLM, task
# not stated", which is what every deep-research and thinking model published in November 2026 got. Three more
# sources say what such a model is for, tried in this order:
#   1. the tags on the original model's Hugging Face card (the weights repo the bundle points at);
#   2. the "<Name>, a <phrase> model: ..." opening of the bundle card's description, when the phrase says more
#      than a size ("a multimodal deep-research agent model" yes, "a 122B-parameter mixture-of-experts model" no);
#   3. words in the model's name (Thinker, DeepResearch, Coder).
# The same Hugging Face card's pipeline tag also supplies the kind when the bundle card has no task tag.
HF_API = "https://huggingface.co/api/models/"


def kind_from_hf_card(card):
    """The kind named by the original model's Hugging Face pipeline tag, or None when the card has none."""
    tag = (card or {}).get("pipeline_tag")
    return (TAG_KIND.get(tag) or tag.replace("-", " ").capitalize()) if tag else None


# Hugging Face tags that say what a model is for, most specific first: the first that matches is the purpose.
PURPOSE_TAGS = [("deep-research", "deep-research agent"), ("code-video", "code to video"),
                ("video-generation", "video generation"), ("tool-use", "agent with tool calling"), ("agent", "agent"),
                ("reasoning", "reasoning"), ("thinking", "reasoning"), ("code", "code"), ("math", "math"),
                ("medical", "medical"), ("ocr", "OCR"), ("translation", "translation")]
# Words in a name that say the same, in the same order of specificity.
PURPOSE_NAMES = [(r"deep-?research", "deep-research agent"), (r"think|reason", "reasoning"), (r"coder|\bcode\b", "code"),
                 (r"\bmath\b", "math"), (r"\bocr\b", "OCR"), (r"rerank", "reranking"), (r"embed", "embedding")]
# A description phrase is a purpose only when it names one of these; a phrase that is all size and architecture
# ("122B-parameter mixture-of-experts") is not.
PURPOSE_WORDS = {"agent", "research", "reasoning", "thinking", "code", "coder", "math", "detector", "detection",
                 "planner", "planning", "segmentation", "ranker", "reranker", "reranking", "embedding", "speech",
                 "text-to-speech", "tts", "music", "video", "image", "ocr", "decision", "verifier", "translation",
                 "vision", "perception", "depth", "pose", "generation", "generator", "synthesis", "transcription",
                 "recognition", "forecasting", "classification", "retrieval", "seeking", "assistant", "chat"}
_PHRASE_RE = re.compile(r"^[^,:(]+, an? (.+?)(?=:|\(|\.\s|\.$|$)")
_PARAM_RE = re.compile(r"\b\d[\d.]*[BMK]?-parameter\s*", re.I)


def _purpose_from_description(description):
    m = _PHRASE_RE.match(re.sub(r"\s+", " ", description or "").strip())
    if not m:
        return None
    phrase = _PARAM_RE.sub("", m.group(1)).strip(" ,")
    if len(phrase) > 70 or not (set(re.findall(r"[a-z-]+", phrase.lower())) & PURPOSE_WORDS):
        return None
    return re.sub(r"\s+model$", "", phrase)


def infer_purpose(name, hf_card, description):
    """(purpose, basis) for a model, or (None, None) when nothing says what it is for."""
    tags = set((hf_card or {}).get("tags") or [])
    for tag, purpose in PURPOSE_TAGS:
        if tag in tags:
            return purpose, "the tags on the original model's Hugging Face card"
    phrase = _purpose_from_description(description)
    if phrase:
        return phrase, "the bundle card's description"
    for pattern, purpose in PURPOSE_NAMES:
        if re.search(pattern, name or "", re.I):
            return purpose, "the model's name"
    return None, None


def fetch_hf_card(repo):
    """pipeline_tag and tags of a Hugging Face model repo; an _error record when it cannot be read."""
    headers = {"Authorization": f"Bearer {os.environ['HF_TOKEN']}"} if os.environ.get("HF_TOKEN") else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(HF_API + repo, headers=headers), timeout=30) as r:
            j = json.load(r)
        return {"pipeline_tag": j.get("pipeline_tag"), "tags": [t for t in j.get("tags") or [] if isinstance(t, str)]}
    except Exception as e:  # a model whose card cannot be read keeps the kind the bundle gives it
        return {"_error": str(e)[:120]}

def manifest_hardware_names(mf):
    """The hardware names a manifest gives: its serve profiles, else its mesh device names."""
    cont = mf.get("container") or {}
    serve = cont.get("serve") or {}
    profiles = cont.get("serve_profiles") or []
    names = [serve.get("hardware")] + [p.get("hardware") for p in profiles]
    if not any(names):
        names = [serve.get("mesh_device")] + [p.get("mesh_device") for p in profiles] + [(mf.get("mesh") or {}).get("topology")]
    return [str(h) for h in names if h]


def choose_spellings():
    """One spelling for each hardware name that tt-inference-server does not list: the one most manifests use, and
    on a tie the first in sort order. It does not depend on the order the catalog comes back in."""
    seen = {}
    for c in catalog:
        mf = manifests[c["id"]]
        if "_error" in mf:
            continue
        for h in manifest_hardware_names(mf):
            seen.setdefault(h.strip().lower(), Counter())[h.strip()] += 1
    for low, counts in seen.items():
        HW_SEEN[low] = min(counts, key=lambda sp: (-counts[sp], sp))


def bundle_facts(c):
    """-> (bundle dict, weights repo the bundle was built from, manifest)."""
    repo = c["id"]
    mf = manifests[repo]
    b = dict(repo=repo, owner=repo.split("/")[0], updated=c["last_modified"][:10], readable="_error" not in mf)
    if not b["readable"]:
        return b, repo, mf
    cont = mf.get("container") or {}
    serve = cont.get("serve") or {}
    names = manifest_hardware_names(mf)
    card = cont.get("card") or {}
    caps = serve.get("capabilities") or mf.get("capabilities") or {}
    b.update(
        schema=mf.get("schema_version"), arch=mf.get("arch"), devices=mf.get("device_count"),
        bundleKind=cont.get("kind") or (mf.get("deps") or {}).get("kind"),
        hardware=[hardware(h) for h in sorted({str(h) for h in names if h}, key=str.lower)],
        context=k(serve.get("max_model_len") or (mf.get("resources") or {}).get("max_model_len")),
        toolParser=caps.get("tool_parser"), reasoningParser=caps.get("reasoning_parser"),
        task=card.get("pipeline_tag"), license=card.get("license"), blurb=blurb(card.get("description")),
        # The opening of the card's description, for infer_purpose; not shown on the site.
        descriptionHead=re.sub(r"\s+", " ", card.get("description") or "")[:240],
        perf=bundle_perf(card.get("performance")),
        decision=bool(DECISION.search(" ".join(str(card.get(f) or "") for f in ("description", "intended_use")))))
    return b, (mf.get("weights") or {}).get("repo_id") or repo, mf


INFERRED = json.load(open(HERE / "data/model_kinds_inferred.json"))["kinds"]
choose_spellings()
only = {}
for c in catalog:
    b, wrepo, mf = bundle_facts(c)
    decision = b.get("decision")
    name = c["id"].split("/")[-1] if decision else wrepo.split("/")[-1]
    tgt = None if decision else (by_repo.get(wrepo.lower()) or by_name.get(norm(name)))
    if tgt:
        tgt["bundles"].append(b)
        continue
    m = only.setdefault(wrepo.lower(), dict(
        name=name, upstream=wrepo, weights=wrepo, kind=NOT_STATED_ANY, kindFrom="the tt-model bundle manifest", modelType=None,
        params=None, minDiskGb=None, minRamGb=None, modalities=None, rows=[], bundles=[], inSpec=False, status=None,
        serve=None, toolParser=None, reasoningParser=None, impls=[], studio=None))
    m["bundles"].append(b)

# The original model's Hugging Face card, for every model with a weights repo: a second source of kind for a
# bundle with no task tag, and the first source of purpose for every model. Cached like the manifests.
hf_cache = pathlib.Path(args.hf_cards) if args.hf_cards else None
hf_cards = json.loads(hf_cache.read_text()) if hf_cache and hf_cache.exists() else {}
want = sorted({m["weights"] for m in list(models.values()) + list(only.values()) if m.get("weights")} - set(hf_cards))
if want:
    with cf.ThreadPoolExecutor(8) as ex:
        for repo, card in zip(want, ex.map(fetch_hf_card, want)):
            hf_cards[repo] = card
    if hf_cache:
        hf_cache.write_text(json.dumps(hf_cards))


def hf_card_for(m):
    card = hf_cards.get(m.get("weights") or "") or {}
    return {} if "_error" in card else card


for m in only.values():
    newest = sorted(m["bundles"], key=lambda b: (b["updated"], b["repo"]), reverse=True)
    tag = next((b["task"] for b in newest if b.get("task")), None)
    bundle_kind = next((b.get("bundleKind") for b in newest if b.get("bundleKind")), None)
    m["kind"] = NOT_STATED.get(bundle_kind, NOT_STATED_ANY)
    if tag:
        m["kind"] = TAG_KIND.get(tag, tag.replace("-", " ").capitalize())
        m["kindFrom"] = "the task tag on the bundle's card"
    m["kindInferred"] = False
    if any(b.get("decision") for b in m["bundles"]):
        m["kind"] = "Decision model"
        m["kindFrom"] = "the bundle card, which says it answers typed System One questions and generates no text"
        tag = "decision"
    guess = INFERRED.get(m["upstream"].lower())
    if guess and not tag:
        m["kind"], m["kindInferred"] = guess["kind"], True
        m["kindFrom"] = "an inference: " + guess["basis"]
    elif not tag and kind_from_hf_card(hf_card_for(m)):
        m["kind"] = kind_from_hf_card(hf_card_for(m))
        m["kindFrom"] = "the task tag on the original model's Hugging Face card"
    m["serve"] = newest[0]["repo"]
    m["toolParser"] = next((b.get("toolParser") for b in newest if b.get("toolParser")), None)
    m["reasoningParser"] = next((b.get("reasoningParser") for b in newest if b.get("reasoningParser")), None)

all_models = list(models.values()) + list(only.values())

def perf_text(perf):
    """Display strings for the browse card: decode speed per user, and time to first token when there is one."""
    d, t = perf["decode"], perf.get("ttft")
    perf["decodeText"] = f"{d:.1f}" if d < 10 else f"{d:.0f}"
    perf["ttftText"] = None if not t else (f"{t / 1000:.1f} s" if t >= 1000 else f"{t:.0f} ms")
    return perf


# One speed figure per language model. A tt-inference-server model uses its best-status vLLM row that has a reference
# figure; any other model uses the newest bundle with a readable latency table.
for m in all_models:
    m["perf"] = None
    if m["kind"] not in ("LLM", "VLM"):
        continue
    if m["inSpec"]:
        row = next((x for x in m["rows"] if x.get("perf") and x["engine"] == "vLLM"), None)
        if row:
            m["perf"] = dict(row["perf"], hardware=row["hardware"], chips=None)
    else:
        b = next((b for b in sorted(m["bundles"], key=lambda b: (b["updated"], b["repo"]), reverse=True) if b.get("perf")), None)
        if b:
            perf = dict(b["perf"])
            # A table that names no board takes the bundle's own hardware when the manifest lists exactly one.
            if not perf["board"] and len(b.get("hardware") or []) == 1:
                raw = b["hardware"][0]["raw"].lower()
                perf["board"] = raw if raw in CHIPS else None
                perf["chips"] = CHIPS.get(raw) or b.get("devices")
                perf["hardware"] = b["hardware"][0]["product"]
            elif perf["board"]:
                perf["hardware"] = hardware(perf["board"])["product"]
            if perf.get("hardware"):
                m["perf"] = perf

# ---- derived fields, all from the facts above ----
FAMILY_PREFIXES = json.load(open(HERE / "data/model_families.json"))["prefixes"]


def family_of(name):
    low = name.lower()
    for prefix, label in FAMILY_PREFIXES:
        if low.startswith(prefix):
            return label
    first = re.split(r"[-_. ]", name)[0]
    return re.sub(r"(?<=[A-Za-z])v?\d+$", "", first) or name


single_products = {PRODUCT[key] for key in SINGLE_CARD_KEYS if key in PRODUCT}
for m in all_models:
    m["family"] = family_of(m["name"])
    hws = {x["hardware"] for x in m["rows"]}
    for b in m["bundles"]:
        hws |= {h["product"] for h in b.get("hardware", [])}
    m["hardware"] = sorted(hws)
    m["singleCard"] = bool(hws & single_products)
    m["newest"] = max([b["updated"] for b in m["bundles"]] or [""])
    n = len(m["bundles"])
    newest_bundle = max(m["bundles"], key=lambda b: (b["updated"], b["repo"]), default={})
    m["purpose"], m["purposeFrom"] = infer_purpose(m["name"], hf_card_for(m), newest_bundle.get("descriptionHead"))
    if m["inSpec"]:
        # Name the hardware rather than count it: "on WH LoudBox/QuietBox and Galaxy" tells a reader more than "on 2
        # hardware types". Only the spec rows count here, since the sentence is about tt-inference-server; bundles
        # get their own sentence below.
        hw = sorted({x["hardware"] for x in m["rows"]})
        names = hw[0] if len(hw) == 1 else ", ".join(hw[:-1]) + " and " + hw[-1]
        m["summary"] = (f"Runs through tt-inference-server on {names}; status {m['status']}."
                        + (f" {n} tt-model {'bundle' if n == 1 else 'bundles'} also published." if n else ""))
    else:
        blurb = next((b["blurb"] for b in sorted(m["bundles"], key=lambda b: (b["updated"], b["repo"]), reverse=True) if b.get("blurb")), "")
        owners = ", ".join(sorted({b["owner"] for b in m["bundles"]}))
        m["summary"] = blurb or f"Published as {n} tt-model {'bundle' if n == 1 else 'bundles'} by {owners}."
    m["source"] = "tt-inference-server" if m["inSpec"] else "tt-model bundle"
    # A tt-inference-server model is checked by tt against the spec: a vLLM row means chat, and a vLLM row's tool-call
    # parser means tool calling. A bundle-only model is not in tt's catalog, so tt cannot check it. Its manifest says
    # whether it is served with vLLM and names a parser, and the clients that follow are marked as not checked by tt.
    if m["inSpec"]:
        chat, checked = any(x["engine"] == "vLLM" for x in m["rows"]), True
    else:
        # A decision model is served through its own API, so no chat client connects to it.
        chat = m["kind"] != "Decision model" and any(b.get("bundleKind") in VLLM_BUNDLE_KINDS for b in m["bundles"])
        checked = False
    m["clients"] = [dict(id=cid, type=ctype,
                         note=(f"Tool calling: {m['toolParser']}" if needs else "Any chat model"), checked=checked)
                    for cid, ctype, needs in CLIENTS if chat and (m["toolParser"] or not needs)]

# A family label keeps the casing most of its models use.
spell = {}
for m in all_models:
    spell.setdefault(m["family"].lower(), Counter())[m["family"]] += 1
for m in all_models:
    m["family"] = spell[m["family"].lower()].most_common(1)[0][0]

# tt-inference-server models first, then by name; ids are URL slugs and must be unique
for m in all_models:
    if m["perf"]:
        perf_text(m["perf"])
all_models.sort(key=lambda m: (not m["inSpec"], m["name"].lower()))
used = set()
for m in all_models:
    base = slug(m["name"]) or "model"
    s, i = base, 2
    while s in used:
        s, i = f"{base}-{i}", i + 1
    used.add(s)
    m["id"] = s
    m["bundles"].sort(key=lambda b: b["repo"])
    # A card's license is {id, name, link}; "other" has no meaning alone, so its name is shown.
    m["licenses"] = sorted({(b["license"].get("name") if b["license"].get("id") == "other" else None) or b["license"].get("id")
                            for b in m["bundles"] if isinstance(b.get("license"), dict)} - {None})

# The hardware names tt-inference-server uses, for the Hardware page.
hardware_names = [dict(key=e, product=PRODUCT[e], mesh=MESH.get(e)) for e in MEMBERS if e in PRODUCT]
def checkout_commit(root):
    """Short commit of a checkout, read from .git/HEAD (no git process; a detached HEAD or a branch ref)."""
    try:
        head = (root / ".git" / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            ref_file = root / ".git" / ref
            if ref_file.is_file():
                head = ref_file.read_text().strip()
            else:
                packed = (root / ".git" / "packed-refs").read_text().splitlines()
                head = next(l.split()[0] for l in packed if l.endswith(" " + ref))
        return head[:9] if re.fullmatch(r"[0-9a-f]{40}", head) else ""
    except (OSError, StopIteration):
        return ""


commit = args.spec_commit or checkout_commit(ISRV)
if not commit:
    die("could not read the tt-inference-server commit (no .git directory in --isrv?); pass --spec-commit")
out = dict(models=all_models, hardware=hardware_names,
           spec=dict(commit=commit, release=spec["release_version"]), unreadableBundles=unreadable,
           unclassified=sorted(m["name"] for m in all_models if "task not stated" in m["kind"].lower()))
outp = pathlib.Path(args.out)
if outp.exists():
    before = len(json.loads(outp.read_text()).get("models", []))
    if before and len(all_models) < before / 2:
        die(f"refusing to write: {len(all_models)} models, down from {before}")
if not models:
    die("refusing to write: no tt-inference-server models were read")
outp.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
print(f"wrote {outp}: {len(models)} in tt-inference-server, {len(only)} tt-model only, "
      f"{sum(len(m['bundles']) for m in all_models)} bundles, {len(unreadable)} manifests unreadable")
