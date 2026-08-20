from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ttslab.product_contract import GenerationRequest
from ttslab.product_runtime import generate, plan_generation
from ttslab.voice_library import VoiceLibrary

from .store import LocalStore


class GenerationJobManager:
    """Local generation queue with SQLite-backed state.

    Cancellation is cooperative in this first product slice: queued work can be cancelled before
    it starts; a running isolated model call is allowed to finish and its result is discarded if
    cancellation was requested meanwhile. Hard process interruption belongs in RuntimeManager v2.
    """

    def __init__(
        self,
        store: LocalStore,
        *,
        output_root: Path,
        voice_library: VoiceLibrary,
        max_workers: int = 1,
    ) -> None:
        self.store = store
        self.output_root = output_root.expanduser().resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.voice_library = voice_library
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="ourtts")
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.Lock()

    def submit(self, request: GenerationRequest) -> dict[str, Any]:
        job = self.store.create_job(request.to_dict())
        job_id = str(job["id"])
        with self._lock:
            self._futures[job_id] = self._executor.submit(self._run, job_id, request)
        return job

    def _voice_root(self, request: GenerationRequest) -> Path | None:
        return self.voice_library.resolve(request.voice) if request.voice else None

    def _cancelled(self, job_id: str) -> bool:
        job = self.store.get_job(job_id)
        return bool(job and job.get("cancel_requested"))

    def _run(self, job_id: str, request: GenerationRequest) -> None:
        try:
            if self._cancelled(job_id):
                self.store.update_job(job_id, status="cancelled", phase="cancelled", progress=0.0)
                return

            voicepack_root = self._voice_root(request)
            self.store.update_job(job_id, status="planning", phase="planning", progress=0.08)
            plan = plan_generation(request, voicepack_root=voicepack_root)
            if self._cancelled(job_id):
                self.store.update_job(job_id, status="cancelled", phase="cancelled", progress=0.08)
                return

            self.store.update_job(
                job_id,
                status="loading_model",
                phase="loading_model",
                progress=0.18,
                result={"engine": plan.engine, "routing_reasons": list(plan.routing_reasons)},
            )
            self.store.update_job(job_id, status="generating", phase="generating", progress=0.25)

            audio_path = self.output_root / f"{job_id}.wav"
            manifest_path = self.output_root / f"{job_id}.manifest.json"
            result = generate(
                request,
                audio_path,
                voicepack_root=voicepack_root,
                manifest_path=manifest_path,
            )

            if self._cancelled(job_id):
                audio_path.unlink(missing_ok=True)
                manifest_path.unlink(missing_ok=True)
                self.store.update_job(
                    job_id,
                    status="cancelled",
                    phase="cancelled",
                    progress=1.0,
                    result={"engine": result.engine, "discarded_after_cancel": True},
                )
                return

            payload = result.to_dict()
            payload.update(
                {
                    "audio_url": f"/v1/audio/{job_id}",
                    "manifest_url": f"/v1/manifests/{job_id}",
                }
            )
            self.store.update_job(
                job_id,
                status="completed",
                phase="done",
                progress=1.0,
                result=payload,
            )
            self.store.record_history(
                job_id=job_id,
                text=request.text,
                voice_id=result.voice_id,
                language=request.language,
                engine=result.engine,
                audio_path=str(audio_path),
                manifest_path=str(manifest_path),
                metadata={"routing_reasons": list(result.routing_reasons)},
            )
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            self.store.update_job(
                job_id,
                status="failed",
                phase="failed",
                progress=1.0,
                error=f"{type(exc).__name__}: {exc}",
            )
        except Exception as exc:  # noqa: BLE001 - job boundary must persist unexpected failures
            self.store.update_job(
                job_id,
                status="failed",
                phase="failed",
                progress=1.0,
                error=f"Unexpected {type(exc).__name__}: {exc}",
            )
        finally:
            with self._lock:
                self._futures.pop(job_id, None)

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self.store.get_job(job_id)

    def list(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.list_jobs(limit=limit)

    def cancel(self, job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job["status"] in {"completed", "failed", "cancelled", "interrupted"}:
            return job
        updated = self.store.request_cancel(job_id)
        with self._lock:
            future = self._futures.get(job_id)
        if future is not None and future.cancel():
            updated = self.store.update_job(
                job_id, status="cancelled", phase="cancelled", progress=float(job["progress"])
            )
        return updated

    def shutdown(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=False)
