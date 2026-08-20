from pathlib import Path

from ourtts.store import LocalStore


def test_store_migrates_and_persists_project_segments_and_takes(tmp_path: Path) -> None:
    path = tmp_path / "ourtts.sqlite3"
    store = LocalStore(path)
    assert store.schema_version() == 1

    project = store.create_project("First project", {"kind": "short"})
    segment = store.add_segment(
        project["id"],
        "Hi guys",
        language="en",
        style="energetic",
        controls={"speed": 1.05},
    )
    take = store.add_take(
        segment["id"],
        status="completed",
        audio_path="audio/take.wav",
        engine="pocket_tts",
    )

    reopened = LocalStore(path)
    assert reopened.get_project(project["id"])["metadata"] == {"kind": "short"}
    segments = reopened.list_segments(project["id"])
    assert [item["text"] for item in segments] == ["Hi guys"]
    assert segments[0]["controls"] == {"speed": 1.05}
    assert reopened.list_takes(segment["id"])[0]["id"] == take["id"]


def test_store_recovers_interrupted_generation_jobs(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    store = LocalStore(path)
    job = store.create_job({"text": "hello"})
    store.update_job(job["id"], status="generating", phase="generating", progress=0.4)

    recovered = LocalStore(path).get_job(job["id"])
    assert recovered is not None
    assert recovered["status"] == "interrupted"
    assert recovered["phase"] == "interrupted"
    assert recovered["progress"] == 0.4
    assert "restarted" in recovered["error"]


def test_job_cancel_history_and_settings_are_persistent(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / "local.sqlite3")
    job = store.create_job({"text": "cancel me"})
    cancelled = store.request_cancel(job["id"])
    assert cancelled["cancel_requested"] is True
    assert cancelled["status"] == "cancel_requested"

    history = store.record_history(
        job_id=job["id"],
        text="A   long\nline for history",
        voice_id="brookey",
        language="en",
        engine="kokoro",
        audio_path="audio.wav",
        manifest_path="audio.manifest.json",
    )
    assert history["text_preview"] == "A long line for history"
    assert store.list_history()[0]["id"] == history["id"]

    store.set_setting("performance.memory_budget_mb", 4096)
    assert store.get_setting("performance.memory_budget_mb") == 4096
    assert store.get_setting("missing", "fallback") == "fallback"
