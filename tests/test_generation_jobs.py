import time
from pathlib import Path
from types import SimpleNamespace

from ourtts.jobs import GenerationJobManager
from ourtts.store import LocalStore
from ttslab.product_contract import GenerationRequest, ResolvedGeneration
from ttslab.voice_library import VoiceLibrary


def _wait_for_terminal(manager: GenerationJobManager, job_id: str) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        assert job is not None
        if job["status"] in {"completed", "failed", "cancelled", "interrupted"}:
            return job
        time.sleep(0.02)
    raise AssertionError("generation job did not reach a terminal state")


def test_generation_job_records_progress_result_and_history(monkeypatch, tmp_path: Path) -> None:
    def fake_plan(request, *, voicepack_root=None):
        del request, voicepack_root
        return SimpleNamespace(engine="pocket_tts", routing_reasons=("test route",))

    def fake_generate(request, output, *, voicepack_root=None, manifest_path=None):
        del voicepack_root
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"RIFFfake")
        assert manifest_path is not None
        manifest_path.write_text('{"engine":"pocket_tts"}', encoding="utf-8")
        return ResolvedGeneration(
            request=request,
            engine="pocket_tts",
            output_path=str(output),
            manifest_path=str(manifest_path),
            status="completed",
            routing_reasons=("test route",),
        )

    monkeypatch.setattr("ourtts.jobs.plan_generation", fake_plan)
    monkeypatch.setattr("ourtts.jobs.generate", fake_generate)

    store = LocalStore(tmp_path / "state.sqlite3")
    manager = GenerationJobManager(
        store,
        output_root=tmp_path / "audio",
        voice_library=VoiceLibrary(tmp_path / "voices"),
    )
    job = manager.submit(GenerationRequest(text="Hello", language="en"))
    terminal = _wait_for_terminal(manager, job["id"])
    manager.shutdown()

    assert terminal["status"] == "completed"
    assert terminal["phase"] == "done"
    assert terminal["progress"] == 1.0
    assert terminal["result"]["engine"] == "pocket_tts"
    assert terminal["result"]["audio_url"].endswith(f"{job['id']}")
    history = store.list_history()
    assert len(history) == 1
    assert history[0]["job_id"] == job["id"]
    assert history[0]["engine"] == "pocket_tts"


def test_generation_job_persists_unexpected_failure(monkeypatch, tmp_path: Path) -> None:
    def broken_plan(request, *, voicepack_root=None):
        del request, voicepack_root
        raise RuntimeError("planned failure")

    monkeypatch.setattr("ourtts.jobs.plan_generation", broken_plan)
    store = LocalStore(tmp_path / "state.sqlite3")
    manager = GenerationJobManager(
        store,
        output_root=tmp_path / "audio",
        voice_library=VoiceLibrary(tmp_path / "voices"),
    )
    job = manager.submit(GenerationRequest(text="Hello"))
    terminal = _wait_for_terminal(manager, job["id"])
    manager.shutdown()

    assert terminal["status"] == "failed"
    assert terminal["phase"] == "failed"
    assert "planned failure" in terminal["error"]
