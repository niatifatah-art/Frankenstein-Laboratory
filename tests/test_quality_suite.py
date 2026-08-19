import json
from pathlib import Path

import pytest

from ttslab.quality_suite import (
    ListeningRating,
    QualitySample,
    aggregate_objective,
    build_listening_packet,
    build_release_evidence,
    normalize_transcript,
    quality_cases,
    score_transcript,
)


def _sample(engine: str, case_key: str, hypothesis: str | None, *, status: str = "passed") -> QualitySample:
    return QualitySample(
        engine=engine,
        case_key=case_key,
        language="en",
        task="general",
        reference_text="Hello, reproducible world!",
        hypothesis_text=hypothesis,
        status=status,
        evidence_ref=f"artifact:{engine}:{case_key}",
        audio_path=f"audio/{engine}/{case_key}.wav",
        audio_sha256=(engine + case_key).encode().hex().ljust(64, "0")[:64],
    )


def test_transcript_normalization_is_unicode_and_punctuation_stable() -> None:
    assert normalize_transcript("  HELLO—World!  ") == "hello world"
    assert normalize_transcript("Ｈｅｌｌｏ") == "hello"


def test_score_transcript_reports_wer_and_cer() -> None:
    perfect = score_transcript("Hello, world!", "hello world")
    assert perfect.wer == 0.0
    assert perfect.cer == 0.0

    changed = score_transcript("hello world", "hello duck")
    assert changed.reference_words == 2
    assert changed.word_errors == 1
    assert changed.wer == 0.5
    assert 0.0 < changed.cer < 1.0


def test_empty_reference_does_not_divide_by_zero() -> None:
    assert score_transcript("", "").wer == 0.0
    assert score_transcript("", "hallucination").wer == 1.0


def test_existing_corpus_is_reused_for_quality_tasks() -> None:
    english_general = quality_cases(language="en", task="general")
    keys = {case.key for case in english_general}
    assert "en_basic" in keys
    assert "elongated" in keys
    assert "clone_target" not in keys

    cloning = quality_cases(language="en", task="cloning")
    assert [case.key for case in cloning] == ["clone_target"]


def test_objective_aggregation_uses_corpus_level_error_counts() -> None:
    samples = (
        _sample("pocket_tts", "a", "hello reproducible world"),
        _sample("pocket_tts", "b", "hello broken world"),
        _sample("pocket_tts", "c", None, status="failed"),
    )
    summary = aggregate_objective(samples)[0]
    assert summary.samples == 3
    assert summary.evaluated_transcripts == 2
    assert summary.failures == 1
    assert summary.failure_rate == pytest.approx(1 / 3)
    assert summary.reference_words == 6
    assert summary.word_errors == 1
    assert summary.wer == pytest.approx(1 / 6)


def test_listening_packet_hides_engine_identity_and_is_deterministic() -> None:
    samples = (
        _sample("kokoro", "en_basic", "hello reproducible world"),
        _sample("pocket_tts", "en_basic", "hello reproducible world"),
    )
    packet_a, mapping_a = build_listening_packet(samples, seed="fixed")
    packet_b, mapping_b = build_listening_packet(reversed(samples), seed="fixed")
    assert packet_a == packet_b
    assert mapping_a == mapping_b
    assert len(packet_a["samples"]) == 2
    assert "engine" not in packet_a["samples"][0]
    assert set(mapping_a["mapping"].values())
    assert {value["engine"] for value in mapping_a["mapping"].values()} == {
        "kokoro",
        "pocket_tts",
    }


def test_release_evidence_requires_real_human_ratings_and_minimum_samples() -> None:
    samples = tuple(
        _sample("kokoro", f"case-{index}", "hello reproducible world")
        for index in range(10)
    )
    packet, mapping = build_listening_packet(samples, seed="release")

    too_few = [
        ListeningRating(item["blind_id"], 4.0)
        for item in packet["samples"][:9]
    ]
    assert not build_release_evidence(
        samples,
        too_few,
        mapping,
        evidence_ref="artifact:quality-cast",
        minimum_samples=10,
    )

    ratings = [ListeningRating(item["blind_id"], 4.2) for item in packet["samples"]]
    evidence = build_release_evidence(
        samples,
        ratings,
        mapping,
        evidence_ref="artifact:quality-cast",
        minimum_samples=10,
    )
    assert len(evidence) == 1
    item = evidence[0]
    assert item.engine == "kokoro"
    assert item.samples == 10
    assert item.naturalness_mos == pytest.approx(4.2)
    assert item.wer == 0.0
    assert item.failure_rate == 0.0


def test_duplicate_blind_rating_is_rejected() -> None:
    samples = (_sample("kokoro", "a", "hello reproducible world"),)
    packet, mapping = build_listening_packet(samples, seed="duplicate")
    blind_id = packet["samples"][0]["blind_id"]
    ratings = [ListeningRating(blind_id, 4.0), ListeningRating(blind_id, 4.5)]
    with pytest.raises(ValueError, match="duplicate listening rating"):
        build_release_evidence(
            samples,
            ratings,
            mapping,
            evidence_ref="artifact:test",
            minimum_samples=1,
        )


def test_quality_sample_json_shape_is_portable(tmp_path: Path) -> None:
    sample = _sample("kokoro", "arabic-path", "hello reproducible world")
    path = tmp_path / "نتائج quality.json"
    path.write_text(json.dumps({"samples": [sample.to_dict()]}, ensure_ascii=False), encoding="utf-8")
    assert "نتائج" in path.name
