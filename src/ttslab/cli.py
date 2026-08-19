from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .benchmark import benchmark_case, load_corpus, write_result
from .doctor import inspect_environment
from .isolation import execute_worker, run_worker
from .pipeline import build_synthesis_plan
from .pronunciation import PronunciationLexicon
from .prosody import ProsodyTimeline, parse_control_markup
from .registry import get_engine, load_registry, validate_registry
from .rendering import render_text
from .router import RouteRequest, route_engines
from .text_engine import prepare_text
from .voicepack import VoicePack


def _cmd_list(_: argparse.Namespace) -> int:
    for engine in load_registry():
        rtf = f"{engine.cpu_generation_rtf:.3f}" if engine.cpu_generation_rtf is not None else "unknown"
        print(
            f"{engine.key:24} zone={engine.zone:8} kind={engine.kind:16} "
            f"status={engine.integration_status:19} cpu_rtf={rtf:8} "
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
        max_generation_rtf=args.max_generation_rtf,
    )
    candidates = route_engines(request)
    if not candidates:
        print("No qualified engine matches the request.", file=sys.stderr)
        return 1
    for item in candidates:
        reason = "; ".join(item.reasons) if item.reasons else "qualified"
        print(f"{item.engine.key:24} score={item.score:3} {reason}")
    return 0


def _load_lexicon(path: Path | None) -> PronunciationLexicon | None:
    return PronunciationLexicon.from_json(path) if path else None


def _cmd_text(args: argparse.Namespace) -> int:
    lexicon = _load_lexicon(args.lexicon)
    clean, markers = parse_control_markup(args.text)
    prepared = prepare_text(clean, language=args.language, lexicon=lexicon)
    payload = {
        "original": prepared.original,
        "normalized": prepared.normalized,
        "segments": list(prepared.segments),
        "script_hints": list(prepared.script_hints),
        "pronunciation_overrides": [asdict(item) for item in prepared.pronunciation_overrides],
        "control_markers": [asdict(item) for item in markers],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_lexicon_check(args: argparse.Namespace) -> int:
    lexicon = PronunciationLexicon.from_json(args.path)
    print(json.dumps({"schema_version": 1, "entries": len(lexicon.entries)}))
    return 0


def _cmd_prosody_check(args: argparse.Namespace) -> int:
    timeline = ProsodyTimeline.from_json(args.path)
    print(json.dumps({"schema_version": 1, "events": len(timeline.events)}))
    return 0


def _cmd_voicepack_check(args: argparse.Namespace) -> int:
    pack = VoicePack.load(args.root)
    errors = pack.validate_files(args.root, verify_hashes=not args.skip_hashes)
    payload = {
        "voice_id": pack.voice_id,
        "display_name": pack.display_name,
        "references": len(pack.references),
        "backend_states": len(pack.backend_states),
        "style_presets": sorted(pack.style_presets),
        "errors": list(errors),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def _parse_controls(values: list[str]) -> dict[str, object]:
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


def _cmd_plan(args: argparse.Namespace) -> int:
    try:
        controls = _parse_controls(args.control)
        plan = build_synthesis_plan(
            args.text,
            language=args.language,
            explicit_engine=args.engine,
            controls=controls,
            lexicon=_load_lexicon(args.lexicon),
            max_generation_rtf=args.max_generation_rtf,
        )
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "engine": plan.engine.key,
                "text": {
                    "normalized": plan.text.normalized,
                    "segments": list(plan.text.segments),
                    "script_hints": list(plan.text.script_hints),
                    "pronunciation_overrides": [
                        asdict(item) for item in plan.text.pronunciation_overrides
                    ],
                },
                "controls": asdict(plan.controls),
                "requested_controls": plan.requested_controls,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _voicepack_render_inputs(
    args: argparse.Namespace,
) -> tuple[Path | None, str | None, PronunciationLexicon | None, dict[str, object], dict[str, object]]:
    controls = _parse_controls(args.control)
    if args.voicepack is None:
        return args.reference, args.language, _load_lexicon(args.lexicon), controls, {}

    if args.reference is not None:
        raise ValueError("--reference and --voicepack are mutually exclusive.")

    root = args.voicepack.resolve()
    pack = VoicePack.load(root)
    pack_controls = pack.style_controls(args.style_preset)
    pack_controls.update(controls)

    if pack.references:
        selection = pack.select_reference(
            root,
            allow_unknown_consent=args.allow_unknown_voice_consent,
            verify_hash=True,
        )
    elif pack.backend_states:
        raise ValueError(
            f"VoicePack {pack.voice_id!r} contains cached backend state but no reference clip. "
            "Backend-state execution is deliberately not integrated yet, so refusing to fake it."
        )
    else:
        raise ValueError(
            f"VoicePack {pack.voice_id!r} contains no executable identity material. "
            "Add a consented/provenanced reference clip or a future supported backend state."
        )

    language = args.language
    if language is None and len(pack.languages) == 1:
        language = pack.languages[0]

    lexicon_path = args.lexicon
    if lexicon_path is None and pack.pronunciation_lexicon:
        lexicon_path = root / pack.pronunciation_lexicon

    metadata: dict[str, object] = {
        "voicepack": {
            "voice_id": pack.voice_id,
            "display_name": pack.display_name,
            "style_preset": args.style_preset,
            "reference": {
                "path": selection.clip.path,
                "sha256": selection.clip.sha256,
                "license": selection.clip.license,
                "source": selection.clip.source,
                "consent": selection.clip.consent,
            },
            "provenance": pack.provenance,
            "unknown_consent_explicitly_allowed": bool(args.allow_unknown_voice_consent),
        }
    }
    return selection.path, language, _load_lexicon(lexicon_path), pack_controls, metadata


def _cmd_synthesize(args: argparse.Namespace) -> int:
    try:
        reference, language, lexicon, controls, metadata = _voicepack_render_inputs(args)
        manifest = render_text(
            args.text,
            args.output,
            language=language,
            engine_key=args.engine,
            voice=args.voice,
            reference=reference,
            controls=controls,
            lexicon=lexicon,
            max_generation_rtf=args.max_generation_rtf,
            engine_args=args.engine_arg,
            manifest_path=args.manifest,
            manifest_metadata=metadata,
            keep_parts=args.keep_parts,
            timeout_seconds=args.timeout,
        )
    except (KeyError, RuntimeError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 5
    print(json.dumps(manifest, ensure_ascii=False))
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

    route_parser = sub.add_parser("route", help="Select qualified engines by capability/performance.")
    route_parser.add_argument("--language")
    route_parser.add_argument("--require", action="append", default=[])
    route_parser.add_argument("--prefer", action="append", default=[])
    route_parser.add_argument("--max-generation-rtf", type=float)
    route_parser.add_argument("--allow-restricted-commercial-use", action="store_true")
    route_parser.set_defaults(func=_cmd_route)

    text_parser = sub.add_parser("text", help="Run OurTTS text/pronunciation/control preprocessing.")
    text_parser.add_argument("--text", required=True)
    text_parser.add_argument("--language")
    text_parser.add_argument("--lexicon", type=Path)
    text_parser.set_defaults(func=_cmd_text)

    lexicon_parser = sub.add_parser("lexicon-check", help="Validate a pronunciation lexicon.")
    lexicon_parser.add_argument("path", type=Path)
    lexicon_parser.set_defaults(func=_cmd_lexicon_check)

    prosody_parser = sub.add_parser("prosody-check", help="Validate a Prosody Timeline JSON file.")
    prosody_parser.add_argument("path", type=Path)
    prosody_parser.set_defaults(func=_cmd_prosody_check)

    voicepack_parser = sub.add_parser("voicepack-check", help="Validate a VoicePack directory.")
    voicepack_parser.add_argument("root", type=Path)
    voicepack_parser.add_argument("--skip-hashes", action="store_true")
    voicepack_parser.set_defaults(func=_cmd_voicepack_check)

    plan_parser = sub.add_parser("plan", help="Build an engine-aware OurTTS synthesis plan.")
    plan_parser.add_argument("--text", required=True)
    plan_parser.add_argument("--language")
    plan_parser.add_argument("--engine")
    plan_parser.add_argument("--lexicon", type=Path)
    plan_parser.add_argument("--control", action="append", default=[])
    plan_parser.add_argument("--max-generation-rtf", type=float)
    plan_parser.set_defaults(func=_cmd_plan)

    synth_parser = sub.add_parser(
        "synthesize",
        help="Render text through the owned OurTTS pipeline and a qualified backend.",
    )
    synth_parser.add_argument("--text", required=True)
    synth_parser.add_argument("--output", type=Path, required=True)
    synth_parser.add_argument("--language")
    synth_parser.add_argument("--engine")
    synth_parser.add_argument("--voice")
    synth_parser.add_argument("--reference", type=Path)
    synth_parser.add_argument("--voicepack", type=Path)
    synth_parser.add_argument("--style-preset")
    synth_parser.add_argument("--allow-unknown-voice-consent", action="store_true")
    synth_parser.add_argument("--lexicon", type=Path)
    synth_parser.add_argument("--control", action="append", default=[])
    synth_parser.add_argument("--max-generation-rtf", type=float)
    synth_parser.add_argument("--manifest", type=Path)
    synth_parser.add_argument("--keep-parts", action="store_true")
    synth_parser.add_argument("--timeout", type=float, default=1800.0)
    synth_parser.add_argument("--engine-arg", action="append", default=[])
    synth_parser.set_defaults(func=_cmd_synthesize)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
