# OurTTS v0.4 product path

```text
user / ACE / Studio
        |
        v
SynthesisRequest
        |
        +--> rights + VoicePack resolution
        +--> neutral control parser
        +--> pronunciation lexicon
        +--> profile + device + capability router
        |
        v
adapter-argument compiler
        |
        v
isolated qualified worker
        |
        +--> validated PCM segments
        |
        v
owned exact-pause audio timeline
        |
        v
content-addressed cache + provenance result
        |
        v
WAV
```

The product boundary never imports upstream model packages into the Core environment. Workers remain
isolated. `qualified_external` records real inference evidence that lacks a stable worker, while
`ready` is reserved for product-routable isolated workers.

## Deliberate limits

v0.4 does not claim universal phoneme syntax, universal emotion conversion, or objective quality
leadership. Kokoro has a verified phoneme compiler. Inline Chatterbox Nano/Turbo nonverbal tags have a
small verified allow-list. Other neutral controls remain explicit until a backend compiler or owned
post-processor is tested.
