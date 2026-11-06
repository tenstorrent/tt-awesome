# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.
"""What a model is for: kind_from_hf_card() and infer_purpose() in scripts/build_models_data.py.

A bundle with no task tag used to be listed as "Served with vLLM, task not stated", which is what the
deep-research and thinking models published in November 2026 all got. Three more sources now say what
such a model is for, in this order: the tags on the original model's Hugging Face card, the "a ... model"
phrase that opens the bundle card's description, and words in the model's name.

The builder is a script, so its helper block is read out of the file and run on its own."""
import pathlib
import re

SRC = (pathlib.Path(__file__).parent.parent / "scripts/build_models_data.py").read_text()
block = SRC[SRC.index("# ---- Purpose inference"):SRC.index("\ndef manifest_hardware_names")]
ns = {"re": re}
exec(SRC[SRC.index("TAG_KIND = "):SRC.index("\n", SRC.index("TAG_KIND = ") + 200)], ns)  # the tag → kind map
exec(block, ns)
kind_from_hf_card, infer_purpose = ns["kind_from_hf_card"], ns["infer_purpose"]


def test_kind_from_the_original_cards_pipeline_tag():
    assert kind_from_hf_card({"pipeline_tag": "image-text-to-text"}) == "VLM"
    assert kind_from_hf_card({"pipeline_tag": "text-generation"}) == "LLM"
    assert kind_from_hf_card({"pipeline_tag": "text-ranking"}) == "Text ranking"
    assert kind_from_hf_card({}) is None and kind_from_hf_card(None) is None


def test_purpose_from_hugging_face_tags():
    card = {"tags": ["transformers", "safetensors", "qwen3_5_moe", "deep-research", "multimodal", "agent"]}
    assert infer_purpose("MIRA-SFT-35B-A3B", card, "") == ("deep-research agent", "the tags on the original model's Hugging Face card")
    assert infer_purpose("X", {"tags": ["code-video", "video-generation", "agent"]}, "")[0] == "code to video"


def test_purpose_from_the_description_phrase():
    desc = "Tongyi DeepResearch, an agent model for long-horizon, deep information seeking: a 30B-parameter mixture of experts."
    assert infer_purpose("Tongyi-DeepResearch-30B-A3B", {}, desc) == ("agent model for long-horizon, deep information seeking", "the bundle card's description")
    desc2 = "MIRA-SFT-35B-A3B, a multimodal deep-research agent model: Qwen3.6-35B-A3B trained to search the web."
    assert infer_purpose("MIRA-SFT-35B-A3B", {}, desc2)[0] == "multimodal deep-research agent"


def test_description_phrase_that_only_gives_a_size_is_not_a_purpose():
    desc = "Ornith-1.5-122B, a 122B-parameter mixture-of-experts model with 10B parameters active per token."
    assert infer_purpose("Ornith-1.5-122B", {}, desc) == (None, None)


def test_purpose_from_the_name():
    assert infer_purpose("MiroThinker-1.7-mini", {}, "") == ("reasoning", "the model's name")
    assert infer_purpose("Tongyi-DeepResearch-30B-A3B", {}, "")[0] == "deep-research agent"
    assert infer_purpose("Qwen3-Coder-Next", {}, "")[0] == "code"
    assert infer_purpose("ELYZA-Thinking-1.0-llm-jp-4-33b", {}, "")[0] == "reasoning"


def test_tags_win_over_description_and_name():
    card = {"tags": ["deep-research"]}
    assert infer_purpose("MiroThinker-1.7-mini", card, "MiroThinker, a reasoning model.")[0] == "deep-research agent"


def test_no_purpose_for_a_plain_chat_model():
    assert infer_purpose("Llama-3.1-8B-Instruct", {"tags": ["transformers", "conversational"]}, "") == (None, None)
