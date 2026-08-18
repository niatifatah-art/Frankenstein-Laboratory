# OurTTS v0.3 — owned core boundary

Frankenstein Laboratory is a research and qualification system. OurTTS is the product boundary.
The purpose of v0.3 is to ensure that valuable behavior increasingly lives in code we own rather
than in assumptions tied to one upstream model.

## Owned subsystems introduced in v0.3

### Text Engine

`ttslab.text_engine` performs deterministic Unicode/whitespace normalization, sentence segmentation
and script hints. It deliberately does **not** pretend to be a universal semantic normalizer or
language detector. Language-specific number/date/currency expansion will be added behind explicit
language modules and tests.

### Pronunciation

`ttslab.pronunciation` stores persistent text and phoneme overrides. Text substitutions can be
applied generically. Phoneme overrides remain structured metadata unless the selected engine has a
verified `phoneme_input` capability. This prevents the core from silently sending model-specific
markup to engines that ignore it.

### Prosody

`ttslab.prosody` defines an engine-neutral timeline and a neutral inline control syntax such as
`[[pause:320ms]]`. Markers are parsed into structured controls; they are not passed through as if
every model understands the same tags.

### Exact digital silence

`ttslab.audio_timeline` concatenates compatible PCM WAV segments and inserts exact zero-valued
silence in frame units. It refuses hidden resampling or format conversion.

### VoicePack

`ttslab.voicepack` defines a persistent voice identity container with reference-clip provenance,
per-backend cached states, language metadata, style presets and a pronunciation lexicon link.
Paths are constrained to remain inside the pack root and optional SHA-256 verification detects
stale or replaced assets.

### Synthesis planning

`ttslab.pipeline` prepares text and selects a qualified backend. Requested controls are classified as:

- native to the selected engine,
- core post-processing,
- unsupported.

Unsupported controls stay explicit; the lab does not fake capability parity.

## Routing change

"Runs on CPU" is not equivalent to "good CPU choice". v0.3 overlays measured CPU generation RTF
from retained qualification artifacts and allows `--max-generation-rtf` filtering. The values are
environment-specific evidence from GitHub-hosted CPU runners, not universal model rankings.

## Design rule

External engines remain isolated workers. Owned code may reuse permissively licensed components
when useful, but model code, weights, datasets and voice assets remain separately tracked. Research
systems do not enter runtime routing merely because their source repository can be cloned.
