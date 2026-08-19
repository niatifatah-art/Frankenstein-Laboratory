# Frankenstein Laboratory

A reproducible laboratory for **running, benchmarking, dissecting and integrating open-source TTS**
while progressively building **OurTTS**, a stable product-facing speech engine that does not belong
to any single upstream model.

The lab can contain many models. The user should not have to manage them.

## The simple path — OurTTS v0.4

```bash
python -m pip install -e ".[dev]"

ourtts speak \
  --text "Yessss! [[pause:320ms]] It actually works." \
  --language en \
  --profile fast_cpu \
  --lexicon examples/pronunciation-v1.json \
  --output out.wav
```

`ourtts` now provides the product boundary:

- human-friendly routing profiles (`auto`, `fast_cpu`, `balanced_cpu`, `quality`, `voice_clone`,
  `voice_design`, `multilingual`);
- lightweight device-aware routing plus measured CPU evidence;
- explicit commercial/license gating;
- persistent pronunciation lexicons;
- a verified Kokoro phoneme compiler so stored phoneme fixes actually reach synthesis;
- exact PCM digital pauses with no hidden resampling;
- VoicePack reference provenance and consent checks;
- natural-language Voice Design where the selected backend supports it;
- stable engine argument translation instead of leaking model-specific flags into ACE/Studio;
- content-addressed caching;
- JSON batch manifests for many voices/languages;
- a stable Python facade for ACE and future Studio integration.

Python:

```python
from pathlib import Path
from ttslab.api import OurTTS
from ttslab.synthesis import SynthesisRequest

client = OurTTS()
result = client.speak(
    SynthesisRequest(
        text="Hello from OurTTS.",
        output=Path("hello.wav"),
        language="en",
        profile="fast_cpu",
    )
)
print(result.engine, result.output_path)
```

Batch:

```bash
ourtts batch examples/batch-v1.json --output-root outputs/batch
```

Pocket TTS voice-state export for a consented VoicePack:

```bash
ourtts voice-state --voicepack voices/my_voice --engine pocket_tts --language en
```

## Voice cloning safety

A cloning reference is not treated as safe merely because a model is open source. By default an
explicit reference must declare one of:

```text
owned | licensed | consented | synthetic
```

Example:

```bash
ourtts speak \
  --profile voice_clone \
  --reference my-reference.wav \
  --reference-consent owned \
  --text "This is a consented cloning test." \
  --output clone.wav
```

Unknown rights are rejected unless the caller explicitly opts into that risk. VoicePack references
carry their own consent/license/source metadata.

## Voice Design

The same product request can ask for a described voice and let routing select a qualified backend:

```bash
ourtts speak \
  --profile voice_design \
  --voice-design "young adult male, warm, energetic, clear, slightly fast" \
  --text "This voice was described in plain language." \
  --output designed.wav
```

VoxCPM2's v0.4 worker exposes its documented natural-language Voice Design and reference-transcript
cloning path. Qwen3-TTS VoiceDesign remains another qualified option; device/performance evidence
helps the router avoid absurd CPU choices where possible.

## Qualified runtime evidence

Real synthesis evidence retained by the laboratory currently includes:

- **Kokoro 0.9.4**
- **Pocket TTS 2.1.0** — real streaming qualification
- **Chatterbox Base / Nano / Turbo / Multilingual V3**
- **Qwen3-TTS 0.6B CustomVoice / Base**
- **Qwen3-TTS 1.7B VoiceDesign**
- **VoxCPM2**
- **MeloTTS**

**OpenVoice V2** is separately qualified as a real voice-conversion component rather than mislabeled
as standalone TTS.

**CosyVoice3** now has retained real five-reference zero-shot inference evidence from the corrected
workflow. It is recorded as `qualified_external`: real inference is proven, but it is deliberately
not product-routable until it has the same stable isolated worker contract as `ready` engines.

**VibeVoice Realtime** and other license/research candidates remain in the research zone unless their
current terms and runtime evidence meet the product gate.

`ready` means real model load + real generated PCM WAV + validation + retained evidence. It does not
mean the backend is fast on every device. The retained GitHub CPU measurements make this especially
clear: Pocket is near/above realtime in our CPU measurement while several large Qwen/Chatterbox
variants are functionally CPU-capable but much slower.

## Research CLI

The original laboratory CLI remains available:

```bash
python -m ttslab registry-check
python -m ttslab list
python -m ttslab corpus
python -m ttslab doctor
python -m ttslab route --language en --prefer streaming --max-generation-rtf 2
python -m ttslab benchmark pocket_tts --case en_basic
```

The product CLI does not replace the research CLI; it sits above it.

## Product controls and honesty

Neutral OurTTS markup is parsed before model invocation:

```text
[[pause:320ms]]
[[nonverbal:laugh]]
```

Exact pauses are owned post-processing. Verified Chatterbox Nano/Turbo nonverbal tags can be compiled
natively. Controls that do not yet have a verified native compiler or owned post-processor are
reported as unsupported; they are never silently ignored. `--allow-degraded` exists for explicit
experimentation.

## Core rules

- code license != model weights license != dataset license != voice asset license;
- voice consent/provenance is separate from all of the above;
- an adapter existing is not the same as a model working;
- a model loading is not the same as valid audio;
- CPU-compatible is not the same as CPU-realtime;
- research-only/restricted components do not silently enter product routing;
- one engine's dependency conflict must not break the Core;
- unsupported controls remain visible;
- unmeasured values stay unknown;
- expensive multi-engine casts are manual/targeted, not mandatory on every PR.

## What remains after v0.4

Functional qualification is not the same as complete quality evaluation. The next research layers are
common-corpus WER/CER, speaker similarity on consented/synthetic references, hallucination/repetition
detection, long-form and code-switching quality, GPU calibration, more language-specific semantic
normalization/G2P, more verified prosody compilers, persistent exported backend voice states beyond
Pocket, and component-by-component architecture harvesting toward original OurTTS synthesis models.

See:

- `MASTER_AGENT_PROMPT.md` — durable engineering mission and acceptance criteria;
- `PROJECT_INSTRUCTIONS.md` — laboratory constitution;
- `docs/product/USER_NEEDS.md` — user-facing definition of useful;
- `docs/architecture/ourtts-v0.4-product-path.md` — product path and boundaries.
