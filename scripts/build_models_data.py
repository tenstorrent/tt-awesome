#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.
"""Build src/_data/models.json, the data behind the Models section of the site.

Sources, in order of precedence:
  1. tt-inference-server's release_model_spec.json (read from a checkout or a `git archive`).
  2. tt-model's catalog (`tt-model search --catalog --json --limit 300`, a read-only Hub listing).

A model listed in both is one entry with tt-inference-server's facts, and its tt-model bundles are
attached. A model only in tt-model is an entry with the bundle facts and nothing else.

Nothing is measured here. Status, context and users are copied from the release spec. No device is
opened. Device names go through scripts/data/model_device_names.json; a name it does not know is
shown as the spec spells it, marked "(unmapped)".

The nightly workflow (.github/workflows/nightly-models.yml) runs this. By hand:
  tt-model search --catalog --json --limit 300 > catalog.json
  python3 scripts/build_models_data.py --spec <tt-inference-server>/release_model_spec.json \
      --catalog catalog.json --spec-commit <short sha of that checkout>

The output is deterministic (sorted, no build date), so a night with no upstream change makes no diff.
The script refuses to write a list that shrank by more than half, so a failed fetch cannot empty the page.
"""
import argparse
import json
import pathlib
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--spec", required=True, help="tt-inference-server release_model_spec.json")
ap.add_argument("--catalog", required=True, help="JSON from `tt-model search --catalog --json`")
ap.add_argument("--spec-commit", required=True, help="tt-inference-server commit the spec was read at")
ap.add_argument("--limit", type=int, default=0,
                help="the --limit given to tt-model search; a catalog with exactly this many rows was cut off")
ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parent.parent / "src/_data/models.json"))
args = ap.parse_args()

DEVICES = json.load(open(pathlib.Path(__file__).resolve().parent / "data/model_device_names.json"))["devices"]

RANK = {"COMPLETE": 3, "FUNCTIONAL": 2, "EXPERIMENTAL": 1}
# tt-studio's interaction page per model type (app/frontend/src/api/modelsDeployedApis.ts,
# getDestinationFromModelType). The page depends on the model type only.
STUDIO = {"LLM": "Chat", "VLM": "Chat, with image input", "IMAGE": "Image generation",
          "VIDEO": "Video generation", "AUDIO": "Speech to text", "TEXT_TO_SPEECH": "Text to speech",
          "EMBEDDING": "Embedding demo", "CNN": "Object detection"}
KIND = {"LLM": "Language model", "VLM": "Vision-language model", "IMAGE": "Image generation",
        "VIDEO": "Video generation", "AUDIO": "Speech to text", "TEXT_TO_SPEECH": "Text to speech",
        "EMBEDDING": "Embedding", "CNN": "Vision (CNN)"}


def dev_name(spec_name):
    d = DEVICES.get(spec_name.lower())
    return (d["name"] if d else spec_name.lower() + " (unmapped)"), (d["chips"] if d else None)


def k(n):
    return f"{n // 1024}K" if n and n >= 1024 else (str(n) if n else None)


def params(p):
    if not p:
        return None
    return f"{p:g}B" if p >= 1 else f"{p * 1000:g}M"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---- tt-inference-server ----
spec = json.load(open(args.spec))
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

models = {}
for r in rows:
    m = models.setdefault(r["hf_model_repo"], dict(
        id=norm(r["model_name"]), name=r["model_name"], upstream=r["hf_model_repo"],
        kind=KIND[r["model_type"]], kindGuess=False, params=params(r.get("param_count")),
        rows=[], bundles=[], inSpec=True, serve=r["model_name"], studio=STUDIO[r["model_type"]],
        chat=False, parser=None))
    m["chat"] = m["chat"] or r["inference_engine"] == "vLLM"
    # tt launch reads the tool-call parser from a vLLM row (tt-cli launchers/base.py).
    if r["inference_engine"] == "vLLM" and not m["parser"]:
        m["parser"] = (r.get("metadata") or {}).get("tool_call_parser_name")
    dm = r["device_model_spec"]
    dn, chips = dev_name(r["device_type"])
    m["rows"].append(dict(device=dn, chips=chips, engine=r["inference_engine"], status=r["status"].title(),
                          context=k(dm.get("max_context")), users=dm.get("max_concurrency")))
for m in models.values():
    seen, uniq = set(), []
    for x in sorted(m["rows"], key=lambda x: (-RANK[x["status"].upper()], x["device"], x["engine"])):
        key = (x["device"], x["engine"])
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    m["rows"] = uniq
    m["status"] = max((x["status"] for x in uniq), key=lambda s: RANK[s.upper()])
    m["devices"] = sorted({x["device"] for x in uniq})
    m["singleCard"] = any(x["chips"] == 1 for x in uniq)
    m["multiOnly"] = all((x["chips"] or 2) > 1 for x in uniq)

# ---- tt-model catalog ----
HW_TOKENS = r"(p100a|p150x8|p150x4|p150x2|p150|p300x2|p300|blackhole|bh|wh|galaxy|qb2|v51|fast|wormhole|256k)"
catalog = json.load(open(args.catalog))
if args.limit and len(catalog) >= args.limit:
    sys.exit(f"catalog has {len(catalog)} rows, the search limit: it was cut off. Raise --limit.")


def base_and_boards(repo_id):
    name = repo_id.split("/", 1)[1].lower()
    boards = []
    for t in re.findall(HW_TOKENS, name):
        if t in ("p100a", "p150x8", "p150x4", "p150x2", "p150", "p300x2", "p300"):
            boards.append(dev_name(t)[0])
        elif t in ("bh", "blackhole"):
            boards.append("Blackhole")
        elif t in ("wh", "wormhole"):
            boards.append("Wormhole")
        elif t == "galaxy":
            boards.append("Galaxy")
        elif t == "qb2":
            boards.append("QB2")
    base = name
    for _ in range(4):
        base = re.sub(r"[-_.]?" + HW_TOKENS + r"$", "", base)
    return base, sorted(set(boards))


by_norm = {}
for m in models.values():
    by_norm[m["id"]] = m
    by_norm[norm(m["upstream"].split("/")[-1])] = m

only = {}
for c in catalog:
    base, boards = base_and_boards(c["id"])
    b = dict(repo=c["id"], owner=c["id"].split("/")[0], boards=boards, updated=c["last_modified"][:10])
    tgt = by_norm.get(norm(base))
    if tgt:
        tgt["bundles"].append(b)
    else:
        m = only.setdefault(norm(base), dict(id=norm(base), name=base, upstream=None, kind=None, kindGuess=True,
                                             params=None, rows=[], bundles=[], inSpec=False, status=None,
                                             serve=None, studio=None, chat=None, parser=None,
                                             devices=[], singleCard=False, multiOnly=False))
        m["bundles"].append(b)

# tt-model bundles carry no model type, so the kind of a bundle-only model is guessed from its name.
GUESS = [
    ("Audio and speech", r"tts|voice|music|diffrhythm|acestep|s2-pro|speech|asr|voxtral|audio"),
    ("Image generation", r"flux|hidream|z-image|qwen-image|image-edit"),
    ("Vision", r"sam3|depth-anything|hamer|superpoint|rf-detr|mast3r|moge|vggt|locate-anything|gaze|yolox|meteor"),
    ("Automotive perception", r"bev|ptv3|frnet|centerpoint|transfusion|pointpainting|sceneseg|diffusion-planner|streampetr"),
    ("Robotics", r"pi05|gr00t|xvla|rldx|alpamayo|openvla"),
    ("Video generation", r"wan2|skyreels|waypoint"),
    ("Embedding", r"embedding"),
    ("Language model", r"qwen|llama|gemma|gpt-oss|deepseek|kimi|glm|olmo|mistral|nemotron|muse|ornith|laguna|"
                       r"exaone|solar|vibethinker|llm-jp|elyza|mimo|lfm|motif|clm|cohost-llm|rag-gate|smollm|openthai|minimax-h3"),
]
for m in only.values():
    m["kind"] = next((kd for kd, rx in GUESS if re.search(rx, m["name"])), "Unclassified")
    m["devices"] = sorted({b for x in m["bundles"] for b in x["boards"]})

all_models = list(models.values()) + list(only.values())
for m in all_models:
    owners = sorted({b["owner"] for b in m["bundles"]})
    n = len(m["bundles"])
    if m["inSpec"]:
        nd = len(m["devices"])
        m["summary"] = (f"Listed in tt-inference-server on {nd} device {'type' if nd == 1 else 'types'}; "
                        f"best status {m['status']}."
                        + (f" {n} tt-model {'bundle' if n == 1 else 'bundles'} also published." if n else ""))
    else:
        m["summary"] = (f"Published as {n} tt-model {'bundle' if n == 1 else 'bundles'} by "
                        + ", ".join(owners) + ". Not listed in tt-inference-server.")
        m["serve"] = max(m["bundles"], key=lambda b: b["updated"])["repo"]
    m["source"] = "tt-inference-server" if m["inSpec"] else "tt-model only"
    m["newest"] = max([b["updated"] for b in m["bundles"]] or [""])

# tt-inference-server models first
all_models.sort(key=lambda m: (not m["inSpec"], m["name"].lower()))

for m in all_models:
    m["bundles"].sort(key=lambda b: b["repo"])

out = dict(models=all_models, spec=dict(commit=args.spec_commit, release=spec["release_version"]))
outp = pathlib.Path(args.out)
if outp.exists():
    before = len(json.loads(outp.read_text()).get("models", []))
    if before and len(all_models) < before / 2:
        sys.exit(f"refusing to write: {len(all_models)} models, down from {before}")
if not models:
    sys.exit("refusing to write: no tt-inference-server models were read")
pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
print(f"wrote {args.out}: {len(models)} in tt-inference-server, {len(only)} tt-model only, "
      f"{sum(len(m['bundles']) for m in all_models)} bundles")
