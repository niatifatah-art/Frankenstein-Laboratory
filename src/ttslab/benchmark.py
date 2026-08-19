from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .audio import inspect_wav
from .isolation import execute_worker
from .registry import EngineRecord, get_engine, repository_root


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    key: str
    text: str
    language: str | None
    tags: tuple[str, ...]


def load_corpus(path: Path | None = None) -> tuple[BenchmarkCase, ...]:
    corpus_path = path or repository_root() / "benchmarks" / "corpus.json"
    raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    return tuple(
        BenchmarkCase(
            key=item["id"],
            text=item["text"],
            language=item.get("language"),
            tags=tuple(item.get("tags", [])),
        )
        for item in raw["cases"]
    )


def get_case(key: str, path: Path | None = None) -> BenchmarkCase:
    for case in load_corpus(path):
        if case.key == key:
            return case
    raise KeyError(key)


def benchmark_case(
    engine: EngineRecord | str,
    case: BenchmarkCase | str,
    *,
    output_root: Path,
    engine_args: list[str] | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    engine_record = get_engine(engine) if isinstance(engine, str) else engine
    case_record = get_case(case) if isinstance(case, str) else case
    if not engine_record.worker:
        raise RuntimeError(f"{engine_record.key} has no worker")

    output_root.mkdir(parents=True, exist_ok=True)
    audio_path = output_root / f"{engine_record.key}__{case_record.key}.wav"
    execution = execute_worker(
        engine_record.worker,
        text=case_record.text,
        output=audio_path,
        extra_args=engine_args,
        timeout_seconds=timeout_seconds,
    )

    result: dict[str, Any] = {
        "schema_version": 1,
        "recorded_at": datetime.now(UTC).isoformat(),
        "engine": engine_record.key,
        "engine_version": engine_record.version,
        "case": asdict(case_record),
        "host": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "machine": platform.machine(),
            "processor": platform.processor() or None,
        },
        "command": list(execution.command),
        "returncode": execution.returncode,
        "worker_result": execution.payload,
        "stderr_tail": execution.stderr[-4000:] if execution.stderr else "",
        "audio": None,
        "status": "failed" if execution.returncode else "generated",
    }

    if execution.returncode == 0:
        try:
            result["audio"] = inspect_wav(audio_path, min_frames=100).as_dict()
            result["status"] = "passed"
        except (FileNotFoundError, ValueError) as exc:
            result["status"] = "invalid_audio"
            result["validation_error"] = str(exc)
    return result


def write_result(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
