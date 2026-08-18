from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .doctor import inspect_environment
from .isolation import run_worker
from .registry import get_engine, load_registry


def _cmd_list(_: argparse.Namespace) -> int:
    for engine in load_registry():
        print(
            f"{engine.key:14} zone={engine.zone:8} status={engine.integration_status:12} "
            f"license={engine.license_status}"
        )
    return 0


def _cmd_doctor(_: argparse.Namespace) -> int:
    report = inspect_environment()
    print(f"python:   {report.python}")
    print(f"platform: {report.platform}")
    print(f"ffmpeg:   {report.ffmpeg or 'NOT FOUND'}")
    print(f"uv:       {report.uv or 'NOT FOUND'}")
    return 0 if report.ok else 2


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        engine = get_engine(args.engine)
    except KeyError:
        print(f"Unknown engine: {args.engine}", file=sys.stderr)
        return 2

    if engine.integration_status != "ready":
        print(
            f"{engine.name} is registered but not production-runnable yet "
            f"(status={engine.integration_status}).",
            file=sys.stderr,
        )
        print(
            "Use the explicit experimental smoke path until a real-model run has passed.",
            file=sys.stderr,
        )
        return 3

    if not engine.worker:
        print(f"{engine.name} has no isolated worker configured.", file=sys.stderr)
        return 4

    try:
        return run_worker(
            engine.worker,
            text=args.text,
            output=args.output,
            extra_args=args.engine_arg,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 5


def _cmd_smoke(args: argparse.Namespace) -> int:
    try:
        engine = get_engine(args.engine)
    except KeyError:
        print(f"Unknown engine: {args.engine}", file=sys.stderr)
        return 2
    if not engine.worker:
        print(f"{engine.name} has no isolated worker configured.", file=sys.stderr)
        return 4
    try:
        return run_worker(
            engine.worker,
            text=args.text,
            output=args.output,
            extra_args=args.engine_arg,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 5


def _add_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("engine")
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", type=Path, default=Path("tts_output.wav"))
    parser.add_argument(
        "--engine-arg",
        action="append",
        default=[],
        help="Pass one raw argument to the isolated worker. Repeat for multiple arguments.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ttslab")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List registered TTS engines.")
    list_parser.set_defaults(func=_cmd_list)

    doctor_parser = sub.add_parser("doctor", help="Inspect the local runtime.")
    doctor_parser.set_defaults(func=_cmd_doctor)

    run_parser = sub.add_parser("run", help="Run a verified engine adapter.")
    _add_generation_args(run_parser)
    run_parser.set_defaults(func=_cmd_run)

    smoke_parser = sub.add_parser(
        "smoke",
        help="Explicitly run an experimental worker before it is promoted to ready.",
    )
    _add_generation_args(smoke_parser)
    smoke_parser.set_defaults(func=_cmd_smoke)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
