# OurTTS v0.5 — Voice Identity Execution Boundary

## Purpose

v0.5 begins turning VoicePack from a validated storage format into an executable identity boundary for OurTTS.

The invariant is strict: a caller supplying voice identity must never receive audio from a backend that silently ignored that identity.

## Identity resolution

A VoicePack reference is eligible for execution only when:

- its path remains inside the VoicePack root
- the asset exists
- its SHA-256 matches when a digest is registered
- its consent state is `owned`, `licensed`, `consented`, or `synthetic`

`unknown` consent is deliberately rejected by default. A caller may opt in explicitly, and that override is recorded in the render manifest.

Reference selection is deterministic in VoicePack order. This is intentionally simple until a later reference-quality selector is measured and justified.

## Identity is not style

Voice identity and voice style remain separate concepts.

A VoicePack may contain style presets, but a preset only becomes executable when the selected backend both advertises the relevant normalized capability and the current OurTTS adapter has a verified translation for that control.

A registry capability alone is not enough. An upstream model may support a feature that our adapter has not integrated yet.

## Truthful reference routing

When reference audio is supplied, automatic routing requires `voice_cloning` and then verifies that the selected adapter actually consumes a reference path.

An explicit backend is rejected when it would ignore the reference. This prevents a serious failure mode where a VoicePack appears to work while a default or unrelated backend voice is actually rendered.

## Normalized controls

The owned control vocabulary now classifies:

- style
- emotion
- pace
- pitch
- volume
- emphasis
- whisper
- phoneme override
- voice design
- non-verbal events

This classification is not a claim that all controls render today. Rendering requires two independent facts:

1. the engine registry advertises the required capability
2. the active adapter implements a verified mapping

Unknown or unmapped controls fail explicitly.

Exact inline `[[pause:...]]` markers remain the generally supported core-rendered control because they are implemented as deterministic PCM silence.

## Render manifest v2

Render manifests now retain normalized controls and caller metadata in addition to the existing engine, text, segment, worker-payload and final-audio evidence.

When a VoicePack is used, manifest metadata records:

- VoicePack ID and display name
- requested style preset
- selected reference path within the pack
- reference SHA-256
- reference license/source/consent
- VoicePack provenance
- whether unknown consent was explicitly allowed

This is evidence metadata, not a transferable legal conclusion about the underlying voice asset.

## Deliberately unfinished

v0.5 does not yet claim:

- generation or execution of cached backend speaker states/embeddings
- universal VoicePack portability across all engines
- mixed local text/phoneme replacement rendering
- general Prosody Timeline rendering
- automatic reference-quality ranking
- speaker-similarity quality guarantees
- GPU-aware identity routing

Those remain subsequent vertical slices.

## Next execution slices

1. Add backend-state preparation/execution behind explicit adapter contracts where upstream engines expose reusable speaker state.
2. Add cloning-specific benchmark cases and speaker-similarity evidence.
3. Expand normalized control mappings only after real backend tests.
4. Implement language-specific text/G2P and mixed pronunciation repair paths.
5. Extend exact pauses into an actually rendered Prosody Timeline.
