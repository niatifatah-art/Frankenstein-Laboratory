from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .doctor import inspect_environment
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
            f"{engine.name} is registered but not runnable yet "
            f"(status={engine.integration_status}).",
            file=sys.stderr,
        )
        print(
            "The laboratory intentionally refuses to fake an integration. "
            "Add and test an isolated adapter before marking it ready.",
            file=sys.stderr,
        )
        return 3

    # Deliberately not pretending a model integration exists before one is tested.
    print(f"Adapter for {engine.name} is marked ready but has no dispatcher.", file=sys.stderr)
    return 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ttslab")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List registered TTS engines.")
    list_parser.set_defaults(func=_cmd_list)

    doctor_parser = sub.add_parser("doctor", help="Inspect the local runtime.")
    doctor_parser.set_defaults(func=_cmd_doctor)

    run_parser = sub.add_parser("run", help="Run a tested isolated engine adapter.")
    run_parser.add_argument("engine")
    run_parser.add_argument("--text", required=True)
    run_parser.add_argument("--output", type=Path, default=Path("tts_output.wav"))
    run_parser.set_defaults(func=_cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
