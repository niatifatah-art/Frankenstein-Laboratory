# Frankenstein Laboratory

A reproducible laboratory for **running, benchmarking, dissecting, integrating, and learning from open-source text-to-speech systems** while progressively building an independent modular TTS platform.

This is not a "many models behind one UI" project. Every external engine is isolated, licensed/provenanced separately, tested against shared contracts, and promoted only after real evidence exists.

## Current qualification state

Already qualified with real CPU synthesis:

- **Kokoro 0.9.4** — ready
- **Pocket TTS 2.1.0** — ready, real streaming qualification

Qualification wave staged in v0.2:

- Chatterbox Base / Nano / Turbo / Multilingual V3
- Qwen3-TTS 0.6B CustomVoice / Base, with 1.7B VoiceDesign tracked separately
- VoxCPM2
- MeloTTS
- CosyVoice3 source/container contract
- OpenVoice V2 as a voice-conversion component rather than a fake standalone TTS backend
- VibeVoice Realtime as a research-zone backend because current upstream use restrictions are stricter than repository license metadata alone

## Core v0.2

The Core now includes:

- machine-readable engine, licensing, hardware and capability registry
- strict integration states (`ready`, `adapter_ready`, `component`, `researching`, etc.)
- isolated `uv` worker contracts
- common worker JSON result parsing
- shared multilingual benchmark corpus
- PCM WAV validation and SHA-256 artifact identity
- reproducible benchmark result writer
- capability/language router that only selects qualified engines
- registry validation and CI tests
- qualification workflows that preserve failures instead of hiding them

## Quick start

```bash
python -m pip install -e ".[dev]"
python -m ttslab registry-check
python -m ttslab list
python -m ttslab corpus
python -m ttslab doctor
pytest
```

Run qualified engines:

```bash
python -m ttslab run kokoro --text "hello world" --output outputs/kokoro.wav
python -m ttslab run pocket_tts --text "hello world" --output outputs/pocket.wav
```

Ask the router for a qualified backend:

```bash
python -m ttslab route --require cpu --prefer streaming --language en
```

Run one reproducible benchmark corpus case:

```bash
python -m ttslab benchmark pocket_tts --case ar_en_codeswitch
```

Experimental adapters are deliberately gated behind `smoke` until a real-model qualification run passes:

```bash
python -m ttslab smoke chatterbox_nano --text "hello"
```

## Rules

- code license != model weights license != dataset license != voice asset license
- a README claim is not our benchmark result
- an adapter existing is not the same as a model working
- a model loading is not the same as valid audio
- research-only components do not silently enter the runtime product
- one engine's dependency conflict must not break the laboratory
- unmeasured values stay unknown

See `PROJECT_INSTRUCTIONS.md` for the project constitution.
