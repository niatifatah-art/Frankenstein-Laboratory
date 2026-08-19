import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from ttslab import product_api
from ttslab.product_contract import ResolvedGeneration
from ttslab.voicepack import ReferenceClip, VoicePack


def _make_voice(root: Path, voice_id: str = "creator") -> Path:
    pack_root = root / voice_id
    refs = pack_root / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    ref = refs / "reference.wav"
    ref.write_bytes(b"controlled-reference")
    digest = hashlib.sha256(ref.read_bytes()).hexdigest()
    VoicePack(
        voice_id=voice_id,
        display_name="Creator Voice",
        languages=("en",),
        references=(
            ReferenceClip(
                path="refs/reference.wav",
                sha256=digest,
                license="test-only",
                source="unit test",
                consent="synthetic",
            ),
        ),
        provenance={"synthetic": True},
    ).save(pack_root)
    return pack_root


def test_health_family_and_studio(tmp_path: Path) -> None:
    client = TestClient(
        product_api.create_app(output_root=tmp_path / "out", voice_root=tmp_path / "voices")
    )
    assert client.get("/health").json() == {"product": "ourTTS", "status": "ok"}
    family = client.get("/v1/family").json()
    assert family["product"] == "ourTTS"
    assert any(model["key"] == "atom" for model in family["models"])
    studio = client.get("/")
    assert studio.status_code == 200
    assert "What should it say?" in studio.text


def test_plan_uses_product_auto_router(tmp_path: Path) -> None:
    client = TestClient(
        product_api.create_app(output_root=tmp_path / "out", voice_root=tmp_path / "voices")
    )
    response = client.post(
        "/v1/plan",
        json={"text": "Hello", "language": "en", "quality": "auto"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["engine"] == "pocket_tts"
    assert payload["request"]["quality"] == "auto"


def test_voice_library_is_product_id_based(tmp_path: Path) -> None:
    voice_root = tmp_path / "voices"
    _make_voice(voice_root)
    client = TestClient(product_api.create_app(output_root=tmp_path / "out", voice_root=voice_root))

    library = client.get("/v1/voices").json()
    assert library["voices"][0]["voice_id"] == "creator"
    assert library["voices"][0]["ready"] is True

    response = client.post(
        "/v1/plan",
        json={"text": "Hello", "voice": "creator", "language": "en"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["voice_id"] == "creator"
    assert payload["reference"].endswith("reference.wav")
    assert payload["engine"] == "chatterbox_nano"


def test_unknown_voice_is_refused(tmp_path: Path) -> None:
    client = TestClient(
        product_api.create_app(output_root=tmp_path / "out", voice_root=tmp_path / "voices")
    )
    response = client.post(
        "/v1/plan",
        json={"text": "Hello", "voice": "missing", "language": "en"},
    )
    assert response.status_code == 422
    assert "Unknown ourTTS voice" in response.json()["detail"]


def test_best_mode_is_truthfully_refused_without_quality_evidence(tmp_path: Path) -> None:
    client = TestClient(
        product_api.create_app(output_root=tmp_path / "out", voice_root=tmp_path / "voices")
    )
    response = client.post(
        "/v1/plan",
        json={"text": "Hello", "language": "en", "quality": "best"},
    )
    assert response.status_code == 422
    assert "No release-quality evidence" in response.json()["detail"]


def test_generate_returns_safe_artifact_urls(monkeypatch, tmp_path: Path) -> None:
    def fake_generate(request, output, *, voicepack_root=None, manifest_path=None, timeout_seconds=1800.0):
        del voicepack_root, timeout_seconds
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"RIFFfake-wave")
        assert manifest_path is not None
        manifest_path.write_text(json.dumps({"engine": "pocket_tts"}))
        return ResolvedGeneration(
            request=request,
            engine="pocket_tts",
            output_path=str(output),
            manifest_path=str(manifest_path),
            status="completed",
            routing_reasons=("measured CPU generation faster than 2x realtime",),
        )

    monkeypatch.setattr(product_api, "generate", fake_generate)
    client = TestClient(
        product_api.create_app(output_root=tmp_path / "out", voice_root=tmp_path / "voices")
    )
    response = client.post("/v1/generate", json={"text": "Hello", "language": "en"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["engine"] == "pocket_tts"
    assert payload["audio_url"].startswith("/v1/audio/")
    assert payload["manifest_url"].startswith("/v1/manifests/")

    audio = client.get(payload["audio_url"])
    assert audio.status_code == 200
    assert audio.content == b"RIFFfake-wave"

    manifest = client.get(payload["manifest_url"])
    assert manifest.status_code == 200
    assert manifest.json()["engine"] == "pocket_tts"


def test_artifact_path_rejects_path_traversal(tmp_path: Path) -> None:
    client = TestClient(
        product_api.create_app(output_root=tmp_path / "out", voice_root=tmp_path / "voices")
    )
    response = client.get("/v1/audio/not-a-hex-id")
    assert response.status_code == 404
