from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .batch import run_batch
from .hardware import detect_device
from .profiles import list_profiles
from .registry import load_registry
from .synthesis import SynthesisRequest, synthesize
from .voice_state import export_voicepack_state


def _parse_control(values: list[str]) -> dict[str, object]:
    controls: dict[str, object] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Control must be key=value: {raw!r}")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Control key must not be empty.")
        try:
            controls[key] = json.loads(value)
        except json.JSONDecodeError:
            controls[key] = value
    return controls


def _cmd_profiles(_: argparse.Namespace) -> int:
    for profile in list_profiles():
        print(f"{profile.key:16} {profile.description}")
    return 0


def _cmd_engines(_: argparse.Namespace) -> int:
    for engine in load_registry():
        if not engine.runnable or engine.kind != "tts":
            continue
        rtf = f"{engine.cpu_generation_rtf:.2f}" if engine.cpu_generation_rtf is not None else "?"
        caps = ",".join(engine.capabilities) or "-"
        print(f"{engine.key:24} cpu_rtf={rtf:>6} caps={caps}")
    return 0


def _cmd_speak(args: argparse.Namespace) -> int:
    try:
        request = SynthesisRequest(
            text=args.text,
            output=args.output,
            language=args.language,
            engine=args.engine,
            profile=args.profile,
            voice=args.voice,
            reference=args.reference,
            reference_text=args.reference_text,
            reference_consent=args.reference_consent,
            voice_design=args.voice_design,
            style=args.style,
            speed=args.speed,
            device=args.device,
            lexicon=args.lexicon,
            voicepack_root=args.voicepack,
            controls=_parse_control(args.control),
            allow_unknown_voice_rights=args.allow_unknown_voice_rights,
            allow_restricted_models=args.allow_restricted_models,
            allow_degraded=args.allow_degraded,
            use_cache=not args.no_cache,
            cache_dir=args.cache_dir,
            timeout_seconds=args.timeout,
            engine_args=tuple(args.engine_arg),
        )
        result = synthesize(request)
    except Exception as exc:  # noqa: BLE001 - CLI should return a clean boundary error
        print(f"ourtts: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    try:
        result = run_batch(
            args.manifest,
            output_root=args.output_root,
            fail_fast=args.fail_fast,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ourtts: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["failed"] == 0 else 1


def _cmd_doctor(_: argparse.Namespace) -> int:
    print(json.dumps({"detected_device": detect_device()}))
    return 0


def _cmd_voice_state(args: argparse.Namespace) -> int:
    try:
        state = export_voicepack_state(
            args.voicepack, engine_key=args.engine, language=args.language
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ourtts: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(state), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ourtts",
        description="One product-facing interface over qualified Frankenstein Laboratory TTS backends.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("profiles", help="List human-friendly routing profiles.").set_defaults(
        func=_cmd_profiles
    )
    sub.add_parser("engines", help="List qualified runnable TTS engines.").set_defaults(
        func=_cmd_engines
    )
    sub.add_parser("doctor", help="Show the lightweight detected accelerator.").set_defaults(
        func=_cmd_doctor
    )

    speak = sub.add_parser("speak", help="Generate speech through the safe unified OurTTS path.")
    speak.add_argument("--text", required=True)
    speak.add_argument("--output", type=Path, required=True)
    speak.add_argument("--language")
    speak.add_argument("--engine")
    speak.add_argument("--profile", default="auto")
    speak.add_argument("--voice")
    speak.add_argument("--reference", type=Path)
    speak.add_argument("--reference-text")
    speak.add_argument(
        "--reference-consent",
        choices=["owned", "licensed", "consented", "synthetic", "unknown"],
        default="unknown",
    )
    speak.add_argument("--allow-unknown-voice-rights", action="store_true")
    speak.add_argument(
        "--allow-restricted-models",
        action="store_true",
        help="Explicitly permit a runtime whose commercial-use state is not in the safe default set.",
    )
    speak.add_argument("--voice-design")
    speak.add_argument("--style")
    speak.add_argument("--speed", type=float)
    speak.add_argument(
        "--device", default=None, help="auto/cpu/cuda/mps; profile default is used when omitted"
    )
    speak.add_argument("--lexicon", type=Path)
    speak.add_argument("--voicepack", type=Path)
    speak.add_argument("--control", action="append", default=[], help="Generic key=value control.")
    speak.add_argument(
        "--allow-degraded",
        action="store_true",
        help="Allow explicitly reported unsupported controls.",
    )
    speak.add_argument("--no-cache", action="store_true")
    speak.add_argument("--cache-dir", type=Path)
    speak.add_argument("--timeout", type=float, default=1800.0)
    speak.add_argument(
        "--engine-arg", action="append", default=[], help="Advanced raw worker argument."
    )
    speak.set_defaults(func=_cmd_speak)

    batch = sub.add_parser(
        "batch", help="Run a JSON manifest of many voices/jobs through the same safe path."
    )
    batch.add_argument("manifest", type=Path)
    batch.add_argument("--output-root", type=Path)
    batch.add_argument("--fail-fast", action="store_true")
    batch.set_defaults(func=_cmd_batch)

    voice_state = sub.add_parser(
        "voice-state",
        help="Build a reusable backend state inside a VoicePack (Pocket TTS is verified in v0.4).",
    )
    voice_state.add_argument("--voicepack", type=Path, required=True)
    voice_state.add_argument("--engine", default="pocket_tts")
    voice_state.add_argument("--language")
    voice_state.set_defaults(func=_cmd_voice_state)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
