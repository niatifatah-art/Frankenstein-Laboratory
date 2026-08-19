from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCHEMA_VERSION = 1
ADAPTER_VERSION = "0.2.0"
UPSTREAM_REVISION = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
STATE_FORMAT = "chatterbox-conditionals-pt-v1"


def describe(variant: str) -> dict[str, object]:
    caps = {
        "base": {
            "cpu": True,
            "voice_cloning": True,
            "voice_cache": True,
            "style_control": True,
            "languages": ["en"],
        },
        "nano": {
            "cpu": True,
            "voice_cloning": True,
            "voice_cache": True,
            "paralinguistic_tags": True,
            "languages": ["en"],
        },
        "turbo": {
            "cpu": True,
            "voice_cloning": True,
            "voice_cache": True,
            "paralinguistic_tags": True,
            "languages": ["en"],
        },
        "v3": {
            "cpu": True,
            "voice_cloning": True,
            "voice_cache": True,
            "multilingual": True,
            "languages": [
                "ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi", "it",
                "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv", "sw", "tr", "zh",
            ],
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "engine": f"chatterbox_{variant}",
        "adapter_version": ADAPTER_VERSION,
        "upstream_revision": UPSTREAM_REVISION,
        "voice_state_format": STATE_FORMAT,
        "capabilities": caps[variant],
        "watermark": "PerTh upstream watermark",
    }


def _numpy(wav):
    if hasattr(wav, "detach"):
        wav = wav.detach()
    if hasattr(wav, "cpu"):
        wav = wav.cpu()
    if hasattr(wav, "numpy"):
        wav = wav.numpy()
    return wav


def _load_model(args: argparse.Namespace):
    if args.variant in {"nano", "turbo"}:
        from chatterbox.tts_turbo import ChatterboxTurboTTS, Conditionals

        model = ChatterboxTurboTTS.from_pretrained(
            device=args.device,
            nano=args.variant == "nano",
        )
    elif args.variant == "v3":
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals

        model = ChatterboxMultilingualTTS.from_pretrained(device=args.device, t3_model="v3")
    else:
        from chatterbox.tts import ChatterboxTTS, Conditionals

        model = ChatterboxTTS.from_pretrained(device=args.device)
    return model, Conditionals


def prepare_voice(args: argparse.Namespace) -> int:
    if args.reference is None:
        raise ValueError("--prepare-voice requires --reference")
    if args.state_output is None:
        raise ValueError("--prepare-voice requires --state-output")

    state_output = args.state_output.resolve()
    state_output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    load_started = time.perf_counter()
    model, _conditionals = _load_model(args)
    load_seconds = time.perf_counter() - load_started

    prepare_started = time.perf_counter()
    model.prepare_conditionals(str(args.reference.resolve()), exaggeration=args.exaggeration)
    prepare_seconds = time.perf_counter() - prepare_started
    if model.conds is None:
        raise RuntimeError("Chatterbox did not produce voice conditionals")
    model.conds.save(state_output)

    print(
        json.dumps(
            {
                "schema_version": 1,
                "operation": "prepare_voice",
                "engine": f"chatterbox_{args.variant}",
                "adapter_version": ADAPTER_VERSION,
                "state_path": str(state_output),
                "state_format": STATE_FORMAT,
                "upstream_revision": UPSTREAM_REVISION,
                "model_load_seconds": load_seconds,
                "voice_prepare_seconds": prepare_seconds,
                "total_seconds": time.perf_counter() - started,
                "reference": str(args.reference.resolve()),
                "device": args.device,
            },
            ensure_ascii=False,
        )
    )
    return 0


def synthesize(args: argparse.Namespace) -> int:
    import numpy as np
    import soundfile as sf

    if args.reference is not None and args.voice_state is not None:
        raise ValueError("--reference and --voice-state are mutually exclusive")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    load_started = time.perf_counter()
    model, conditionals_cls = _load_model(args)
    load_seconds = time.perf_counter() - load_started

    state_load_seconds = None
    if args.voice_state is not None:
        state_started = time.perf_counter()
        model.conds = conditionals_cls.load(
            args.voice_state.resolve(),
            map_location=args.device,
        ).to(args.device)
        state_load_seconds = time.perf_counter() - state_started

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
        "adapter_version": ADAPTER_VERSION,
        "output_path": str(output),
        "sample_rate": sample_rate,
        "audio_duration_seconds": duration,
        "model_load_seconds": load_seconds,
        "voice_state_load_seconds": state_load_seconds,
        "generation_seconds": generation_seconds,
        "total_seconds": time.perf_counter() - started,
        "generation_real_time_factor": generation_seconds / duration if duration else None,
        "variant": args.variant,
        "language": args.language,
        "reference": str(args.reference) if args.reference else None,
        "voice_state": str(args.voice_state) if args.voice_state else None,
        "voice_state_format": STATE_FORMAT if args.voice_state else None,
        "upstream_revision": UPSTREAM_REVISION,
        "device": args.device,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--prepare-voice", action="store_true")
    parser.add_argument("--variant", choices=["base", "nano", "turbo", "v3"], default="nano")
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path, default=Path("outputs/chatterbox.wav"))
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--state-output", type=Path)
    parser.add_argument("--voice-state", type=Path)
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
    try:
        if args.prepare_voice:
            return prepare_voice(args)
        if not args.text:
            print("--text is required", file=sys.stderr)
            return 2
        return synthesize(args)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
