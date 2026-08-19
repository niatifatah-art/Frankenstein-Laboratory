from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .synthesis import SynthesisRequest, SynthesisResult, synthesize


def _request_from_job(job: dict[str, Any], output_root: Path | None) -> SynthesisRequest:
    data = dict(job)
    data.pop("id", None)
    output = Path(data.pop("output"))
    if output_root is not None and not output.is_absolute():
        output = output_root / output
    for key in ("reference", "lexicon", "voicepack_root", "cache_dir"):
        if data.get(key):
            data[key] = Path(data[key])
    engine_args = data.get("engine_args")
    if engine_args is not None:
        data["engine_args"] = tuple(str(item) for item in engine_args)
    return SynthesisRequest(output=output, **data)


def run_batch(
    manifest: Path,
    *,
    output_root: Path | None = None,
    fail_fast: bool = False,
    synth: Callable[[SynthesisRequest], SynthesisResult] = synthesize,
) -> dict[str, Any]:
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported batch manifest schema.")
    jobs = raw.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("Batch manifest jobs must be a list.")

    results: list[dict[str, Any]] = []
    failed = 0
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            raise ValueError(f"Batch job {index} must be an object.")
        job_id = str(job.get("id", index))
        try:
            result = synth(_request_from_job(job, output_root))
            results.append({"id": job_id, "status": "passed", "result": asdict(result)})
        except Exception as exc:  # noqa: BLE001 - batch must preserve individual failures
            failed += 1
            results.append(
                {
                    "id": job_id,
                    "status": "failed",
                    "error": type(exc).__name__,
                    "message": str(exc),
                }
            )
            if fail_fast:
                break

    return {
        "schema_version": 1,
        "jobs_requested": len(jobs),
        "jobs_completed": len(results),
        "passed": sum(item["status"] == "passed" for item in results),
        "failed": failed,
        "results": results,
    }
