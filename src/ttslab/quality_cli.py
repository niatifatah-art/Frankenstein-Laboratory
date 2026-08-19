from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .quality_suite import (
    QUALITY_SUITE_VERSION,
    aggregate_objective,
    build_listening_packet,
    build_release_evidence,
    load_ratings,
    load_samples,
    quality_cases,
    score_transcript,
    write_json,
)


def _cmd_corpus(args: argparse.Namespace) -> int:
    cases = quality_cases(language=args.language, task=args.task, corpus_path=args.corpus)
    payload = {
        "schema_version": 1,
        "suite_version": QUALITY_SUITE_VERSION,
        "cases": [
            {
                "id": case.key,
                "text": case.text,
                "language": case.language,
                "task": (
                    "cloning"
                    if "voice_cloning" in case.tags
                    else "long_form"
                    if "long_form" in case.tags
                    else "expressive"
                    if set(case.tags).intersection({"emotion", "prosody", "dialogue"})
                    else "general"
                ),
                "tags": list(case.tags),
            }
            for case in cases
        ],
    }
    if args.output:
        write_json(payload, args.output)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    score = score_transcript(args.reference, args.hypothesis)
    print(json.dumps(score.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _cmd_summarize(args: argparse.Namespace) -> int:
    samples = load_samples(args.samples)
    payload = {
        "schema_version": 1,
        "suite_version": QUALITY_SUITE_VERSION,
        "objective": [item.to_dict() for item in aggregate_objective(samples)],
    }
    if args.output:
        write_json(payload, args.output)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_listening_pack(args: argparse.Namespace) -> int:
    samples = load_samples(args.samples)
    packet, mapping = build_listening_packet(samples, seed=args.seed)
    write_json(packet, args.output)
    write_json(mapping, args.mapping)
    print(
        json.dumps(
            {
                "samples": len(packet["samples"]),
                "public_packet": str(args.output),
                "private_mapping": str(args.mapping),
                "blinded": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_evidence(args: argparse.Namespace) -> int:
    samples = load_samples(args.samples)
    ratings = load_ratings(args.ratings)
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    evidence = build_release_evidence(
        samples,
        ratings,
        mapping,
        evidence_ref=args.evidence_ref,
        minimum_samples=args.minimum_samples,
    )
    payload = {
        "schema_version": 1,
        "suite_version": QUALITY_SUITE_VERSION,
        "evidence": [asdict(item) | {"score": item.score} for item in evidence],
    }
    write_json(payload, args.output)
    if not evidence:
        print(
            "No release-quality evidence was produced. Check objective transcripts, blind ratings, "
            "and minimum sample counts.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ourtts-quality",
        description="Build measured ourTTS quality evidence without inventing model rankings.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    corpus = sub.add_parser("corpus", help="List the controlled quality cases.")
    corpus.add_argument("--language")
    corpus.add_argument("--task", choices=["general", "cloning", "expressive", "long_form"])
    corpus.add_argument("--corpus", type=Path)
    corpus.add_argument("--output", type=Path)
    corpus.set_defaults(func=_cmd_corpus)

    score = sub.add_parser("score", help="Measure deterministic WER/CER for one transcript pair.")
    score.add_argument("--reference", required=True)
    score.add_argument("--hypothesis", required=True)
    score.set_defaults(func=_cmd_score)

    summarize = sub.add_parser("summarize", help="Aggregate objective sample evidence.")
    summarize.add_argument("samples", type=Path)
    summarize.add_argument("--output", type=Path)
    summarize.set_defaults(func=_cmd_summarize)

    listening = sub.add_parser(
        "listening-pack",
        help="Create a blinded listening packet plus a separate private engine mapping.",
    )
    listening.add_argument("samples", type=Path)
    listening.add_argument("--output", type=Path, required=True)
    listening.add_argument("--mapping", type=Path, required=True)
    listening.add_argument("--seed", default=QUALITY_SUITE_VERSION)
    listening.set_defaults(func=_cmd_listening_pack)

    evidence = sub.add_parser(
        "evidence",
        help="Combine objective transcripts with human MOS ratings into release evidence.",
    )
    evidence.add_argument("--samples", type=Path, required=True)
    evidence.add_argument("--ratings", type=Path, required=True)
    evidence.add_argument("--mapping", type=Path, required=True)
    evidence.add_argument("--evidence-ref", required=True)
    evidence.add_argument("--minimum-samples", type=int, default=10)
    evidence.add_argument("--output", type=Path, required=True)
    evidence.set_defaults(func=_cmd_evidence)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
