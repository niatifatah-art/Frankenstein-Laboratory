# ourTTS quality evidence

`Best` is a measured product mode, not a marketing label.

The release ledger starts empty on purpose. An engine may enter `benchmarks/quality/ledger.json` only after the common suite retains enough comparable evidence for the same suite version.

The executable v0.9 evidence workflow is documented in [`docs/product/V09_QUALITY_BRAIN.md`](../../docs/product/V09_QUALITY_BRAIN.md) and exposed through `ourtts-quality`.

## v1 required release fields

Each release evidence item records:

- engine
- language
- task (`general`, `cloning`, `expressive`, or `long_form`)
- sample count
- measured **human** naturalness MOS (1..5)
- measured WER (0..1)
- measured failure rate (0..1)
- suite version
- evidence reference pointing to retained artifacts/results

CER is retained in objective diagnostics but is not silently mixed into the v1 release score.

The v1 product score is deliberately transparent:

```text
55% naturalness + 30% intelligibility + 15% stability
```

This weighting is a routing policy, not a benchmark measurement. Raw metrics remain available and must be retained.

## Quick evaluator commands

List the shared English general cases:

```bash
ourtts-quality corpus --language en --task general
```

Measure one transcript pair:

```bash
ourtts-quality score \
  --reference "Hello, reproducible world!" \
  --hypothesis "hello reproducible world"
```

Aggregate a real sample set:

```bash
ourtts-quality summarize samples.json --output objective.json
```

Create a blinded listening packet and a separate private engine mapping:

```bash
ourtts-quality listening-pack samples.json \
  --output listening-public.json \
  --mapping listening-private.json
```

After human ratings exist, build candidate release evidence:

```bash
ourtts-quality evidence \
  --samples samples.json \
  --ratings ratings.json \
  --mapping listening-private.json \
  --evidence-ref "artifact:<run-or-digest>" \
  --output release-evidence.json
```

Promotion into `ledger.json` remains explicit and reviewable; the evaluator does not silently rewrite product routing.

## Acceptance rules

- Never copy quality claims from a model card into this ledger.
- Compare engines on the same corpus/suite revision and equivalent task.
- Keep unmeasured values unknown; do not infer them.
- Human MOS must come from listening ratings; an automatic proxy must never be mislabeled as human MOS.
- Keep failed generations in the sample set so failure rate remains honest.
- Do not enable `Best` for a language/task until at least one eligible engine meets `minimum_samples`.
- Keep listening-test methodology, raters/sample counts, ASR evaluator revision, hardware/runtime metadata, and generated audio in the associated evidence artifact.
- A later policy may use more metrics, but changing weights or required metrics must bump the suite/policy version rather than rewriting historical evidence.
