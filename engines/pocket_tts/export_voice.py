from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a Pocket TTS voice state for fast reuse.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--reference", type=Path)
    source.add_argument("--catalog-voice")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="english")
    args = parser.parse_args(argv)

    from pocket_tts import TTSModel, export_model_state

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    model = TTSModel.load_model(language=args.language)
    prompt = args.catalog_voice or str(args.reference.resolve())
    state = model.get_state_for_audio_prompt(prompt)
    export_model_state(state, str(output))
    print(
        json.dumps(
            {
                "schema_version": 1,
                "engine": "pocket_tts",
                "language": args.language,
                "source_kind": "catalog_voice" if args.catalog_voice else "reference_audio",
                "source": args.catalog_voice or str(args.reference.resolve()),
                "output_path": str(output),
                "sha256": _sha256(output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
