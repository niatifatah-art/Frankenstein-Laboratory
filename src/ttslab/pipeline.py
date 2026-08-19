from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .pronunciation import PronunciationLexicon
from .registry import EngineRecord, get_engine
from .router import RouteRequest, route_engines
from .text_engine import PreparedText, prepare_text

_CONTROL_CAPABILITY = {
    "style": "style_control",
    "emotion": "emotion_control",
    "phoneme": "phoneme_input",
    "voice_design": "voice_design",
    "nonverbal": "paralinguistic_tags",
}
_CORE_POSTPROCESS = {"pause"}


@dataclass(frozen=True, slots=True)
class ControlPlan:
    native: tuple[str, ...]
    core_postprocess: tuple[str, ...]
    unsupported: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SynthesisPlan:
    engine: EngineRecord
    text: PreparedText
    controls: ControlPlan
    requested_controls: dict[str, Any]


def build_synthesis_plan(
    text: str,
    *,
    language: str | None = None,
    explicit_engine: str | None = None,
    controls: dict[str, Any] | None = None,
    lexicon: PronunciationLexicon | None = None,
    max_generation_rtf: float | None = None,
) -> SynthesisPlan:
    requested = dict(controls or {})
    required_capabilities = tuple(
        capability
        for key, capability in _CONTROL_CAPABILITY.items()
        if key in requested and key not in _CORE_POSTPROCESS
    )

    if explicit_engine:
        engine = get_engine(explicit_engine)
        if not engine.runnable or engine.kind != "tts":
            raise ValueError(f"Engine {explicit_engine!r} is not a qualified runnable TTS backend.")
        if language and not engine.supports_language(language):
            raise ValueError(f"Engine {explicit_engine!r} does not advertise language {language!r}.")
    else:
        candidates = route_engines(
            RouteRequest(
                language=language,
                require=required_capabilities,
                max_generation_rtf=max_generation_rtf,
            )
        )
        if not candidates:
            raise ValueError("No qualified TTS backend satisfies the requested plan.")
        engine = candidates[0].engine

    native: list[str] = []
    core: list[str] = []
    unsupported: list[str] = []
    for key in requested:
        if key in _CORE_POSTPROCESS:
            core.append(key)
            continue
        capability = _CONTROL_CAPABILITY.get(key)
        if capability and engine.supports(capability):
            native.append(key)
        else:
            unsupported.append(key)

    prepared = prepare_text(text, language=language, lexicon=lexicon)
    if any(item.mode == "phoneme" for item in prepared.pronunciation_overrides):
        if engine.supports("phoneme_input"):
            native.append("pronunciation_phoneme_overrides")
        else:
            unsupported.append("pronunciation_phoneme_overrides")

    return SynthesisPlan(
        engine=engine,
        text=prepared,
        controls=ControlPlan(
            native=tuple(sorted(set(native))),
            core_postprocess=tuple(sorted(set(core))),
            unsupported=tuple(sorted(set(unsupported))),
        ),
        requested_controls=requested,
    )
