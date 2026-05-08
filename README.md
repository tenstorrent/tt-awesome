# ⚡ Awesome Tenstorrent

> A curated, community-first collection of awesome demos, tools, projects, and resources built by and for the Tenstorrent ecosystem.

> **This file is auto-generated from `entries/*.json`. Do not edit directly — see [CONTRIBUTING.md](CONTRIBUTING.md) to add an entry.**

## Contents

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

- **[tt-boltz](https://github.com/moritztng/tt-boltz)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Boltz-2 biomolecular model for drug discovery on Tenstorrent Blackhole. Supports single-card and multi-card configurations — QuietBox (4×) and Galaxy (32×). Approaches physics-based FEP accuracy at 1000× the speed.
  [📦 repo](https://github.com/moritztng/tt-boltz) · [🎤 FOSDEM 2026 — Drug Discovery on Tenstorrent Hardware](https://fosdem.org/2026/schedule/event/AJLNVH-tt-boltz/)

- **[gsplat_tt](https://github.com/Kovelja009/gsplat_tt)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Port of Gaussian Splatting (3D scene reconstruction from 2D images) to Tenstorrent hardware.
  [📦 repo](https://github.com/Kovelja009/gsplat_tt)

- **[koyeb/tenstorrent-examples](https://github.com/koyeb/tenstorrent-examples)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Example applications and deployment configurations for running AI workloads on Tenstorrent hardware via Koyeb's cloud platform.
  [📦 repo](https://github.com/koyeb/tenstorrent-examples) · [🌐 Koyeb blog post](https://www.koyeb.com/blog/tenstorrent-cloud-instances-unveiling-next-gen-ai-accelerators)

- **[grayskull-attention](https://github.com/moritztng/grayskull-attention)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  FlashAttention-style attention kernel implemented entirely in on-chip SRAM on the Tenstorrent Grayskull chip using TT-Metalium. Pioneering work in low-level attention on TT hardware.
  [📦 repo](https://github.com/moritztng/grayskull-attention)

- **[dflash](https://github.com/zoecarver/dflash)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  DFlash: Block Diffusion for Flash Speculative Decoding on Tenstorrent hardware using tt-lang. Combines block diffusion with speculative decoding for faster inference.
  [📦 repo](https://github.com/zoecarver/dflash)

- **[diamond](https://github.com/zoecarver/diamond)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  DIAMOND: Atari game-playing agent implemented on Tenstorrent hardware via tt-lang. Diffusion-based world model for reinforcement learning.
  [📦 repo](https://github.com/zoecarver/diamond)

- **[Engram](https://github.com/zoecarver/Engram)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  A Tenstorrent port of the DeepSeek Engram model using tt-lang. Brings DeepSeek's memory-efficient architecture to TT hardware.
  [📦 repo](https://github.com/zoecarver/Engram)

- **[gemma4](https://github.com/zoecarver/gemma4)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Gemma 4 language model implemented in tt-lang (e4b variant) for direct execution on Tenstorrent hardware.
  [📦 repo](https://github.com/zoecarver/gemma4)

- **[open-oasis](https://github.com/zoecarver/open-oasis)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  tt-lang inference script for Oasis 500M — an interactive video world model running on Tenstorrent hardware via the tt-lang DSL.
  [📦 repo](https://github.com/zoecarver/open-oasis)

- **[tt-lang-models](https://github.com/zoecarver/tt-lang-models)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  A growing collection of models that use tt-lang for some or all of their implementation. Reference implementations for bringing modern models to the tt-lang DSL.
  [📦 repo](https://github.com/zoecarver/tt-lang-models)

- **[tt-model-runner](https://github.com/tsingletaryTT/tt-model-runner)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Discover, load, and benchmark models with a GUI and TUI for tt-inference-server. Makes exploring available models on Tenstorrent hardware as easy as browsing a catalog.
  [📦 repo](https://github.com/tsingletaryTT/tt-model-runner)

- **[tt-blacksmith](https://github.com/tenstorrent/tt-blacksmith)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Optimized training recipes for a variety of ML models on Tenstorrent hardware, powered by the TT-Forge compiler stack. Reference implementations for fine-tuning and training from scratch.
  [📦 repo](https://github.com/tenstorrent/tt-blacksmith) · [📖 Custom Training lessons (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-buda-demos](https://github.com/tenstorrent/tt-buda-demos)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Repository of model demos using TT-Buda. The largest collection of pre-compiled model examples for Tenstorrent hardware — BERT, ResNet, YOLO, GPT-2, Whisper, and many more.
  [📦 repo](https://github.com/tenstorrent/tt-buda-demos)

- **[tt-example-apps](https://github.com/tenstorrent/tt-example-apps)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  End-to-end AI applications running on Tenstorrent AI accelerators. Complete application examples from retrieval-augmented generation to image generation pipelines.
  [📦 repo](https://github.com/tenstorrent/tt-example-apps)

- **[tt-inference-server](https://github.com/tenstorrent/tt-inference-server)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Production-ready model serving for Tenstorrent hardware with OpenAI-compatible REST API. Supports continuous batching, multiple models, and all TT hardware configurations.
  [📦 repo](https://github.com/tenstorrent/tt-inference-server) · [📖 Production Inference lesson (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-local-generator](https://github.com/tenstorrent/tt-local-generator)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Generate infinite videos and images (and imaginative prompts to inspire them) on Tenstorrent's Quietbox 2. Fully local generative media pipeline.
  [📦 repo](https://github.com/tenstorrent/tt-local-generator)

- **[TT-Studio](https://github.com/tenstorrent/tt-studio)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Web-based GUI for deploying and chatting with AI models on Tenstorrent hardware. Handles all technical setup automatically — deploy models, run inference, and explore capabilities through a simple browser interface.
  [📦 repo](https://github.com/tenstorrent/tt-studio)

## 🕵️ AI Agents

- **[dstack](https://github.com/dstackai/dstack)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Vendor-agnostic orchestration for training, inference, and agentic workloads across NVIDIA, AMD, TPU, and Tenstorrent on clouds, Kubernetes, and bare metal.
  [📦 repo](https://github.com/dstackai/dstack) · [🌐 website](https://dstack.ai)

- **[tt-example-apps](https://github.com/tenstorrent/tt-example-apps)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  End-to-end AI applications running on Tenstorrent AI accelerators. Complete application examples from retrieval-augmented generation to image generation pipelines.
  [📦 repo](https://github.com/tenstorrent/tt-example-apps)

## ⚙️ Custom Kernels & Low-Level

- **[triton-tenstorrent](https://github.com/kernelize-ai/triton-tenstorrent)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  OpenAI Triton compiler plugin for Tenstorrent hardware. Write Triton kernels and target Tensix cores — brings the Triton ML kernel ecosystem to TT devices.
  [📦 repo](https://github.com/kernelize-ai/triton-tenstorrent)

- **Programming Tenstorrent Processors** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Deep-dive into the Tenstorrent architecture and Metalium programming model — circular buffers, kernel synchronization, NoC routing, and where the footguns are. The honest guide to thinking in Tensix.
  [📝 clehaxze.tw — April 2025](https://clehaxze.tw/gemlog/2025/04-21-programming-tensotrrent-processors.gmi)

- **[tt-tiny](https://github.com/geohot/tt-tiny)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal Python code to access and program the Tenstorrent Blackhole chip directly — George Hotz's exploration of TT hardware programmability with pointed commentary on the architecture.
  [📦 repo](https://github.com/geohot/tt-tiny)

- **[ttMandelbrot](https://github.com/marty1885/ttMandelbrot)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Mandelbrot Set fractal renderer running on Tenstorrent hardware. A classic demo showcasing parallel compute on Tensix cores.
  [📦 repo](https://github.com/marty1885/ttMandelbrot)

- **[TT-Metal Mini Template](https://github.com/JushBJJ/TT-Metal-Mini-Template)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal working CMake project template for starting a new TT-Metal project from scratch. Good starting point for community kernel development.
  [📦 repo](https://github.com/JushBJJ/TT-Metal-Mini-Template)

- **Optimal "where" on Tenstorrent** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Deep-dive into implementing the where(condition, t, f, out) kernel on the Tenstorrent Wormhole vector unit. Achieves optimal throughput of 3 cycles/row (in-place) and 4 cycles/row (out-of-place) by cycle-counting assembly on the 32-lane SFPU.
  [📝 article](https://www.jasondavies.com/2025/tenstorrent-where/)

- **[current](https://github.com/seansiddens/current)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  High-level parallel programming framework for Tenstorrent accelerators, abstracting TT-Metal into a research-oriented programming model for parallel computation.
  [📦 repo](https://github.com/seansiddens/current)

- **[grayskull-attention](https://github.com/moritztng/grayskull-attention)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  FlashAttention-style attention kernel implemented entirely in on-chip SRAM on the Tenstorrent Grayskull chip using TT-Metalium. Pioneering work in low-level attention on TT hardware.
  [📦 repo](https://github.com/moritztng/grayskull-attention)

- **[tenstorrent-tiny-examples](https://github.com/jaebaek/tenstorrent-tiny-examples)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Simple C++ kernel experiments on a GraySkull e75 chip. Hands-on examples for learning the TT-Metal programming model at the metal level.
  [📦 repo](https://github.com/jaebaek/tenstorrent-tiny-examples)

- **[tt-twitch](https://github.com/geohot/tt-twitch)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  A Tenstorrent Grayskull kernel written live on Twitch by George Hotz. 120-core grid demonstration of live kernel programming.
  [📦 repo](https://github.com/geohot/tt-twitch)

- **[ttnn-helloworld-cpp](https://github.com/marty1885/ttnn-helloworld-cpp)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal working example of using Tenstorrent TTNN in C++. The simplest possible starting point for C++ developers targeting TT hardware with TTNN.
  [📦 repo](https://github.com/marty1885/ttnn-helloworld-cpp)

- **[ttVecAdd](https://github.com/marty1885/ttVecAdd)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal vector-addition example on Tenstorrent devices using TT-Metalium. A clean hello-world for the TT-Metal kernel programming model in C++.
  [📦 repo](https://github.com/marty1885/ttVecAdd)

- **Exploring Fast Fourier Transforms on the Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Ports the Cooley-Tukey FFT algorithm to the Wormhole n300 RISC-V accelerator. The Wormhole draws 8× less power and consumes 2.8× less energy than a 24-core Xeon Platinum for a 2D FFT. ISC 2025.
  [📄 arXiv:2506.15437](https://arxiv.org/abs/2506.15437) · [📝 University of Edinburgh](https://www.research.ed.ac.uk/en/publications/exploring-fast-fourier-transforms-on-the-tenstorrent-wormhole/)

- **[dflash](https://github.com/zoecarver/dflash)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  DFlash: Block Diffusion for Flash Speculative Decoding on Tenstorrent hardware using tt-lang. Combines block diffusion with speculative decoding for faster inference.
  [📦 repo](https://github.com/zoecarver/dflash)

- **[tt-lang-models](https://github.com/zoecarver/tt-lang-models)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  A growing collection of models that use tt-lang for some or all of their implementation. Reference implementations for bringing modern models to the tt-lang DSL.
  [📦 repo](https://github.com/zoecarver/tt-lang-models)

- **[tt-lang](https://github.com/tenstorrent/tt-lang)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Python-based domain-specific language for authoring custom operations on Tenstorrent hardware. Expresses concurrent compute and data-movement programs that compile directly to Tensix kernels.
  [📦 repo](https://github.com/tenstorrent/tt-lang) · [📖 Introduction to tt-lang (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-metal](https://github.com/tenstorrent/tt-metal)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TT-NN operator library and TT-Metalium low-level kernel programming model. The primary SDK for developing on Tenstorrent hardware — from high-level tensor ops to bare-metal RISC-V kernels.
  [📦 repo](https://github.com/tenstorrent/tt-metal)

## 🔨 Compilers & Frontends

- **[BarraCUDA](https://github.com/Zaneham/BarraCUDA)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Open-source CUDA compiler targeting multiple GPU architectures including Tenstorrent. Compiles .cu files to run on AMD and Tenstorrent hardware without modification.
  [📦 repo](https://github.com/Zaneham/BarraCUDA)

- **[triton-tenstorrent](https://github.com/kernelize-ai/triton-tenstorrent)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  OpenAI Triton compiler plugin for Tenstorrent hardware. Write Triton kernels and target Tensix cores — brings the Triton ML kernel ecosystem to TT devices.
  [📦 repo](https://github.com/kernelize-ai/triton-tenstorrent)

- **[tt-iree](https://github.com/swote-git/tt-iree)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  IREE (Intermediate Representation Execution Environment) ML compiler ported to Tenstorrent AI accelerators. Brings the IREE compiler ecosystem to TT hardware.
  [📦 repo](https://github.com/swote-git/tt-iree)

- **[tt-forge-compiletron](https://github.com/tsingletaryTT/tt-forge-compiletron)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Compile more than 100 models on tt-forge in a display format suitable for demos. Comprehensive showcase of tt-forge model compatibility.
  [📦 repo](https://github.com/tsingletaryTT/tt-forge-compiletron)

- **[tt-buda](https://github.com/tenstorrent/tt-buda)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TT-BUDA: Tenstorrent's original Python compiler and runtime for AI workloads. Legacy stack — tt-forge is the recommended successor, but tt-buda has the largest model demo library.
  [📦 repo](https://github.com/tenstorrent/tt-buda)

- **[tt-forge](https://github.com/tenstorrent/tt-forge)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent's MLIR-based compiler frontend. Enables running AI workloads from PyTorch, ONNX, and other frameworks on all Tenstorrent hardware configurations through an open-source, general, and performant compiler.
  [📦 repo](https://github.com/tenstorrent/tt-forge) · [🌐 website](https://tenstorrent.com)

- **[tt-mlir](https://github.com/tenstorrent/tt-mlir)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent MLIR compiler — the core compiler infrastructure shared by tt-forge and other frontends. Handles graph optimization, lowering, and code generation for Tensix hardware.
  [📦 repo](https://github.com/tenstorrent/tt-mlir)

- **[tt-torch](https://github.com/tenstorrent/tt-torch)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Frontend integration for PyTorch with tt-mlir. Compile PyTorch models directly to Tenstorrent hardware via torch.compile integration.
  [📦 repo](https://github.com/tenstorrent/tt-torch)

- **[tt-tvm](https://github.com/tenstorrent/tt-tvm)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TVM for Tenstorrent ASICs. Brings the Apache TVM compiler stack to Tenstorrent hardware, enabling model compilation from TensorFlow, PyTorch, ONNX, and more.
  [📦 repo](https://github.com/tenstorrent/tt-tvm)

- **[tt-xla](https://github.com/tenstorrent/tt-xla)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  PJRT device plugin for Tenstorrent hardware. Enables JAX, PyTorch/XLA, and other XLA-based frameworks to target TT accelerators.
  [📦 repo](https://github.com/tenstorrent/tt-xla)

- **[tt-metal](https://github.com/tenstorrent/tt-metal)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  TT-NN operator library and TT-Metalium low-level kernel programming model. The primary SDK for developing on Tenstorrent hardware — from high-level tensor ops to bare-metal RISC-V kernels.
  [📦 repo](https://github.com/tenstorrent/tt-metal)

## 🛠 Dev Tools & Debugging

- **[nvtop](https://github.com/Syllo/nvtop)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  htop-style process monitor for GPUs and AI accelerators. Supports AMD, Apple, Huawei, Intel, NVIDIA, Qualcomm — and Tenstorrent. Real-time utilization, memory, and process info in a terminal UI.
  [📦 repo](https://github.com/Syllo/nvtop)

- **[tt-sim](https://github.com/mesham/tt-sim)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Community-built Tenstorrent architecture simulator written in Python. Runs without hardware — useful for researchers and developers exploring the Tensix architecture offline.
  [📦 repo](https://github.com/mesham/tt-sim)

- **[ttPEAK](https://github.com/TT-Bounty-Hunters/ttPEAK)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  clpeak-style peak-performance benchmark for Tenstorrent devices using TT-Metalium. Measures theoretical peak throughput across operations — useful for hardware characterization.
  [📦 repo](https://github.com/TT-Bounty-Hunters/ttPEAK)

- **[tensix-viz](https://github.com/tsingletaryTT/tensix-viz)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Hardware topology visualizer for Tenstorrent chips — from individual chip to full cluster. Interactive JavaScript visualization of Tensix core layout and NoC connections.
  [📦 repo](https://github.com/tsingletaryTT/tensix-viz)

- **[tt-model-runner](https://github.com/tsingletaryTT/tt-model-runner)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Discover, load, and benchmark models with a GUI and TUI for tt-inference-server. Makes exploring available models on Tenstorrent hardware as easy as browsing a catalog.
  [📦 repo](https://github.com/tsingletaryTT/tt-model-runner)

- **[tt-warp](https://github.com/tsingletaryTT/tt-warp)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Warp terminal plugin for Tenstorrent — integrates hardware status, model management, and developer workflows directly into the Warp terminal.
  [📦 repo](https://github.com/tsingletaryTT/tt-warp)

- **[TT-Studio](https://github.com/tenstorrent/tt-studio)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Web-based GUI for deploying and chatting with AI models on Tenstorrent hardware. Handles all technical setup automatically — deploy models, run inference, and explore capabilities through a simple browser interface.
  [📦 repo](https://github.com/tenstorrent/tt-studio)

- **[tt-exalens](https://github.com/tenstorrent/tt-exalens)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Low-level hardware debugger for Tenstorrent devices. Inspect register state, memory contents, and kernel execution at the hardware level.
  [📦 repo](https://github.com/tenstorrent/tt-exalens)

- **[tt-npe](https://github.com/tenstorrent/tt-npe)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Network-on-chip Performance Estimator for Tenstorrent Tensix-based devices. Model and estimate NoC utilization before running kernels on hardware.
  [📦 repo](https://github.com/tenstorrent/tt-npe)

- **[ttnn-visualizer](https://github.com/tenstorrent/ttnn-visualizer)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Comprehensive tool for visualizing and analyzing model execution on Tenstorrent hardware. Interactive graphs, memory plots, tensor details, buffer overviews, operation flow graphs, and multi-instance support.
  [📦 repo](https://github.com/tenstorrent/ttnn-visualizer)

- **[tt-vscode-toolkit](https://github.com/tenstorrent/tt-vscode-toolkit)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  48 interactive lessons covering the full Tenstorrent developer path — from hardware detection to custom training — with click-to-run commands and hardware auto-detection. Available in VSCode and code-server.
  [📦 repo](https://github.com/tenstorrent/tt-vscode-toolkit) · [📖 All 48 lessons](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-smi](https://github.com/tenstorrent/tt-smi)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent System Management Interface — monitor device telemetry, issue board-level resets, and inspect hardware health. The nvidia-smi equivalent for Tenstorrent hardware.
  [📦 repo](https://github.com/tenstorrent/tt-smi)

- **[tt-toplike](https://github.com/tenstorrent/tt-toplike)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  A vibrant htop-style visualizer for Tenstorrent hardware written in Rust. Real-time process and utilization view for TT accelerators.
  [📦 repo](https://github.com/tenstorrent/tt-toplike)

- **[tensix-isa-simulator](https://github.com/tenstorrent/tensix-isa-simulator)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  ISA-level simulator for the Tensix compute engine. Simulates the matrix, vector, and scalar units inside each Tensix core.
  [📦 repo](https://github.com/tenstorrent/tensix-isa-simulator)

- **[ttsim](https://github.com/tenstorrent/ttsim)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Fast full-system simulator of Tenstorrent Wormhole and Blackhole hardware. Runs TT-Metalium workloads on any Linux/x86_64 system without physical silicon. Bit-exact results relative to hardware.
  [📦 repo](https://github.com/tenstorrent/ttsim)

## 🖥 Hardware & System

- **[nvtop](https://github.com/Syllo/nvtop)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  htop-style process monitor for GPUs and AI accelerators. Supports AMD, Apple, Huawei, Intel, NVIDIA, Qualcomm — and Tenstorrent. Real-time utilization, memory, and process info in a terminal UI.
  [📦 repo](https://github.com/Syllo/nvtop)

- **[blackhole-py](https://github.com/boopdotpng/blackhole-py)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Pure Python driver for Tenstorrent Blackhole cards providing direct low-level hardware access without going through the full TT-Metal stack.
  [📦 repo](https://github.com/boopdotpng/blackhole-py)

- **[tenstorrent.nix](https://github.com/RossComputerGuy/tenstorrent.nix)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Nix flake packaging the Tenstorrent software stack for NixOS and Nix users. Reproducible, declarative installation of TT drivers and tools.
  [📦 repo](https://github.com/RossComputerGuy/tenstorrent.nix)

- **SwiftNPU: Scalable Shape-Flexible Allocation for Inter-Core Connected NPUs** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Makes multi-tenant NPU sharing practical for Blackhole-class hardware using polynomial-time allocation algorithms. Delivers up to 1.37× higher utilization and 1.14× faster workload completion. Up to 890,000× faster than NP-hard baselines.
  [📄 ACM DL](https://dl.acm.org/doi/10.1145/3805621.3807614)

- **[tt-qb-lights](https://github.com/tsingletaryTT/tt-qb-lights)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Sync your Tenstorrent Quietbox's RGB lighting to accelerator utilization status. Visual feedback for hardware activity in real time.
  [📦 repo](https://github.com/tsingletaryTT/tt-qb-lights)

- **[luwen](https://github.com/tenstorrent/luwen)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent system interface library written in Rust. Low-level Rust bindings for communicating with and managing TT hardware.
  [📦 repo](https://github.com/tenstorrent/luwen)

- **[tt-firmware](https://github.com/tenstorrent/tt-firmware)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent firmware repository. Board management and control firmware for Tenstorrent accelerator cards.
  [📦 repo](https://github.com/tenstorrent/tt-firmware)

- **[tt-flash](https://github.com/tenstorrent/tt-flash)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent firmware update utility. Flash new firmware onto Tenstorrent accelerator cards from the command line.
  [📦 repo](https://github.com/tenstorrent/tt-flash)

- **[tt-installer](https://github.com/tenstorrent/tt-installer)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Install the complete Tenstorrent software stack with one command. Handles drivers, firmware, Python environment, and SDK setup automatically.
  [📦 repo](https://github.com/tenstorrent/tt-installer) · [📖 Modern Setup lesson (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-kmd](https://github.com/tenstorrent/tt-kmd)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent kernel module driver. The Linux kernel module required to interface with Tenstorrent PCIe accelerator cards.
  [📦 repo](https://github.com/tenstorrent/tt-kmd)

- **[tt-smi](https://github.com/tenstorrent/tt-smi)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Tenstorrent System Management Interface — monitor device telemetry, issue board-level resets, and inspect hardware health. The nvidia-smi equivalent for Tenstorrent hardware.
  [📦 repo](https://github.com/tenstorrent/tt-smi)

- **[tt-system-firmware](https://github.com/tenstorrent/tt-system-firmware)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  System firmware for Tenstorrent hardware. Low-level system initialization and control firmware that runs on-device.
  [📦 repo](https://github.com/tenstorrent/tt-system-firmware)

- **[tt-toplike](https://github.com/tenstorrent/tt-toplike)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  A vibrant htop-style visualizer for Tenstorrent hardware written in Rust. Real-time process and utilization view for TT accelerators.
  [📦 repo](https://github.com/tenstorrent/tt-toplike)

- **[tt-topology](https://github.com/tenstorrent/tt-topology)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Configure Ethernet routing on multi-card Tenstorrent systems. Flash NB cards to use specific ETH routing configurations for scale-out deployments.
  [📦 repo](https://github.com/tenstorrent/tt-topology)

- **[tt-umd](https://github.com/tenstorrent/tt-umd)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  User-mode driver for Tenstorrent hardware. The userspace layer that sits between the kernel module and higher-level SDKs.
  [📦 repo](https://github.com/tenstorrent/tt-umd)

- **[WallaBMC](https://github.com/tenstorrent/wallabmc)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Lightweight BMC (Baseboard Management Controller) for STM32 and similar MCUs, with Web UI, Redfish API, and HTTPS support. Built on Zephyr RTOS. Used in Tenstorrent systems.
  [📦 repo](https://github.com/tenstorrent/wallabmc)

## ☁️ Cloud & Orchestration

- **[dstack](https://github.com/dstackai/dstack)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Vendor-agnostic orchestration for training, inference, and agentic workloads across NVIDIA, AMD, TPU, and Tenstorrent on clouds, Kubernetes, and bare metal.
  [📦 repo](https://github.com/dstackai/dstack) · [🌐 website](https://dstack.ai)

- **[koyeb/tenstorrent-examples](https://github.com/koyeb/tenstorrent-examples)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Example applications and deployment configurations for running AI workloads on Tenstorrent hardware via Koyeb's cloud platform.
  [📦 repo](https://github.com/koyeb/tenstorrent-examples) · [🌐 Koyeb blog post](https://www.koyeb.com/blog/tenstorrent-cloud-instances-unveiling-next-gen-ai-accelerators)

- **[tt-inference-server](https://github.com/tenstorrent/tt-inference-server)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Production-ready model serving for Tenstorrent hardware with OpenAI-compatible REST API. Supports continuous batching, multiple models, and all TT hardware configurations.
  [📦 repo](https://github.com/tenstorrent/tt-inference-server) · [📖 Production Inference lesson (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-topology](https://github.com/tenstorrent/tt-topology)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Configure Ethernet routing on multi-card Tenstorrent systems. Flash NB cards to use specific ETH routing configurations for scale-out deployments.
  [📦 repo](https://github.com/tenstorrent/tt-topology)

## 🔩 RISC-V & Architecture

- **[bhx](https://github.com/olofj/bhx)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Boot stock Linux cloud images on the SiFive X280 RISC-V cores inside Tenstorrent Blackhole AI accelerators. Per-card Rust daemon with virtio-mmio block/net/console and U-Boot/EFI support.
  [📦 repo](https://github.com/olofj/bhx)

- **[tt-sim](https://github.com/mesham/tt-sim)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Community-built Tenstorrent architecture simulator written in Python. Runs without hardware — useful for researchers and developers exploring the Tensix architecture offline.
  [📦 repo](https://github.com/mesham/tt-sim)

- **[tt-bh-linux](https://github.com/tenstorrent/tt-bh-linux)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Linux demo for the Tenstorrent Blackhole P100/P150 card RISC-V cores. Boot a real Linux kernel on the 16 high-performance RISC-V cores built into the Blackhole chip.
  [📦 repo](https://github.com/tenstorrent/tt-bh-linux)

- **[RiESCUE](https://github.com/tenstorrent/riescue)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  RISC-V Directed Test Framework and Compliance Suite. Comprehensive test infrastructure for verifying RISC-V processor implementations against the specification.
  [📦 repo](https://github.com/tenstorrent/riescue)

- **[riscv-ocelot](https://github.com/tenstorrent/riscv-ocelot)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  The Berkeley Out-of-Order Machine with V-EXT (RISC-V Vector Extension) support. Tenstorrent's research-grade out-of-order RISC-V core with vector extension.
  [📦 repo](https://github.com/tenstorrent/riscv-ocelot)

- **[tensix-isa-simulator](https://github.com/tenstorrent/tensix-isa-simulator)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  ISA-level simulator for the Tensix compute engine. Simulates the matrix, vector, and scalar units inside each Tensix core.
  [📦 repo](https://github.com/tenstorrent/tensix-isa-simulator)

- **[ttsim](https://github.com/tenstorrent/ttsim)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Fast full-system simulator of Tenstorrent Wormhole and Blackhole hardware. Runs TT-Metalium workloads on any Linux/x86_64 system without physical silicon. Bit-exact results relative to hardware.
  [📦 repo](https://github.com/tenstorrent/ttsim)

- **[whisper](https://github.com/tenstorrent/whisper)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  RISC-V Instruction Set Simulator (ISS) used by Tenstorrent for processor verification. Powers the co-simulation architecture checker.
  [📦 repo](https://github.com/tenstorrent/whisper)

## 🔬 Research & Papers

- **[tt-boltz](https://github.com/moritztng/tt-boltz)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Boltz-2 biomolecular model for drug discovery on Tenstorrent Blackhole. Supports single-card and multi-card configurations — QuietBox (4×) and Galaxy (32×). Approaches physics-based FEP accuracy at 1000× the speed.
  [📦 repo](https://github.com/moritztng/tt-boltz) · [🎤 FOSDEM 2026 — Drug Discovery on Tenstorrent Hardware](https://fosdem.org/2026/schedule/event/AJLNVH-tt-boltz/)

- **[tt-tutorial (HPC)](https://github.com/RISCVtestbed/tt-tutorial)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Tutorial on Tenstorrent hardware for HPC researchers from the RISC-V Testbed project at Edinburgh/EPCC. Covers Wormhole from an HPC parallel-computing perspective.
  [📦 repo](https://github.com/RISCVtestbed/tt-tutorial)

- **Exploring Fast Fourier Transforms on the Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Ports the Cooley-Tukey FFT algorithm to the Wormhole n300 RISC-V accelerator. The Wormhole draws 8× less power and consumes 2.8× less energy than a 24-core Xeon Platinum for a 2D FFT. ISC 2025.
  [📄 arXiv:2506.15437](https://arxiv.org/abs/2506.15437) · [📝 University of Edinburgh](https://www.research.ed.ac.uk/en/publications/exploring-fast-fourier-transforms-on-the-tenstorrent-wormhole/)

- **Accelerating Gravitational N-Body Simulations on Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Accelerates an astrophysical N-body simulation on the Wormhole n300. Achieves 2× speedup and 2× energy savings over a highly optimized CPU implementation. SC '25 Workshop.
  [📄 arXiv:2509.19294](https://arxiv.org/abs/2509.19294) · [📝 ACM SC '25](https://dl.acm.org/doi/10.1145/3731599.3767528)

- **Numerical Kernels on a Spatial Accelerator: Tenstorrent Wormhole** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Implements three numerical kernels and composes them into a conjugate gradient solver on Wormhole. Demonstrates AI accelerators merit consideration for HPC workloads traditionally dominated by CPUs and GPUs. 2026.
  [📄 arXiv:2603.23343](https://arxiv.org/abs/2603.23343)

- **[Collective Operations on Wormhole n150 (Sapienza University of Rome)](https://github.com/EngineerCharlie/TenstorrentAllreduce)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Master's thesis implementing and benchmarking five allreduce algorithms (Swing, Recursive Doubling, Bandwidth Optimal, Latency Optimal, Shared Memory) on the Wormhole n150. Bandwidth Optimal achieved best performance, approaching within 2× of theoretical optimal.
  [📦 repo](https://github.com/EngineerCharlie/TenstorrentAllreduce)

- **Accelerating Stencils on the Tenstorrent Grayskull RISC-V Accelerator** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Explores stencil computation on the Grayskull PCIe RISC-V accelerator. Early academic work examining TT hardware for HPC stencil workloads. 2024.
  [📄 arXiv:2409.18835](https://arxiv.org/abs/2409.18835)

- **SwiftNPU: Scalable Shape-Flexible Allocation for Inter-Core Connected NPUs** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Makes multi-tenant NPU sharing practical for Blackhole-class hardware using polynomial-time allocation algorithms. Delivers up to 1.37× higher utilization and 1.14× faster workload completion. Up to 890,000× faster than NP-hard baselines.
  [📄 ACM DL](https://dl.acm.org/doi/10.1145/3805621.3807614)

## 🎮 Games & Demos

- **[TT-GoL](https://github.com/JushBJJ/TT-GoL)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Conway's Game of Life implemented on Tenstorrent hardware using TT-Metal kernels.
  [📦 repo](https://github.com/JushBJJ/TT-GoL)

- **[ttMandelbrot](https://github.com/marty1885/ttMandelbrot)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Mandelbrot Set fractal renderer running on Tenstorrent hardware. A classic demo showcasing parallel compute on Tensix cores.
  [📦 repo](https://github.com/marty1885/ttMandelbrot)

- **[tt-twitch](https://github.com/geohot/tt-twitch)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  A Tenstorrent Grayskull kernel written live on Twitch by George Hotz. 120-core grid demonstration of live kernel programming.
  [📦 repo](https://github.com/geohot/tt-twitch)

- **[tt-zork-and-more](https://github.com/tsingletaryTT/tt-zork-and-more)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  A Tenstorrent fork of Infocom's Zork I (and more!), running a Z-machine interpreter at least four different ways on TT hardware. The most fun you can have with an AI accelerator.
  [📦 repo](https://github.com/tsingletaryTT/tt-zork-and-more)

- **[diamond](https://github.com/zoecarver/diamond)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  DIAMOND: Atari game-playing agent implemented on Tenstorrent hardware via tt-lang. Diffusion-based world model for reinforcement learning.
  [📦 repo](https://github.com/zoecarver/diamond)

- **[tt-forge-compiletron](https://github.com/tsingletaryTT/tt-forge-compiletron)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Compile more than 100 models on tt-forge in a display format suitable for demos. Comprehensive showcase of tt-forge model compatibility.
  [📦 repo](https://github.com/tsingletaryTT/tt-forge-compiletron)

- **[tt-qb-lights](https://github.com/tsingletaryTT/tt-qb-lights)** ![affiliated](https://img.shields.io/badge/affiliated-EC96B8?style=flat-square)
  Sync your Tenstorrent Quietbox's RGB lighting to accelerator utilization status. Visual feedback for hardware activity in real time.
  [📦 repo](https://github.com/tsingletaryTT/tt-qb-lights)

## 📚 Guides, Tutorials & Education

- **Programming Tenstorrent Processors** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Deep-dive into the Tenstorrent architecture and Metalium programming model — circular buffers, kernel synchronization, NoC routing, and where the footguns are. The honest guide to thinking in Tensix.
  [📝 clehaxze.tw — April 2025](https://clehaxze.tw/gemlog/2025/04-21-programming-tensotrrent-processors.gmi)

- **A Gentle Guide: Tenstorrent Card on Arch Linux with Metalium** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Step-by-step guide to getting a Tenstorrent card running on Arch Linux with the full Metalium stack. Practical troubleshooting from someone who did it the hard way first.
  [📝 clehaxze.tw — July 2024](https://clehaxze.tw/gemlog/2024/07-07-a-gentle-guide-on-getting-your-tenstorrent-card-running-on-arch-linux-with-the-metalium-stack.gmi)

- **Thoughts and Logs After Messing with Tenstorrent Grayskull** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Honest field notes from getting a Grayskull card running and writing first Metalium kernels. Covers setup pitfalls, processor hangs, memory protection quirks, and what makes Metalium compelling despite early rough edges.
  [📝 clehaxze.tw — June 2024](https://clehaxze.tw/gemlog/2024/06-02-thoughts-and-logs-after-messing-with-tenstorrent-grayskull.gmi)

- **[TT-Metal Mini Template](https://github.com/JushBJJ/TT-Metal-Mini-Template)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal working CMake project template for starting a new TT-Metal project from scratch. Good starting point for community kernel development.
  [📦 repo](https://github.com/JushBJJ/TT-Metal-Mini-Template)

- **[tt-tutorial (HPC)](https://github.com/RISCVtestbed/tt-tutorial)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Tutorial on Tenstorrent hardware for HPC researchers from the RISC-V Testbed project at Edinburgh/EPCC. Covers Wormhole from an HPC parallel-computing perspective.
  [📦 repo](https://github.com/RISCVtestbed/tt-tutorial)

- **[tt-tutorial (Korean)](https://github.com/changh95/tt-tutorial)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Comprehensive tutorials for the Tenstorrent software stack in Korean. Jupyter notebooks covering the full developer path from hardware setup to model inference.
  [📦 repo](https://github.com/changh95/tt-tutorial)

- **[tenstorrent-tiny-examples](https://github.com/jaebaek/tenstorrent-tiny-examples)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Simple C++ kernel experiments on a GraySkull e75 chip. Hands-on examples for learning the TT-Metal programming model at the metal level.
  [📦 repo](https://github.com/jaebaek/tenstorrent-tiny-examples)

- **[ttnn-helloworld-cpp](https://github.com/marty1885/ttnn-helloworld-cpp)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal working example of using Tenstorrent TTNN in C++. The simplest possible starting point for C++ developers targeting TT hardware with TTNN.
  [📦 repo](https://github.com/marty1885/ttnn-helloworld-cpp)

- **[ttVecAdd](https://github.com/marty1885/ttVecAdd)** ![community](https://img.shields.io/badge/community-27AE60?style=flat-square)
  Minimal vector-addition example on Tenstorrent devices using TT-Metalium. A clean hello-world for the TT-Metal kernel programming model in C++.
  [📦 repo](https://github.com/marty1885/ttVecAdd)

- **[tt-vscode-toolkit](https://github.com/tenstorrent/tt-vscode-toolkit)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  48 interactive lessons covering the full Tenstorrent developer path — from hardware detection to custom training — with click-to-run commands and hardware auto-detection. Available in VSCode and code-server.
  [📦 repo](https://github.com/tenstorrent/tt-vscode-toolkit) · [📖 All 48 lessons](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

- **[tt-installer](https://github.com/tenstorrent/tt-installer)** ![official](https://img.shields.io/badge/official-607D8B?style=flat-square)
  Install the complete Tenstorrent software stack with one command. Handles drivers, firmware, Python environment, and SDK setup automatically.
  [📦 repo](https://github.com/tenstorrent/tt-installer) · [📖 Modern Setup lesson (VSCode Toolkit)](https://docs.tenstorrent.com/tt-vscode-toolkit/lessons)

---

*Generated by `scripts/generate_readme.py`.*
