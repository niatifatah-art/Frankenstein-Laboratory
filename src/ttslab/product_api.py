from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ourtts.jobs import GenerationJobManager
from ourtts.models import ModelManager
from ourtts.paths import AppPaths
from ourtts.platform import inspect_platform
from ourtts.store import LocalStore

from .product import PRODUCT_NAME, PRODUCT_TAGLINE, product_manifest
from .product_contract import GenerationRequest
from .product_runtime import generate, plan_generation
from .voice_library import VoiceLibrary


class GenerationBody(BaseModel):
    text: str = Field(min_length=1)
    voice: str | None = None
    language: str | None = None
    style: str = "natural"
    quality: str = "auto"
    offline: bool = False
    controls: dict[str, Any] = Field(default_factory=dict)

    def to_request(self) -> GenerationRequest:
        return GenerationRequest(
            text=self.text,
            voice=self.voice,
            language=self.language,
            style=self.style,
            quality=self.quality,
            offline=self.offline,
            controls=dict(self.controls),
        )


class ProjectBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SegmentBody(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str | None = None
    language: str | None = None
    style: str = "natural"
    quality: str = "auto"
    controls: dict[str, Any] = Field(default_factory=dict)


def create_app(
    *,
    output_root: Path | None = None,
    voice_root: Path | None = None,
    database_path: Path | None = None,
    app_paths: AppPaths | None = None,
) -> FastAPI:
    paths = (app_paths or AppPaths.default()).ensure()
    root = (output_root or paths.artifacts).resolve()
    root.mkdir(parents=True, exist_ok=True)
    voices = VoiceLibrary(voice_root or paths.voices)
    store = LocalStore(database_path or paths.database)
    models = ModelManager()
    jobs = GenerationJobManager(store, output_root=root, voice_library=voices)
    studio_root = Path(__file__).with_name("studio")

    app = FastAPI(
        title=PRODUCT_NAME,
        version="0.10-dev",
        description=PRODUCT_TAGLINE,
    )

    if studio_root.is_dir():
        app.mount("/studio-assets", StaticFiles(directory=studio_root), name="studio-assets")

        @app.get("/", include_in_schema=False)
        def studio() -> FileResponse:
            return FileResponse(studio_root / "index.html", media_type="text/html")

    @app.get("/health")
    def legacy_health() -> dict[str, str]:
        """Keep the established lightweight probe stable for existing clients."""
        return {"product": PRODUCT_NAME, "status": "ok"}

    @app.get("/v1/health")
    def health() -> dict[str, object]:
        report = inspect_platform(paths)
        return {
            "product": PRODUCT_NAME,
            "status": "ok",
            "database_schema": store.schema_version(),
            "platform": {
                "os": report.os,
                "machine": report.machine,
                "accelerator": report.accelerator,
            },
        }

    @app.get("/v1/system")
    def system() -> dict[str, object]:
        return inspect_platform(paths).to_dict()

    @app.get("/v1/family")
    def family() -> dict[str, object]:
        return product_manifest()

    @app.get("/v1/models")
    def model_library() -> dict[str, object]:
        report = inspect_platform(paths)
        return {
            "models": [item.to_dict() for item in models.list()],
            "recommended": list(models.recommend(report)),
        }

    @app.get("/v1/models/{model_id}")
    def model(model_id: str) -> dict[str, object]:
        try:
            return models.get(model_id).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="model not found") from exc

    @app.get("/v1/voices")
    def voice_library() -> dict[str, object]:
        return {"voices": [voice.to_dict() for voice in voices.list()]}

    @app.get("/v1/projects")
    def projects() -> dict[str, object]:
        return {"projects": store.list_projects()}

    @app.post("/v1/projects", status_code=201)
    def create_project(body: ProjectBody) -> dict[str, object]:
        try:
            return store.create_project(body.name, body.metadata)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/projects/{project_id}")
    def project(project_id: str) -> dict[str, object]:
        item = store.get_project(project_id)
        if item is None:
            raise HTTPException(status_code=404, detail="project not found")
        item["segments"] = store.list_segments(project_id)
        return item

    @app.get("/v1/projects/{project_id}/segments")
    def project_segments(project_id: str) -> dict[str, object]:
        if store.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="project not found")
        return {"segments": store.list_segments(project_id)}

    @app.post("/v1/projects/{project_id}/segments", status_code=201)
    def create_segment(project_id: str, body: SegmentBody) -> dict[str, object]:
        try:
            return store.add_segment(
                project_id,
                body.text,
                voice_id=body.voice_id,
                language=body.language,
                style=body.style,
                quality=body.quality,
                controls=body.controls,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="project not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/history")
    def history(limit: int = 100) -> dict[str, object]:
        return {"history": store.list_history(limit=limit)}

    @app.post("/v1/plan")
    def plan(body: GenerationBody) -> dict[str, Any]:
        try:
            voicepack_root = voices.resolve(body.voice) if body.voice else None
            return plan_generation(body.to_request(), voicepack_root=voicepack_root).to_dict()
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/v1/jobs", status_code=202)
    def submit_job(body: GenerationBody) -> dict[str, object]:
        try:
            return jobs.submit(body.to_request())
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/jobs")
    def list_jobs(limit: int = 100) -> dict[str, object]:
        return {"jobs": jobs.list(limit=limit)}

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        item = jobs.get(job_id)
        if item is None:
            raise HTTPException(status_code=404, detail="job not found")
        return item

    @app.post("/v1/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict[str, object]:
        try:
            return jobs.cancel(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.post("/v1/generate")
    def synthesize(body: GenerationBody) -> dict[str, Any]:
        """Backward-compatible synchronous generation endpoint.

        New Studio flows should prefer `/v1/jobs` so progress and history remain visible.
        """
        artifact_id = uuid4().hex
        audio_path = root / f"{artifact_id}.wav"
        manifest_path = root / f"{artifact_id}.manifest.json"
        try:
            voicepack_root = voices.resolve(body.voice) if body.voice else None
            result = generate(
                body.to_request(),
                audio_path,
                voicepack_root=voicepack_root,
                manifest_path=manifest_path,
            )
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        store.record_history(
            job_id=None,
            text=body.text,
            voice_id=result.voice_id,
            language=body.language,
            engine=result.engine,
            audio_path=str(audio_path),
            manifest_path=str(manifest_path),
            metadata={"routing_reasons": list(result.routing_reasons), "legacy_sync": True},
        )
        return {
            "id": artifact_id,
            "status": result.status,
            "engine": result.engine,
            "voice_id": result.voice_id,
            "routing_reasons": result.routing_reasons,
            "audio_url": f"/v1/audio/{artifact_id}",
            "manifest_url": f"/v1/manifests/{artifact_id}",
        }

    @app.get("/v1/audio/{artifact_id}")
    def audio(artifact_id: str) -> FileResponse:
        path = _artifact_path(root, artifact_id, ".wav")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="audio artifact not found")
        return FileResponse(path, media_type="audio/wav", filename=f"ourtts-{artifact_id}.wav")

    @app.get("/v1/manifests/{artifact_id}")
    def manifest(artifact_id: str) -> FileResponse:
        path = _artifact_path(root, artifact_id, ".manifest.json")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="manifest artifact not found")
        return FileResponse(path, media_type="application/json")

    return app


def _artifact_path(root: Path, artifact_id: str, suffix: str) -> Path:
    if not artifact_id or any(char not in "0123456789abcdef" for char in artifact_id.casefold()):
        raise HTTPException(status_code=404, detail="artifact not found")
    path = (root / f"{artifact_id}{suffix}").resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=404, detail="artifact not found")
    return path


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("ttslab.product_api:app", host="127.0.0.1", port=7860, reload=False)
