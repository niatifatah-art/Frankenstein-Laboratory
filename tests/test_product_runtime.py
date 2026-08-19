import pytest

from ttslab.product_cli import main as product_main
from ttslab.product_contract import GenerationRequest
from ttslab.product_runtime import plan_generation


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
    with pytest.raises(ValueError, match="common quality benchmark"):
        plan_generation(GenerationRequest(text="Hello", language="en", quality="best"))


def test_product_voice_id_requires_voicepack_mapping() -> None:
    with pytest.raises(ValueError, match="requires a VoicePack mapping"):
        plan_generation(GenerationRequest(text="Hello", language="en", voice="creator_voice"))


def test_simple_plan_cli_hides_backend_until_after_routing(capsys) -> None:
    assert product_main(["plan", "--text", "Hello", "--language", "en"]) == 0
    output = capsys.readouterr().out
    assert "ourTTS will use: pocket_tts" in output
    assert "why:" in output
