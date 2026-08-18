# Frankenstein Laboratory

Experimental laboratory for benchmarking, integrating, dissecting, and learning from open-source text-to-speech systems while progressively building an independent modular TTS platform.

The goal is **not** to hide many models behind one UI. The laboratory exists to produce evidence: reproducible benchmarks, stable adapter contracts, licensing/provenance records, reusable text/pronunciation/prosody infrastructure, and eventually original TTS components and models.

## Status

Bootstrap phase. The first target is a small working vertical slice with isolated engine adapters and a real CLI, followed by fair benchmarks.

## Principles

- isolate external engines instead of forcing incompatible dependencies into one Python environment
- verify code, model-weight, and dataset licenses separately
- prefer measurements over architecture-by-opinion
- keep heavyweight model tests optional
- never fabricate benchmark results
- gradually replace external components with our own implementations

See `PROJECT_INSTRUCTIONS.md` once the bootstrap branch lands for the full project constitution.
