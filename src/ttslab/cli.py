from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .benchmark import benchmark_case, load_corpus, write_result
from .doctor import inspect_environment
from .isolation import execute_worker, run_worker
from .registry import get_engine, load_registry, validate_registry
from .router import RouteRequest, route_engines


def _cmd_list(_: argparse.Namespace) -> int:
    for engine in load_registry():
        print(
            f"{engine.key:22} zone={engine.zone:8} kind={engine.kind:16} "
            f"status={engine.integration_status:16} license={engine.license_status}"
        )
    return 0


def _cmd_doctor(_: argparse.Namespace) -> int:
    report = inspect_environment()
    print(f"python:   {report.python}")
    print(f"platform: {report.platform}")
    print(f"ffmpeg:   {report.ffmpeg or 'NOT FOUND'}")
    print(f"uv:       {report.uv or 'NOT FOUND'}")
    return 0 if report.ok else 2


def _resolve_engine(name: str):
    try:
        return get_engine(name)
    except KeyError:
        print(f"Unknown engine: {name}", file=sys.stderr)
        return None


def _cmd_run(args: argparse.Namespace) -> int:
    engine = _resolve_engine(args.engine)
    if engine is None:
        return 2
    if engine.integration_status != "ready":
        print(
            f"{engine.name} is registered but not production-runnable yet "
            f"(status={engine.integration_status}).",
            file=sys.stderr,
        )
        print("Use the explicit smoke path until a real-model run has passed.", file=sys.stderr)
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
    engine = _resolve_engine(args.engine)
    if engine is None:
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


def _cmd_describe(args: argparse.Namespace) -> int:
    engine = _resolve_engine(args.engine)
    if engine is None:
        return 2
    if not engine.worker:
        print(json.dumps({"engine": engine.key, "worker": None, "record": asdict(engine)}))
        return 0
    try:
        execution = execute_worker(engine.worker, describe=True, extra_args=args.engine_arg)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 5
    if execution.stdout:
        print(execution.stdout, end="")
    if execution.stderr:
        print(execution.stderr, file=sys.stderr, end="")
    return execution.returncode


def _cmd_registry_check(_: argparse.Namespace) -> int:
    errors = validate_registry()
    if not errors:
        print("registry: OK")
        return 0
    for error in errors:
        print(f"registry: {error}", file=sys.stderr)
    return 1


def _cmd_corpus(_: argparse.Namespace) -> int:
    for case in load_corpus():
        print(f"{case.key:20} language={case.language or 'mixed':8} tags={','.join(case.tags)}")
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    engine = _resolve_engine(args.engine)
    if engine is None:
        return 2
    if not engine.worker:
        print(f"{engine.name} has no worker configured.", file=sys.stderr)
        return 4
    try:
        result = benchmark_case(
            engine,
            args.case,
            output_root=args.output_dir,
            engine_args=args.engine_arg,
            timeout_seconds=args.timeout,
        )
    except (KeyError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 5
    result_path = args.result or args.output_dir / f"{engine.key}__{args.case}.json"
    write_result(result, result_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


def _cmd_route(args: argparse.Namespace) -> int:
    request = RouteRequest(
        language=args.language,
        require=tuple(args.require),
        prefer=tuple(args.prefer),
        allow_restricted_commercial_use=args.allow_restricted_commercial_use,
    )
    candidates = route_engines(request)
    if not candidates:
        print("No qualified engine matches the request.", file=sys.stderr)
        return 1
    for item in candidates:
        reason = "; ".join(item.reasons) if item.reasons else "qualified"
        print(f"{item.engine.key:22} score={item.score:3} {reason}")
    return 0


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

    list_parser = sub.add_parser("list", help="List registered TTS engines and components.")
    list_parser.set_defaults(func=_cmd_list)

    doctor_parser = sub.add_parser("doctor", help="Inspect the local runtime.")
    doctor_parser.set_defaults(func=_cmd_doctor)

    check_parser = sub.add_parser("registry-check", help="Validate the engine registry.")
    check_parser.set_defaults(func=_cmd_registry_check)

    corpus_parser = sub.add_parser("corpus", help="List benchmark corpus cases.")
    corpus_parser.set_defaults(func=_cmd_corpus)

    run_parser = sub.add_parser("run", help="Run a verified engine adapter.")
    _add_generation_args(run_parser)
    run_parser.set_defaults(func=_cmd_run)

    smoke_parser = sub.add_parser(
        "smoke", help="Explicitly run an experimental worker before it is promoted to ready."
    )
    _add_generation_args(smoke_parser)
    smoke_parser.set_defaults(func=_cmd_smoke)

    describe_parser = sub.add_parser("describe", help="Query an isolated worker's capabilities.")
    describe_parser.add_argument("engine")
    describe_parser.add_argument("--engine-arg", action="append", default=[])
    describe_parser.set_defaults(func=_cmd_describe)

    benchmark_parser = sub.add_parser("benchmark", help="Run one shared corpus case on an engine.")
    benchmark_parser.add_argument("engine")
    benchmark_parser.add_argument("--case", default="en_basic")
    benchmark_parser.add_argument("--output-dir", type=Path, default=Path("benchmarks/artifacts"))
    benchmark_parser.add_argument("--result", type=Path)
    benchmark_parser.add_argument("--timeout", type=float, default=1800.0)
    benchmark_parser.add_argument("--engine-arg", action="append", default=[])
    benchmark_parser.set_defaults(func=_cmd_benchmark)

    route_parser = sub.add_parser("route", help="Select qualified engines by capability.")
    route_parser.add_argument("--language")
    route_parser.add_argument("--require", action="append", default=[])
    route_parser.add_argument("--prefer", action="append", default=[])
    route_parser.add_argument("--allow-restricted-commercial-use", action="store_true")
    route_parser.set_defaults(func=_cmd_route)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
