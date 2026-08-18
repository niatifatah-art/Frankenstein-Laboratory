from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCHEMA_VERSION = 1
SAMPLE_RATE = 24_000


def describe() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine": "kokoro",
        "adapter_version": "0.2.0",
        "capabilities": {
            "cpu": True,
            "streaming": True,
            "voice_cloning": False,
            "voice_design": False,
            "raw_phoneme_input": True,
            "phoneme_override": False,
            "languages": ["a", "b", "e", "f", "h", "i", "j", "p", "z"],
        },
        "notes": {
            "raw_phoneme_input": "Uses upstream KPipeline.generate_from_tokens with a complete raw phoneme string.",
            "phoneme_override": "Mixed text + local phoneme replacement is not yet integrated by this adapter.",
        },
    }


def _audio_to_numpy(audio):
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
    from kokoro import KPipeline

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    pipeline = KPipeline(lang_code=args.language)
    model_ready_seconds = time.perf_counter() - started

    if args.phonemes:
        generator = pipeline.generate_from_tokens(
            tokens=args.phonemes,
            voice=args.voice,
            speed=args.speed,
        )
        input_mode = "raw_phonemes"
    else:
        generator = pipeline(
            args.text,
            voice=args.voice,
            speed=args.speed,
            split_pattern=args.split_pattern,
        )
        input_mode = "text"

    chunks = []
    first_audio_seconds = None
    segment_count = 0
    observed_phonemes: list[str] = []
    for result in generator:
        if first_audio_seconds is None:
            first_audio_seconds = time.perf_counter() - started
        audio = getattr(result, "audio", None)
        phonemes = getattr(result, "phonemes", None)
        if audio is None and isinstance(result, tuple):
            _graphemes, phonemes, audio = result
        if audio is None:
            continue
        if phonemes:
            observed_phonemes.append(str(phonemes))
        chunks.append(np.asarray(_audio_to_numpy(audio), dtype=np.float32))
        segment_count += 1

    if not chunks:
        print(json.dumps({"error": "Kokoro produced no audio chunks."}), file=sys.stderr)
        return 5

    waveform = np.concatenate(chunks)
    sf.write(output, waveform, SAMPLE_RATE, subtype="PCM_16")

    total_seconds = time.perf_counter() - started
    audio_duration = len(waveform) / SAMPLE_RATE
    result = {
        "schema_version": SCHEMA_VERSION,
        "engine": "kokoro",
        "output_path": str(output),
        "sample_rate": SAMPLE_RATE,
        "audio_duration_seconds": audio_duration,
        "model_ready_seconds": model_ready_seconds,
        "time_to_first_audio_seconds": first_audio_seconds,
        "total_generation_seconds": total_seconds,
        "real_time_factor": total_seconds / audio_duration if audio_duration else None,
        "segments": segment_count,
        "voice": args.voice,
        "language": args.language,
        "speed": args.speed,
        "input_mode": input_mode,
        "observed_phonemes": observed_phonemes,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Isolated Kokoro worker for Frankenstein Laboratory.")
    parser.add_argument("--describe", action="store_true")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text")
    source.add_argument("--phonemes")
    parser.add_argument("--output", type=Path, default=Path("outputs/kokoro.wav"))
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--language", default="a")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--split-pattern", default=r"\n+")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(describe(), ensure_ascii=False))
        return 0
    if not args.text and not args.phonemes:
        print("--text or --phonemes is required unless --describe is used.", file=sys.stderr)
        return 2
    return synthesize(args)


if __name__ == "__main__":
    raise SystemExit(main())
