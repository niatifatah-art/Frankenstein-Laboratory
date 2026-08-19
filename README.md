# Frankenstein Laboratory → ourTTS

**Frankenstein Laboratory** is the reproducible R&D environment for running, qualifying, benchmarking and dissecting open-source TTS systems.

**ourTTS** is the product boundary built on top of that evidence. The lab may contain many models; a normal user should not have to understand or manage them.

## Start simple

Core/CLI:

```bash
python -m pip install -e ".[dev]"

ourtts speak \
  --text "Yessss! [[pause:320ms]] It actually works." \
  --language en \
  --profile auto \
  --output out.wav
```

Local Studio:

```bash
python -m pip install -e ".[studio]"
ourtts-studio
```

Then open `http://127.0.0.1:7860`.

The Studio deliberately starts with a small surface: **text, voice, language, mode, feel, Generate**. Speed and engine override stay behind “More controls”. The backend still uses the same safe ourTTS synthesis path as the CLI; the browser does not get a second fake synthesis implementation.

## What ourTTS already does

- one stable `ourtts speak` product path plus the Python `OurTTS` facade;
- human-friendly profiles: `auto`, `fast_cpu`, `balanced_cpu`, `quality`, `voice_clone`, `voice_design`, `multilingual`;
- measured device/performance-aware routing instead of choosing engines alphabetically;
- commercial/license gating and isolated engine environments;
- exact leading/internal/trailing PCM digital pauses;
- persistent pronunciation lexicons and verified Kokoro phoneme compilation;
- VoicePack identity with reference provenance and explicit consent status;
- reusable backend-specific voice state where an upstream system exposes a real serializable representation;
- Voice Design and style controls only where a qualified adapter actually supports them;
- content-addressed generation cache;
- JSON batch generation;
- a lightweight local Studio with light/dark responsive UI and playback;
- retained real-model evidence in GitHub Actions rather than “it imported, therefore it works”.

## VoicePacks and reusable identity

Voice cloning references are never assumed safe merely because a model is open source. By default a reference must be marked:

```text
owned | licensed | consented | synthetic
```

Unknown rights are rejected unless the caller explicitly opts into that risk.

A VoicePack keeps identity separate from the model that happens to synthesize it. It can hold references, languages, pronunciation links, styles and backend-specific prepared states.

Inspect one:

```bash
ourtts voice-inspect --voicepack voices/my_voice
```

### Pocket TTS state

Pocket catalog state reuse remains supported:

```bash
ourtts voice-state \
  --voicepack voices/alba_cached \
  --engine pocket_tts \
  --language en \
  --catalog-voice alba
```

Reference-audio Pocket export uses the upstream cloning-capable weights and therefore still requires the applicable Hugging Face access/terms. ourTTS reports that gate rather than pretending the export worked.

### Chatterbox prepared state — v0.5

Qualified Chatterbox Base/Nano/Turbo/V3 can prepare upstream-native `Conditionals` once and save them inside the VoicePack:

```bash
ourtts voice-state \
  --voicepack voices/my_voice \
  --engine chatterbox_nano \
  --device cpu
```

The saved state is **not** described as a universal ourTTS speaker embedding. It remains tied to the backend, source reference SHA-256, adapter version, state format and qualified upstream model revision. A later synthesis may reuse it instead of preprocessing the raw reference again.

The dedicated v0.5 E2E exercises this path with a controlled synthetic reference:

```text
Kokoro synthetic reference
        ↓
VoicePack with provenance
        ↓
Chatterbox Nano prepare_conditionals()
        ↓
serialized backend state
        ↓
state reload
        ↓
unified ourtts speak
        ↓
validated PCM WAV
```

## Local Studio — v0.5

`ourtts-studio` is intentionally local-first. By default:

```text
outputs: ~/.cache/ourtts/studio
voices:  ~/.local/share/ourtts/voices
```

Browser voice selection is limited to that managed VoicePack library; it does not accept arbitrary filesystem paths. The Studio exposes:

- text composer;
- managed VoicePack selection;
- language;
- profile/mode;
- Natural / Energetic / Calm feel shortcuts;
- speed and expert engine override under progressive disclosure;
- Generate / Regenerate;
- audio playback;
- a collapsed “What did ourTTS do?” section with routing/result evidence.

If a selected backend cannot execute a requested style/control, generation fails clearly instead of silently discarding the request.

This v0.5 slice does **not** claim hosted cloud inference, accounts or billing. Those belong after the local product contract is stable.

## Python

```python
from pathlib import Path
from ttslab.api import OurTTS
from ttslab.synthesis import SynthesisRequest

client = OurTTS()
result = client.speak(
    SynthesisRequest(
        text="Hello from ourTTS.",
        output=Path("hello.wav"),
        language="en",
        profile="fast_cpu",
    )
)
print(result.engine, result.output_path)
```

## Batch

```bash
ourtts batch examples/batch-v1.json --output-root outputs/batch
```

## Voice Design

```bash
ourtts speak \
  --profile voice_design \
  --voice-design "young adult male, warm, energetic, clear, slightly fast" \
  --text "This voice was described in plain language." \
  --output designed.wav
```

VoxCPM2 exposes a qualified natural-language Voice Design path. Qwen3-TTS VoiceDesign is another qualified option; routing uses capability/device evidence instead of assuming a large CPU model is a sensible default.

## Qualified runtime evidence

Retained real synthesis evidence currently includes:

- Kokoro 0.9.4;
- Pocket TTS 2.1.0;
- Chatterbox Base / Nano / Turbo / Multilingual V3;
- Qwen3-TTS 0.6B CustomVoice / Base;
- Qwen3-TTS 1.7B VoiceDesign;
- VoxCPM2;
- MeloTTS.

OpenVoice V2 is qualified as a voice-conversion component, not mislabeled standalone TTS. CosyVoice3 has retained real zero-shot inference evidence but remains `qualified_external` until it has the same stable isolated product-worker contract as `ready` engines. Restricted/research candidates stay outside normal product routing.

`ready` means real model load + real generated PCM WAV + validation + retained evidence. It does not mean the backend is fast on every device.

## Research CLI

The laboratory interface remains separate:

```bash
python -m ttslab registry-check
python -m ttslab list
python -m ttslab corpus
python -m ttslab doctor
python -m ttslab route --language en --prefer streaming --max-generation-rtf 2
python -m ttslab benchmark pocket_tts --case en_basic
```

## Product controls and honesty

Neutral ourTTS markup is parsed before model invocation:

```text
[[pause:320ms]]
[[nonverbal:laugh]]
```

Exact pauses are owned post-processing. Native tags are compiled only for engines with verified support. An unimplemented pitch/emotion/style/pronunciation path stays unsupported rather than being faked. `--allow-degraded` exists only as an explicit experiment escape hatch.

## Core rules

- code license != weights license != dataset/training provenance != voice rights;
- voice consent/provenance is independent of the model license;
- adapter exists != model works;
- model loads != valid audio;
- CPU-compatible != CPU-realtime;
- external engines remain isolated;
- research-only/restricted components do not silently enter product routing;
- unsupported controls remain visible;
- unmeasured values remain unknown;
- model weights, personal references and large generated audio do not go in Git.

## What remains

ourTTS is usable infrastructure, not a claim of TTS quality leadership yet. The next evidence layers include common-corpus WER/CER, speaker similarity for consented/synthetic voices, hallucination/repetition checks, long-form and code-switching evaluation, GPU calibration, better language-specific text/G2P, more verified prosody compilers, persistent workers/streaming, and component-by-component architecture harvesting toward original **ourTTS Atom / Nano / Mini / Core / Pro / Omni** checkpoints.

See:

- `MASTER_AGENT_PROMPT.md` — durable engineering mission;
- `PROJECT_INSTRUCTIONS.md` — laboratory constitution;
- `docs/product/USER_NEEDS.md` — user-facing definition of useful;
- `docs/architecture/ourtts-v0.4-product-path.md` — canonical product boundary;
- `docs/product/V04_ACCEPTANCE.md` — v0.4 evidence ledger;
- `docs/product/V05_ACCEPTANCE.md` — v0.5 Studio/prepared-voice evidence ledger.
