# ourTTS Product Foundation

## Product promise

**Make a voice in seconds. Keep the complexity optional.**

ourTTS should expose a tiny default workflow even when the backend contains many engines, models, controls, caches, and routing rules.

## Default generation flow

The first usable Studio should fit on one primary screen:

```text
┌──────────────────────────────────────────────────────────────┐
│ ourTTS                                         Project ▾     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  What should it say?                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Type or paste your text…                               │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Voice                 Feel                  Quality          │
│  [ My voice       ▾ ]   [ Natural ]          [ Auto      ▾ ] │
│                        [ Energetic ]                           │
│                        [ Calm ]                               │
│                                                              │
│                                      [ ▶ Generate ]          │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  Result                                                      │
│  ▶  ━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0:07               │
│  [ Regenerate ] [ Fix pronunciation ] [ More controls ]      │
└──────────────────────────────────────────────────────────────┘
```

A beginner should not need to understand engines, parameter counts, codecs, speaker embeddings, or model routing.

## Progressive disclosure

### Default
- text
- voice
- a few style choices
- quality = Auto
- Generate
- playback

### More controls
- pace
- emphasis
- exact pause
- pronunciation
- language override
- segment regeneration

### Expert
- backend override
- routing explanation
- model/runtime state
- raw metrics
- benchmark comparison
- advanced prosody representation

Expert mode must never be required for ordinary generation.

## Friendly states

Avoid raw stack traces in product UI.

Preferred state language:

- `Getting your voice ready…`
- `Making the first audio…`
- `Almost there…`
- `Ready`.

When failure occurs, say what the user can do next:

- `This voice needs a reference clip before it can speak.`
- `Arabic is not supported by the selected local model. Auto can choose another model.`
- `This style control is not available for this voice yet.`

Preserve technical error evidence in diagnostics/logs, not as the primary user message.

## Model selection UX

The default selector should be about intent, not implementation:

- **Auto** — best fit for the request/device
- **Fast** — prioritize latency
- **Best** — prioritize measured quality
- **Local** — stay offline/local

Model-family names such as Atom, Nano, Core, and Pro may appear in an optional model manager or Expert mode. As owned checkpoints mature, they can become friendly downloadable presets without changing the generation workflow.

## Voice UX

Voice identity and style are separate.

A VoicePack is shown as one voice. A user should not see duplicate entries such as `My Voice - Calm`, `My Voice - Excited`, etc. Style changes how the identity speaks.

Creating a voice should eventually be a guided flow:

1. `Choose a reference` or `Describe a new voice`.
2. Show clear consent/provenance requirement.
3. Analyze/prepare once when supported.
4. Give the voice a friendly name.
5. Save as a VoicePack.
6. Reuse it across compatible backends automatically.

## Pronunciation UX

Pronunciation repair is a first-class experience.

Ideal flow:

1. User highlights a word in text or generated segment.
2. Clicks **Fix pronunciation**.
3. Enters a text spelling or supported phoneme form.
4. Preview only the affected phrase when technically possible.
5. Save correction to the voice/project dictionary.

## Generation result

Every generation should produce a product-level record containing at least:

- project/job id
- input text hash/version
- voice identity id
- requested style/quality
- resolved backend/model revision
- output audio metadata/hash
- timestamps/latency evidence when available
- manifest/provenance reference

The default UI can hide most of this, while Expert mode makes it inspectable.

## Visual direction

- clean and modern rather than 'AI cyberpunk'
- generous spacing
- clear typography
- one strong primary action
- restrained use of accent color
- waveform/audio is the visual hero after generation
- no wall of sliders on first load
- subtle motion only when it communicates progress
- mobile usable from the beginning

## First implementation milestones

1. Product/model-family manifest + friendly CLI (v0.6 foundation).
2. Freeze simple generation request/response contract.
3. Build a lightweight local API facade over the existing Core.
4. Make one default `auto` path produce real audio through a qualified backend.
5. Add VoicePack selection through the API.
6. Build a minimal Studio against that API.
7. Validate desktop and mobile flows.
8. Only then add accounts/history/cloud services and advanced editing.
