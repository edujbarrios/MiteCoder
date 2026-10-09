# MiteCoder

[![CI](https://github.com/edujbarrios/MiteCoder/actions/workflows/ci.yml/badge.svg)](https://github.com/edujbarrios/MiteCoder/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-6f42c1.svg)](LICENSE)

**Keep coding with a local SLM and enhanced agentic capabilities while your main hardware is busy.**

MiteCoder is a CPU-first coding agent for moments when the GPU and most system resources are busy
with training or other AI workloads. It uses quantized SLMs, small contexts and limited RAM to
answer questions, inspect a folder, edit files and verify changes without sending the workspace to
a cloud service. The goal is useful local assistance—not reproducing a large cloud agent.

MiteCoder is in **early development**, but its CLI, local web interface, model download, GGUF
inference, constrained tools, verification loop, artifacts, and benchmark are functional.

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/edujbarrios/MiteCoder.git
cd MiteCoder
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX: source .venv/bin/activate
python -m pip install -e ".[llama]"
mitecoder download-model qwen2.5-coder-0.5b-q4
```

The model is downloaded from its official source, checked against the manifest SHA-256, and stored
under `models/`. Agent execution itself remains offline.

## Use the CLI

A workspace may be a Git repository or an ordinary folder. Ask a question or request a change:

```bash
mitecoder run --workspace ./examples/simple_bug \
  --task "Explain the failing test and fix it" \
  --config configs/ultra_low.yaml \
  --model-path models/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf
```

MiteCoder reads code, text, configuration, Markdown and notebook cells. Read-only questions do not
change files. Edits cannot be reported as verified unless every configured check passes.

## Use the local interface

```bash
mitecoder web --workspace ./examples/simple_bug \
  --config configs/ultra_low.yaml \
  --model-path models/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). The local workbench starts with an empty chat
and combines a folder picker, file explorer, editor and integrated terminal. You decide whether to
ask about the selected codebase, inspect a file or request a verified change. Follow-up messages
keep only a small amount of recent context.

The server binds only to localhost and loads no third-party assets. The terminal does not expose an
arbitrary shell: it runs only the commands listed under `testing.commands` in the selected config.

## Why it can work with a small model

MiteCoder treats local coding assistance as an **agentic Edge ML** systems problem. The SLM does
not work alone:

1. Context selection finds relevant workspace files and notebook cells.
2. The local quantized model proposes one structured action.
3. A strict registry limits which tools can run.
4. Paths remain inside the selected workspace.
5. Operator-configured checks verify every edit.
6. Tokens, timing, memory, actions, failures, checksums, and diffs are recorded.

The aim is useful verified behavior per unit of RAM, CPU time, context, and generated tokens—not
reproducing a large cloud agent on a smaller machine.

## Models and resource profiles

```bash
mitecoder models
mitecoder download-model qwen2.5-coder-0.5b-q4
mitecoder verify-model qwen2.5-coder-0.5b-q4
```

- `ultra_low`: smallest model and context budget.
- `balanced`: 1.5B Q4 model with more context.
- `quality`: less restrictive local experiments.

These are experiment profiles, not universal RAM guarantees. Actual use depends on the model,
quantization, context length, llama.cpp build, operating system, and hardware.

## Benchmark and development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check backend/src cli/src tests scripts
npm ci
npm run check
npm run build
mitecoder benchmark --suite microswe --config configs/ultra_low.yaml
```

The browser interface lives in `frontend/` and is authored in strictly typed TypeScript.
`npm run build` compiles and copies its generated runtime assets into the Python package.

### Repository layout

- `backend/` — agent loop, inference, retrieval, tools, configuration, metrics, and local web API.
- `cli/` — thin command-line adapter and console entry point.
- `frontend/` — TypeScript and browser asset sources.
- `tests/` — behavior, security, packaging, and architecture checks.
- `benchmarks/` — the offline MicroSWE evaluation suite.

Generated frontend assets are packaged under `backend/src/mitecoder/web/static/`. MicroSWE is a
small original offline benchmark, not SWE-bench.

## Limits

Small models can misunderstand tasks, select poor context, or produce incorrect edits. Passing
tests only proves compatibility with the configured checks. MiteCoder is not an operating-system
sandbox: project tests, native libraries, and dependencies run with the user's permissions.

Use a disposable branch or copy for edits, review every diff, and isolate untrusted dependencies.

## Project information

[Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

MiteCoder is licensed under [Apache License 2.0](LICENSE). Models and third-party dependencies keep
their upstream licenses. Citation metadata is available in [CITATION.cff](CITATION.cff).
