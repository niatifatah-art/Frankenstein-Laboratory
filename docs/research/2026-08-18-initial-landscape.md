# Initial TTS landscape — 2026-08-18

This is a source-backed starting snapshot, not a benchmark result.

## Immediate runtime/adapter candidates

### Pocket TTS
Official source: https://github.com/kyutai-labs/pocket-tts

Why it matters:
- CPU-oriented ~100M model
- audio streaming and low first-chunk latency claims
- voice cloning
- persistent exported voice state is interesting for the future Voice Pack format
- multiple language models

Do not record vendor performance claims as our measurements. Re-run on our hardware.

### Kokoro
Official source: https://github.com/hexgrad/kokoro

Why it matters:
- 82M parameter footprint
- strong lightweight/CPU baseline
- Apache-licensed repository and published weights according to upstream

### Chatterbox
Official source: https://github.com/resemble-ai/chatterbox

Why it matters:
- Nano / Turbo / Multilingual V3 family gives us multiple deployment profiles
- voice cloning and expressive/paralinguistic controls
- useful comparison for CPU vs larger-model behavior

### Qwen3-TTS
Official source: https://github.com/QwenLM/Qwen3-TTS

Why it matters:
- voice cloning
- free-form voice design
- streaming speech generation
- 0.6B / 1.7B family
- Apache-2.0 code LICENSE verified on 2026-08-18

### CosyVoice
Official source: https://github.com/FunAudioLLM/CosyVoice

Why it matters:
- pronunciation inpainting
- bi-streaming text-in/audio-out
- instruction control for language, emotion, speed and volume
- multilingual/cross-lingual zero-shot cloning

### VoxCPM2
Official source: https://github.com/OpenBMB/VoxCPM
Technical report: https://arxiv.org/abs/2606.06928

Why it matters:
- tokenizer-free architecture
- multilingual speech generation
- natural-language voice design
- controllable voice cloning
- Apache-2.0 upstream code/weights statement

## Rule

A project appearing in this document does not make it a shipping dependency. Each engine must pass:
1. provenance/license review
2. isolated installation
3. smoke inference
4. benchmark capture
5. adapter contract review

Only then may its registry status become `ready`.
