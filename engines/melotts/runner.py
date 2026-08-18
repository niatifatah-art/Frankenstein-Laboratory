from __future__ import annotations

import argparse
import json
import sys
import time
import wave
from pathlib import Path


def describe() -> dict[str, object]:
    return {
        "schema_version": 1,
        "engine": "melotts",
        "adapter_version": "0.1.0",
        "capabilities": {
            "cpu": True,
            "multilingual": True,
            "languages": ["EN", "ES", "FR", "ZH", "JP", "KR"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path, default=Path("outputs/melo.wav"))
    parser.add_argument("--language", default="EN")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args(argv)
    if args.describe:
        print(json.dumps(describe()))
        return 0
    if not args.text:
        return 2
    try:
        from melo.api import TTS

        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        load_started = time.perf_counter()
        model = TTS(language=args.language, device=args.device)
        load_seconds = time.perf_counter() - load_started
        speaker = next(iter(model.hps.data.spk2id.values()))
        generation_started = time.perf_counter()
        model.tts_to_file(args.text, speaker, str(output), speed=args.speed, quiet=True)
        generation_seconds = time.perf_counter() - generation_started
        with wave.open(str(output), "rb") as wav:
            sample_rate = wav.getframerate()
            duration = wav.getnframes() / sample_rate
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "engine": "melotts",
                    "output_path": str(output),
                    "sample_rate": sample_rate,
                    "audio_duration_seconds": duration,
                    "model_load_seconds": load_seconds,
                    "generation_seconds": generation_seconds,
                    "total_seconds": time.perf_counter() - started,
                    "generation_real_time_factor": generation_seconds / duration if duration else None,
                    "language": args.language,
                    "device": args.device,
                }
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
