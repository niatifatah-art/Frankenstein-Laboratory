from pathlib import Path

from ttslab.registry import get_engine

REGISTRY = Path(__file__).parents[1] / "registry" / "engines.toml"


def test_current_primary_source_license_overrides_are_effective() -> None:
    assert get_engine("dia2", REGISTRY).weights_license == "Apache-2.0"
    assert get_engine("glm_tts", REGISTRY).weights_license == "MIT"
    assert get_engine("fireredtts2", REGISTRY).weights_license == "Apache-2.0"
    assert get_engine("spark_tts", REGISTRY).weights_license == "CC-BY-NC-SA-4.0"
    assert get_engine("higgs_audio", REGISTRY).commercial_use == "research_only"
    assert get_engine("orpheus_tts", REGISTRY).weights_license == "Apache-2.0"


def test_openvoice_is_qualified_component_not_fake_tts() -> None:
    openvoice = get_engine("openvoice_v2", REGISTRY)
    assert openvoice.kind == "voice_conversion"
    assert openvoice.integration_status == "qualified_component"
    assert openvoice.qualification_run == 32186303818
    assert openvoice.artifact_digest
