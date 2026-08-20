from pathlib import Path

from ttslab.quality_cast import cast_quality


def test_cast_quality_reuses_same_case_and_hashes_retained_audio(
    monkeypatch, tmp_path: Path
) -> None:
    seen: list[tuple[str, str]] = []

    def fake_benchmark(engine, case, *, output_root, timeout_seconds):
        seen.append((engine, case.key))
        audio = output_root / f"{engine}__{case.key}.wav"
        audio.write_bytes(b"RIFF-quality-test")
        return {"schema_version": 1, "engine": engine, "status": "passed", "audio": {}}

    monkeypatch.setattr("ttslab.quality_cast.benchmark_case", fake_benchmark)
    samples = cast_quality(
        ["kokoro", "pocket_tts"],
        output_root=tmp_path / "cast",
        language="en",
        task="general",
        max_cases=1,
    )

    assert len(samples) == 2
    assert seen[0][1] == seen[1][1]
    assert {sample.engine for sample in samples} == {"kokoro", "pocket_tts"}
    assert all(sample.status == "passed" for sample in samples)
    assert all(sample.audio_path for sample in samples)
    assert all(sample.audio_sha256 and len(sample.audio_sha256) == 64 for sample in samples)


def test_cast_quality_keeps_runner_failures_in_evidence(monkeypatch, tmp_path: Path) -> None:
    def broken_benchmark(*args, **kwargs):
        raise RuntimeError("deliberate worker failure")

    monkeypatch.setattr("ttslab.quality_cast.benchmark_case", broken_benchmark)
    samples = cast_quality(
        ["kokoro"],
        output_root=tmp_path / "cast",
        language="en",
        task="general",
        max_cases=1,
    )

    assert len(samples) == 1
    assert samples[0].status == "runner_error"
    assert samples[0].audio_path is None
    assert (tmp_path / "cast" / "kokoro" / "kokoro__en_basic.json").is_file()
