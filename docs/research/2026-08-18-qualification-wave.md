# Qualification wave — 2026-08-18

This note records why the v0.2 qualification wave exists and what evidence is required before an engine is promoted to `ready`.

## Promotion rule

An adapter is not `ready` merely because it imports or starts downloading weights. Promotion requires:

1. the isolated environment resolves reproducibly;
2. the actual upstream model loads;
3. real synthesis completes;
4. a non-trivial PCM WAV is validated;
5. the workflow preserves the audio/result artifact;
6. licensing/provenance fields are explicit enough for the claimed use zone;
7. observed runtime details replace assumptions (for example sample rate and actual dependency footprint).

## First-wave findings that motivated the clean rerun

- Qwen3-TTS 0.6B CustomVoice completed real CPU synthesis and produced valid 24 kHz audio, but its first worker environment accidentally resolved CUDA/NVIDIA packages through transitive PyTorch dependencies. The clean worker now declares CPU PyTorch directly.
- VoxCPM2 completed real CPU synthesis and produced valid 48 kHz audio. The first run also loaded an unused denoiser and CUDA dependency stack; the clean worker disables the denoiser and pins CPU PyTorch.
- Chatterbox's PyPI package lagged the current upstream source: Nano's documented `nano=True` API was absent in the installed release. Chatterbox workers now pin the current reviewed upstream source revision.
- Chatterbox Base hit an upstream-known PerTh watermarker initialization failure in the older dependency path. The clean rerun uses the current upstream source instead of bypassing watermarking.
- MeloTTS exposed legacy dependency assumptions (`pkg_resources`) and an unnecessary 526 MB UniDic download during an English-only qualification. The clean worker pins the observed source revision, restores the compatible setuptools surface, uses CPU PyTorch, and skips unrelated dictionaries.
- Shell pipelines now use `set -euo pipefail`; model failures can no longer be hidden by `tee` returning success.

## Clean-wave coverage

Real-model qualification jobs:

- Chatterbox Base
- Chatterbox Nano, with a synthetic reference generated inside the lab
- Chatterbox Turbo, with a synthetic reference generated inside the lab
- Chatterbox Multilingual V3, with a synthetic reference generated inside the lab
- Qwen3-TTS 0.6B CustomVoice
- Qwen3-TTS 0.6B Base voice cloning, with a synthetic reference generated inside the lab
- VoxCPM2
- MeloTTS

Source-contract jobs:

- CosyVoice3 source + submodules
- OpenVoice V2 as a voice-conversion component
- VibeVoice Realtime as a research-zone system

Synthetic reference audio is used deliberately so qualification does not silently depend on a borrowed human voice sample.
