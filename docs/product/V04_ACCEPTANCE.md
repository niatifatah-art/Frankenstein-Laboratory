# OurTTS v0.4 acceptance / verification ledger

This file is the durable evidence checklist for the first coherent product-facing OurTTS path.
Items are not considered complete because code exists; runtime items require GitHub Actions evidence.

## Required product acceptance

- [ ] Core CI passes on Python 3.11 on the final v0.4 head.
- [ ] Core CI passes on Python 3.12 on the final v0.4 head.
- [ ] Core CI passes on Python 3.13 on the final v0.4 head.
- [ ] Research CLI smoke still passes.
- [ ] Product CLI (`ourtts`) smoke passes.
- [ ] Registry/license/provenance validation passes.
- [ ] Real Kokoro product E2E generates validated PCM WAV through `ourtts speak`.
- [ ] Stored `Yessss -> jɛːs` phoneme override reaches Kokoro native phoneme syntax.
- [ ] Exact 320 ms digital pause survives in the final rendered PCM output.
- [ ] Existing real Pocket TTS benchmark contract still passes.
- [ ] Pocket TTS VoicePack exported state path passes a real smoke test and reuses the exported state.
- [x] VoxCPM2 natural-language Voice Design passed a real targeted smoke on run `32263946129` after the seed fix.
- [ ] Unknown-rights cloning reference is blocked by default.
- [ ] Batch manifest path is covered by unit tests.
- [ ] Content-addressed cache path is covered by unit tests.
- [x] Historical heavyweight listening/qualification casts are manual-only and no longer mandatory on every PR synchronize.

## Candidate evidence before final revalidation

The v0.4 candidate has already proved the broad owned path:

- Core run `32263946171`: success on Python 3.11, 3.12 and 3.13, including Ruff, full pytest,
  research CLI smoke and product CLI smoke.
- Lab E2E run `32263946134`: success, including real `ourtts speak`, Kokoro pronunciation path,
  exact 320 ms digital pause validation, and the retained Pocket benchmark contract.
- VoxCPM2 targeted run `32263946129`: success after moving deterministic seeding outside the
  unsupported `VoxCPM.generate()` keyword contract.
- Pocket state run `32263946150` exposed an external access boundary: reference-audio state export
  requires accepting the gated Pocket cloning weights and authenticating with Hugging Face. v0.4 now
  reports that requirement explicitly and verifies the same official export/reuse format with an
  ungated catalog voice. The final rerun must prove that catalog-state path.

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
