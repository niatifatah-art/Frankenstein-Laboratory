from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def describe() -> dict[str, object]:
    return {
        "schema_version": 1,
        "engine": "voxcpm2",
        "adapter_version": "0.4.0",
        "capabilities": {
            "multilingual": True,
            "streaming": True,
            "voice_cloning": True,
            "voice_design": True,
            "style_control": True,
            "sample_rate": 48000,
        },
    }


def _designed_text(text: str, instruction: str | None) -> str:
    if not instruction:
        return text
    return f"({instruction.strip()}){text}"


def synthesize(args: argparse.Namespace) -> int:
    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    load_started = time.perf_counter()
    model = VoxCPM.from_pretrained(
        "openbmb/VoxCPM2",
        load_denoiser=False,
        optimize=False,
        device=args.device,
    )
    load_seconds = time.perf_counter() - load_started
    torch.manual_seed(args.seed)
    generation_started = time.perf_counter()
    kwargs: dict[str, object] = {
        "text": _designed_text(args.text, args.voice_design),
        "cfg_value": args.cfg,
        "inference_timesteps": args.steps,
        "max_len": args.max_len,
        "normalize": True,
        "denoise": False,
        "retry_badcase": False,
    }
    if args.reference:
        reference = str(args.reference.resolve())
        kwargs["reference_wav_path"] = reference
        if args.reference_text:
            kwargs["prompt_wav_path"] = reference
            kwargs["prompt_text"] = args.reference_text
    wav = model.generate(**kwargs)
    generation_seconds = time.perf_counter() - generation_started
    sample_rate = int(model.tts_model.sample_rate)
    sf.write(output, wav, sample_rate, subtype="PCM_16")
    duration = len(wav) / sample_rate
    print(
        json.dumps(
            {
                "schema_version": 1,
                "engine": "voxcpm2",
                "output_path": str(output),
                "sample_rate": sample_rate,
                "audio_duration_seconds": duration,
                "model_load_seconds": load_seconds,
                "generation_seconds": generation_seconds,
                "total_seconds": time.perf_counter() - started,
                "generation_real_time_factor": generation_seconds / duration if duration else None,
                "device": args.device,
                "steps": args.steps,
                "seed": args.seed,
                "voice_design": args.voice_design,
                "reference": str(args.reference) if args.reference else None,
                "ultimate_clone": bool(args.reference and args.reference_text),
                "denoiser_loaded": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path, default=Path("outputs/voxcpm2.wav"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--cfg", type=float, default=2.0)
    parser.add_argument("--max-len", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reference-text", default="")
    parser.add_argument("--voice-design", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(describe()))
        return 0
    if not args.text:
        return 2
    try:
        return synthesize(args)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
