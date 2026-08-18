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
        "adapter_version": "0.1.0",
        "capabilities": {
            "multilingual": True,
            "streaming": True,
            "voice_cloning": True,
            "voice_design": True,
            "sample_rate": 16000,
        },
    }


def synthesize(args: argparse.Namespace) -> int:
    import soundfile as sf
    from voxcpm import VoxCPM

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    load_started = time.perf_counter()
    model = VoxCPM.from_pretrained("openbmb/VoxCPM2", optimize=False, device=args.device)
    load_seconds = time.perf_counter() - load_started
    generation_started = time.perf_counter()
    kwargs = dict(
        text=args.text,
        cfg_value=args.cfg,
        inference_timesteps=args.steps,
        max_len=args.max_len,
        normalize=True,
        denoise=False,
        retry_badcase=False,
    )
    if args.reference:
        kwargs["reference_wav_path"] = str(args.reference.resolve())
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
    parser.add_argument("--reference", type=Path)
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
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
