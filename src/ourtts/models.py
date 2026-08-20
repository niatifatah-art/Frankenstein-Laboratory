from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ttslab.isolation import get_worker
from ttslab.registry import EngineRecord, load_registry

from .platform import PlatformReport


@dataclass(frozen=True, slots=True)
class ModelManifest:
    id: str
    name: str
    family: str
    version: str
    upstream: str
    revision: str | None
    status: str
    kind: str
    capabilities: tuple[str, ...]
    languages: tuple[str, ...]
    hardware: tuple[str, ...]
    code_license: str
    weights_license: str
    commercial_use: str
    license_status: str
    restrictions: tuple[str, ...]
    verified_on: str
    worker: str | None
    cpu_generation_rtf: float | None
    cpu_ttfa_seconds: float | None
    runtime_state: str
    weights_state: str
    access_gated: bool
    install_path: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelManager:
    """Product-facing view of isolated workers and their local runtime state.

    A worker environment being installed is deliberately separate from model-weight state. Many
    upstream libraries download weights lazily on first model load, and some checkpoints are gated.
    """

    def __init__(self, records: tuple[EngineRecord, ...] | None = None) -> None:
        self.records = records or load_registry()

    @staticmethod
    def _worker_path(record: EngineRecord) -> Path | None:
        if not record.worker:
            return None
        try:
            return get_worker(record.worker).project_dir
        except KeyError:
            return None

    @staticmethod
    def _access_gated(record: EngineRecord) -> bool:
        text = " ".join((record.notes, *record.restrictions)).casefold()
        return "gated" in text or "requires auth" in text or "authentication" in text

    def manifest(self, record: EngineRecord) -> ModelManifest:
        project_dir = self._worker_path(record)
        venv = None if project_dir is None else project_dir / ".venv"
        if project_dir is None:
            runtime_state = "not_product_worker"
        elif venv.is_dir():
            runtime_state = "runtime_installed"
        else:
            runtime_state = "runtime_on_demand"
        access_gated = self._access_gated(record)
        weights_state = "gated_or_on_demand" if access_gated else "on_demand_or_cached"
        return ModelManifest(
            id=record.key,
            name=record.name,
            family=record.family or record.key,
            version=record.version,
            upstream=record.upstream,
            revision=record.source_revision,
            status=record.integration_status,
            kind=record.kind,
            capabilities=record.capabilities,
            languages=record.languages,
            hardware=record.hardware,
            code_license=record.code_license,
            weights_license=record.weights_license,
            commercial_use=record.commercial_use,
            license_status=record.license_status,
            restrictions=record.restrictions,
            verified_on=record.verified_on,
            worker=record.worker,
            cpu_generation_rtf=record.cpu_generation_rtf,
            cpu_ttfa_seconds=record.cpu_ttfa_seconds,
            runtime_state=runtime_state,
            weights_state=weights_state,
            access_gated=access_gated,
            install_path=str(project_dir) if project_dir else None,
        )

    def list(self) -> tuple[ModelManifest, ...]:
        return tuple(self.manifest(record) for record in self.records)

    def get(self, model_id: str) -> ModelManifest:
        for record in self.records:
            if record.key == model_id:
                return self.manifest(record)
        raise KeyError(model_id)

    def recommend(self, report: PlatformReport, *, limit: int = 5) -> tuple[dict[str, Any], ...]:
        ranked: list[tuple[float, EngineRecord, list[str]]] = []
        for record in self.records:
            if not record.runnable or record.kind != "tts":
                continue
            score = 0.0
            reasons: list[str] = []
            hardware = {item.casefold() for item in record.hardware}
            if report.accelerator == "cpu" and "cpu" not in hardware:
                continue
            if "cpu" in hardware:
                score += 20
                reasons.append("CPU-capable")
            if record.cpu_generation_rtf is not None:
                if record.cpu_generation_rtf <= 1.0:
                    score += 40
                    reasons.append("measured faster than realtime on qualification CPU")
                elif record.cpu_generation_rtf <= 3.0:
                    score += 20
                    reasons.append("measured usable CPU generation")
                else:
                    score -= min(record.cpu_generation_rtf, 30)
            if record.license_status.casefold() in {"verified", "partially_verified"}:
                score += 10
                reasons.append("license metadata verified")
            if record.commercial_use.casefold() in {"yes", "allowed", "permitted"}:
                score += 10
                reasons.append("commercial-use metadata permits use")
            if "streaming" in record.capabilities:
                score += 8
                reasons.append("streaming capability")
            if self._access_gated(record):
                score -= 8
                reasons.append("upstream access may require authentication")
            ranked.append((score, record, reasons))
        ranked.sort(key=lambda item: (-item[0], item[1].key))
        return tuple(
            {
                "model": self.manifest(record).to_dict(),
                "score": round(score, 3),
                "reasons": reasons,
            }
            for score, record, reasons in ranked[: max(1, limit)]
        )

    @staticmethod
    def _uv() -> str:
        direct = shutil.which("uv")
        if direct:
            return direct
        names = ("uv.exe", "uv") if sys.platform == "win32" else ("uv",)
        for name in names:
            candidate = Path(sys.executable).resolve().parent / name
            if candidate.is_file():
                return str(candidate)
        raise RuntimeError("uv is required to install or repair isolated model runtimes")

    def sync_runtime(self, model_id: str, *, timeout_seconds: float = 1800.0) -> dict[str, Any]:
        manifest = self.get(model_id)
        if manifest.install_path is None or manifest.worker is None:
            raise ValueError(f"{model_id} does not have an installable isolated product worker")
        completed = subprocess.run(
            [self._uv(), "sync", "--project", manifest.install_path],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "model_id": model_id,
            "operation": "sync_runtime",
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
            "runtime_state": self.get(model_id).runtime_state,
            "weights_note": "Model weights may still download lazily on first model load.",
        }

    def uninstall_runtime(self, model_id: str) -> dict[str, Any]:
        manifest = self.get(model_id)
        if manifest.install_path is None:
            raise ValueError(f"{model_id} has no isolated runtime path")
        venv = Path(manifest.install_path) / ".venv"
        removed = venv.is_dir()
        if removed:
            shutil.rmtree(venv)
        return {
            "model_id": model_id,
            "operation": "uninstall_runtime",
            "removed": removed,
            "weights_note": "Shared Hugging Face/model caches are intentionally left untouched.",
        }
