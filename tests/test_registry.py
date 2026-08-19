from pathlib import Path

from ttslab.registry import get_engine, load_registry, validate_registry

REGISTRY = Path(__file__).parents[1] / "registry" / "engines.toml"


def test_registry_has_runtime_and_research_candidates() -> None:
    keys = {engine.key for engine in load_registry(REGISTRY)}
    assert {
        "kokoro",
        "pocket_tts",
        "chatterbox",
        "qwen3_tts",
        "cosyvoice",
        "cosyvoice3",
        "voxcpm2",
        "openvoice_v2",
        "melotts",
        "vibevoice_realtime",
    } <= keys


def test_licenses_are_explicit() -> None:
    for engine in load_registry(REGISTRY):
        assert engine.code_license
        assert engine.weights_license
        assert engine.license_status


def test_qwen_code_and_weights_are_verified_separately() -> None:
    qwen = get_engine("qwen3_tts", REGISTRY)
    assert qwen.code_license == "Apache-2.0"
    assert qwen.weights_license == "Apache-2.0"
    assert qwen.license_status == "verified"


def test_registry_validation_passes() -> None:
    assert validate_registry(REGISTRY) == ()
