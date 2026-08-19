# ourTTS v0.5 acceptance — usable Studio + prepared voices

This document defines the evidence gate for the v0.5 slice. A feature is not accepted because the code exists; the final PR head must keep the named checks green.

## Scope

v0.5 does **not** train or release an original ourTTS checkpoint. It turns the verified v0.4 product path into a more usable local product and extends reusable VoicePack identity beyond the existing Pocket state path.

## Acceptance gates

### 1. Core remains clean

Required check: `core-ci`

Must pass on Python 3.11, 3.12 and 3.13 with:

- Ruff;
- full lightweight pytest suite;
- research CLI smoke;
- product CLI smoke.

The Studio remains optional so importing/running the Core does not require FastAPI.

### 2. Local Studio contract

Required check: `ourtts-studio-ci`

Must prove:

- `.[dev,studio]` installs;
- Ruff passes;
- Studio TestClient exercises `/`, health, profiles, generation result and audio retrieval;
- managed voice IDs cannot escape the configured VoicePack library;
- the whole lightweight test suite still passes with Studio dependencies installed;
- `ourtts --help` and `ourtts-studio --help` work;
- the FastAPI app can be instantiated without loading a TTS model.

The Studio is local-first and does not claim hosted accounts, billing or remote GPU execution.

### 3. Reusable Chatterbox VoicePack identity

Required check: `ourtts-v05-chatterbox-state-e2e`

The workflow uses only a controlled synthetic reference and must prove:

```text
Kokoro synthetic reference
        -> VoicePack (synthetic provenance + SHA-256)
        -> Chatterbox Nano prepare_conditionals()
        -> native serialized Conditionals state
        -> state SHA/model revision/format/adapter evidence
        -> state reload without raw-reference preprocessing
        -> unified ourtts speak
        -> valid mono PCM WAV
```

The persisted state must record:

- `engine = chatterbox_nano`;
- `format = chatterbox-conditionals-pt-v1`;
- qualified upstream model revision;
- adapter version;
- prepared-state SHA-256;
- source-reference SHA-256.

The unified synthesis result must retain backend-state provenance.

A prepared state is backend/revision-specific. It is **not** a universal ourTTS speaker embedding.

### 4. Existing product evidence must not regress

The final head must also keep the targeted canonical checks green, including:

- `lab-e2e`;
- `pocket-voice-state-smoke`;
- `voxcpm2-product-smoke`.

Pocket's reference-audio cloning gate remains explicit. VoxCPM2 Voice Design remains a real targeted path. No v0.5 change may weaken those boundaries simply to obtain green CI.

### 5. UX truth

The normal Studio surface exposes a small number of decisions:

- text;
- managed VoicePack;
- language;
- mode/profile;
- feel;
- Generate.

Speed and engine override are progressively disclosed. Unsupported styles or controls fail clearly rather than being silently ignored.

### 6. Security / provenance boundary

- browser requests cannot supply arbitrary VoicePack filesystem paths;
- generated artifacts live outside Git;
- personal reference audio is not committed;
- state/references are hash checked;
- cloning consent remains `owned`, `licensed`, `consented` or `synthetic` by default;
- external engine packages remain isolated from the Core environment.

## Release decision

v0.5 is accepted only when every applicable check above is green on the final PR head. If a real-model workflow fails, inspect the failure and fix the implementation; do not weaken the assertion or rewrite the evidence claim.

After acceptance, the next major evidence layer is common-corpus quality evaluation before claiming that `quality`/future `Best` routing represents quality leadership. The model-family roadmap (Atom, Nano, Mini, Core, Pro, Omni) remains a research/release target rather than a set of already-existing checkpoints.
