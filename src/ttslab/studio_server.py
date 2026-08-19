from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .profiles import list_profiles
from .registry import load_registry
from .synthesis import SynthesisRequest, synthesize
from .voice_state import export_voicepack_state
from .voicepack import VoicePack


class StudioGenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    language: str | None = "en"
    profile: str = "auto"
    voice_id: str | None = None
    style: str | None = None
    speed: float | None = Field(default=None, gt=0.0, le=3.0)
    engine: str | None = None
    device: str | None = None


class PrepareVoiceRequest(BaseModel):
    engine: str = "chatterbox_nano"
    device: str = "cpu"
    language: str | None = None


def _safe_voicepack_root(voices_root: Path, voice_id: str | None) -> Path | None:
    if not voice_id:
        return None
    candidate = (voices_root / voice_id).resolve()
    if not candidate.is_relative_to(voices_root.resolve()):
        raise ValueError("Invalid voice identity.")
    if not (candidate / "voicepack.json").is_file():
        raise FileNotFoundError(f"Unknown VoicePack: {voice_id}")
    return candidate


def _voice_payload(root: Path) -> dict[str, object]:
    pack = VoicePack.load(root)
    return {
        "voice_id": pack.voice_id,
        "display_name": pack.display_name,
        "languages": list(pack.languages),
        "styles": sorted(pack.style_presets),
        "prepared_engines": [state.engine for state in pack.backend_states],
        "errors": list(pack.validate_files(root, verify_hashes=True)),
    }


def create_app(
    *,
    output_root: Path | None = None,
    voices_root: Path | None = None,
) -> FastAPI:
    output_root = (output_root or Path.home() / ".cache" / "ourtts" / "studio").resolve()
    voices_root = (voices_root or Path.home() / ".local" / "share" / "ourtts" / "voices").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    voices_root.mkdir(parents=True, exist_ok=True)
    static_root = Path(__file__).with_name("studio")

    app = FastAPI(title="ourTTS Studio", version="0.5.0")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static_root / "index.html", media_type="text/html")

    @app.get("/assets/{asset}", include_in_schema=False)
    def asset(asset: str):
        if asset not in {"styles.css", "app.js"}:
            raise HTTPException(status_code=404, detail="Unknown asset")
        path = static_root / asset
        media = "text/css" if asset.endswith(".css") else "application/javascript"
        return FileResponse(path, media_type=media)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "product": "ourTTS",
            "version": "0.5.0",
            "outputs": str(output_root),
            "voices": str(voices_root),
        }

    @app.get("/api/profiles")
    def profiles() -> list[dict[str, object]]:
        return [asdict(profile) for profile in list_profiles()]

    @app.get("/api/engines")
    def engines() -> list[dict[str, object]]:
        payload = []
        for engine in load_registry():
            if not engine.runnable or engine.kind != "tts":
                continue
            payload.append(
                {
                    "key": engine.key,
                    "name": engine.name,
                    "family": engine.family,
                    "languages": list(engine.languages),
                    "capabilities": list(engine.capabilities),
                    "hardware": list(engine.hardware),
                    "cpu_generation_rtf": engine.cpu_generation_rtf,
                }
            )
        return payload

    @app.get("/api/voices")
    def voices() -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for child in sorted(voices_root.iterdir()):
            if not child.is_dir() or not (child / "voicepack.json").is_file():
                continue
            try:
                payload.append(_voice_payload(child))
            except (OSError, TypeError, ValueError) as exc:
                payload.append(
                    {
                        "voice_id": child.name,
                        "display_name": child.name,
                        "languages": [],
                        "styles": [],
                        "prepared_engines": [],
                        "errors": [str(exc)],
                    }
                )
        return payload

    @app.post("/api/voices/{voice_id}/prepare")
    def prepare_voice(voice_id: str, request: PrepareVoiceRequest) -> dict[str, object]:
        try:
            root = _safe_voicepack_root(voices_root, voice_id)
            assert root is not None
            state = export_voicepack_state(
                root,
                engine_key=request.engine,
                language=request.language,
                device=request.device,
            )
            return asdict(state)
        except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/generate")
    def generate(request: StudioGenerateRequest) -> dict[str, object]:
        try:
            voicepack_root = _safe_voicepack_root(voices_root, request.voice_id)
            output = output_root / f"{uuid4().hex}.wav"
            style = request.style
            if style and style.casefold() == "natural":
                style = None
            result = synthesize(
                SynthesisRequest(
                    text=request.text,
                    output=output,
                    language=request.language,
                    profile=request.profile,
                    engine=request.engine,
                    style=style,
                    speed=request.speed,
                    device=request.device,
                    voicepack_root=voicepack_root,
                )
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        payload = asdict(result)
        payload["audio_url"] = f"/api/audio/{output.name}"
        return payload

    @app.get("/api/audio/{filename}")
    def audio(filename: str):
        if Path(filename).name != filename or not filename.endswith(".wav"):
            raise HTTPException(status_code=404, detail="Unknown audio")
        path = output_root / filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Unknown audio")
        return FileResponse(path, media_type="audio/wav", filename=filename)

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ourtts-studio", description="Run the local ourTTS Studio.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--voices-root", type=Path)
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run(
        create_app(output_root=args.output_root, voices_root=args.voices_root),
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
