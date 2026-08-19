from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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


def create_app(
    *,
    output_root: Path | None = None,
    voice_root: Path | None = None,
) -> FastAPI:
    root = (output_root or Path("outputs/api")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    voices = VoiceLibrary(voice_root or Path("voices"))
    studio_root = Path(__file__).with_name("studio")

    app = FastAPI(
        title=PRODUCT_NAME,
        version="0.6-dev",
        description=PRODUCT_TAGLINE,
    )

    if studio_root.is_dir():
        app.mount("/studio-assets", StaticFiles(directory=studio_root), name="studio-assets")

        @app.get("/", include_in_schema=False)
        def studio() -> FileResponse:
            return FileResponse(studio_root / "index.html", media_type="text/html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"product": PRODUCT_NAME, "status": "ok"}

    @app.get("/v1/family")
    def family() -> dict[str, object]:
        return product_manifest()

    @app.get("/v1/voices")
    def voice_library() -> dict[str, object]:
        return {"voices": [voice.to_dict() for voice in voices.list()]}

    @app.post("/v1/plan")
    def plan(body: GenerationBody) -> dict[str, Any]:
        try:
            voicepack_root = voices.resolve(body.voice) if body.voice else None
            return plan_generation(body.to_request(), voicepack_root=voicepack_root).to_dict()
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/v1/generate")
    def synthesize(body: GenerationBody) -> dict[str, Any]:
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
