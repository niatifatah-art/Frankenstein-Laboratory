# OurTTS v0.4 acceptance / verification ledger

This file is the durable evidence checklist for the first coherent product-facing OurTTS path.
Runtime claims below are backed by GitHub Actions evidence on the final v0.4 code candidate
`bc126294f251d886db3bd04a428c490f51ba2100`; the later commits only reconcile documentation/evidence.

## Required product acceptance

- [x] Core CI passes on Python 3.11.
- [x] Core CI passes on Python 3.12.
- [x] Core CI passes on Python 3.13.
- [x] Research CLI smoke still passes.
- [x] Product CLI (`ourtts`) smoke passes.
- [x] Registry/license/provenance validation passes.
- [x] Real Kokoro product E2E generates validated PCM WAV through `ourtts speak`.
- [x] Stored `Yessss -> jɛːs` phoneme override reaches Kokoro native phoneme syntax.
- [x] Exact 320 ms digital pause survives in the final rendered PCM output.
- [x] Existing real Pocket TTS benchmark contract still passes.
- [x] Pocket TTS VoicePack catalog-state path exports, persists, reloads and generates real speech.
- [x] Pocket reference-audio state export reports the gated Hugging Face access requirement clearly when cloning weights are unavailable.
- [x] VoxCPM2 natural-language Voice Design passes a real targeted smoke and retains an artifact.
- [x] Unknown-rights cloning reference is blocked by default.
- [x] Batch manifest path is covered by unit tests with per-job failure preservation.
- [x] Content-addressed cache path is covered by unit tests, including reference-sensitive keys.
- [x] Historical heavyweight listening/qualification casts are manual-only and no longer mandatory on every PR synchronize.

## Final retained evidence

### Core / product E2E

- Core CI run `32264437789`: success on Python 3.11, 3.12 and 3.13; each matrix job passed
  installation, Ruff, full pytest, research CLI smoke and product CLI smoke.
- Lab E2E run `32264437178`: success.
- Lab artifact `9369642051` (`lab-e2e-v04-product`).
- Artifact digest: `sha256:212c307648f17a530f117adae5379c3fb7647a1024cded89b4198e665c7f3d2c`.
- That E2E executes real `ourtts speak` through Kokoro, applies the stored pronunciation override,
  validates the final mono PCM WAV, verifies an inserted 320 ms digital-silence region, and keeps the
  existing real Pocket benchmark contract alive.

### VoxCPM2 Voice Design

- Targeted run `32264435938`: success.
- Artifact `9369654015` (`voxcpm2-v04-voice-design`).
- Artifact digest: `sha256:e9921ec461b80fbaf98f50e68ad8b7835259ab0d55fb7758cfccb49ec3a575d7`.
- The earlier failing seed kwarg was not ignored or weakened; deterministic seeding was moved outside
  the unsupported `VoxCPM.generate()` keyword contract and the real model path was rerun successfully.

### Pocket VoicePack state

- Targeted run `32264436071`: success.
- Artifact `9369594148` (`pocket-v04-voicepack-state`).
- Artifact digest: `sha256:55264094a9bcb98c3832638c121d3329d8a082f343bfd77e49ecd93360dd6e51`.
- The workflow exports an official Pocket catalog identity to `safetensors`, stores SHA/provenance in
  the VoicePack, reloads the exported file in the isolated Pocket worker, and generates real 24 kHz
  speech from the persisted state.
- Reference-audio state export remains implemented, but the upstream cloning-capable weights require
  accepting Pocket's Hugging Face terms and authenticating. That access requirement is surfaced
  explicitly rather than hidden or faked in anonymous CI.

## Evidence already reconciled

- [x] CosyVoice3 corrected five-reference zero-shot inference is recorded as real evidence without
      falsely marking it product-routable (`qualified_external`).
- [x] OpenVoice V2 remains a qualified voice-conversion component rather than being mislabeled as
      standalone TTS.
- [x] Existing qualified runtime evidence for Kokoro, Pocket, Chatterbox variants, Qwen3-TTS variants,
      VoxCPM2 and MeloTTS is preserved.
- [x] Research-only/restricted candidates remain outside safe default routing.

## What this acceptance does not claim

v0.4 proves a coherent, tested product boundary; it does **not** claim that OurTTS already owns a
state-of-the-art acoustic model or that every language/control/backend has equal quality. Remaining
research includes common-corpus WER/CER, speaker similarity, hallucination/repetition detection,
long-form and code-switching evaluation, GPU calibration, deeper language-specific normalization/G2P,
more verified prosody/control compilers, more persistent backend states, stable workers for useful
qualified-external components, and component harvesting toward original synthesis models.

## Completion rule

Do not manually convert a failed check into a weaker assertion just to obtain green CI. Fix the
underlying bug, rerun, and record any truthful remaining limitation. Generated audio and model weights
stay in Actions artifacts/cache, not Git.
