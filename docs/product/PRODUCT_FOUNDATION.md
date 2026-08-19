# ourTTS Product Foundation

## Product promise

**Make a voice in seconds. Keep the complexity optional.**

ourTTS should expose a tiny default workflow even when the backend contains many engines, models, controls, caches, and routing rules.

## Current v0.6 implementation

The product path is now executable rather than only conceptual:

```text
text + voice + feel + quality
        ↓
GenerationRequest
        ↓
ourTTS product router
        ↓
verified Core adapter
        ↓
real WAV + manifest
```

Available product surfaces on this branch:

- `ourtts plan` previews the verified route without running a model.
- `ourtts generate` renders a real WAV through the product contract.
- `ourtts-api` starts a local FastAPI service at `127.0.0.1:7860`.
- `/` serves the first lightweight Studio UI from the same local service.
- `/v1/voices` exposes a managed local VoicePack library from `voices/`.
- browser clients pass a stable `voice_id`; they never pass arbitrary filesystem paths.
- generated audio and manifests receive safe opaque artifact IDs and same-origin URLs.

Install the optional local API/Studio dependencies and start it:

```bash
python -m pip install -e ".[dev,api]"
ourtts-api
```

Then open `http://127.0.0.1:7860/`.

The default Studio keeps engine names out of the primary controls. Routing detail is available only under **Why this route?**.

`Best` remains deliberately disabled until a common measured quality score exists. We do not relabel the fastest backend as the best-sounding backend.

## Default generation flow

The first usable Studio fits on one primary screen:

```text
┌──────────────────────────────────────────────────────────────┐
│ ourTTS                                           Local ●     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  What should it say?                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Type or paste your text…                               │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Voice          Language        Feel             Quality     │
│  [ Default ▾ ]  [ English ▾ ]   [ Natural ]      [ Auto ▾ ] │
│                                  [ Energetic ]                │
│                                  [ Calm ]                     │
│                                                              │
│                                      [ ▶ Generate ]          │
├──────────────────────────────────────────────────────────────┤
│  Result                                                      │
│  ▶  ━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0:07               │
│  Why this route? ▸                                           │
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

- `Finding the right route…`
- `Preparing your voice…`
- `Generating your voice…`
- `Ready to play`.

When failure occurs, say what the user can do next:

- `This voice needs a reference clip before it can speak.`
- `Arabic is not supported by the selected local model. Auto can choose another model.`
- `This style control is not available for this voice yet.`

Preserve technical error evidence in diagnostics/logs, not as the primary user message.

## Model selection UX

The default selector is about intent, not implementation:

- **Auto** — choose a verified fit for the request/device
- **Fast** — require measured realtime-or-better CPU generation in the current first policy
- **Best** — reserved for measured quality ranking; currently disabled
- **Local** — request local/offline inference behavior

Model-family names such as Atom, Nano, Core, and Pro may appear in an optional model manager or Expert mode. As owned checkpoints mature, they can become friendly downloadable presets without changing the generation workflow.

## Voice UX

Voice identity and style are separate.

A VoicePack is shown as one voice. A user should not see duplicate entries such as `My Voice - Calm`, `My Voice - Excited`, etc. Style changes how the identity speaks.

The current local library is intentionally simple:

```text
voices/
  my_voice/
    voicepack.json
    refs/
      reference.wav
```

The API validates VoicePack files/hashes before presenting them as ready. The product path keeps unknown-consent references blocked.

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
- audio playback is the visual hero after generation
- no wall of sliders on first load
- subtle motion only when it communicates progress
- mobile usable from the beginning
- light/dark mode follows the operating system automatically in the first Studio

## Implementation milestones

1. Product/model-family manifest + friendly CLI. **Done in v0.6 branch.**
2. Freeze simple generation request/response contract. **Done.**
3. Build a lightweight local API facade over the existing Core. **Done, optional FastAPI extra.**
4. Make one default `auto` path produce real audio through a qualified backend. **Implemented; real-model CI is the acceptance gate.**
5. Add VoicePack selection through the API. **Implemented as managed `voice_id` library.**
6. Build a minimal Studio against that API. **Implemented as the first lightweight local shell.**
7. Validate desktop/mobile behavior and real generation end-to-end. **In progress.**
8. Add quality evaluation so `Best` becomes evidence-backed. **Next.**
9. Add pronunciation repair, prepared voice states, streaming, history/projects, then cloud services.
