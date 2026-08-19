import pytest

from ttslab.product_contract import GenerationRequest, ResolvedGeneration, request_example


def test_default_request_is_simple() -> None:
    request = GenerationRequest(text="Hello")
    assert request.quality == "auto"
    assert request.style == "natural"
    assert request.controls == {}


def test_user_facing_quality_modes_are_small_and_explicit() -> None:
    for quality in ("auto", "fast", "best", "local"):
        assert GenerationRequest(text="Hello", quality=quality).quality == quality
    with pytest.raises(ValueError, match="quality must be one of"):
        GenerationRequest(text="Hello", quality="ultra-secret-engine-mode")


def test_empty_text_is_refused_early() -> None:
    with pytest.raises(ValueError, match="text must not be empty"):
        GenerationRequest(text="   ")


def test_resolved_generation_keeps_routing_evidence() -> None:
    request = GenerationRequest(text="Hello", quality="auto")
    result = ResolvedGeneration(
        request=request,
        engine="pocket_tts",
        routing_reasons=("qualified", "measured CPU fit"),
    )
    payload = result.to_dict()
    assert payload["request"]["quality"] == "auto"
    assert payload["engine"] == "pocket_tts"
    assert payload["routing_reasons"] == ("qualified", "measured CPU fit")


def test_public_example_hides_backend_choice() -> None:
    example = request_example()
    assert example["quality"] == "auto"
    assert "engine" not in example
