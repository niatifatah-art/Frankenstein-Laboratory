import json
from pathlib import Path

import pytest

from ttslab.quality import QualityEvidence, load_quality_ledger


def _write_ledger(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "suite_version": "ourtts-quality-v1",
                "minimum_samples": 10,
                "evidence": [
                    {
                        "engine": "pocket_tts",
                        "language": "en",
                        "task": "general",
                        "samples": 20,
                        "naturalness_mos": 4.1,
                        "wer": 0.06,
                        "failure_rate": 0.02,
                        "suite_version": "ourtts-quality-v1",
                        "evidence_ref": "artifact:test-pocket",
                    },
                    {
                        "engine": "kokoro",
                        "language": "en",
                        "task": "general",
                        "samples": 20,
                        "naturalness_mos": 4.5,
                        "wer": 0.04,
                        "failure_rate": 0.01,
                        "suite_version": "ourtts-quality-v1",
                        "evidence_ref": "artifact:test-kokoro",
                    },
                    {
                        "engine": "melotts",
                        "language": "en",
                        "task": "general",
                        "samples": 3,
                        "naturalness_mos": 5.0,
                        "wer": 0.0,
                        "failure_rate": 0.0,
                        "suite_version": "ourtts-quality-v1",
                        "evidence_ref": "artifact:too-small",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_quality_score_rewards_measured_naturalness_intelligibility_and_stability() -> None:
    weaker = QualityEvidence(
        engine="a",
        language="en",
        task="general",
        samples=10,
        naturalness_mos=3.5,
        wer=0.10,
        failure_rate=0.05,
        suite_version="v1",
        evidence_ref="artifact:a",
    )
    stronger = QualityEvidence(
        engine="b",
        language="en",
        task="general",
        samples=10,
        naturalness_mos=4.5,
        wer=0.04,
        failure_rate=0.01,
        suite_version="v1",
        evidence_ref="artifact:b",
    )
    assert stronger.score > weaker.score


def test_ledger_filters_under_sampled_and_ineligible_engines(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    _write_ledger(path)
    ledger = load_quality_ledger(path)
    ranked = ledger.ranked(language="en", eligible_engines={"pocket_tts", "melotts"})
    assert [item.engine for item in ranked] == ["pocket_tts"]


def test_best_uses_measured_score_not_engine_speed(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    _write_ledger(path)
    best = load_quality_ledger(path).best(
        language="en",
        task="general",
        eligible_engines={"pocket_tts", "kokoro"},
    )
    assert best.engine == "kokoro"
    assert best.evidence_ref == "artifact:test-kokoro"


def test_empty_evidence_keeps_best_disabled(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "suite_version": "ourtts-quality-v1",
                "minimum_samples": 10,
                "evidence": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="No release-quality evidence"):
        load_quality_ledger(path).best(language="en")
