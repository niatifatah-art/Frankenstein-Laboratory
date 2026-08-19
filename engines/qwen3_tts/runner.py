from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

CUSTOM = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
BASE = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
VOICE_DESIGN = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"


def _engine_key(variant: str) -> str:
    if variant == "voice_design":
        return "qwen3_voice_design_17b"
    return f"qwen3_{variant}_06b"


def describe(variant: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "engine": _engine_key(variant),
        "adapter_version": "0.2.0",
        "capabilities": {
            "multilingual": True,
            "streaming_text_simulation": True,
            "voice_cloning": variant == "base",
            "voice_design": variant == "voice_design",
            "style_control": variant in {"custom", "voice_design"},
            "languages": ["Chinese", "English", "Japanese", "Korean", "German", "French", "Russian", "Portuguese", "Spanish", "Italian"],
        },
    }


def synthesize(args: argparse.Namespace) -> int:
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    model_id = {
        "custom": CUSTOM,
        "base": BASE,
        "voice_design": VOICE_DESIGN,
    }[args.variant]
    started = time.perf_counter()
    load_started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(model_id, device_map=args.device, dtype=torch.bfloat16)
    load_seconds = time.perf_counter() - load_started

    generation_started = time.perf_counter()
    if args.variant == "custom":
        wavs, sample_rate = model.generate_custom_voice(
            text=args.text,
            language=args.language,
            speaker=args.speaker,
            instruct=args.instruct or "",
            max_new_tokens=args.max_new_tokens,
        )
    elif args.variant == "voice_design":
        wavs, sample_rate = model.generate_voice_design(
            text=args.text,
            language=args.language,
            instruct=args.instruct or "A calm, clear adult synthetic voice with neutral pacing.",
            max_new_tokens=args.max_new_tokens,
        )
    else:
        if not args.reference:
            raise ValueError("Base voice-cloning qualification requires --reference")
        wavs, sample_rate = model.generate_voice_clone(
            text=args.text,
            language=args.language,
            ref_audio=str(args.reference.resolve()),
            ref_text=args.reference_text or None,
            x_vector_only_mode=not bool(args.reference_text),
            max_new_tokens=args.max_new_tokens,
        )
    generation_seconds = time.perf_counter() - generation_started
    wav = wavs[0]
    sf.write(output, wav, sample_rate, subtype="PCM_16")
    duration = len(wav) / sample_rate
    print(
        json.dumps(
            {
                "schema_version": 1,
                "engine": _engine_key(args.variant),
                "output_path": str(output),
                "sample_rate": sample_rate,
                "audio_duration_seconds": duration,
                "model_load_seconds": load_seconds,
                "generation_seconds": generation_seconds,
                "total_seconds": time.perf_counter() - started,
                "generation_real_time_factor": generation_seconds / duration if duration else None,
                "model_id": model_id,
                "language": args.language,
                "speaker": args.speaker if args.variant == "custom" else None,
                "instruct": args.instruct if args.variant == "voice_design" else None,
                "device": args.device,
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--variant", choices=["custom", "base", "voice_design"], default="custom")
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen3.wav"))
    parser.add_argument("--language", default="English")
    parser.add_argument("--speaker", default="Ryan")
    parser.add_argument("--instruct", default="")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reference-text", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(describe(args.variant)))
        return 0
    if not args.text:
        print("--text required", file=sys.stderr)
        return 2
    try:
        return synthesize(args)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
