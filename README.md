# Frankenstein Laboratory

A reproducible laboratory for **running, benchmarking, dissecting, integrating, and learning from open-source text-to-speech systems** while progressively building an independent modular TTS platform.

This is not a "many models behind one UI" project. Every external engine is isolated, licensed/provenanced separately, tested against shared contracts, and promoted only after real evidence exists. The long-term product boundary is **OurTTS**; Frankenstein Laboratory remains the place where external systems are qualified, compared and dissected.

## Current qualification state

Real synthesis/conversion evidence retained by the laboratory:

- **Kokoro 0.9.4** — ready
- **Pocket TTS 2.1.0** — ready; real streaming qualification
- **Chatterbox Base** — ready
- **Chatterbox Nano** — ready
- **Chatterbox Turbo** — ready
- **Chatterbox Multilingual V3** — ready
- **Qwen3-TTS 0.6B CustomVoice** — ready
- **Qwen3-TTS 0.6B Base** — ready; synthetic-reference cloning qualification
- **Qwen3-TTS 1.7B VoiceDesign** — ready; functionally CPU-qualified but extremely slow there
- **VoxCPM2** — ready
- **MeloTTS** — ready after worker-local legacy compatibility fixes
- **OpenVoice V2** — qualified voice-conversion component; deliberately not presented as standalone TTS
- **CosyVoice3** — source/submodule install verified; full checkpoint inference not yet claimed
- **VibeVoice Realtime** — research zone because current use restrictions are stricter than ordinary permissive-runtime policy

"Ready" means the lab loaded the real model, generated PCM WAV audio, validated the artifact and retained qualification evidence. It does **not** mean every backend is fast on every device.

## OurTTS owned core — v0.3

The repository now contains product-facing subsystems that do not belong to any single upstream model:

- deterministic Text Engine with Unicode normalization, segmentation and script hints
- persistent pronunciation lexicon with text and phoneme overrides kept distinct
- engine-neutral Prosody Timeline and control-marker parser
- exact PCM digital-silence insertion without hidden resampling
- VoicePack v1 schema with provenance, consent status, per-backend cached states and SHA-256 validation
- synthesis planner that classifies controls as native, core post-processing or unsupported
- performance-aware router using retained CPU RTF measurements instead of treating "CPU works" as "CPU is fast"

These are intentionally small, auditable foundations. Language-specific semantic normalization, full G2P, alignment, advanced prosody rendering and original acoustic models are future layers rather than fake claims in v0.3.

## Core laboratory infrastructure

- machine-readable engine, licensing, hardware and capability registry
- strict integration states (`ready`, `adapter_ready`, `qualified_component`, `install_verified`, `researching`, etc.)
- isolated `uv` worker contracts
- common worker JSON result parsing
- shared multilingual benchmark corpus
- PCM WAV validation and SHA-256 artifact identity
- reproducible benchmark result writer
- capability/language/performance router that only selects qualified TTS engines
- date-scoped license overlays backed by primary upstream sources
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

Run qualified backends:

```bash
python -m ttslab run kokoro --text "hello world" --output outputs/kokoro.wav
python -m ttslab run pocket_tts --text "hello world" --output outputs/pocket.wav
```

Ask the router for a qualified backend and bound measured CPU generation cost:

```bash
python -m ttslab route --language en --prefer streaming --max-generation-rtf 2
```

Inspect our text/pronunciation/control layer:

```bash
python -m ttslab text \
  --text "DevShelf says Yessss! [[pause:320ms]] Really." \
  --language en \
  --lexicon examples/pronunciation-v1.json
```

Build an engine-aware synthesis plan:

```bash
python -m ttslab plan \
  --text "Hello from OurTTS." \
  --language en \
  --control pause=320 \
  --max-generation-rtf 2
```

Validate owned formats:

```bash
python -m ttslab lexicon-check examples/pronunciation-v1.json
python -m ttslab prosody-check examples/prosody-v1.json
python -m ttslab voicepack-check examples/voicepack-v1 --skip-hashes
```

Run one reproducible benchmark corpus case:

```bash
python -m ttslab benchmark pocket_tts --case ar_en_codeswitch
```

Experimental adapters remain gated behind `smoke` until a real-model qualification run passes:

```bash
python -m ttslab smoke <engine> --text "hello world"
```

## Rules

- code license != model weights license != dataset license != voice asset license
- a README claim is not our benchmark result
- an adapter existing is not the same as a model working
- a model loading is not the same as valid audio
- CPU-compatible is not the same as CPU-realtime
- research-only components do not silently enter runtime routing
- one engine's dependency conflict must not break the laboratory
- unsupported controls remain unsupported instead of being silently ignored
- unmeasured values stay unknown

See `PROJECT_INSTRUCTIONS.md` for the project constitution and `docs/architecture/ourtts-v0.3-owned-core.md` for the owned-core boundary.
