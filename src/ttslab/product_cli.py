from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .product import MODEL_FAMILY, PRODUCT_NAME, PRODUCT_TAGLINE, model_profile, product_manifest
from .product_contract import GenerationRequest
from .product_runtime import generate, plan_generation
from .voice_prepare import prepare_voicepack_state
from .voicepack import VoicePack


def _human_family() -> str:
    lines = [
        f"{PRODUCT_NAME} — {PRODUCT_TAGLINE}",
        "",
        "Model family (targets, not released checkpoints):",
    ]
    for profile in MODEL_FAMILY:
        size = (
            f"~{profile.target_parameters_millions}M params / ~{profile.target_weight_mb_fp16} MB FP16"
            if profile.target_parameters_millions is not None
            else "architecture/size decided by evidence"
        )
        lines.append(f"  {profile.display_name:16} {size}")
        lines.append(f"    {profile.purpose}")
    lines.extend(
        [
            "",
            "Try: ourtts plan --text \"Hello world\" --language en",
            "Then: ourtts generate --text \"Hello world\" --language en --output hello.wav",
            "",
            "Rule: training completion is not a release. Each checkpoint must pass its target baseline.",
        ]
    )
    return "\n".join(lines)


def _parse_controls(values: list[str]) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"control must be key=value: {raw!r}")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("control key must not be empty")
        try:
            controls[key] = json.loads(value)
        except json.JSONDecodeError:
            controls[key] = value
    return controls


def _add_request_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text", required=True, help="What should ourTTS say?")
    parser.add_argument("--voice", help="Product VoicePack identity, not a backend-specific voice name.")
    parser.add_argument("--voicepack", type=Path, help="Local VoicePack directory for this identity.")
    parser.add_argument("--language", help="Language hint such as en, fr, es, ru, ar.")
    parser.add_argument(
        "--style",
        default="natural",
        help="Natural by default; other styles route only when verified.",
    )
    parser.add_argument(
        "--quality",
        choices=("auto", "fast", "best", "local"),
        default="auto",
        help="Keep it simple: Auto, Fast, Best (after quality evidence), or Local.",
    )
    parser.add_argument("--offline", action="store_true", help="Request local/offline inference.")
    parser.add_argument(
        "--control",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional expert normalized control. Repeat for more controls.",
    )


def _request_from_args(args: argparse.Namespace) -> GenerationRequest:
    return GenerationRequest(
        text=args.text,
        voice=args.voice,
        language=args.language,
        style=args.style,
        quality=args.quality,
        offline=bool(args.offline),
        controls=_parse_controls(args.control),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ourtts", description="ourTTS — simple speech creation")
    parser.add_argument("--json", action="store_true", help="Print the product manifest as JSON.")
    parser.add_argument("--model", help="Show one model-family target, e.g. atom or core.")

    sub = parser.add_subparsers(dest="command")

    plan_parser = sub.add_parser(
        "plan",
        help="Preview the verified Auto route without generating audio.",
    )
    _add_request_args(plan_parser)
    plan_parser.add_argument("--json", action="store_true", dest="command_json")

    generate_parser = sub.add_parser(
        "generate",
        help="Generate a real WAV through the verified ourTTS product path.",
    )
    _add_request_args(generate_parser)
    generate_parser.add_argument("--output", type=Path, default=Path("ourtts.wav"))
    generate_parser.add_argument("--manifest", type=Path)
    generate_parser.add_argument("--timeout", type=float, default=1800.0)
    generate_parser.add_argument("--json", action="store_true", dest="command_json")

    voice_parser = sub.add_parser("voice", help="Inspect or prepare a reusable VoicePack identity.")
    voice_sub = voice_parser.add_subparsers(dest="voice_command", required=True)

    voice_prepare = voice_sub.add_parser(
        "prepare",
        help="Prepare a reusable backend voice state once instead of reprocessing its reference.",
    )
    voice_prepare.add_argument("voicepack", type=Path)
    voice_prepare.add_argument(
        "--engine",
        default="chatterbox_nano",
        choices=(
            "chatterbox_nano",
            "chatterbox_base",
            "chatterbox_turbo",
            "chatterbox_v3",
        ),
        help="Explicit preparation backend. Normal generation still uses Auto routing.",
    )
    voice_prepare.add_argument("--timeout", type=float, default=1800.0)
    voice_prepare.add_argument("--json", action="store_true", dest="command_json")

    voice_inspect = voice_sub.add_parser("inspect", help="Show one VoicePack identity and cached states.")
    voice_inspect.add_argument("voicepack", type=Path)
    voice_inspect.add_argument("--json", action="store_true", dest="command_json")
    return parser


def _show_model(args: argparse.Namespace) -> int:
    try:
        profile = model_profile(args.model)
    except KeyError:
        choices = ", ".join(item.key for item in MODEL_FAMILY)
        parser = build_parser()
        parser.error(f"unknown model {args.model!r}; choose one of: {choices}")
    payload = profile.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{profile.display_name}\n{profile.purpose}")
        print("priorities: " + ", ".join(profile.priority))
        print(f"status: {profile.status}")
    return 0


def _voice_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.voice_command == "prepare":
        try:
            result = prepare_voicepack_state(
                args.voicepack,
                args.engine,
                timeout_seconds=args.timeout,
            )
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        payload = result.to_dict()
        if args.command_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Prepared {result.voice_id} for fast reuse with {result.engine}.")
            print(f"state: {result.state_path}")
            print(f"sha256: {result.sha256}")
        return 0

    pack = VoicePack.load(args.voicepack.resolve())
    payload = {
        "voice_id": pack.voice_id,
        "display_name": pack.display_name,
        "languages": list(pack.languages),
        "references": len(pack.references),
        "styles": sorted(pack.style_presets),
        "backend_states": [
            {
                "engine": state.engine,
                "path": state.path,
                "format": state.format,
                "model_revision": state.model_revision,
                "sha256": state.sha256,
            }
            for state in pack.backend_states
        ],
        "errors": list(pack.validate_files(args.voicepack.resolve(), verify_hashes=True)),
    }
    if args.command_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{pack.display_name} ({pack.voice_id})")
        print("languages: " + (", ".join(pack.languages) or "unspecified"))
        print(f"references: {len(pack.references)}")
        print("prepared: " + (", ".join(state.engine for state in pack.backend_states) or "none"))
        if payload["errors"]:
            print("problems: " + "; ".join(payload["errors"]))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        try:
            plan = plan_generation(_request_from_args(args), voicepack_root=args.voicepack)
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        payload = plan.to_dict()
        if args.command_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"ourTTS will use: {plan.engine}")
            print("why: " + "; ".join(plan.routing_reasons))
            if plan.voice_id:
                print(f"voice: {plan.voice_id}")
            if plan.voice_state:
                print("voice preparation: cached state")
            if plan.controls:
                print("verified controls: " + ", ".join(sorted(plan.controls)))
        return 0

    if args.command == "generate":
        try:
            result = generate(
                _request_from_args(args),
                args.output,
                voicepack_root=args.voicepack,
                manifest_path=args.manifest,
                timeout_seconds=args.timeout,
            )
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        payload = result.to_dict()
        if args.command_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Done — {result.output_path}")
            print(f"engine: {result.engine} (chosen by ourTTS)")
            print("why: " + "; ".join(result.routing_reasons))
            print(f"manifest: {result.manifest_path}")
        return 0

    if args.command == "voice":
        return _voice_command(args, parser)

    if args.model:
        return _show_model(args)
    if args.json:
        print(json.dumps(product_manifest(), ensure_ascii=False, indent=2))
    else:
        print(_human_family())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
