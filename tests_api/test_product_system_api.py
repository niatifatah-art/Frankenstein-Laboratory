from pathlib import Path

from fastapi.testclient import TestClient

from ourtts.paths import AppPaths
from ttslab import product_api


def _client(tmp_path: Path) -> TestClient:
    paths = AppPaths.default(
        env={"OURTTS_HOME": str(tmp_path / "app-data")},
        home=tmp_path,
        platform_name="linux",
    )
    return TestClient(
        product_api.create_app(
            output_root=tmp_path / "audio",
            voice_root=tmp_path / "voices",
            database_path=tmp_path / "state.sqlite3",
            app_paths=paths,
        )
    )


def test_v1_health_system_and_models_are_product_backed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["database_schema"] == 1
    assert health.json()["product"] == "ourTTS"

    system = client.get("/v1/system")
    assert system.status_code == 200
    assert system.json()["paths"]["root"].endswith("app-data")
    assert system.json()["python"]

    models = client.get("/v1/models")
    assert models.status_code == 200
    payload = models.json()
    assert any(item["id"] == "pocket_tts" for item in payload["models"])
    pocket = next(item for item in payload["models"] if item["id"] == "pocket_tts")
    assert "code_license" in pocket
    assert "weights_license" in pocket
    assert "runtime_state" in pocket


def test_projects_segments_and_history_use_sqlite(tmp_path: Path) -> None:
    client = _client(tmp_path)
    project = client.post(
        "/v1/projects",
        json={"name": "Video one", "metadata": {"platform": "youtube"}},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    segment = client.post(
        f"/v1/projects/{project_id}/segments",
        json={
            "text": "Hi guys",
            "language": "en",
            "style": "energetic",
            "controls": {"speed": 1.05},
        },
    )
    assert segment.status_code == 201, segment.text
    assert segment.json()["position"] == 0

    fetched = client.get(f"/v1/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["segments"][0]["text"] == "Hi guys"
    assert client.get("/v1/history").json() == {"history": []}


def test_job_endpoints_exist_without_forcing_real_generation(monkeypatch, tmp_path: Path) -> None:
    def fake_submit(self, request):
        del self
        return {
            "id": "a" * 32,
            "status": "queued",
            "phase": "queued",
            "progress": 0.0,
            "request": request.to_dict(),
        }

    monkeypatch.setattr(product_api.GenerationJobManager, "submit", fake_submit)
    client = _client(tmp_path)
    response = client.post("/v1/jobs", json={"text": "Hello", "language": "en"})
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"

    schema = client.get("/openapi.json").json()
    assert "/v1/jobs/{job_id}" in schema["paths"]
    assert "/v1/jobs/{job_id}/cancel" in schema["paths"]
