# OurTTS v0.4 acceptance / verification ledger

This file is the durable evidence checklist for the first coherent product-facing OurTTS path.
Items are not considered complete because code exists; runtime items require GitHub Actions evidence.

## Required product acceptance

- [ ] Core CI passes on Python 3.11.
- [ ] Core CI passes on Python 3.12.
- [ ] Core CI passes on Python 3.13.
- [ ] Research CLI smoke still passes.
- [ ] Product CLI (`ourtts`) smoke passes.
- [ ] Registry/license/provenance validation passes.
- [ ] Real Kokoro product E2E generates validated PCM WAV through `ourtts speak`.
- [ ] Stored `Yessss -> jɛːs` phoneme override reaches Kokoro native phoneme syntax.
- [ ] Exact 320 ms digital pause survives in the final rendered PCM output.
- [ ] Existing real Pocket TTS benchmark contract still passes.
- [ ] Pocket TTS VoicePack exported state path passes a real smoke test.
- [ ] VoxCPM2 natural-language Voice Design passes a real targeted smoke and retains an artifact.
- [ ] Unknown-rights cloning reference is blocked by default.
- [ ] Batch manifest path is covered by unit tests.
- [ ] Content-addressed cache path is covered by unit tests.
- [ ] Stale broad all-engine PR cast is no longer a permanent required red check.

## Evidence already reconciled

- [x] CosyVoice3 corrected five-reference zero-shot inference is recorded as real evidence without
      falsely marking it product-routable (`qualified_external`).
- [x] OpenVoice V2 remains a qualified voice-conversion component rather than being mislabeled as
      standalone TTS.
- [x] Existing qualified runtime evidence for Kokoro, Pocket, Chatterbox variants, Qwen3-TTS variants,
      VoxCPM2 and MeloTTS is preserved.
- [x] Research-only/restricted candidates remain outside safe default routing.

## Completion rule

Do not manually convert a failed check into a weaker assertion just to obtain green CI. Fix the
underlying bug, rerun, and record any truthful remaining limitation. Generated audio and model weights
stay in Actions artifacts/cache, not Git.
