import hashlib
import json
from pathlib import Path

import pytest

from ttslab.product_cli import main as product_main
from ttslab.product_contract import GenerationRequest
from ttslab.product_runtime import plan_generation
from ttslab.voicepack import BackendVoiceState, ReferenceClip, VoicePack

REVISION = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"


def _quality_ledger(path: Path) -> Path:
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
                        "naturalness_mos": 4.0,
                        "wer": 0.05,
                        "failure_rate": 0.02,
                        "suite_version": "ourtts-quality-v1",
                        "evidence_ref": "artifact:pocket",
                    },
                    {
                        "engine": "kokoro",
                        "language": "en",
                        "task": "general",
                        "samples": 20,
                        "naturalness_mos": 4.6,
                        "wer": 0.04,
                        "failure_rate": 0.01,
                        "suite_version": "ourtts-quality-v1",
                        "evidence_ref": "artifact:kokoro",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _prepared_voicepack(root: Path, *, stale: bool = False) -> Path:
    reference = root / "refs" / "voice.wav"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"synthetic-reference")
    reference_digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    state = root / "backend_states" / "chatterbox_nano.conds.pt"
    state.parent.mkdir(parents=True)
    state.write_bytes(b"prepared-conditionals")
    state_digest = hashlib.sha256(state.read_bytes()).hexdigest()
    pack = VoicePack(
        voice_id="creator",
        display_name="Creator",
        languages=("en",),
        references=(
            ReferenceClip(
                path="refs/voice.wav",
                sha256=reference_digest,
                license="test-only",
                source="synthetic test",
                consent="synthetic",
            ),
        ),
        backend_states=(
            BackendVoiceState(
                engine="chatterbox_nano",
                path="backend_states/chatterbox_nano.conds.pt",
                model_revision="stale" if stale else REVISION,
                sha256=state_digest,
                format="chatterbox-conditionals-pt-v1",
                source_reference_sha256=reference_digest,
                adapter_version="0.2.0",
            ),
        ),
        provenance={"synthetic": True},
    )
    pack.save(root)
    return root


def test_auto_natural_english_prefers_measured_fast_backend() -> None:
    plan = plan_generation(GenerationRequest(text="Hello", language="en"))
    assert plan.engine == "pocket_tts"
    assert plan.controls == {}
    assert plan.routing_reasons


def test_fast_mode_enforces_realtime_measured_route() -> None:
    plan = plan_generation(GenerationRequest(text="Hello", language="en", quality="fast"))
    assert plan.engine == "pocket_tts"
    assert plan.max_generation_rtf == 1.0


def test_non_natural_style_routes_only_to_verified_style_adapter() -> None:
    plan = plan_generation(
        GenerationRequest(text="Hello", language="en", style="energetic", quality="auto")
    )
    assert plan.engine == "qwen3_custom_06b"
    assert plan.controls == {"style": "energetic"}


def test_fast_expressive_request_fails_instead_of_ignoring_style() -> None:
    with pytest.raises(ValueError, match="No qualified TTS backend"):
        plan_generation(
            GenerationRequest(text="Hello", language="en", style="energetic", quality="fast")
        )


def test_best_mode_waits_for_real_quality_evidence() -> None:
    with pytest.raises(ValueError, match="No release-quality evidence"):
        plan_generation(GenerationRequest(text="Hello", language="en", quality="best"))


def test_best_mode_can_choose_slower_engine_when_quality_evidence_wins(tmp_path: Path) -> None:
    plan = plan_generation(
        GenerationRequest(text="Hello", language="en", quality="best"),
        quality_ledger_path=_quality_ledger(tmp_path / "quality.json"),
    )
    assert plan.engine == "kokoro"
    assert plan.metadata["product"]["routing"]["quality_evidence"]["engine"] == "kokoro"
    assert plan.routing_reasons[0].startswith("measured Best score")


def test_best_requires_language_scoped_evidence() -> None:
    with pytest.raises(ValueError, match="Best requires an explicit language"):
        plan_generation(GenerationRequest(text="Hello", quality="best"))


def test_product_voice_id_requires_voicepack_mapping() -> None:
    with pytest.raises(ValueError, match="requires a VoicePack mapping"):
        plan_generation(GenerationRequest(text="Hello", language="en", voice="creator_voice"))


def test_product_prefers_compatible_prepared_state_over_reference(tmp_path: Path) -> None:
    voicepack = _prepared_voicepack(tmp_path / "voice")
    plan = plan_generation(
        GenerationRequest(text="Hello", language="en", voice="creator"),
        voicepack_root=voicepack,
    )
    assert plan.engine == "chatterbox_nano"
    assert plan.reference is None
    assert plan.voice_state is not None
    assert plan.voice_state.name == "chatterbox_nano.conds.pt"
    assert plan.metadata["voicepack"]["prepared_state"]["status"] == "used"
    assert "using verified prepared VoicePack state" in plan.routing_reasons


def test_stale_prepared_state_falls_back_to_verified_reference(tmp_path: Path) -> None:
    voicepack = _prepared_voicepack(tmp_path / "voice", stale=True)
    plan = plan_generation(
        GenerationRequest(text="Hello", language="en", voice="creator"),
        voicepack_root=voicepack,
    )
    assert plan.engine == "chatterbox_nano"
    assert plan.reference is not None
    assert plan.voice_state is None
    assert plan.metadata["voicepack"]["prepared_state"]["status"] == "stale_model_revision"


def test_simple_plan_cli_hides_backend_until_after_routing(capsys) -> None:
    assert product_main(["plan", "--text", "Hello", "--language", "en"]) == 0
    output = capsys.readouterr().out
    assert "ourTTS will use: pocket_tts" in output
    assert "why:" in output
