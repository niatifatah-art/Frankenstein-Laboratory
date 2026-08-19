from __future__ import annotations

import wave
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from ttslab.studio_server import create_app
from ttslab.synthesis import SynthesisResult


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x01\x00" * 2400)


def test_studio_serves_simple_surface_and_safe_generation(tmp_path: Path, monkeypatch) -> None:
    outputs = tmp_path / "outputs"
    voices = tmp_path / "voices"
    voices.mkdir()

    def fake_synthesize(request):
        _write_wav(request.output)
        return SynthesisResult(
            schema_version=1,
            engine="fake_engine",
            profile=request.profile,
            device="cpu",
            output_path=str(request.output),
            cached=False,
            audio={"frames": 2400, "sample_rate": 24000},
            segments=1,
            exact_pause_ms=0,
            native_controls=(),
            degraded_controls=(),
            reference_provenance=None,
            cache_key="fake-cache-key",
        )

    monkeypatch.setattr("ttslab.studio_server.synthesize", fake_synthesize)
    client = TestClient(create_app(output_root=outputs, voices_root=voices))

    assert client.get("/").status_code == 200
    health = client.get("/api/health").json()
    assert health["product"] == "ourTTS"
    assert health["version"] == "0.5.0"
    assert any(item["key"] == "auto" for item in client.get("/api/profiles").json())

    response = client.post(
        "/api/generate",
        json={
            "text": "Hello from the Studio",
            "language": "en",
            "profile": "auto",
            "style": "natural",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["engine"] == "fake_engine"
    assert payload["audio_url"].startswith("/api/audio/")
    assert client.get(payload["audio_url"]).status_code == 200


def test_studio_voice_ids_cannot_escape_managed_library(tmp_path: Path) -> None:
    client = TestClient(
        create_app(output_root=tmp_path / "outputs", voices_root=tmp_path / "voices")
    )
    response = client.post(
        "/api/generate",
        json={"text": "hello", "voice_id": "../escape"},
    )
    assert response.status_code == 400
