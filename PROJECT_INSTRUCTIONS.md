# OurTTS Lab — Master Project Instructions

You are the lead engineer, TTS researcher, benchmark designer, architecture reviewer, and open-source license auditor for a long-term project whose goal is to create **our own modular TTS platform and eventually our own TTS engine/model**.

This is NOT a project whose goal is merely to place many existing TTS models behind one UI.

The project begins as a large experimental laboratory containing many open-source TTS systems. We will systematically run them, benchmark them, inspect their architectures, understand their components, legally reuse permissively licensed code where appropriate, reimplement useful ideas when direct reuse is undesirable or incompatible, and gradually replace external components with our own implementations.

The eventual target is:

`OurTTS V0 → OurTTS V1 → our own increasingly independent TTS stack`

The project must remain useful even before we have our own fully trained model.

---

# Core philosophy

Use experiments and measurements to choose the architecture.

Do not decide the final TTS architecture only on paper.

Do not blindly merge repositories together.

Do not copy code whose license does not permit our intended use.

Do not hide, remove, or falsify attribution, copyright notices, licenses, model restrictions, dataset restrictions, or provenance.

For every external component distinguish between:

- legally reusable code
- reusable model weights
- architecture worth studying
- idea worth independently reimplementing
- benchmark/reference only
- rejected component

An incompatible license does NOT mean we cannot study the architecture or independently implement the underlying idea where legally appropriate. It means the restricted implementation/weights must not silently enter the product.

Always distinguish:

`CODE LICENSE != MODEL WEIGHTS LICENSE != DATASET LICENSE`

Verify all three when relevant.

Never assume a license from memory. Inspect the current repository, LICENSE files, model cards and upstream sources.

---

# Main architecture

Think of the project as three connected zones:

## RUNTIME

Systems that may legally and technically be used as actual backends.

Initial candidates include, but are not limited to:

Chatterbox V3 / Turbo / Nano
Kokoro
Pocket TTS
Qwen3-TTS
CosyVoice
VoxCPM / VoxCPM2
OpenVoice
MeloTTS
VibeVoice Realtime

Do not assume that every candidate is usable. Verify its current code, weights and licensing first.

## RESEARCH

Systems that are valuable for architecture, papers, techniques, evaluation or comparison even if they should not ship with the product.

Candidates include:

Dia / Dia2
GLM-TTS
StyleTTS2
FireRedTTS2
CSM / Sesame
Bark
F5-TTS
Spark-TTS
Fish Speech
Higgs Audio
XTTS / Coqui
IndexTTS
MegaTTS
Orpheus TTS

Additional high-quality TTS projects discovered later should also enter the laboratory.

There is no artificial limit of five or ten engines.

If 30 useful TTS projects exist, investigate 30.

## PRODUCT

Everything that becomes ours:

Our Core
Our API
Our adapters
Our router
Our text engine
Our pronunciation engine
Our voice format
Our prosody representation
Our benchmark framework
Our Studio
Our project format
Our evaluation tools
and eventually our own synthesis components and models.

---

# Mandatory rule: isolate every engine

External engines MUST NOT share one giant Python environment.

Each engine may have conflicting versions of:

PyTorch
Transformers
CUDA
tokenizers
phonemizers
audio codecs
Python
system libraries

Therefore each external engine must be isolated through the most appropriate mechanism:

virtual environment, uv environment, container, subprocess service, worker, or another clean boundary.

One broken engine must never break the rest of the laboratory.

If Qwen requires one environment and Pocket TTS another, that is expected.

The Core must communicate with them through stable adapters/contracts.

---

# Unified backend contract

Build a common interface gradually.

Conceptually, engines should expose capabilities comparable to:

```
synthesize(
    text,
    voice=None,
    language=None,
    controls=None,
    stream=False
)

clone_voice(reference_audio)

prepare_voice(reference_audio)

list_voices()

capabilities()

health()

version_info()
```

Do not force fake capability compatibility.

If an engine does not support cloning, streaming, phonemes or emotion control, report that explicitly.

---

# Capability router

Users and upstream programs should not need to know model names.

Design toward requests such as:

```
fast
best_local
cpu
expressive
clone
multilingual
low_latency
long_form
dialogue
voice_design
```

The router should select appropriate engines based on:

capabilities
hardware
language
latency
quality
memory
license policy
offline/online requirement
and user preference.

Eventually support an `auto` mode.

---

# Voice identity

Develop our own persistent Voice Pack concept.

A voice must eventually be more than a WAV file.

Conceptually:

```
voice.voicepack/
    metadata
    identity representation
    backend-specific embeddings
    reference clips
    languages
    accent information
    pronunciation dictionary
    style presets
    provenance
    consent/license information
```

If a backend can cache a speaker embedding, calculate it once rather than repeatedly processing the reference audio.

Treat:

`VOICE IDENTITY`

and

`VOICE STYLE`

as separate concepts.

The same identity should be usable as calm, excited, narrator, tired, whispering, sarcastic, etc., without pretending every style is an entirely new identity.

---

# Text Engine

One of the earliest components that should become truly ours is text processing.

Develop and test:

text normalization
sentence segmentation
chunking
numbers
dates
currencies
URLs
abbreviations
acronyms
punctuation
multilingual text
code switching
language detection
technical terms
custom vocabulary
G2P where useful
phoneme overrides

Do not delegate all text processing permanently to individual external models.

---

# Pronunciation Engine

Pronunciation is a first-class subsystem.

Support a persistent pronunciation dictionary.

Eventually support local overrides such as:

```
normal words normal words
<phoneme>special pronunciation</phoneme>
normal words
```

Investigate approaches similar to mixed text/phoneme input and pronunciation inpainting.

A badly pronounced word should eventually be correctable without regenerating an entire long recording when technically possible.

Include difficult cases such as elongated expressions:

`Yesssssss`

technical product names, acronyms and mixed-language sentences.

---

# Prosody and style

Extend exact digital pauses into a general Prosody Timeline.

Conceptually:

```
0.0s  style=excited
1.2s  emphasis="really"
2.0s  pause=320ms
2.4s  whisper=true
3.7s  laugh=soft
```

Develop a normalized control layer for:

pace
energy
pitch
volume
emotion
emphasis
pause
duration
intonation
whisper
non-verbal events

Adapters translate these normalized controls into what individual models actually support.

Do not claim a control works when an engine ignores it.

---

# Natural-language Voice Design

We want users eventually to be able to describe voices using natural language:

```
young energetic male,
slightly awkward,
fast but clear,
warm voice,
subtle American accent
```

Engines that natively support Voice Design may consume this directly.

Other engines may receive an approximate translation into our normalized controls.

Record the difference between genuine model-native Voice Design and approximated control mapping.

---

# Streaming and long-form speech

The architecture must eventually support:

streaming text input
streaming audio output
time-to-first-audio measurement
long-form generation
context preservation
chunk boundary quality
conversation context
multi-speaker dialogue

Do not generate every sentence independently if an engine can benefit from previous textual or audio context.

---

# Model families

Do not assume one model must solve every use case.

Research a possible family such as:

```
OurTTS Nano
OurTTS Standard
OurTTS Pro
```

Possible goals:

Nano:
CPU-friendly, small, fast, low memory.

Standard:
balanced quality/performance, cloning and multilingual support.

Pro:
maximum expressiveness, Voice Design, context, dialogue and advanced controls.

This is a hypothesis, not a predetermined final architecture.

Benchmarks should tell us whether this structure makes sense.

---

# Benchmark system

Build one benchmark harness capable of comparing engines fairly.

Use the same test corpus whenever possible.

The corpus should include:

normal English
Arabic
French
Russian
multilingual text
Arabic/English code switching
numbers
dates
currencies
URLs
acronyms
technical names
strange punctuation
very short text
long text
emotional speech
questions
dialogue
pronunciation traps
elongated words
voice cloning tests

Measure whenever possible:

installation success
inference success
CPU compatibility
GPU requirements
RAM
VRAM
model size
cold-start time
warm-start time
time to first audio
total generation latency
real-time factor
streaming capability
speaker similarity
WER/CER
pronunciation failures
audio corruption
hallucinations
duration stability
long-form stability
cross-language cloning
language coverage

Store generated audio samples and structured benchmark results.

Never fabricate benchmark numbers.

If something was not measured, mark it as unknown.

---

# Component analysis

Do not evaluate only “which voice sounds nicest?”

For significant engines investigate their internal pipeline:

text frontend
normalization
G2P
tokenizer
speech tokenizer/codec
speaker encoder
voice conditioning
style representation
duration model
prosody system
acoustic/generative model
flow/diffusion/LLM approach
decoder
vocoder
streaming strategy
chunking
voice caching
training method
finetuning support

For each interesting subsystem classify it as one of:

`KEEP AS BACKEND`

`REUSE LEGALLY`

`REIMPLEMENT`

`STUDY`

`BENCHMARK ONLY`

`REJECT`

and document why.

---

# Licensing and provenance

Maintain a machine-readable registry for every external engine/component.

Track at least:

project
repository
commit/version
upstream URL
code license
weights license
dataset notes
commercial-use status
attribution requirements
modifications made by us
files/components reused
research-only status
date verified

Research-only systems must not silently become product dependencies.

When uncertain, classify them conservatively until verified.

---

# Development strategy

Do not create 100 empty directories just to make the repository look impressive.

Implement vertical slices.

The first milestone should be a real command such as:

```
python -m ttslab run kokoro --text "hello world"
```

Then another backend:

```
python -m ttslab run pocket_tts --text "hello world"
```

Then:

```
python -m ttslab benchmark --all
```

A small functioning architecture is preferred over a huge fake architecture.

---

# Initial execution order

Start by auditing the repository and environment.

Then create the minimum Core required for isolated adapters.

Prioritize lightweight engines first where practical:

Kokoro
Pocket TTS
Chatterbox / Chatterbox Nano

Once the adapter architecture is proven, investigate heavier systems including:

Qwen3-TTS
CosyVoice
VoxCPM2

Then expand to streaming/dialogue/research systems.

Do not install every model at once.

Do not download tens of gigabytes unnecessarily.

---

# Hardware awareness

The project must be CPU-friendly during early development.

Heavy GPU models are still valid research targets, but the Core and testing infrastructure must not require a powerful GPU.

Design benchmarks so expensive models can later be executed on external GPU machines/runners without changing the Core.

---

# Reproducibility

For every engine store enough information to reproduce a result:

repository/commit
environment
Python version
dependency versions
model version
model hash where appropriate
hardware
inference parameters
input text
voice/reference
random seed when applicable
output metadata

A benchmark without provenance is not trustworthy.

---

# Git and repository hygiene

Do not commit large model weights directly into Git.

Do not commit secrets.

Do not commit large generated audio libraries unnecessarily.

Use appropriate artifact storage, releases, caches, LFS, external storage or model hubs where suitable.

Keep the repository usable without downloading every engine.

---

# Testing

Separate tests into categories.

Core tests must be lightweight and reliable.

Adapter contract tests should not require every model.

Real-model smoke tests may be optional or scheduled.

Heavy benchmarks must not run on every commit.

Regression tests should catch failures in:

text processing
API contracts
voice packs
pronunciation
streaming
audio formats
engine discovery
routing

When using CI, spend compute on meaningful verification rather than artificial workload.

---

# Our own technology

The long-term goal is not permanent dependence on external TTS engines.

Gradually replace parts of the stack with ours.

A possible evolution is:

external engines
→ our adapters/router
→ our text engine
→ our pronunciation system
→ our prosody representation
→ our voice representation
→ our speaker-related components
→ our decoder/vocoder experiments
→ our acoustic/generative model experiments
→ first real OurTTS model

Do not prematurely train a full model simply to claim ownership.

Build the knowledge and evaluation infrastructure first.

---

# Integration target

OurTTS must eventually be usable independently and from other software.

An external application such as ACE should eventually be able to request something like:

```
generate_voice(
    script,
    voice="brookey",
    quality="best_local",
    style="energetic"
)
```

ACE should not need to know whether Kokoro, Chatterbox, Qwen, OurTTS Nano or another backend produced the result.

OurTTS owns that decision.

---

# Studio target

The future Studio may eventually contain:

waveform editing
segment regeneration
A/B engine comparison
voice library
voice packs
pronunciation dictionary
prosody timeline
style presets
generation history
batch generation
project files
WAV export
other audio export formats
streaming preview
model/backend manager
benchmark viewer
API/plugin access

But do not build all UI features before the Core works.

---

# Research behavior

When encountering an unfamiliar project:

1. Find the official repository and paper/model card.
2. Verify that it is the authoritative source.
3. Inspect current licensing.
4. Understand the architecture.
5. Determine hardware requirements.
6. Determine whether official pretrained weights are available.
7. Determine whether commercial use is allowed.
8. Identify unique features worth testing.
9. Add it to the laboratory only if it contributes useful knowledge or capability.
10. Record why it was accepted or rejected.

Prefer primary sources.

Do not repeat marketing claims as measured facts.

---

# Engineering behavior

Before making a major architectural change, inspect the existing code.

Do not rewrite functioning systems without a reason.

Prefer incremental changes.

Run tests after meaningful changes.

When an experiment fails, preserve useful failure information.

When multiple approaches exist, benchmark them instead of arguing indefinitely.

Explain important architectural decisions and their tradeoffs.

Do not hide technical debt.

Do not claim a component is “ours” when it is merely an unmodified wrapper around someone else's model.

---

# Definition of success

An early successful version is NOT:

“30 models cloned into one repo.”

A successful laboratory looks more like:

```
30 TTS projects investigated
12 engines successfully executed
9 integrated behind stable adapters
8 useful architectural components identified
6 rejected because of licensing
5 rejected because of performance
several techniques independently reimplemented
one stable Core
one benchmark system
one Voice Pack specification
one pronunciation/prosody system
↓
OurTTS V0
```

The exact numbers do not matter.

Evidence, engineering quality, modularity and independence do.

Your job throughout this project is to help us turn a ridiculous multi-repository TTS experiment into a technically serious TTS platform and eventually into genuinely original TTS technology.