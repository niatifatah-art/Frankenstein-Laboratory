from pathlib import Path

from ttslab.registry import get_engine, load_registry

REGISTRY = Path(__file__).parents[1] / "registry" / "engines.toml"


def test_registry_has_initial_candidates() -> None:
    keys = {engine.key for engine in load_registry(REGISTRY)}
    assert {"kokoro", "pocket_tts", "chatterbox", "qwen3_tts", "cosyvoice", "voxcpm2"} <= keys


def test_unknown_licenses_are_explicit() -> None:
    for engine in load_registry(REGISTRY):
        assert engine.code_license
        assert engine.weights_license
        assert engine.license_status


def test_qwen_code_license_recorded_separately() -> None:
    qwen = get_engine("qwen3_tts", REGISTRY)
    assert qwen.code_license == "Apache-2.0"
    assert qwen.weights_license == "unknown"
