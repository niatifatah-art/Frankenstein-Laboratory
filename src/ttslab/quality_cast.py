from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .benchmark import benchmark_case, write_result
from .quality_suite import QualitySample, quality_cases, task_for_case


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cast_quality(
    engines: Iterable[str],
    *,
    output_root: Path,
    language: str,
    task: str = "general",
    max_cases: int | None = None,
    timeout_seconds: float = 1800.0,
) -> tuple[QualitySample, ...]:
    """Generate the same controlled cases across engines and retain failures as evidence."""
    engine_keys = tuple(dict.fromkeys(engine.strip() for engine in engines if engine.strip()))
    if not engine_keys:
        raise ValueError("quality cast requires at least one --engine")
    if max_cases is not None and max_cases < 1:
        raise ValueError("max_cases must be positive")

    cases = quality_cases(language=language, task=task)
    if max_cases is not None:
        cases = cases[:max_cases]
    if not cases:
        raise ValueError(f"no quality cases match language={language!r}, task={task!r}")

    output_root.mkdir(parents=True, exist_ok=True)
    samples: list[QualitySample] = []
    for engine in engine_keys:
        engine_root = output_root / engine
        engine_root.mkdir(parents=True, exist_ok=True)
        for case in cases:
            result_path = engine_root / f"{engine}__{case.key}.json"
            audio_path = engine_root / f"{engine}__{case.key}.wav"
            try:
                result = benchmark_case(
                    engine,
                    case,
                    output_root=engine_root,
                    timeout_seconds=timeout_seconds,
                )
            except (KeyError, OSError, RuntimeError, ValueError) as exc:
                result: dict[str, Any] = {
                    "schema_version": 1,
                    "engine": engine,
                    "case": {
                        "key": case.key,
                        "text": case.text,
                        "language": case.language,
                        "tags": list(case.tags),
                    },
                    "status": "runner_error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "audio": None,
                }
            write_result(result, result_path)

            status = str(result.get("status", "failed"))
            audio_sha256 = None
            retained_audio = None
            if status == "passed" and audio_path.is_file():
                retained_audio = str(audio_path)
                audio_sha256 = _sha256_file(audio_path)

            samples.append(
                QualitySample(
                    engine=engine,
                    case_key=case.key,
                    language=case.language or language,
                    task=task_for_case(case),
                    reference_text=case.text,
                    hypothesis_text=None,
                    status=status,
                    evidence_ref=f"artifact:{result_path.as_posix()}",
                    audio_path=retained_audio,
                    audio_sha256=audio_sha256,
                )
            )
    return tuple(samples)
