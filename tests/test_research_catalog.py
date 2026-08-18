from pathlib import Path

from ttslab.registry import get_engine, load_registry, validate_registry

ROOT = Path(__file__).parents[1]
REGISTRY = ROOT / "registry" / "engines.toml"
RESEARCH_SWEEP_KEYS = {
    "dia2",
    "glm_tts",
    "styletts2",
    "fireredtts2",
    "csm_sesame",
    "bark",
    "f5_tts",
    "spark_tts",
    "fish_speech",
    "higgs_audio",
    "xtts_v2",
    "indextts2",
    "megatts3",
    "orpheus_tts",
}


def test_constitution_research_candidates_are_catalogued() -> None:
    keys = {engine.key for engine in load_registry(REGISTRY)}
    assert RESEARCH_SWEEP_KEYS <= keys


def test_research_catalog_never_becomes_routable_by_accident() -> None:
    for engine in load_registry(REGISTRY):
        if engine.zone == "research":
            assert not engine.runnable


def test_all_swept_research_sources_are_pinned() -> None:
    for key in RESEARCH_SWEEP_KEYS:
        engine = get_engine(key, REGISTRY)
        assert engine.source_revision and len(engine.source_revision) == 40
        assert engine.qualification_run == 32183788463
        assert engine.artifact_id == 9341702081


def test_restricted_models_are_explicit() -> None:
    f5 = get_engine("f5_tts", REGISTRY)
    fish = get_engine("fish_speech", REGISTRY)
    mega = get_engine("megatts3", REGISTRY)
    assert f5.commercial_use == "research_only"
    assert fish.commercial_use == "research_only"
    assert mega.commercial_use == "research_only"
    assert "NC" in f5.weights_license


def test_full_registry_with_research_catalog_validates() -> None:
    assert validate_registry(REGISTRY) == ()
