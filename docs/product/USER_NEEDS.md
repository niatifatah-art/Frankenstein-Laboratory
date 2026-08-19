# OurTTS — user needs distilled from the build session

## The job to be done

The user should be able to ask for speech, not manage a collection of ML repositories. The common
case must be one request with a text, voice/style, language and output path. OurTTS decides which
qualified backend to use unless the user deliberately chooses one.

## What the user expects

1. **Simple first use.** One CLI/API call; no model-specific imports.
2. **Local-first.** Good CPU choices on ordinary hardware and GPU acceleration when available.
3. **Choice without chaos.** Many engines may exist in the lab, but dependency isolation and routing
   hide their conflicts from the product path.
4. **Predictable speech editing.** Exact pauses, persistent pronunciation fixes, reusable styles and
   eventually segment-level regeneration.
5. **Reusable voice identity.** VoicePack owns references/provenance and can later cache backend
   embeddings/states.
6. **Safe cloning.** A random WAV is not automatically a licensed voice. Consent/provenance is a
   first-class field and unknown rights are rejected by default.
7. **Natural control.** Voice Design and style prompts where supported; explicit unsupported reports
   elsewhere.
8. **Multilingual use.** English first-class, plus Arabic/French/Russian and code-switching as the
   quality suite grows.
9. **Speed.** Streaming/low-latency backends for preview/agents; measured performance should inform
   routing.
10. **Scale.** Batch jobs for dozens of voices/languages without manual repetition.
11. **ACE compatibility.** A stable Python boundary so ACE can request speech without knowing Kokoro,
    Qwen, Chatterbox, etc.
12. **Honesty.** `ready` means tested audio, not an adapter stub; research licenses and failed
    experiments stay visible instead of being hidden.

## Definition of usable v0.4

A user can run `ourtts speak`, get a valid WAV, use exact pause markup and the pronunciation lexicon,
select a profile or an explicit engine, perform consented cloning where supported, use Voice Design
where supported, and submit a batch manifest. Every degradation is reported rather than silently
ignored.

This is not yet the final research-grade original TTS model. It is the first coherent product path on
top of the qualified laboratory.
