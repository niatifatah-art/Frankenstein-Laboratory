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


def test_router_does_not_select_unqualified_engines() -> None:
    records = load_registry(ROOT / "registry" / "engines.toml")
    routed = route_engines(RouteRequest(require=("cpu",)), records=records)
    assert routed
    assert all(item.engine.integration_status == "ready" for item in routed)
    assert {item.engine.key for item in routed} <= {"kokoro", "pocket_tts"}


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
