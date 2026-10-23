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
import pathlib
import re
import subprocess
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--isrv", required=True, help="tt-inference-server checkout (release_model_spec.json, workflows/, docs/)")
ap.add_argument("--catalog", required=True, help="JSON from `tt-model search --catalog --json`")
ap.add_argument("--limit", type=int, default=0,
                help="the --limit given to tt-model search; a catalog with exactly this many rows was cut off")
ap.add_argument("--spec-commit", default="", help="commit of the checkout; read from git when left out")
ap.add_argument("--manifests", default="", help="JSON cache of `tt-model info` output. Read when it exists; written after a fetch.")
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
HW_SEEN = {}   # lower-case name -> spelling first seen, for names tt-inference-server does not list


def hardware(raw):
    """-> {raw, key, product, listed}. `key` is the DeviceTypes member when tt-inference-server lists the name."""
    r = str(raw).strip()
    enum = r.upper() if r.upper() in PRODUCT else BY_MESH.get(r.lower())
    if enum and enum in PRODUCT:
        return dict(raw=r, key=enum, product=PRODUCT[enum], listed=True)
    HW_SEEN.setdefault(r.lower(), r)
    return dict(raw=r, key=None, product=HW_SEEN[r.lower()], listed=False)


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
        hardware=hw["product"], deviceKey=r["device_type"], listed=hw["listed"], engine=r["inference_engine"],
        status=r["status"].title(), context=k(dm.get("max_context")), users=dm.get("max_concurrency"),
        impl=impl.get("impl_name"), codeLink=r.get("code_link"), ttMetal=r.get("tt_metal_commit"),
        vllm=r.get("vllm_commit"), image=r.get("docker_image"), version=r.get("version"),
        doc=doc if (DOCS / doc).exists() else None))
for m in models.values():
    seen, uniq = set(), []
    for x in sorted(m["rows"], key=lambda x: (-RANK[x["status"].upper()], x["hardware"], x["engine"])):
        key = (x["hardware"], x["engine"])
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


def first_sentence(text, n=240):
    t = re.sub(r"\s+", " ", re.sub(r"[`*_#>]|\[([^\]]*)\]\([^)]*\)", r"\1", text or "")).strip()
    cut = re.search(r"(?<=[.!?])\s", t[:n * 2])
    return t[:cut.start()] if cut and cut.start() <= n else (t[:n].rsplit(" ", 1)[0] + "…" if len(t) > n else t)


def bundle_facts(c):
    """-> (bundle dict, weights repo the bundle was built from, manifest)."""
    repo = c["id"]
    mf = manifests[repo]
    b = dict(repo=repo, owner=repo.split("/")[0], updated=c["last_modified"][:10], readable="_error" not in mf)
    if not b["readable"]:
        return b, repo, mf
    cont = mf.get("container") or {}
    serve = cont.get("serve") or {}
    profiles = cont.get("serve_profiles") or []
    names = [serve.get("hardware")] + [p.get("hardware") for p in profiles]
    if not any(names):
        names = [serve.get("mesh_device")] + [p.get("mesh_device") for p in profiles] + [(mf.get("mesh") or {}).get("topology")]
    card = cont.get("card") or {}
    caps = serve.get("capabilities") or mf.get("capabilities") or {}
    b.update(
        schema=mf.get("schema_version"), arch=mf.get("arch"), devices=mf.get("device_count"),
        bundleKind=cont.get("kind") or (mf.get("deps") or {}).get("kind"),
        hardware=[hardware(h) for h in sorted({str(h) for h in names if h}, key=str.lower)],
        context=k(serve.get("max_model_len") or (mf.get("resources") or {}).get("max_model_len")),
        toolParser=caps.get("tool_parser"), reasoningParser=caps.get("reasoning_parser"),
        task=card.get("pipeline_tag"), license=card.get("license"), blurb=first_sentence(card.get("description")))
    return b, (mf.get("weights") or {}).get("repo_id") or repo, mf


INFERRED = json.load(open(HERE / "data/model_kinds_inferred.json"))["kinds"]
only = {}
for c in catalog:
    b, wrepo, mf = bundle_facts(c)
    name = wrepo.split("/")[-1]
    tgt = by_repo.get(wrepo.lower()) or by_name.get(norm(name))
    if tgt:
        tgt["bundles"].append(b)
        continue
    m = only.setdefault(wrepo.lower(), dict(
        name=name, upstream=wrepo, weights=wrepo, kind=NOT_STATED_ANY, kindFrom="the tt-model bundle manifest", modelType=None,
        params=None, minDiskGb=None, minRamGb=None, modalities=None, rows=[], bundles=[], inSpec=False, status=None,
        serve=None, toolParser=None, reasoningParser=None, impls=[], studio=None))
    m["bundles"].append(b)

for m in only.values():
    newest = sorted(m["bundles"], key=lambda b: b["updated"], reverse=True)
    tag = next((b["task"] for b in newest if b.get("task")), None)
    bundle_kind = next((b.get("bundleKind") for b in newest if b.get("bundleKind")), None)
    m["kind"] = NOT_STATED.get(bundle_kind, NOT_STATED_ANY)
    if tag:
        m["kind"] = TAG_KIND.get(tag, tag.replace("-", " ").capitalize())
        m["kindFrom"] = "the task tag on the bundle's card"
    m["kindInferred"] = False
    guess = INFERRED.get(m["upstream"].lower())
    if guess and not tag:
        m["kind"], m["kindInferred"] = guess["kind"], True
        m["kindFrom"] = "an inference: " + guess["basis"]
    m["serve"] = newest[0]["repo"]
    m["toolParser"] = next((b.get("toolParser") for b in newest if b.get("toolParser")), None)
    m["reasoningParser"] = next((b.get("reasoningParser") for b in newest if b.get("reasoningParser")), None)

all_models = list(models.values()) + list(only.values())

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
    if m["inSpec"]:
        nh = len({x["hardware"] for x in m["rows"]})
        m["summary"] = (f"Listed in tt-inference-server on {nh} hardware type{'s' if nh != 1 else ''}; best status {m['status']}."
                        + (f" {n} tt-model {'bundle' if n == 1 else 'bundles'} also published." if n else ""))
    else:
        blurb = next((b["blurb"] for b in sorted(m["bundles"], key=lambda b: b["updated"], reverse=True) if b.get("blurb")), "")
        owners = ", ".join(sorted({b["owner"] for b in m["bundles"]}))
        m["summary"] = blurb or f"Published as {n} tt-model {'bundle' if n == 1 else 'bundles'} by {owners}."
    m["source"] = "tt-inference-server" if m["inSpec"] else "tt-model only"
    # A tt-inference-server model is checked by tt against the spec: a vLLM row means chat, and a vLLM row's tool-call
    # parser means tool calling. A bundle-only model is not in tt's catalog, so tt cannot check it. Its manifest says
    # whether it is served with vLLM and names a parser, and the clients that follow are marked as not checked by tt.
    if m["inSpec"]:
        chat, checked = any(x["engine"] == "vLLM" for x in m["rows"]), True
    else:
        chat, checked = any(b.get("bundleKind") in VLLM_BUNDLE_KINDS for b in m["bundles"]), False
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
