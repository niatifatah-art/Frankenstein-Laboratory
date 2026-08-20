# ourTTS v0.9 — Quality Brain

`Best` must mean **measured on our common suite**, not "the model we currently like most".

This pass turns the existing empty quality ledger and routing contract into an executable evidence pipeline while preserving a strict boundary between objective measurements and human judgement.

## Evidence layers

### 1. Generation evidence

Every sample begins with a real engine run against a case from the existing shared corpus in `benchmarks/corpus.json`.

A local real-model cast can be started with:

```bash
ourtts-quality cast \
  --engine kokoro \
  --engine pocket_tts \
  --language en \
  --task general \
  --max-cases 10 \
  --output-dir benchmarks/quality/cast/audio \
  --samples benchmarks/quality/cast/samples-generated.json
```

The command sends the **same selected corpus cases** through every requested engine. It retains per-case benchmark JSON, audio hashes, passed/failed states, and a common sample manifest. A failed generation remains a sample and contributes to failure rate.

Retain at least:

- engine key and exact model/source revision when available;
- case ID, text, language and task;
- success/failure state;
- WAV metadata and SHA-256;
- runtime/hardware metadata;
- an artifact/run reference.

### 2. Objective transcript evidence

A fixed ASR evaluator produces a hypothesis transcript from generated audio. The quality pipeline stores both the original text and hypothesis, then computes corpus-level:

- WER;
- CER;
- generation failure rate.

`ourtts-quality score` is deterministic and dependency-light. The ASR model that produced the hypothesis is intentionally outside the Core package so evaluator model/version/hardware can be pinned and recorded independently.

Example:

```bash
ourtts-quality score \
  --reference "Hello, reproducible world!" \
  --hypothesis "hello reproducible world"
```

The repository also contains `scripts/quality_transcribe_whisper.py`. The manual quality-cast workflow installs the official OpenAI Whisper implementation at revision:

```text
5f86d1d86363843179951550570367b37c5d6f78
```

and records the chosen Whisper model, device, Python version and platform in the retained sample manifest. Changing the evaluator revision/model creates a different evaluation condition and must be recorded rather than mixed silently with an older cast.

For release casts, use one fixed evaluator configuration for every engine in a comparison. Do not compare WER from different ASR evaluators as though it were the same measurement.

### 3. Blinded human naturalness

Naturalness MOS is human evidence.

The Core deliberately does **not** synthesize an automatic number and call it MOS. Instead:

```bash
ourtts-quality listening-pack samples.json \
  --output listening-public.json \
  --mapping listening-private.json
```

The public file hides engine identity. The private mapping is kept separately until ratings are complete.

Each public sample contains a blank `naturalness_mos` field on the conventional 1..5 scale. Multiple raters can be aggregated upstream, but the rating source/count must be retained in the evidence artifact.

### 4. Release evidence

After objective transcripts and blind human ratings exist:

```bash
ourtts-quality evidence \
  --samples samples.json \
  --ratings ratings.json \
  --mapping listening-private.json \
  --evidence-ref "artifact:<run-or-digest>" \
  --output release-evidence.json
```

The command refuses to emit a `QualityEvidence` item until both objective transcript coverage and human rating coverage meet `minimum_samples` (10 by default).

The resulting item is compatible with the existing `benchmarks/quality/ledger.json` schema. Promotion into that release ledger remains an explicit reviewed action; the quality runner does not silently rewrite product rankings.

## Current v1 score

The existing product policy remains:

```text
55% naturalness + 30% intelligibility + 15% stability
```

where:

- naturalness is measured human MOS normalized from 1..5;
- intelligibility is `1 - WER`;
- stability is `1 - failure_rate`.

CER is retained as diagnostic evidence but is not silently added to the v1 score. A future score-policy change must bump the suite/policy version rather than rewriting old results.

## Tasks

The common corpus is classified into four product quality tasks:

- `general`;
- `cloning`;
- `expressive`;
- `long_form`.

`Best` is therefore allowed to differ by language and task. A model that wins neutral English synthesis does not automatically become the best cloning, expressive or long-form engine.

## Evaluators

The first objective evaluator is the official OpenAI Whisper implementation using one pinned revision/model configuration for a complete cast. WER/CER semantics remain standard edit-distance measurements; JiWER is a useful independent reference implementation.

Speaker identity is deliberately separate from naturalness and transcript accuracy. A later cloning-quality pass can add a pinned speaker-verification evaluator such as an ECAPA-TDNN system, but its similarity score must remain a separate raw metric until a reviewed routing policy decides how to use it.

## Manual real-model workflow

`.github/workflows/quality-cast-manual.yml` is intentionally `workflow_dispatch` only.

Its first controlled cast:

1. installs the lab tooling;
2. generates the same English/general cases with Kokoro and Pocket TTS;
3. installs the pinned official Whisper evaluator;
4. transcribes each successful generation;
5. aggregates objective WER/CER/failure evidence;
6. builds a blinded human-listening packet;
7. records evaluator/host provenance;
8. uploads the complete cast directory even when generation or ASR fails;
9. only then marks the run failed if a stage failed.

`HF_TOKEN` is passed only from the GitHub Actions secret when present. It is never committed or printed. This matters for upstream assets/models whose access state may change over time.

## CI policy

Normal PR CI tests only:

- normalization and WER/CER math;
- corpus/task selection;
- failure aggregation;
- real-cast orchestration with mocked model execution;
- blind-packet determinism;
- release-evidence gates;
- CLI contracts;
- Whisper helper contract without downloading Whisper;
- Windows/Linux portability of the evidence tooling.

It does **not** download every TTS model and ASR evaluator on every source change.

Real multi-model casts belong in explicit/manual workflows with retained artifacts.

## Truth boundary

Do not:

- copy MOS/WER claims from model cards into our ledger;
- call an automatic naturalness predictor "human MOS";
- discard failed generations;
- expose engine names during blind listening;
- mix evaluator versions inside one comparison;
- enable `Best` from fewer samples than the configured release threshold;
- infer cloning quality from ordinary TTS quality.
