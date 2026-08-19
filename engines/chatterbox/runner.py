from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCHEMA_VERSION = 1


def describe(variant: str) -> dict[str, object]:
    caps = {
        "base": {"cpu": True, "voice_cloning": True, "style_control": True, "languages": ["en"]},
        "nano": {"cpu": True, "voice_cloning": True, "paralinguistic_tags": True, "languages": ["en"]},
        "turbo": {"cpu": True, "voice_cloning": True, "paralinguistic_tags": True, "languages": ["en"]},
        "v3": {"cpu": True, "voice_cloning": True, "multilingual": True, "languages": ["ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi", "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv", "sw", "tr", "zh"]},
    }
    return {"schema_version": SCHEMA_VERSION, "engine": f"chatterbox_{variant}", "adapter_version": "0.1.0", "capabilities": caps[variant], "watermark": "PerTh upstream watermark"}


def _numpy(wav):
    if hasattr(wav, "detach"):
        wav = wav.detach()
    if hasattr(wav, "cpu"):
        wav = wav.cpu()
    if hasattr(wav, "numpy"):
        wav = wav.numpy()
    return wav


def synthesize(args: argparse.Namespace) -> int:
    import numpy as np
    import soundfile as sf

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    load_started = time.perf_counter()
    if args.variant in {"nano", "turbo"}:
        from chatterbox.tts_turbo import ChatterboxTurboTTS

        model = ChatterboxTurboTTS.from_pretrained(device=args.device, nano=args.variant == "nano")
    elif args.variant == "v3":
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        model = ChatterboxMultilingualTTS.from_pretrained(device=args.device, t3_model="v3")
    else:
        from chatterbox.tts import ChatterboxTTS

        model = ChatterboxTTS.from_pretrained(device=args.device)
    load_seconds = time.perf_counter() - load_started

    generation_started = time.perf_counter()
    kwargs = {}
    if args.reference:
        kwargs["audio_prompt_path"] = str(args.reference.resolve())
    if args.variant == "v3":
        kwargs["language_id"] = args.language
    elif args.variant == "base":
        kwargs.update(exaggeration=args.exaggeration, cfg_weight=args.cfg_weight)
    wav = model.generate(args.text, **kwargs)
    generation_seconds = time.perf_counter() - generation_started
    audio = np.asarray(_numpy(wav), dtype=np.float32).squeeze()
    sample_rate = int(model.sr)
    sf.write(output, audio, sample_rate, subtype="PCM_16")
    duration = len(audio) / sample_rate
    result = {
        "schema_version": 1,
        "engine": f"chatterbox_{args.variant}",
        "output_path": str(output),
        "sample_rate": sample_rate,
        "audio_duration_seconds": duration,
        "model_load_seconds": load_seconds,
        "generation_seconds": generation_seconds,
        "total_seconds": time.perf_counter() - started,
        "generation_real_time_factor": generation_seconds / duration if duration else None,
        "variant": args.variant,
        "language": args.language,
        "reference": str(args.reference) if args.reference else None,
        "device": args.device,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--variant", choices=["base", "nano", "turbo", "v3"], default="nano")
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path, default=Path("outputs/chatterbox.wav"))
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--language", default="en")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--exaggeration", type=float, default=0.5)
    parser.add_argument("--cfg-weight", type=float, default=0.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(describe(args.variant), ensure_ascii=False))
        return 0
    if not args.text:
        print("--text is required", file=sys.stderr)
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
