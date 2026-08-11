# tt-awesome

## A hidden dimension of Tenstorrent awesomeness

A curated directory of projects, tools, models, and research for Tenstorrent hardware — contributed by the community and our team.

> **This file is auto-generated from `entries/*.json`. Do not edit directly — [submit an entry via issue](https://github.com/tenstorrent/tt-awesome/issues/new?template=submit-entry.yml) or see [CONTRIBUTING.md](CONTRIBUTING.md) for other options.**

## Contents

- [🚀 Getting Started](#getting-started)
- [🤖 AI & Models](#ai-models)
- [🕵️ AI Agents](#ai-agents)
- [⚙️ Custom Kernels & Low-Level](#custom-kernels-low-level)
- [🔨 Compilers & Frontends](#compilers-frontends)
- [🛠 Dev Tools & Debugging](#dev-tools-debugging)
- [🖥 Hardware & System](#hardware-system)
- [☁️ Cloud & Orchestration](#cloud-orchestration)
- [🔩 RISC-V & Architecture](#risc-v-architecture)
- [🔬 Research & Papers](#research-papers)
- [🎮 Games & Demos](#games-demos)
- [📚 Guides, Tutorials & Education](#guides-tutorials-education)

## 🤖 AI & Models

- **[tt-bio](https://github.com/moritztng/tt-bio)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@moritztng](https://github.com/moritztng) — Boltz-2 biomolecular model for drug discovery on Tenstorrent Blackhole. Supports single-card and multi-card configurations — QuietBox (4×) and Galaxy (32×). Approaches physics-based FEP accuracy at 1000× the speed.
  [📦 repo](https://github.com/moritztng/tt-bio) · [🎤 FOSDEM 2026 — Drug Discovery on Tenstorrent Hardware](https://fosdem.org/2026/schedule/event/AJLNVH-tt-boltz/)

- **Video Generation on Tenstorrent** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Three lesson-projects covering on-device video synthesis: frame-by-frame diffusion with tt-local-generator, native AnimateDiff video animation, and video generation on QuietBox 2. All run entirely on TT hardware with no cloud dependency.
  [📖 Video Generation via Frame-by-Frame Diffusion](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/video-generation-ttmetal/) · [📖 Native Video Animation with AnimateDiff](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/animatediff-video-generation/) · [📖 Video Generation on QuietBox 2](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/qb2-video-generation/)

- **[dflash](https://github.com/zoecarver/dflash)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@zoecarver](https://github.com/zoecarver) — DFlash: Block Diffusion for Flash Speculative Decoding on Tenstorrent hardware using tt-lang. Combines block diffusion with speculative decoding for faster inference.
  [📦 repo](https://github.com/zoecarver/dflash) · [🌐 website](https://dflash.z-lab.ai)

- **[diamond](https://github.com/zoecarver/diamond)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@zoecarver](https://github.com/zoecarver) — DIAMOND: Atari game-playing agent implemented on Tenstorrent hardware via tt-lang. Diffusion-based world model for reinforcement learning.
  [📦 repo](https://github.com/zoecarver/diamond) · [🌐 website](https://diamond-wm.github.io)

- **[Engram](https://github.com/zoecarver/Engram)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@zoecarver](https://github.com/zoecarver) — A Tenstorrent port of the DeepSeek Engram model using tt-lang. Brings DeepSeek's memory-efficient architecture to TT hardware.
  [📦 repo](https://github.com/zoecarver/Engram)

- **[gemma4](https://github.com/zoecarver/gemma4)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@zoecarver](https://github.com/zoecarver) — Gemma 4 language model implemented in tt-lang (e4b variant) for direct execution on Tenstorrent hardware.
  [📦 repo](https://github.com/zoecarver/gemma4)

- **[gsplat_tt](https://github.com/smartonTT/gsplat_tt)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@smartonTT](https://github.com/smartonTT) — Port of Gaussian Splatting (3D scene reconstruction from 2D images) to Tenstorrent hardware.
  [📦 repo](https://github.com/smartonTT/gsplat_tt)

- **[open-oasis](https://github.com/zoecarver/open-oasis)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@zoecarver](https://github.com/zoecarver) — tt-lang inference script for Oasis 500M — an interactive video world model running on Tenstorrent hardware via the tt-lang DSL.
  [📦 repo](https://github.com/zoecarver/open-oasis)

- **[tt-atom](https://github.com/moritztng/tt-atom)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@moritztng](https://github.com/moritztng) — Meta's UMA interatomic potential running on Tenstorrent Blackhole — energy, forces, and stress for molecules and periodic materials behind an ASE calculator. Its per-edge Wigner rotation runs as a custom tt-metal kernel for a highest-performance uma-s build.
  [📦 repo](https://github.com/moritztng/tt-atom)

- **[tt-lang-models](https://github.com/zoecarver/tt-lang-models)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@zoecarver](https://github.com/zoecarver) — A growing collection of models that use tt-lang for some or all of their implementation. Reference implementations for bringing modern models to the tt-lang DSL.
  [📦 repo](https://github.com/zoecarver/tt-lang-models)

- **Stable Diffusion XL on Tenstorrent** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — On-device image generation with Stable Diffusion XL running entirely on Tenstorrent hardware. Full inference pipeline with no cloud dependency.
  [📖 Image Generation with Stable Diffusion XL](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/image-generation/)

- **[tt-animatediff](https://github.com/tenstorrent/tt-animatediff)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Generates short, temporally coherent animated GIFs using the AnimateDiff model on Tenstorrent hardware. Phase 1 runs the correct SD 1.4 + MotionAdapter architecture on CPU; Phase 2 accelerates spatial denoising on Blackhole using the TTNN UNet. Produces vibrant 8-frame animations in ~15 s/frame on a P300C.
  [📦 repo](https://github.com/tenstorrent/tt-animatediff) · [📖 Native Video Animation with AnimateDiff (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/animatediff-video-generation/)

- **[tt-blacksmith](https://github.com/tenstorrent/tt-blacksmith)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Optimized training recipes for a variety of ML models on Tenstorrent hardware, powered by the TT-Forge compiler stack. Reference implementations for fine-tuning and training from scratch.
  [📦 repo](https://github.com/tenstorrent/tt-blacksmith) · [🌐 website](https://docs.tenstorrent.com/tt-blacksmith/)

- **[tt-buda-demos](https://github.com/tenstorrent/tt-buda-demos)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Repository of model demos using TT-Buda. The largest collection of pre-compiled model examples for Tenstorrent hardware — BERT, ResNet, YOLO, GPT-2, Whisper, and many more.
  [📦 repo](https://github.com/tenstorrent/tt-buda-demos)

- **[tt-example-apps](https://github.com/tenstorrent/tt-example-apps)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  End-to-end AI applications running on Tenstorrent AI accelerators. Complete application examples from retrieval-augmented generation to image generation pipelines.
  [📦 repo](https://github.com/tenstorrent/tt-example-apps)

- **[tt-forge-models](https://github.com/tenstorrent/tt-forge-models)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  A shared repository of model implementations used across TT-Forge frontends — a single source of truth for the models used in testing and benchmarking, rather than duplicating them across frontend repos.
  [📦 repo](https://github.com/tenstorrent/tt-forge-models)

- **[tt-inference-server](https://github.com/tenstorrent/tt-inference-server)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Production-ready model serving for Tenstorrent hardware with OpenAI-compatible REST API. Supports continuous batching, multiple models, and all TT hardware configurations.
  [📦 repo](https://github.com/tenstorrent/tt-inference-server) · [📖 Production Inference lesson (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/tt-inference-server-lesson/)

- **[tt-local-generator](https://github.com/tenstorrent/tt-local-generator)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Generate infinite videos and images (and imaginative prompts to inspire them) on Tenstorrent's Quietbox 2. Fully local generative media pipeline.
  [📦 repo](https://github.com/tenstorrent/tt-local-generator) · [🌐 website](https://docs.tenstorrent.com/tt-local-generator/)

- **[TT-Studio](https://github.com/tenstorrent/tt-studio)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Web-based GUI for deploying and chatting with AI models on Tenstorrent hardware. Handles all technical setup automatically — deploy models, run inference, and explore capabilities through a simple browser interface.
  [📦 repo](https://github.com/tenstorrent/tt-studio)

- **[vllm-tt-plugin](https://github.com/tenstorrent/vllm-tt-plugin)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent backend for vLLM, built on vLLM's standard plugin mechanism — install it alongside vLLM and TT hardware registers itself as a platform whenever `ttnn` is importable. Self-contained: model registration, platform detection, scheduling, worker execution, model loading, async decode, and data-parallel/multi-lane execution all live in the plugin, so nothing Tenstorrent-specific has to land in vLLM core.
  [📦 repo](https://github.com/tenstorrent/vllm-tt-plugin)

## 🕵️ AI Agents

- **[Tenstorrent Console Skill](https://github.com/aldegad/tenstorrent)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@aldegad](https://github.com/aldegad) — An agent skill (SKILL.md) that teaches Claude Code, Codex, and the Agent SDK how to drive the console.tenstorrent.com inference API: OpenAI-compatible chat with DeepSeek-R1 and Qwen3, async image jobs, and Wan 2.2 text-to-video. Ships runnable curl examples and a mock-curl test harness; documentation is bilingual Korean/English.
  [📦 repo](https://github.com/aldegad/tenstorrent)

- **Local AI Agents on Tenstorrent** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Three agentic projects running fully on-device: local AI agents on QuietBox 2, a coding assistant powered by Aider against a local inference server, and the OpenClaw AI assistant on QuietBox 2. No cloud APIs — all inference runs on TT hardware.
  [📖 Local AI Agents on QuietBox 2](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/qb2-local-agents/) · [📖 Coding Assistant with Aider](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/coding-assistant/)

- **[tt-claw](https://github.com/tsingletaryTT/tt-claw)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — A Tenstorrent-powered claw machine that rewards players with real prizes. The QuietBox 2 runs local AI inference to act as an agent controlling the claw hardware — the OpenClaw AI assistant lesson builds directly on this project.
  [📦 repo](https://github.com/tsingletaryTT/tt-claw) · [📖 OpenClaw AI Assistant on QuietBox 2](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/qb2-openclaw-assistant/)

## ⚙️ Custom Kernels & Low-Level

- **Tenstorrent SFPU Kernel Series — Jason Davies** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@jasondavies](https://github.com/jasondavies) — Sponsored series of deep technical articles on implementing optimal SFPU kernels for the Tenstorrent Wormhole and Blackhole vector units. Covers where, typecasting, 16/32-bit integer multiplication, cube root, and accurate sin/cos/tan — with cycle counts, assembly walkthroughs, and Blackhole vs Wormhole comparisons throughout.
  [📝 Optimal "where" on Tenstorrent](https://www.jasondavies.com/2025/tenstorrent-where/) · [📝 32-bit Integer Multiplication on Tenstorrent](https://www.jasondavies.com/2025/tenstorrent-multiply-int32/) · [📝 Typecast on Tenstorrent](https://www.jasondavies.com/2025/tenstorrent-typecast/) · [📝 16-bit Integer Multiplication on Tenstorrent](https://www.jasondavies.com/2026/tenstorrent-multiply-int16/) · [📝 Cube Root on Tenstorrent](https://www.jasondavies.com/2026/tenstorrent-cbrt/) · [📝 Accurate sin/cos/tan on Tenstorrent](https://www.jasondavies.com/2026/tenstorrent-sin-cos-tan/)

- **[tt-tiny](https://github.com/geohot/tt-tiny)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@geohot](https://github.com/geohot) — Minimal Python code to access and program the Tenstorrent Blackhole chip directly — George Hotz's exploration of TT hardware programmability with pointed commentary on the architecture.
  [📦 repo](https://github.com/geohot/tt-tiny)

- **[current](https://github.com/seansiddens/current)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@seansiddens](https://github.com/seansiddens) — High-level parallel programming framework for Tenstorrent accelerators, abstracting TT-Metal into a research-oriented programming model for parallel computation.
  [📦 repo](https://github.com/seansiddens/current)

- **[tenstorrent-tiny-examples](https://github.com/jaebaek/tenstorrent-tiny-examples)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@jaebaek](https://github.com/jaebaek) — Simple C++ kernel experiments on a GraySkull e75 chip. Hands-on examples for learning the TT-Metal programming model at the metal level.
  [📦 repo](https://github.com/jaebaek/tenstorrent-tiny-examples)

- **[tt-rqm-kernels](https://github.com/RQM-Technologies-dev/tt-rqm-kernels)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@RQM-Technologies-dev](https://github.com/RQM-Technologies-dev) — Structured quaternion, rotor, and phase-aware tensor kernels on ordinary floating-point tensors, plus StructuredBench. Includes CPU/PyTorch references, simulator and emulator paths, and reproducible Wormhole/N300 evidence for quaternion multiply (`qmul`), fused SU(2) composition, and H2A Hamiltonian lowering.
  [📦 repo](https://github.com/RQM-Technologies-dev/tt-rqm-kernels) · [🌐 Tenstorrent landing page](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/tenstorrent-landing.md) · [🌐 Wormhole qmul benchmark](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/benchmarks/wormhole-qmul.md) · [🌐 Wormhole qmul hardware evidence](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/benchmarks/wormhole-qmul-hardware-evidence.md) · [🌐 SU2ComposeBench](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/benchmarks/su2-compose-bench.md) · [🌐 H2A silicon conformance](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/benchmarks/hamiltonian-lowering-h2a.md) · [🌐 Current-main qmul port](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/upstream/current-main-qmul-port.md) · [🌐 StructuredBench specification](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/structuredbench-spec.md) · [🌐 Tenstorrent RFC](https://github.com/RQM-Technologies-dev/tt-rqm-kernels/blob/main/docs/tenstorrent-rfc.md)

- **[tt-splat — matrix-native 3D Gaussian Splatting on Blackhole](https://github.com/kinginu/tt-splat)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@kinginu](https://github.com/kinginu) — 3D Gaussian Splatting rewritten to run on the matrix engine: a polynomial splat and order-independent weighted-sum blending replace exp and depth-sorted alpha, so the pipeline becomes GEMM → activation → GEMM. Renderer + trainer, trained device-resident on a Blackhole p150a.
  [📦 repo](https://github.com/kinginu/tt-splat)

- **[tt-twitch](https://github.com/geohot/tt-twitch)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@geohot](https://github.com/geohot) — A Tenstorrent Grayskull kernel written live on Twitch by George Hotz. 120-core grid demonstration of live kernel programming.
  [📦 repo](https://github.com/geohot/tt-twitch)

- **[ttnn-helloworld-cpp](https://github.com/marty1885/ttnn-helloworld-cpp)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@marty1885](https://github.com/marty1885) — Minimal working example of using Tenstorrent TTNN in C++. The simplest possible starting point for C++ developers targeting TT hardware with TTNN.
  [📦 repo](https://github.com/marty1885/ttnn-helloworld-cpp)

- **[ttPseudoRowMajor](https://github.com/marty1885/ttPseudoRowMajor)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Martin Chang — A small TTNN-facing C++ library (ttprm) for running view-shaped tensor work without first materializing the view in DRAM. Targets Tenstorrent TILE tensors and uses cached device operations to gather/scatter through layout views.
  [📦 repo](https://github.com/marty1885/ttPseudoRowMajor)

- **[ttVecAdd](https://github.com/marty1885/ttVecAdd)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@marty1885](https://github.com/marty1885) — Minimal vector-addition example on Tenstorrent devices using TT-Metalium. A clean hello-world for the TT-Metal kernel programming model in C++.
  [📦 repo](https://github.com/marty1885/ttVecAdd)

- **[ttWKV7](https://github.com/marty1885/ttWKV7)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Martin Chang — A standalone tt-metal demo and test bench for the RWKV-7 (WKV7) state recurrence on Wormhole, built with a GGML backend in mind. Two compute kernels cover the domain: a chunked-parallel DPLR matmul path for any sequence length with on-chip chunk carry, and a sequential per-token decode path for L <= 32 that is faster for large-batch token generation. The host runner validates both against a CPU oracle by PCC/NMSE and benchmarks them over a sequence/batch grid.
  [📦 repo](https://github.com/marty1885/ttWKV7)

- **[grayskull-attention](https://github.com/moritztng/grayskull-attention)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@moritztng](https://github.com/moritztng) — FlashAttention-style attention kernel implemented entirely in on-chip SRAM on the Tenstorrent Grayskull chip using TT-Metalium. Pioneering work in low-level attention on TT hardware.
  [📦 repo](https://github.com/moritztng/grayskull-attention)

- **Tenstorrent Cookbook: Core Recipes** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Three hands-on TT-Metalium kernel recipes: a Mandelbrot fractal explorer, real-time audio signal processing pipeline, and custom image filter stack. Each recipe is a complete kernel project with full source in the lesson.
  [📖 Tenstorrent Cookbook Overview](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cookbook-overview/) · [📖 Recipe 3: Mandelbrot Fractal Explorer](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cookbook-mandelbrot/) · [📖 Recipe 2: Audio Signal Processing](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cookbook-audio-processor/) · [📖 Recipe 4: Custom Image Filters](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cookbook-image-filters/)

- **[SFPI](https://github.com/tenstorrent/sfpi)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent SFPU programming interface — TT-enhanced RISC-V GCC and binutils plus header files for programming the Tensix SFPU (vector engine) from kernel code. The compiler toolchain underneath TT-Metalium's SFPU ops.
  [📦 repo](https://github.com/tenstorrent/sfpi) · 🐧 `apt install sfpi`

- **[tt-lang](https://github.com/tenstorrent/tt-lang)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Python-based DSL that sits between TT-NN and TT-Metalium — expresses custom fused kernels with progressive disclosure, compiling directly to Tensix. Ships an integrated functional simulator (no hardware needed), line-by-line performance metrics, and AI-agent-friendly tooling. Two packages: tt-lang (compiler + hardware, requires ttnn) and tt-lang-sim (simulator only, works on Linux/macOS without Tenstorrent hardware).
  [📦 repo](https://github.com/tenstorrent/tt-lang) · [🌐 website](https://docs.tenstorrent.com/tt-lang/) · [📖 Introduction to tt-lang](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/tt-lang-intro/) · [🐍 `pip install tt-lang`](https://pypi.org/project/tt-lang/) · [🐍 `pip install tt-lang-sim`](https://pypi.org/project/tt-lang-sim/)

- **[tt-llk](https://github.com/tenstorrent/tt-llk)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent Low-Level Kernels: the C++ library that directly programs the RISC-V cores inside each Tensix compute engine. TRISC0 (unpack), TRISC1 (math/FPU/SFPU), and TRISC2 (pack) are all programmed through this layer — it is the interface between TT-Metal kernel code and bare silicon.
  [📦 repo](https://github.com/tenstorrent/tt-llk) · [📝 Top-level architecture overview](https://github.com/tenstorrent/tt-llk/blob/main/docs/llk/l2/top_level_overview.md)

- **[tt-metal](https://github.com/tenstorrent/tt-metal)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TT-NN operator library and TT-Metalium low-level kernel programming model. The primary SDK for developing on Tenstorrent hardware — from high-level tensor ops to bare-metal RISC-V kernels.
  [📦 repo](https://github.com/tenstorrent/tt-metal) · [🌐 website](https://docs.tenstorrent.com/tt-metal/latest/ttnn/) · 🐧 `apt install tt-metalium` · 🐧 `apt install tt-nn`

## 🔨 Compilers & Frontends

- **[BarraCUDA](https://github.com/Zaneham/BarraCUDA)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@Zaneham](https://github.com/Zaneham) — Open-source CUDA compiler targeting multiple GPU architectures including Tenstorrent. Compiles .cu files to run on AMD and Tenstorrent hardware without modification.
  [📦 repo](https://github.com/Zaneham/BarraCUDA)

- **[triton-tenstorrent](https://github.com/kernelize-ai/triton-tenstorrent)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@kernelize-ai](https://github.com/kernelize-ai) — OpenAI Triton compiler plugin for Tenstorrent hardware. Write Triton kernels and target Tensix cores — brings the Triton ML kernel ecosystem to TT devices.
  [📦 repo](https://github.com/kernelize-ai/triton-tenstorrent)

- **[tt-iree](https://github.com/swote-git/tt-iree)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@swote-git](https://github.com/swote-git) — IREE (Intermediate Representation Execution Environment) ML compiler ported to Tenstorrent AI accelerators. Brings the IREE compiler ecosystem to TT hardware.
  [📦 repo](https://github.com/swote-git/tt-iree)

- **[libtt](https://github.com/pcmoritz/libtt)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Philipp Moritz — A Bazel-built PJRT plugin (libtt.so) providing an XLA backend for Tenstorrent devices. Bundles the tt-xla PJRT implementation with tt-mlir and tt-metal into a single shared object so JAX code runs on Tenstorrent hardware, with patches so sglang-jax works out of the box.
  [📦 repo](https://github.com/pcmoritz/libtt)

- **[tt-tinygrad](https://github.com/Gogopex/tt-tinygrad)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@Gogopex](https://github.com/Gogopex) — A Tenstorrent backend for tinygrad that targets TT-Lang rather than raw tt-metal: a Renderer classifies each UOp kernel graph as matmul, reduce, or elementwise and emits ttl.math.* Python source, and a Compiled device parses the rendered kernel's contract, materializes ttnn tensors from host buffers, and calls it in-process. Proof of concept — 110 pass / 13 xfail across 125 cases on a QuietBox, covering fused matmul, reductions, softmax, layernorm, and attention chains, on top of a three-line patch to upstream tinygrad.
  [📦 repo](https://github.com/Gogopex/tt-tinygrad)

- **[zyx](https://github.com/zk4x/zyx)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@zk4x](https://github.com/zk4x) — A complete ML library and compiler in Rust — "from assembly to neural networks" — with a native Tenstorrent backend (src/backend/tenstorrent), autograd, custom kernels, multi-backend support, and Python bindings.
  [📦 repo](https://github.com/zk4x/zyx) · [🌐 website](https://docs.rs/zyx)

- **[tt-forge-compiletron](https://github.com/tsingletaryTT/tt-forge-compiletron)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Compile more than 100 models on tt-forge in a display format suitable for demos. Comprehensive showcase of tt-forge model compatibility.
  [📦 repo](https://github.com/tsingletaryTT/tt-forge-compiletron)

- **Image Classification with TT-Forge** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — End-to-end image classification project using TT-Forge — compile and run a PyTorch classification model on Tenstorrent hardware with no kernel authoring required.
  [📖 Image Classification with TT-Forge](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/forge-image-classification/)

- **[tt-buda](https://github.com/tenstorrent/tt-buda)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TT-BUDA: Tenstorrent's original Python compiler and runtime for AI workloads. Legacy stack — tt-forge is the recommended successor, but tt-buda has the largest model demo library.
  [📦 repo](https://github.com/tenstorrent/tt-buda)

- **[tt-forge-onnx](https://github.com/tenstorrent/tt-forge-onnx)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  ONNX graph compiler for Tenstorrent hardware. Optimizes and transforms ONNX model graphs for efficient execution on Tensix accelerators. Used as a backend by tt-forge for ONNX model ingestion.
  [📦 repo](https://github.com/tenstorrent/tt-forge-onnx)

- **[tt-forge](https://github.com/tenstorrent/tt-forge)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent's MLIR-based compiler frontend. Enables running AI workloads from PyTorch, ONNX, and other frameworks on all Tenstorrent hardware configurations through an open-source, general, and performant compiler.
  [📦 repo](https://github.com/tenstorrent/tt-forge) · [🌐 website](https://tenstorrent.com)

- **[tt-mlir](https://github.com/tenstorrent/tt-mlir)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent MLIR compiler — the core compiler infrastructure shared by tt-forge and other frontends. Handles graph optimization, lowering, and code generation for Tensix hardware.
  [📦 repo](https://github.com/tenstorrent/tt-mlir) · [🌐 website](https://tenstorrent.github.io/tt-mlir/)

- **[tt-torch](https://github.com/tenstorrent/tt-torch)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Frontend integration for PyTorch with tt-mlir. Compile PyTorch models directly to Tenstorrent hardware via torch.compile integration.
  [📦 repo](https://github.com/tenstorrent/tt-torch) · [🌐 website](https://docs.tenstorrent.com/tt-torch/)

- **[tt-tvm](https://github.com/tenstorrent/tt-tvm)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TVM for Tenstorrent ASICs. Brings the Apache TVM compiler stack to Tenstorrent hardware, enabling model compilation from TensorFlow, PyTorch, ONNX, and more.
  [📦 repo](https://github.com/tenstorrent/tt-tvm)

- **[tt-xla](https://github.com/tenstorrent/tt-xla)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  PJRT device plugin for Tenstorrent hardware. Enables JAX, PyTorch/XLA, and other XLA-based frameworks to target TT accelerators.
  [📦 repo](https://github.com/tenstorrent/tt-xla) · [📖 JAX and PyTorch/XLA on Tenstorrent](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/tt-xla-jax/) · [🌐 website](https://docs.tenstorrent.com/tt-xla)

## 🛠 Dev Tools & Debugging

- **[nvtop](https://github.com/Syllo/nvtop)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@Syllo](https://github.com/Syllo) — htop-style process monitor for GPUs and AI accelerators. Supports AMD, Apple, Huawei, Intel, NVIDIA, Qualcomm — and Tenstorrent. Real-time utilization, memory, and process info in a terminal UI.
  [📦 repo](https://github.com/Syllo/nvtop)

- **[libtt-metal-cxx](https://github.com/Knight-Ops/libtt-metal-cxx)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@Knight-Ops](https://github.com/Knight-Ops) — Rust crate that exposes the TT-Metal host API through a C++ bridge via cxx.rs — covering device management, program/kernel creation (from source file or inline string), circular buffers, semaphores, runtime arguments, sharded buffers, and MeshDevice workflows, with hardware-backed integration tests.
  [📦 repo](https://github.com/Knight-Ops/libtt-metal-cxx)

- **[tenstorrent-cli](https://github.com/aldegad/tenstorrent-cli)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@aldegad](https://github.com/aldegad) — A TypeScript/Bun terminal client for console.tenstorrent.com. Opens a chat REPL across DeepSeek-R1, Qwen3-32B, Qwen3-VL, and Gemma, with slash commands that submit image, Wan 2.2 video, TTS, and STT jobs, poll them, and save the results under ./output. Reads its API key only from the TENSTORRENT_KEY environment variable — never from disk.
  [📦 repo](https://github.com/aldegad/tenstorrent-cli)

- **[tt-monitor](https://github.com/antonibertel/tt-monitor)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@antonibertel](https://github.com/antonibertel) — A translucent, undecorated desktop widget showing live per-chip telemetry for Tenstorrent accelerators: temperature and power sparklines against the card's thermal and TDP limits, AI clock, voltage, current, DRAM channel training and ECC error counts, PCIe link generation/width, and board identity. Reads hardware directly through luwen over /dev/tenstorrent — no Python, no tt-smi subprocess, and no root.
  [📦 repo](https://github.com/antonibertel/tt-monitor)

- **[ttas](https://github.com/Zaneham/ttas)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@Zaneham](https://github.com/Zaneham) — ttas is a hacker-friendly assembler/disassembler for Tensix on Wormhole. It turns assembly into the exact 32-bit words the hardware runs, and turns binaries back into readable instructions using the same shared instruction table.
  [📦 repo](https://github.com/Zaneham/ttas)

- **[ttPEAK](https://github.com/TT-Bounty-Hunters/ttPEAK)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@TT-Bounty-Hunters](https://github.com/TT-Bounty-Hunters) — clpeak-style peak-performance benchmark for Tenstorrent devices using TT-Metalium. Measures theoretical peak throughput across operations — useful for hardware characterization.
  [📦 repo](https://github.com/TT-Bounty-Hunters/ttPEAK)

- **[tensix-viz](https://github.com/tsingletaryTT/tensix-viz)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Hardware topology visualizer for Tenstorrent chips — from individual chip to full cluster. Interactive JavaScript visualization of Tensix core layout and NoC connections.
  [📦 repo](https://github.com/tsingletaryTT/tensix-viz) · [🌐 website](https://tsingletarytt.github.io/tensix-viz/)

- **[tt-model-runner](https://github.com/tsingletaryTT/tt-model-runner)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Discover, load, and benchmark models with a GUI and TUI for tt-inference-server. Makes exploring available models on Tenstorrent hardware as easy as browsing a catalog.
  [📦 repo](https://github.com/tsingletaryTT/tt-model-runner)

- **[tt-warp](https://github.com/tsingletaryTT/tt-warp)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Warp terminal plugin for Tenstorrent — integrates hardware status, model management, and developer workflows directly into the Warp terminal.
  [📦 repo](https://github.com/tsingletaryTT/tt-warp)

- **Tensix Grid Playground** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Interactive browser-based visualizer of the Tenstorrent Tensix grid architecture. Explore the NoC, core layout, and dataflow patterns without hardware — a great companion for learning kernel programming.
  [🚀 Tensix Grid Playground (interactive)](https://docs.tenstorrent.com/tt-vscode-toolkit/tensix-playground/)

- **[tt-cli](https://github.com/tenstorrent/tt-cli)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Single entry point to the Tenstorrent software stack: `tt update` converges a machine onto the CI-tested "golden" version set, `tt device` covers status/info/reset, and `tt model`/`tt serve` pull weights and bring up tt-inference-server. Commands either run natively or delegate to tt-smi, tt-flash, and tt-installer behind a stable interface, with `--json` output and documented exit codes on every command. Early prototype — the README labels it an internal prototype and several subcommands are still stubs.
  [📦 repo](https://github.com/tenstorrent/tt-cli)

- **[tt-emule](https://github.com/tenstorrent/tt-emule)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  A C++ software emulator of the Tenstorrent device-level kernel and host APIs. Run tt-metal kernel and host code on a standard x86-64 Linux machine — no Tenstorrent hardware required.
  [📦 repo](https://github.com/tenstorrent/tt-emule)

- **[tt-exalens](https://github.com/tenstorrent/tt-exalens)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Low-level hardware debugger for Tenstorrent devices. Inspect register state, memory contents, and kernel execution at the hardware level.
  [📦 repo](https://github.com/tenstorrent/tt-exalens) · [🐍 `pip install tt-exalens`](https://pypi.org/project/tt-exalens/)

- **[tt-kernel](https://github.com/tenstorrent/tt-kernel-package-manager)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Distributes models over the Hugging Face Hub and serves them on Tenstorrent hardware — `tt-kernel serve <namespace>/<model>` pulls a bundle, registers it with the Tenstorrent vLLM plugin, and launches an OpenAI-compatible server. A vLLM bundle ships only adapter code and metadata (weights stay referenced by HF repo id), while legacy kernel-cache bundles package precompiled tt-metal kernel binaries so a model's first run is a cache hit instead of a slow JIT recompile. Explicitly experimental — the bundle format and APIs may change without notice.
  [📦 repo](https://github.com/tenstorrent/tt-kernel-package-manager)

- **[tt-npe](https://github.com/tenstorrent/tt-npe)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Network-on-chip Performance Estimator for Tenstorrent Tensix-based devices. Model and estimate NoC utilization before running kernels on hardware.
  [📦 repo](https://github.com/tenstorrent/tt-npe)

- **[tt-perf-report](https://github.com/tenstorrent/tt-perf-report)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Performance report analysis tool for Tenstorrent Metal operations — analyzes perf traces to surface throughput, bottlenecks, and optimization opportunities.
  [📦 repo](https://github.com/tenstorrent/tt-perf-report)

- **[ttnn-visualizer](https://github.com/tenstorrent/ttnn-visualizer)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Comprehensive tool for visualizing and analyzing model execution on Tenstorrent hardware. Interactive graphs, memory plots, tensor details, buffer overviews, operation flow graphs, and multi-instance support.
  [📦 repo](https://github.com/tenstorrent/ttnn-visualizer) · [🐍 `pip install ttnn-visualizer`](https://pypi.org/project/ttnn-visualizer/)

## 🖥 Hardware & System

- **[blackhole-py](https://github.com/boopdotpng/blackhole-py)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@boopdotpng](https://github.com/boopdotpng) — Pure Python driver for Tenstorrent Blackhole cards providing direct low-level hardware access without going through the full TT-Metal stack.
  [📦 repo](https://github.com/boopdotpng/blackhole-py)

- **[tenstorrent.nix](https://github.com/RossComputerGuy/tenstorrent.nix)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@RossComputerGuy](https://github.com/RossComputerGuy) — Nix flake packaging the Tenstorrent software stack for NixOS and Nix users. Reproducible, declarative installation of TT drivers and tools.
  [📦 repo](https://github.com/RossComputerGuy/tenstorrent.nix)

- **[tetsuh/tt-metal-community-distro-matrix](https://github.com/tetsuh/tt-metal-community-distro-matrix)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@tetsuh](https://github.com/tetsuh) — A compatibility guardrail that continuously monitors whether [tt-metal](https://github.com/tenstorrent/tt-metal) and the official [tt-installer](https://github.com/tenstorrent/tt-installer) build successfully on community Linux distributions that are not part of Tenstorrent's official CI.
  [📦 repo](https://github.com/tetsuh/tt-metal-community-distro-matrix)

- **[tt-qb-lights](https://github.com/tsingletaryTT/tt-qb-lights)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Sync your Tenstorrent Quietbox's RGB lighting to accelerator utilization status. Visual feedback for hardware activity in real time.
  [📦 repo](https://github.com/tsingletaryTT/tt-qb-lights)

- **[luwen](https://github.com/tenstorrent/luwen)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent system interface library written in Rust. Low-level Rust bindings for communicating with and managing TT hardware.
  [📦 repo](https://github.com/tenstorrent/luwen) · [🦀 `cargo add luwen`](https://crates.io/crates/luwen) · 🐧 `apt install python3-pyluwen`

- **[tt-burnin](https://github.com/tenstorrent/tt-burnin)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Command-line utility that runs a high power-consumption workload on Tenstorrent devices — used for chip testing, burn-in, and validating a system's power delivery and cooling under sustained load.
  [📦 repo](https://github.com/tenstorrent/tt-burnin) · [🐍 `pip install tt-burnin`](https://pypi.org/project/tt-burnin/) · 🐧 `apt install tt-burnin`

- **[tt-CableGen](https://github.com/tenstorrent/tt-CableGen)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Network cabling visualizer for Tenstorrent scale-out deployments: describe a target topology and it generates and renders how to physically cable multiple Wormhole or Blackhole systems together. Works in a physical-deployment mode with racking information and a logical-hierarchy mode for clustering/pod groupings, with topology import/export and a Docker deployment path.
  [📦 repo](https://github.com/tenstorrent/tt-CableGen)

- **[tt-firmware](https://github.com/tenstorrent/tt-firmware)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent firmware repository. Board management and control firmware for Tenstorrent accelerator cards.
  [📦 repo](https://github.com/tenstorrent/tt-firmware)

- **[tt-flash](https://github.com/tenstorrent/tt-flash)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent firmware update utility. Flash new firmware onto Tenstorrent accelerator cards from the command line.
  [📦 repo](https://github.com/tenstorrent/tt-flash) · [🐍 `pip install tt-flash`](https://pypi.org/project/tt-flash/) · 🐧 `apt install tt-flash`

- **[tt-installer](https://github.com/tenstorrent/tt-installer)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Install the complete Tenstorrent software stack with one command. Handles drivers, firmware, Python environment, and SDK setup automatically.
  [📦 repo](https://github.com/tenstorrent/tt-installer) · [📖 Modern Setup lesson (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/modern-setup/)

- **[tt-kmd](https://github.com/tenstorrent/tt-kmd)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent kernel module driver. The Linux kernel module required to interface with Tenstorrent PCIe accelerator cards.
  [📦 repo](https://github.com/tenstorrent/tt-kmd) · 🐧 `apt install tenstorrent-dkms`

- **[TT-QuietBox 2 Guide](https://github.com/tenstorrent/tt-quietbox2-guide)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Official setup and onboarding guide for the TT-QuietBox 2 — a compact, liquid-cooled AI workstation with four Blackhole accelerators, an AMD Ryzen CPU, 256GB RAM, and 4TB NVMe. Covers hardware specs, first-boot setup, and hands-on learning paths for running pre-loaded models like Qwen3-32B and serving text, image, video, and speech models via tt-inference-server.
  [📦 repo](https://github.com/tenstorrent/tt-quietbox2-guide) · [🌐 TT-QuietBox 2 Guide](https://docs.tenstorrent.com/tt-quietbox2-guide)

- **[tt-smi](https://github.com/tenstorrent/tt-smi)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent System Management Interface — monitor device telemetry, issue board-level resets, and inspect hardware health. The nvidia-smi equivalent for Tenstorrent hardware.
  [📦 repo](https://github.com/tenstorrent/tt-smi) · [🐍 `pip install tt-smi`](https://pypi.org/project/tt-smi/) · 🐧 `apt install tt-smi`

- **[tt-system-firmware](https://github.com/tenstorrent/tt-system-firmware)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  System firmware for Tenstorrent hardware. Low-level system initialization and control firmware that runs on-device.
  [📦 repo](https://github.com/tenstorrent/tt-system-firmware) · [🌐 website](https://tenstorrent.com)

- **[tt-system-tools](https://github.com/tenstorrent/tt-system-tools)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  System setup and support utilities for Tenstorrent hardware — hugepages-setup configures the 1GB hugepages TT ASICs need, and tt-oops collects diagnostic data for troubleshooting. Ships as the tenstorrent-tools deb/rpm.
  [📦 repo](https://github.com/tenstorrent/tt-system-tools) · 🐧 `apt install tenstorrent-tools`

- **[tt-tools-common](https://github.com/tenstorrent/tt-tools-common)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Shared helper library of common utilities used across Tenstorrent system tools such as tt-smi, tt-flash, and tt-topology. A dependency rather than a standalone tool.
  [📦 repo](https://github.com/tenstorrent/tt-tools-common) · [🐍 `pip install tt-tools-common`](https://pypi.org/project/tt-tools-common/) · 🐧 `apt install python3-tt-tools-common`

- **[tt-toplike](https://github.com/tenstorrent/tt-toplike)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  A vibrant htop-style visualizer for Tenstorrent hardware written in Rust. Real-time process and utilization view for TT accelerators.
  [📦 repo](https://github.com/tenstorrent/tt-toplike) · [🌐 website](https://docs.tenstorrent.com/tt-toplike/) · 🐧 `apt install tt-toplike` · 🐧 `apt install tt-toplike-app`

- **[tt-topology](https://github.com/tenstorrent/tt-topology)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Configure Ethernet routing on multi-card Tenstorrent systems. Flash NB cards to use specific ETH routing configurations for scale-out deployments.
  [📦 repo](https://github.com/tenstorrent/tt-topology) · [🐍 `pip install tt-topology`](https://pypi.org/project/tt-topology/) · 🐧 `apt install tt-topology`

- **[tt-umd](https://github.com/tenstorrent/tt-umd)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  User-mode driver for Tenstorrent hardware. The userspace layer that sits between the kernel module and higher-level SDKs.
  [📦 repo](https://github.com/tenstorrent/tt-umd)

- **[WallaBMC](https://github.com/tenstorrent/wallabmc)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Lightweight BMC (Baseboard Management Controller) for STM32 and similar MCUs, with Web UI, Redfish API, and HTTPS support. Built on Zephyr RTOS. Used in Tenstorrent systems.
  [📦 repo](https://github.com/tenstorrent/wallabmc)

## ☁️ Cloud & Orchestration

- **[dstack](https://github.com/dstackai/dstack)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@dstackai](https://github.com/dstackai) — Vendor-agnostic orchestration for training, inference, and agentic workloads across NVIDIA, AMD, TPU, and Tenstorrent on clouds, Kubernetes, and bare metal.
  [📦 repo](https://github.com/dstackai/dstack) · [🌐 website](https://dstack.ai)

- **[koyeb/tenstorrent-examples](https://github.com/koyeb/tenstorrent-examples)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@koyeb](https://github.com/koyeb) — Example applications and deployment configurations for running AI workloads on Tenstorrent hardware via Koyeb's cloud platform.
  [📦 repo](https://github.com/koyeb/tenstorrent-examples) · [🌐 Koyeb blog post](https://www.koyeb.com/blog/tenstorrent-cloud-instances-unveiling-next-gen-ai-accelerators)

- **TT Console** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Browser-based cloud console for exploring AI on Tenstorrent hardware. Run LLM inference, image and video generation, and browse the supported model catalog in-browser — backed by Tenstorrent accelerators. Cloud hardware access and advanced workflows (deployments, agents) available in staged rollout.
  [🌐 console.tenstorrent.com](https://console.tenstorrent.com)

- **Cloud-Native Support** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Official documentation hub for running Tenstorrent accelerators on Kubernetes. Centers on tt-operator (the umbrella Helm chart) and covers Node Feature Discovery, kernel-mode driver (tt-kmd) management, firmware flashing, Prometheus telemetry, Fabric Manager topology resolution, Dynamic Resource Allocation, and multi-node scheduling via JobSet and PMIx.
  [🌐 docs.tenstorrent.com](https://docs.tenstorrent.com/cloud-native-support/)

## 🔩 RISC-V & Architecture

- **[bhx](https://github.com/olofj/bhx)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@olofj](https://github.com/olofj) — Boot stock Linux cloud images on the SiFive X280 RISC-V cores inside Tenstorrent Blackhole AI accelerators. Per-card Rust daemon with virtio-mmio block/net/console and U-Boot/EFI support.
  [📦 repo](https://github.com/olofj/bhx)

- **Tenstorrent Blackhole Architecture Guide** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@boopdotpng](https://github.com/boopdotpng) — A 6,500-word community deep dive into the Blackhole p100a architecture: the tile model (Tensix, DRAM, SiFive x280 L2CPU, Ethernet, PCIe, NoC arc), firmware startup sequence, MOP micro-op processor, replay buffer, FPU/SFPU sync, and the anatomy of a kernel. From the author of blackhole-py.
  [📝 anuraagw.me — February 2026](https://anuraagw.me/blog/blackhole-architecture)

- **[tt-sim](https://github.com/mesham/tt-sim)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@mesham](https://github.com/mesham) — Community-built Tenstorrent architecture simulator written in Python. Runs without hardware — useful for researchers and developers exploring the Tensix architecture offline.
  [📦 repo](https://github.com/mesham/tt-sim)

- **[tt-bh-linux](https://github.com/tenstorrent-riscv-software/tt-bh-linux)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Linux demo for the Tenstorrent Blackhole P100/P150 card RISC-V cores. Boot a real Linux kernel on the 16 high-performance RISC-V cores built into the Blackhole chip.
  [📦 repo](https://github.com/tenstorrent-riscv-software/tt-bh-linux) · [🌐 website](https://tenstorrent.com/hardware/blackhole)

- **[RiESCUE](https://github.com/tenstorrent/riescue)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  RISC-V Directed Test Framework and Compliance Suite. Comprehensive test infrastructure for verifying RISC-V processor implementations against the specification.
  [📦 repo](https://github.com/tenstorrent/riescue) · [🌐 website](https://docs.tenstorrent.com/riescue/)

- **[riscv_arch_tests](https://github.com/tenstorrent/riscv_arch_tests)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  RISC-V architectural self-checking directed tests — randomly-generated register operands and data with low-level OS code for test scheduling and self-checking, runnable on a RISC-V design or an ISS such as Whisper or Spike. Generated by an internal Tenstorrent tool from the official RISC-V ISA spec.
  [📦 repo](https://github.com/tenstorrent/riscv_arch_tests)

- **[riscv-ocelot](https://github.com/tenstorrent/riscv-ocelot)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  The Berkeley Out-of-Order Machine with V-EXT (RISC-V Vector Extension) support. Tenstorrent's research-grade out-of-order RISC-V core with vector extension.
  [📦 repo](https://github.com/tenstorrent/riscv-ocelot)

- **[tensix-isa-simulator](https://github.com/tenstorrent/tensix-isa-simulator)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  ISA-level simulator for the Tensix compute engine. Simulates the matrix, vector, and scalar units inside each Tensix core.
  [📦 repo](https://github.com/tenstorrent/tensix-isa-simulator)

- **[tt-rpm](https://github.com/tenstorrent/tt-rpm)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Cycle-level, execution-driven RISC-V CPU performance model built on Sparta (MAP) with Whisper supplying functional execution, so it runs real ELF binaries — CoreMark, Dhrystone — to completion. The pipeline is YAML-configurable across in-order/out-of-order execution, issue policy, execute granularity, write-port arbitration, and bypass paths, with a modeled L1 I$/D$ plus optional unified L2, per-unit logging, stats reports, and Konata pipeline visualization.
  [📦 repo](https://github.com/tenstorrent/tt-rpm)

- **[ttsim-qemu](https://github.com/tenstorrent/ttsim-qemu)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent's fork of QEMU that provides the full-system emulation layer behind ttsim. Models the RISC-V cores and system devices of Wormhole and Blackhole so TT-Metalium workloads can boot and run without physical silicon.
  [📦 repo](https://github.com/tenstorrent/ttsim-qemu)

- **[ttsim](https://github.com/tenstorrent/ttsim)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Fast full-system simulator of Tenstorrent Wormhole and Blackhole hardware. Runs TT-Metalium workloads on any Linux/x86_64 system without physical silicon. Bit-exact results relative to hardware.
  [📦 repo](https://github.com/tenstorrent/ttsim) · [📖 lesson](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ttsim-twenty-and-ten/)

- **[whisper](https://github.com/tenstorrent/whisper)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  RISC-V Instruction Set Simulator (ISS) used by Tenstorrent for processor verification. Powers the co-simulation architecture checker.
  [📦 repo](https://github.com/tenstorrent/whisper)

## 🔬 Research & Papers

- **Attention in SRAM on Tenstorrent Grayskull** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Moritz Thüning — A fused kernel for the Grayskull architecture implementing Transformer self-attention entirely within SRAM. Combines matrix multiply, attention score scaling, and Softmax without DRAM accesses, achieving significant speedups over non-fused implementations.
  [📄 arXiv:2407.13885](https://arxiv.org/abs/2407.13885)

- **Exploring Fast Fourier Transforms on the Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Nick Brown, Jake Davies, Felix LeClair — Ports the Cooley-Tukey FFT algorithm to the Wormhole n300 RISC-V accelerator. The Wormhole draws 8× less power and consumes 2.8× less energy than a 24-core Xeon Platinum for a 2D FFT. ISC 2025.
  [📄 arXiv:2506.15437](https://arxiv.org/abs/2506.15437) · [📝 University of Edinburgh](https://www.research.ed.ac.uk/en/publications/exploring-fast-fourier-transforms-on-the-tenstorrent-wormhole/)

- **Assessing Tenstorrent Grayskull RISC-V MatMul Acceleration for LLMs** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Hiari Pizzini Cavagna, Daniele Cesarini, Andrea Bartolini — Evaluates the Tenstorrent Grayskull e75 RISC-V accelerator for matrix multiplication at reduced numerical precision (BFP8 and LoFi), a fundamental kernel in LLM inference computation.
  [📄 arXiv:2505.06085](https://arxiv.org/abs/2505.06085)

- **Porting Strategies for Gravitational N-Body Simulations on Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Jenny Lynn Almerol, Elisabetta Boella, Mario Spera, Daniele Gregori — Evaluates three strategies for scaling an N-body code across multiple Tenstorrent Wormhole accelerators. Builds on the established performance of single-card N-body work to explore parallelism via the on-chip NoC and multi-accelerator configurations.
  [📄 arXiv:2605.02744](https://arxiv.org/abs/2605.02744)

- **Accelerating Gravitational N-Body Simulations on Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Accelerates an astrophysical N-body simulation on the Wormhole n300. Achieves 2× speedup and 2× energy savings over a highly optimized CPU implementation. SC '25 Workshop.
  [📄 arXiv:2509.19294](https://arxiv.org/abs/2509.19294) · [📝 ACM SC '25](https://dl.acm.org/doi/10.1145/3731599.3767528)

- **Numerical Kernels on a Spatial Accelerator: Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Implements three numerical kernels and composes them into a conjugate gradient solver on Wormhole. Demonstrates AI accelerators merit consideration for HPC workloads traditionally dominated by CPUs and GPUs. 2026.
  [📄 arXiv:2603.23343](https://arxiv.org/abs/2603.23343)

- **[Collective Operations on Wormhole n150 (Sapienza University of Rome)](https://github.com/EngineerCharlie/TenstorrentAllreduce)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Charles Heron (Sapienza University of Rome) — Master's thesis implementing and benchmarking five allreduce algorithms (Swing, Recursive Doubling, Bandwidth Optimal, Latency Optimal, Shared Memory) on the Wormhole n150. Bandwidth Optimal achieved best performance, approaching within 2× of theoretical optimal.
  [📦 repo](https://github.com/EngineerCharlie/TenstorrentAllreduce)

- **Accelerating Stencils on the Tenstorrent Grayskull RISC-V Accelerator** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Explores stencil computation on the Grayskull PCIe RISC-V accelerator. Early academic work examining TT hardware for HPC stencil workloads. 2024.
  [📄 arXiv:2409.18835](https://arxiv.org/abs/2409.18835)

- **Stencil Computations on Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Maps 2D 5-point stencil computations onto the Tenstorrent Wormhole RISC-V AI dataflow accelerator via two implementations: element-wise decomposition (Axpy) and matrix-multiplication reformulation (MatMul). Profiling shows the isolated Wormhole kernel is competitive with CPU execution, with PCIe transfers and initialization driving end-to-end overhead; Axpy achieves lower energy than the CPU baseline at large scales. Identifies architectural and software directions for making AI accelerators viable for HPC stencil workloads. 2025.
  [📄 arXiv:2605.07599](https://arxiv.org/abs/2605.07599)

- **SwiftNPU: Scalable Shape-Flexible Allocation for Inter-Core Connected NPUs** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Makes multi-tenant NPU sharing practical for Blackhole-class hardware using polynomial-time allocation algorithms. Delivers up to 1.37× higher utilization and 1.14× faster workload completion. Up to 890,000× faster than NP-hard baselines.
  [📄 ACM DL](https://dl.acm.org/doi/10.1145/3805621.3807614)

- **TileLoom: Automatic Dataflow Planning for Spatial Dataflow Accelerators** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Wei Li, Zhenyu Bai, Heru Wang, Pranav Dangi — Compiler system that automatically generates efficient dataflow plans for tile-based languages on spatial accelerators including Tenstorrent Wormhole. Exploits on-chip network forwarding between processing elements to reduce DRAM pressure.
  [📄 arXiv:2512.22168](https://arxiv.org/abs/2512.22168)

- **Rewriting TTS Inference Economics: Lightning V2 on Tenstorrent vs. NVIDIA L40S** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Ranjith M. S., Akshat Mandloi, Sudarshan Kamath — Shows that Text-to-Speech inference on Tenstorrent Lightning V2 achieves 4× lower cost than NVIDIA L40S. Applies BlockFloat8 (BFP8) and low-fidelity (LoFi) precision strategies to TTS despite their greater numerical fragility compared to LLMs.
  [📄 arXiv:2604.03279](https://arxiv.org/abs/2604.03279)

- **[polaris](https://github.com/tenstorrent/polaris)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  A high-level AI simulator from Tenstorrent for modeling and exploring AI accelerator and workload performance.
  [📦 repo](https://github.com/tenstorrent/polaris)

- **[tt-isa-documentation](https://github.com/tenstorrent/tt-isa-documentation)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Low-level ISA and microarchitecture documentation for Tenstorrent AI architectures (Grayskull, Wormhole, Blackhole) — the authoritative hardware reference beneath the tt-forge / tt-metal software stack.
  [📦 repo](https://github.com/tenstorrent/tt-isa-documentation)

## 🎮 Games & Demos

- **[TT-GoL](https://github.com/JushBJJ/TT-GoL)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@JushBJJ](https://github.com/JushBJJ) — Conway's Game of Life implemented on Tenstorrent hardware using TT-Metal kernels.
  [📦 repo](https://github.com/JushBJJ/TT-GoL)

- **[ttMandelbrot](https://github.com/marty1885/ttMandelbrot)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@marty1885](https://github.com/marty1885) — Mandelbrot Set fractal renderer running on Tenstorrent hardware. A classic demo showcasing parallel compute on Tensix cores.
  [📦 repo](https://github.com/marty1885/ttMandelbrot)

- **[tt-zork-and-more](https://github.com/tsingletaryTT/tt-zork-and-more)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — A Tenstorrent fork of Infocom's Zork I (and more!), running a Z-machine interpreter at least four different ways on TT hardware. The most fun you can have with an AI accelerator.
  [📦 repo](https://github.com/tsingletaryTT/tt-zork-and-more) · [🌐 website](https://tsingletaryTT.github.io/tt-zork-and-more)

- **Tenstorrent Cookbook: Particle Life Simulator** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Particle Life simulation on Tenstorrent hardware — an emergent-behavior N-body system where simple attraction/repulsion rules between species produce complex lifelike patterns. Cookbook recipe demonstrating parallel N-body compute on Tensix.
  [📖 Cookbook Recipe 5: Particle Life Simulator](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cookbook-particle-life/)

- **Tenstorrent Cookbook: Conway's Game of Life** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — TT-Metalium implementation of Conway's Game of Life as a cookbook recipe. Each generation is a full parallel kernel dispatch over the grid — a clean introduction to stateful compute on Tensix cores.
  [📖 Cookbook Recipe 1: Conway's Game of Life](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cookbook-game-of-life/)

## 📚 Guides, Tutorials & Education

- **Programming Tenstorrent Processors** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Martin Chang — Deep-dive into the Tenstorrent architecture and Metalium programming model — circular buffers, kernel synchronization, NoC routing, and where the footguns are. The honest guide to thinking in Tensix.
  [📝 clehaxze.tw — April 2025](https://clehaxze.tw/gemlog/2025/04-21-programming-tensotrrent-processors.gmi)

- **A Gentle Guide: Tenstorrent Card on Arch Linux with Metalium** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Martin Chang — Step-by-step guide to getting a Tenstorrent card running on Arch Linux with the full Metalium stack. Practical troubleshooting from someone who did it the hard way first.
  [📝 clehaxze.tw — July 2024](https://clehaxze.tw/gemlog/2024/07-07-a-gentle-guide-on-getting-your-tenstorrent-card-running-on-arch-linux-with-the-metalium-stack.gmi)

- **Thoughts and Logs After Messing with Tenstorrent Grayskull** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Martin Chang — Honest field notes from getting a Grayskull card running and writing first Metalium kernels. Covers setup pitfalls, processor hangs, memory protection quirks, and what makes Metalium compelling despite early rough edges.
  [📝 clehaxze.tw — June 2024](https://clehaxze.tw/gemlog/2024/06-02-thoughts-and-logs-after-messing-with-tenstorrent-grayskull.gmi)

- **Tenstorrent Architecture — W&M CSCI654 Advanced Computer Architecture** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Yifan & GPU / William & Mary — Lecture 20 from William & Mary's graduate Computer Architecture course. Frames Tenstorrent in the landscape between GPUs and TPUs, draws comparisons to Cerebras and SambaNova, then dives deep into the Wormhole chip and Tensix core: the 5 RISC-V core design, SFPU, NoC, and dataflow execution model.
  [🎥 Lecture 20 — Tenstorrent Architecture (YouTube)](https://www.youtube.com/watch?v=CixEFPc8oxg)

- **[Tensix Field Guide](https://github.com/OrangeTangy/tensix-field-guide)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by Tanay Anand — A ten-chapter, plain-English tour of Tenstorrent's Tensix architecture written for someone who knows what a CPU and a GPU are and nothing else: the chip-level grid and NoC, the five RISC-V baby cores, the matrix engine and its LoFi/HiFi fidelity trade-off, the SFPU, L1 and circular buffers, and why everything is 32x32 tile-shaped. The goal is to get a newcomer to the point of reading tt-metal kernel code in one sitting. Self-described draft; every claim traces back to tt-metal tech reports, tt-llk docs, or METALIUM_GUIDE.
  [📦 repo](https://github.com/OrangeTangy/tensix-field-guide)

- **[TT-Metal Mini Template](https://github.com/JushBJJ/TT-Metal-Mini-Template)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@JushBJJ](https://github.com/JushBJJ) — Minimal working CMake project template for starting a new TT-Metal project from scratch. Good starting point for community kernel development.
  [📦 repo](https://github.com/JushBJJ/TT-Metal-Mini-Template)

- **[tt-tutorial (HPC)](https://github.com/RISCVtestbed/tt-tutorial)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@RISCVtestbed](https://github.com/RISCVtestbed) — Tutorial on Tenstorrent hardware for HPC researchers from the RISC-V Testbed project at Edinburgh/EPCC. Covers Wormhole from an HPC parallel-computing perspective.
  [📦 repo](https://github.com/RISCVtestbed/tt-tutorial)

- **[tt-tutorial (Korean)](https://github.com/changh95/tt-tutorial)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  by [@changh95](https://github.com/changh95) — Comprehensive tutorials for the Tenstorrent software stack in Korean. Jupyter notebooks covering the full developer path from hardware setup to model inference.
  [📦 repo](https://github.com/changh95/tt-tutorial)

- **CS Fundamentals on Tenstorrent Hardware** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Seven-module computer science curriculum taught on real Tenstorrent hardware. Covers RISC-V architecture, memory hierarchy, parallel computing, networks and NoC, synchronization, abstraction layers, and computational complexity — all grounded in what is physically happening on the chip.
  [📖 Module 1: RISC-V & Computer Architecture](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-01-computer/) · [📖 Module 2: The Memory Hierarchy](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-02-memory/) · [📖 Module 3: Parallel Computing](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-03-parallelism/) · [📖 Module 4: Networks and Communication](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-04-networks/) · [📖 Module 5: Synchronization](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-05-synchronization/) · [📖 Module 6: Abstraction Layers](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-06-abstraction/) · [📖 Module 7: Computational Complexity in Practice](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/cs-fundamentals-07-complexity/)

- **[tt-sim Lab](https://github.com/prag79/tt-sim-lab)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by Pragnajit Datta Roy — A university teaching lab for TT-Metalium kernel programming on a virtual Tenstorrent chip — one-click GitHub Codespace, no silicon and nothing installed locally. The primary track (labs 00-06) points tt-metal straight at libttsim via TT_METAL_SIMULATOR and walks from elementwise add through NoC multicast to multi-core and multicast matmul, backed by a source-level matmul guide. An optional advanced track (labs 10-16) boots an Ubuntu guest under ttsim-qemu, loads tt-kmd, surfaces /dev/tenstorrent/0, and runs tt-metal through the full PCIe path.
  [📦 repo](https://github.com/prag79/tt-sim-lab) · [📖 Student handout](https://github.com/prag79/tt-sim-lab/blob/main/HANDOUT.md) · [📖 Matmul source walkthrough](https://github.com/prag79/tt-sim-lab/blob/main/labs/MATMUL_GUIDE.md)

- **Custom Model Training on Tenstorrent** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  by [@tsingletaryTT](https://github.com/tsingletaryTT) — Eight-lesson series covering the full custom training workflow on TT hardware: dataset fundamentals, configuration patterns, fine-tuning, multi-device distributed training, experiment tracking, model architecture basics, and training from scratch.
  [📖 Understanding Custom Training](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct1-understanding-training/) · [📖 Dataset Fundamentals](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct2-dataset-fundamentals/) · [📖 Configuration Patterns](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct3-configuration-patterns/) · [📖 Fine-tuning Basics](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct4-finetuning-basics/) · [📖 Multi-Device Training](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct5-multi-device-training/) · [📖 Experiment Tracking](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct6-experiment-tracking/) · [📖 Model Architecture Basics](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct7-architecture-basics/) · [📖 Training from Scratch](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons/ct8-training-from-scratch/)

- **[tt-low-level-documentation](https://github.com/tenstorrent/tt-low-level-documentation)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Documentation for the low-level layer of tt-metal: compute LLK APIs and data movement APIs. The data movement side covers the NOC and overlay on Wormhole and Blackhole; the compute side covers Tensix hardware and expected usage of the LLK APIs. Aimed at op and model writers who need to know what the APIs do and how the hardware behaves underneath them.
  [📦 repo](https://github.com/tenstorrent/tt-low-level-documentation)

- **[tt-vscode-toolkit](https://github.com/tenstorrent/tt-vscode-toolkit)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  48 interactive lessons covering the full Tenstorrent developer path — from hardware detection to custom training — with click-to-run commands and hardware auto-detection. Available in VSCode and code-server.
  [📦 repo](https://github.com/tenstorrent/tt-vscode-toolkit) · [📖 All 48 lessons](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons) · [📖 RISC-V Programming Guide](https://docs.tenstorrent.com/tt-vscode-toolkit/riscv-guide/)

## Feeds & Resources

Subscribe to tt-awesome activity via Atom or JSON Feed:

- **[New Entries (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/new-entries.xml)** — newly added projects and resources.
- **[Articles & Resources (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/articles.xml)** — articles, papers, lessons, talks, and demos.
- **[Recent Releases (Atom)](https://tenstorrent.github.io/tt-awesome/feeds/releases.xml)** — latest stable releases. Release items use LLM-generated summaries when available.
- **[JSON Feed](https://tenstorrent.github.io/tt-awesome/feeds/feed.json)** — combined releases, entries, and articles (JSON Feed 1.1).
- **[data.json](https://tenstorrent.github.io/tt-awesome/data.json)** — full machine-readable entry database.
- **[llms.txt](https://tenstorrent.github.io/tt-awesome/llms.txt)** — curated plain-text index for LLM context and AI tooling.

Each Atom and JSON Feed item carries both a short `<summary>` and a full rich `<content>` block containing the project description, all associated links, attribution, and tags — suitable for feed readers that render HTML content.

## Contributing

We welcome contributions from the community! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting entries, bug reports, and pull requests.

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

- **Code and Software**: Licensed under the [Apache License 2.0](LICENSE), except where specified. See [LICENSE_understanding.txt](LICENSE_understanding.txt) for clarifications on how this license applies.

- **Documentation and Images**: Licensed under [Creative Commons Attribution 4.0 International (CC-BY)](LICENSE-DOCS). This includes all content in the docs/ directory, README.md content, and generated website output.

---

*Generated by `scripts/generate_readme.py`.*
