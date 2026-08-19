# ourTTS quality evidence

`Best` is a measured product mode, not a marketing label.

The default ledger starts empty on purpose. An engine may enter `benchmarks/quality/ledger.json` only after the common suite retains enough comparable evidence for the same suite version.

## v1 required fields

Each evidence item records:

- engine
- language
- task (`general`, `cloning`, `expressive`, or `long_form`)
- sample count
- measured naturalness MOS (1..5)
- measured WER (0..1)
- measured failure rate (0..1)
- suite version
- evidence reference pointing to retained artifacts/results

The v1 product score is deliberately transparent:

```text
55% naturalness + 30% intelligibility + 15% stability
```

This weighting is a routing policy, not a benchmark measurement. Raw metrics remain available and must be retained.

## Acceptance rules

- Never copy quality claims from a model card into this ledger.
- Compare engines on the same corpus/suite revision and equivalent task.
- Keep unmeasured values unknown; do not infer them.
- Do not enable `Best` for a language/task until at least one eligible engine meets `minimum_samples`.
- Keep listening-test methodology, raters/sample counts, ASR evaluator revision, hardware/runtime metadata, and generated audio in the associated evidence artifact.
- A later policy may use more metrics, but changing weights or required metrics must bump the suite/policy version rather than rewriting historical evidence.
