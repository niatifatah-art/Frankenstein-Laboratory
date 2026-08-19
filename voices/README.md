# ourTTS local voice library

Put one VoicePack in each subdirectory of this folder:

```text
voices/
  my_voice/
    voicepack.json
    refs/
      reference.wav
```

The Studio reads `/v1/voices` and shows only VoicePacks that validate successfully. Browser clients never send arbitrary filesystem paths; they send the stable `voice_id`, and the local API resolves that ID inside this managed directory.

Reference clips must keep explicit provenance/consent metadata and valid hashes. Unknown-consent references stay blocked by the product path.
