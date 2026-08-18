from ttslab.pipeline import build_synthesis_plan
from ttslab.pronunciation import PronunciationEntry, PronunciationLexicon
from ttslab.registry import EngineRecord
from ttslab.router import RouteRequest, route_engines


def _engine(key: str, *, rtf: float, capabilities: tuple[str, ...]) -> EngineRecord:
    return EngineRecord(
        key=key,
        name=key,
        upstream="https://example.invalid",
        zone="runtime",
        integration_status="ready",
        code_license="MIT",
        weights_license="MIT",
        license_status="verified",
        worker=key,
        kind="tts",
        commercial_use="allowed",
        capabilities=capabilities,
        languages=("en",),
        hardware=("cpu",),
        cpu_generation_rtf=rtf,
    )


def test_router_uses_measured_cpu_performance() -> None:
    fast = _engine("fast", rtf=0.3, capabilities=("streaming",))
    slow = _engine("slow", rtf=30.0, capabilities=("streaming",))
    candidates = route_engines(
        RouteRequest(language="en", prefer=("streaming",), max_generation_rtf=2.0),
        (slow, fast),
    )
    assert [item.engine.key for item in candidates] == ["fast"]


def test_phoneme_override_is_not_faked(monkeypatch) -> None:
    engine = _engine("plain", rtf=0.5, capabilities=())
    monkeypatch.setattr("ttslab.pipeline.get_engine", lambda _: engine)
    lexicon = PronunciationLexicon(
        [PronunciationEntry("Yessss", "jɛːs", mode="phoneme")]
    )
    plan = build_synthesis_plan(
        "Yessss!",
        explicit_engine="plain",
        language="en",
        controls={"pause": 250},
        lexicon=lexicon,
    )
    assert "pause" in plan.controls.core_postprocess
    assert "pronunciation_phoneme_overrides" in plan.controls.unsupported
