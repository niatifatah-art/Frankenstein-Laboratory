from pathlib import Path

from ttslab.audio import inspect_wav, sha256_file
from ttslab.benchmark import load_corpus
from ttslab.registry import get_engine, load_registry, validate_registry
from ttslab.router import RouteRequest, route_engines

ROOT = Path(__file__).parents[1]


def test_registry_is_structurally_valid() -> None:
    assert validate_registry(ROOT / "registry" / "engines.toml") == ()


def test_runtime_families_are_registered() -> None:
    for key in [
        "kokoro",
        "pocket_tts",
        "chatterbox_nano",
        "qwen3_custom_06b",
        "qwen3_voice_design_17b",
        "cosyvoice3",
        "voxcpm2",
        "openvoice_v2",
        "melotts",
        "vibevoice_realtime",
    ]:
        assert get_engine(key, ROOT / "registry" / "engines.toml").name


def test_shared_corpus_is_broad() -> None:
    cases = load_corpus(ROOT / "benchmarks" / "corpus.json")
    tags = {tag for case in cases for tag in case.tags}
    assert len(cases) >= 20
    assert {
        "arabic",
        "french",
        "russian",
        "code_switch",
        "numbers",
        "url",
        "dialogue",
        "pronunciation",
        "long_form",
    } <= tags


def test_qualification_overlay_promotes_only_evidenced_backends() -> None:
    registry = ROOT / "registry" / "engines.toml"
    nano = get_engine("chatterbox_nano", registry)
    qwen = get_engine("qwen3_custom_06b", registry)
    voice_design = get_engine("qwen3_voice_design_17b", registry)
    assert nano.integration_status == "ready" and nano.artifact_digest
    assert qwen.integration_status == "ready" and qwen.qualification_run == 32180309921
    assert voice_design.integration_status == "adapter_ready" and not voice_design.artifact_digest


def test_router_selects_only_qualified_capability_matches() -> None:
    records = load_registry(ROOT / "registry" / "engines.toml")
    routed = route_engines(RouteRequest(require=("cpu",)), records=records)
    assert routed
    assert all(item.engine.integration_status == "ready" for item in routed)
    assert all(item.engine.supports("cpu") for item in routed)
    keys = {item.engine.key for item in routed}
    assert {"kokoro", "pocket_tts", "chatterbox_nano"} <= keys
    assert "qwen3_custom_06b" not in keys


def test_audio_validation_rejects_non_wav(tmp_path: Path) -> None:
    path = tmp_path / "bad.wav"
    path.write_text("not wav")
    try:
        inspect_wav(path)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid WAV unexpectedly accepted")
    assert sha256_file(path)
