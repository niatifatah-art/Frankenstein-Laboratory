from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_VOICE = "alba"


def describe() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine": "pocket_tts",
        "adapter_version": "0.1.0",
        "capabilities": {
            "cpu": True,
            "streaming": True,
            "voice_cloning": True,
            "voice_design": False,
            "phoneme_input": False,
            "long_form": True,
            "languages": [
                "english",
                "french_24l",
                "german_24l",
                "portuguese",
                "italian",
                "spanish_24l",
            ],
        },
        "notes": {
            "voice_cloning": "Full cloning weights are access-gated upstream; predefined voices remain usable with the fallback model.",
            "voice_assets": "Voice assets have licenses separate from the code/model weights.",
        },
    }


def _to_numpy(audio):
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "numpy"):
        audio = audio.numpy()
    return audio


def synthesize(args: argparse.Namespace) -> int:
    import numpy as np
    import soundfile as sf
    from pocket_tts import TTSModel

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    cold_started = time.perf_counter()
    model_started = time.perf_counter()
    model = TTSModel.load_model(language=args.language, quantize=args.quantize)
    model_load_seconds = time.perf_counter() - model_started

    voice_started = time.perf_counter()
    voice_state = model.get_state_for_audio_prompt(args.voice)
    voice_prepare_seconds = time.perf_counter() - voice_started

    generation_started = time.perf_counter()
    first_audio_seconds = None
    chunks = []
    for chunk in model.generate_audio_stream(voice_state, args.text):
        if first_audio_seconds is None:
            first_audio_seconds = time.perf_counter() - generation_started
        chunks.append(np.asarray(_to_numpy(chunk), dtype=np.float32))

    generation_seconds = time.perf_counter() - generation_started
    total_seconds = time.perf_counter() - cold_started

    if not chunks:
        print(json.dumps({"error": "Pocket TTS produced no audio chunks."}), file=sys.stderr)
        return 5

    waveform = np.concatenate(chunks)
    sample_rate = int(model.sample_rate)
    sf.write(output, waveform, sample_rate, subtype="PCM_16")
    audio_duration = len(waveform) / sample_rate

    result = {
        "schema_version": SCHEMA_VERSION,
        "engine": "pocket_tts",
        "output_path": str(output),
        "sample_rate": sample_rate,
        "audio_duration_seconds": audio_duration,
        "model_load_seconds": model_load_seconds,
        "voice_prepare_seconds": voice_prepare_seconds,
        "time_to_first_audio_seconds": first_audio_seconds,
        "generation_seconds": generation_seconds,
        "total_seconds": total_seconds,
        "generation_real_time_factor": generation_seconds / audio_duration if audio_duration else None,
        "cold_real_time_factor": total_seconds / audio_duration if audio_duration else None,
        "chunks": len(chunks),
        "voice": args.voice,
        "language": args.language,
        "quantize": args.quantize,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Isolated Pocket TTS worker for Frankenstein Laboratory."
    )
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path, default=Path("outputs/pocket-tts.wav"))
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--language", default="english")
    parser.add_argument("--quantize", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(describe(), ensure_ascii=False))
        return 0
    if not args.text:
        print("--text is required unless --describe is used.", file=sys.stderr)
        return 2
    return synthesize(args)


if __name__ == "__main__":
    raise SystemExit(main())
