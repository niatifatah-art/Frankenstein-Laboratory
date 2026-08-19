# License audit delta — 2026-08-18

This note records primary-source corrections layered in `registry/license_overrides.toml`.
It is an engineering provenance record, not legal advice.

## Verified changes

- Dia2-1B: the current official Nari Labs checkpoint declares Apache-2.0. Third-party assets retain
  their original licenses, so dependency/asset provenance remains separate.
  Source: https://huggingface.co/nari-labs/Dia2-1B
- GLM-TTS: current GitHub repository code is Apache-2.0, while the current official Hugging Face
  model repository declares MIT. These are intentionally tracked separately.
  Sources: https://github.com/zai-org/GLM-TTS and https://huggingface.co/zai-org/GLM-TTS
- FireRedTTS2: current official GitHub repository and official model repository declare Apache-2.0.
  The checkpoint is large and remains research-zone until runtime qualification.
  Sources: https://github.com/FireRedTeam/FireRedTTS2 and
  https://huggingface.co/FireRedTeam/FireRedTTS2
- Spark-TTS-0.5B: current official checkpoint declares CC-BY-NC-SA-4.0; do not route those weights
  into a commercial product runtime.
  Source: https://huggingface.co/SparkAudio/Spark-TTS-0.5B
- Higgs TTS 3: current official checkpoint uses the Boson Higgs TTS 3 Research and Non-Commercial
  License. Its creator-output grant does not authorize embedding/hosting the model in our product.
  Source: https://huggingface.co/bosonai/higgs-tts-3-4b
- Orpheus 3B 0.1 fine-tuned checkpoint currently declares Apache-2.0. Preset/reference voice-asset
  rights remain a separate unresolved provenance question, so those assets are not assumed safe.
  Source: https://huggingface.co/canopylabs/orpheus-3b-0.1-ft

## Policy

A permissive code or weights license never automatically grants rights to training datasets,
reference clips, preset voices, trademarks, or third-party dependencies. Those remain distinct
registry/provenance concerns.
