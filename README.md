# Frankenstein Laboratory

A reproducible laboratory for **running, benchmarking, dissecting, integrating, and learning from open-source text-to-speech systems** while progressively building an independent modular TTS platform.

This is not a "30 models behind one UI" project. The laboratory is expected to produce evidence and reusable technology: stable adapter contracts, provenance records, fair benchmarks, our own text/pronunciation/prosody infrastructure, and eventually original synthesis components and models.

## Current phase

The Core is bootstrapped and two external CPU backends have passed real-model smoke tests through isolated workers:

- **Kokoro** — lightweight 82M baseline
- **Pocket TTS 2.1.0** — streaming, voice-state capable CPU backend

The repository currently contains:

- a minimal dependency-free Core
- a machine-readable engine/provenance registry
- an environment doctor
- an isolated-worker boundary based on `uv` + subprocesses
- verified Kokoro and Pocket TTS workers using CPU-only PyTorch resolution
- structured real-model smoke evidence
- lightweight contract/registry/CLI tests
- lightweight CI
- the full project constitution in `PROJECT_INSTRUCTIONS.md`
- an initial source-backed TTS landscape note

## Quick start

```bash
python -m pip install -e ".[dev]"
python -m ttslab list
python -m ttslab doctor
pytest
```

Run verified backends:

```bash
python -m ttslab run kokoro --text "hello world" --output outputs/kokoro.wav
python -m ttslab run pocket_tts --text "hello world" --output outputs/pocket.wav
```

Each engine lives in its own `uv` project. CPU PyTorch is pinned on Linux/Windows so CPU installs do not drag in CUDA packages.

Experimental workers use the explicit smoke path until qualified:

```bash
python -m ttslab smoke <engine> --text "hello world"
```

## Next vertical slice

Chatterbox is next. Nano is especially interesting for CPU/on-device use, but its official cloning example requires a reference clip; the laboratory will use an explicitly licensed or synthetic reference rather than silently pulling a human voice sample. After the lightweight adapter boundary is proven, the laboratory expands toward Qwen3-TTS, CosyVoice, VoxCPM2, and research-only systems.

## Principles

- isolate external engines instead of forcing incompatible dependencies into one Python environment
- verify code, model-weight, dataset, and voice-asset licenses separately
- prefer measurements over architecture-by-opinion
- keep heavyweight model tests optional/manual
- never fabricate benchmark results
- preserve failed experiments and provenance
- gradually replace external components with our own implementations
