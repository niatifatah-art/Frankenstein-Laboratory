# ourTTS v0.9 — Quality Brain

`Best` must mean **measured on our common suite**, not "the model we currently like most".

This pass turns the existing empty quality ledger and routing contract into an executable evidence pipeline while preserving a strict boundary between objective measurements and human judgement.

## Evidence layers

### 1. Generation evidence

Every sample begins with a real engine run against a case from the existing shared corpus in `benchmarks/corpus.json`.

Retain at least:

- engine key and exact model/source revision when available;
- case ID, text, language and task;
- success/failure state;
- WAV metadata and SHA-256;
- runtime/hardware metadata;
- an artifact/run reference.

A failed generation remains a sample. It contributes to failure rate and must not disappear from the dataset.

### 2. Objective transcript evidence

A fixed ASR evaluator produces a hypothesis transcript from generated audio. The quality pipeline stores both the original text and hypothesis, then computes corpus-level:

- WER;
- CER;
- failure rate.

`ourtts-quality score` is deterministic and dependency-light. The ASR model that produced the hypothesis is intentionally outside this Core module so evaluator model/version/hardware can be pinned and recorded independently.

Example:

```bash
ourtts-quality score \
  --reference "Hello, reproducible world!" \
  --hypothesis "hello reproducible world"
```

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

The recommended first objective evaluator is the official OpenAI Whisper implementation using one pinned model/configuration for a complete cast. WER/CER semantics should remain compatible with standard edit-distance evaluation (JiWER is a useful independent reference implementation).

Speaker identity is deliberately separate from naturalness and transcript accuracy. A later cloning-quality pass can add a pinned speaker-verification evaluator such as an ECAPA-TDNN system, but its similarity score must remain a separate raw metric until a reviewed routing policy decides how to use it.

## CI policy

Normal PR CI tests only:

- normalization and WER/CER math;
- corpus/task selection;
- failure aggregation;
- blind-packet determinism;
- release-evidence gates;
- CLI contracts;
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
