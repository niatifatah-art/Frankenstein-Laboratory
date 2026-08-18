# Frankenstein Laboratory

A reproducible laboratory for **running, benchmarking, dissecting, integrating, and learning from open-source text-to-speech systems** while progressively building an independent modular TTS platform.

This is not a "30 models behind one UI" project. The laboratory is expected to produce evidence and reusable technology: stable adapter contracts, provenance records, fair benchmarks, our own text/pronunciation/prosody infrastructure, and eventually original synthesis components and models.

## Current phase

Bootstrap. The repository currently contains:

- a minimal dependency-free Core
- a machine-readable engine/provenance registry
- an environment doctor
- a CLI that refuses fake integrations
- lightweight contract/registry tests
- lightweight CI
- the full project constitution in `PROJECT_INSTRUCTIONS.md`
- an initial source-backed TTS landscape note

No external engine is marked `ready` yet.

## Quick start

```bash
python -m pip install -e ".[dev]"
python -m ttslab list
python -m ttslab doctor
pytest
```

A registered-but-untested engine intentionally fails:

```bash
python -m ttslab run kokoro --text "hello world"
```

It will become runnable only after an isolated adapter has been installed and smoke-tested.

## Next milestone

Make the first real isolated engine work end-to-end:

```bash
python -m ttslab run kokoro --text "hello world"
```

Then repeat the same contract with Pocket TTS and Chatterbox before expanding to heavier systems.

## Principles

- isolate external engines instead of forcing incompatible dependencies into one Python environment
- verify code, model-weight, and dataset licenses separately
- prefer measurements over architecture-by-opinion
- keep heavyweight model tests optional
- never fabricate benchmark results
- preserve failed experiments and provenance
- gradually replace external components with our own implementations
