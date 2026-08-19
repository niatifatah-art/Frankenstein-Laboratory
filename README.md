# ourTTS + Frankenstein Laboratory

**ourTTS** is the simple local text-to-speech product built on top of **Frankenstein Laboratory**, the R&D layer where open TTS engines are isolated, qualified, benchmarked and dissected.

You should not need to know which upstream model is underneath just to create speech.

> Current stage: **v0.8 Windows/onboarding pass**. Native Windows and Linux are first-class product targets. External engines remain replaceable and keep their own code, weight, dataset and voice-asset provenance.

## Start here

### Windows 10/11 — native

Use **Python 3.12 x64**. WSL is not required.

Clone the repository, open PowerShell in it, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

Generate your first WAV without activating the virtual environment:

```powershell
.\.venv\Scripts\ourtts.exe generate `
  --text "Hello from ourTTS on Windows." `
  --language en `
  --quality fast `
  --output .\hello.wav
```

Open the local Studio by double-clicking:

```text
start-ourtts-studio.cmd
```

or run:

```powershell
.\.venv\Scripts\ourtts-api.exe
```

and open `http://127.0.0.1:7860/`.

For an install + real model/audio smoke in one command:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 -TestAudio
```

See [`docs/platforms/windows.md`](docs/platforms/windows.md) for diagnostics, reset instructions and the exact Windows support boundary.

### Linux

Python 3.12 is recommended because it overlaps the broadest current worker set.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip uv
python -m pip install -e ".[api]"

ourtts plan --text "Hello from ourTTS." --language en
ourtts generate --text "Hello from ourTTS." --language en --quality fast --output hello.wav
```

Run the local Studio:

```bash
ourtts-api
```

then open `http://127.0.0.1:7860/`.

## The simple product path

Preview what Auto will do:

```bash
ourtts plan --text "Hello world" --language en
```

Generate real speech:

```bash
ourtts generate \
  --text "Hello world" \
  --language en \
  --quality auto \
  --output speech.wav
```

Product quality modes are intentionally small:

- `auto` — choose a qualified route automatically;
- `fast` — prefer measured low-cost/realtime-capable routes;
- `local` — request local/offline inference;
- `best` — only works where the quality ledger contains real comparable evidence. It is not a fake marketing switch.

`ourtts generate` writes the WAV plus a manifest explaining what engine was chosen and why.

## Voices and VoicePacks

A product voice is a managed **VoicePack**, not a loose anonymous WAV and not a backend-specific voice name that another engine might ignore.

Inspect one:

```bash
ourtts voice inspect voices/my_voice
```

Prepare a reusable backend-specific state when the adapter supports it:

```bash
ourtts voice prepare voices/my_voice --engine chatterbox_nano
```

Prepared states are cached acceleration/conditioning artifacts tied to the exact backend/model revision and reference hash. They are **not** presented as a universal ourTTS speaker embedding.

Voice cloning keeps provenance separate from model licensing. A model being open source does not grant rights to clone an arbitrary person. Unknown/unsafe reference provenance is rejected by the product path rather than silently accepted.

## Local API and Studio

Install the API extra if needed:

```bash
python -m pip install -e ".[api]"
ourtts-api
```

The local server exposes the product API and Studio on `127.0.0.1:7860`.

The product layer currently includes:

- simple text → WAV generation;
- Auto/Fast/Local/Best routing semantics;
- managed VoicePack identities;
- prepared reusable voice states where qualified;
- exact PCM pause rendering in the owned renderer;
- pronunciation/prosody foundations;
- local REST API;
- lightweight browser Studio;
- product manifests and routing evidence.

## Platform status

| Platform | Core / CLI / API | Real product audio | Status |
|---|---|---|---|
| Windows 10/11 x64 | tested | tested with a real qualified CPU route | **native supported in v0.8** |
| Linux x64 | tested extensively | tested across multiple qualified engines | **supported / primary R&D platform** |
| macOS Apple Silicon | architecture-aware | not yet release-certified across the product path | **planned / experimental** |
| macOS Intel | expected Python portability | not release-certified | **experimental** |

Platform support does **not** mean every research engine is certified on that OS. An engine earns an OS-specific claim only after real model load, real PCM output validation and retained evidence on that platform.

## What Frankenstein Laboratory does

The laboratory stays underneath the simple product surface. It can hold many engines without forcing their dependency conflicts into one Python environment.

Current retained real synthesis/conversion evidence includes Kokoro, Pocket TTS, Chatterbox Base/Nano/Turbo/Multilingual V3, Qwen3-TTS variants, VoxCPM2, MeloTTS and OpenVoice V2 as a voice-conversion component. Other systems stay research/external until their runtime and licensing boundary is proven.

The lab owns:

- isolated `uv` worker contracts;
- machine-readable engine/capability/license registry;
- multilingual benchmark corpus;
- PCM/audio validation and SHA-256 evidence;
- performance routing evidence;
- quality ledger foundations;
- research qualification workflows;
- explicit `ready`, `qualified_component`, `qualified_external`, `researching`, etc. states.

For research/developer work:

```bash
python -m pip install -e ".[dev,api]"
python -m ttslab registry-check
python -m ttslab list
python -m ttslab doctor
python -m ttslab route --language en --prefer streaming --max-generation-rtf 2
pytest
```

## Rules that do not get weakened

- source-code license != model-weight license != dataset license != voice-asset license;
- voice consent/provenance is a separate fact again;
- an adapter existing is not proof that a model works;
- a model importing is not proof that it generated valid audio;
- CPU-compatible is not the same as a good CPU choice;
- unsupported controls are rejected/reported instead of silently ignored;
- research-only/non-commercial/unresolved checkpoints do not silently enter product routing;
- one engine's dependency conflict must not break the Core;
- benchmark claims need retained evidence;
- no model weights, secrets or personal reference audio belong in Git.

## Where this is going

Frankenstein Laboratory is not the final product and ourTTS is not intended to remain a wrapper forever. The long-term path is to move more value into owned components: text normalization/G2P, pronunciation repair, voice identity, prosody, streaming, evaluation, routing, decoding and eventually original synthesis models/checkpoints where the research evidence justifies it.

Near-term priorities after the Windows/onboarding pass are:

1. common quality evaluation (WER/CER, naturalness, speaker similarity, failures, hallucination/repetition);
2. evidence-backed `Best` routing;
3. more prepared VoicePack states and persistent workers;
4. deeper pronunciation repair and executable prosody;
5. streaming product/API paths and better Studio UX;
6. macOS certification;
7. component harvesting/reimplementation toward original ourTTS models.

## Project docs

- [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md) — laboratory constitution
- [`docs/product/OURTTS_AGENT_PROMPT.md`](docs/product/OURTTS_AGENT_PROMPT.md) — product engineering mission
- [`docs/product/PRODUCT_FOUNDATION.md`](docs/product/PRODUCT_FOUNDATION.md) — product architecture and UX boundary
- [`docs/platforms/windows.md`](docs/platforms/windows.md) — native Windows setup and support
- [`benchmarks/quality/`](benchmarks/quality/) — quality-evidence foundation

---

**Frankenstein Laboratory finds out what is actually good. ourTTS gives the user one sane way to use it.**
