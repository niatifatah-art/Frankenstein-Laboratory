from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeInputs:
    language: str | None = None
    voice: str | None = None
    reference: Path | None = None
    voice_state: Path | None = None
    controls: dict[str, Any] | None = None


_POCKET_LANG = {
    "en": "english",
    "fr": "french_24l",
    "de": "german_24l",
    "pt": "portuguese",
    "it": "italian",
    "es": "spanish_24l",
}

_KOKORO_LANG = {
    "en": "a",
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "pt": "p",
    "ja": "j",
    "zh": "z",
}

_MELO_LANG = {
    "en": "EN",
    "es": "ES",
    "fr": "FR",
    "zh": "ZH",
    "ja": "JP",
    "ko": "KR",
}

_QWEN_LANG = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}

_NORMALIZED_CONTROL_SUPPORT: dict[str, frozenset[str]] = {
    "kokoro": frozenset({"pace"}),
    "melotts": frozenset({"pace"}),
    "qwen3_custom_06b": frozenset({"style"}),
    "qwen3_voice_design_17b": frozenset({"voice_design"}),
}

_REFERENCE_SUPPORT = frozenset(
    {
        "chatterbox_base",
        "chatterbox_nano",
        "chatterbox_turbo",
        "chatterbox_v3",
        "qwen3_base_06b",
        "voxcpm2",
    }
)

_VOICE_STATE_FORMATS: dict[str, str] = {
    "chatterbox_base": "chatterbox-conditionals-pt-v1",
    "chatterbox_nano": "chatterbox-conditionals-pt-v1",
    "chatterbox_turbo": "chatterbox-conditionals-pt-v1",
    "chatterbox_v3": "chatterbox-conditionals-pt-v1",
}


def adapter_supported_controls(engine_key: str) -> frozenset[str]:
    """Return normalized controls that this adapter actually translates today."""
    return _NORMALIZED_CONTROL_SUPPORT.get(engine_key, frozenset())


def adapter_supports_reference(engine_key: str) -> bool:
    """Return whether the current worker adapter actually consumes a reference-audio path."""
    return engine_key in _REFERENCE_SUPPORT


def adapter_voice_state_format(engine_key: str) -> str | None:
    """Return the exact prepared-state format the adapter can execute, if any."""
    return _VOICE_STATE_FORMATS.get(engine_key)


def adapter_supports_voice_state(engine_key: str) -> bool:
    """Return whether the adapter executes a backend-specific prepared VoicePack state."""
    return adapter_voice_state_format(engine_key) is not None


def adapter_args(engine_key: str, inputs: RuntimeInputs) -> list[str]:
    """Translate normalized OurTTS inputs into one worker's explicit CLI arguments.

    This mapping is deliberately small and auditable. Unknown controls are rejected instead of
    being silently dropped. Prepared voice states are backend-specific and mutually exclusive
    with raw references.
    """
    args: list[str] = []
    language = inputs.language.casefold() if inputs.language else None
    controls = inputs.controls or {}

    if inputs.reference is not None and inputs.voice_state is not None:
        raise ValueError("Reference audio and prepared voice state are mutually exclusive.")
    if inputs.reference is not None and not adapter_supports_reference(engine_key):
        raise ValueError(
            f"Adapter {engine_key!r} does not consume reference audio; refusing to ignore it."
        )
    if inputs.voice_state is not None and not adapter_supports_voice_state(engine_key):
        raise ValueError(
            f"Adapter {engine_key!r} does not consume prepared voice state; refusing to ignore it."
        )

    if engine_key == "pocket_tts":
        _reject_unknown_controls(engine_key, controls, set())
        _append_language(args, language, _POCKET_LANG)
        if inputs.voice:
            args.extend(["--voice", inputs.voice])
        return args

    if engine_key == "kokoro":
        _reject_unknown_controls(engine_key, controls, {"pace"})
        _append_language(args, language, _KOKORO_LANG)
        if inputs.voice:
            args.extend(["--voice", inputs.voice])
        if "pace" in controls:
            args.extend(["--speed", str(float(controls["pace"]))])
        return args

    if engine_key == "melotts":
        _reject_unknown_controls(engine_key, controls, {"pace"})
        _append_language(args, language, _MELO_LANG)
        if "pace" in controls:
            args.extend(["--speed", str(float(controls["pace"]))])
        return args

    if engine_key == "chatterbox_v3":
        _reject_unknown_controls(engine_key, controls, set())
        if language:
            args.extend(["--language", language])
        _append_voice_material(args, inputs)
        return args

    if engine_key in {"chatterbox_base", "chatterbox_nano", "chatterbox_turbo"}:
        allowed = {"exaggeration", "cfg_weight"} if engine_key == "chatterbox_base" else set()
        _reject_unknown_controls(engine_key, controls, allowed)
        _append_voice_material(args, inputs)
        if engine_key == "chatterbox_base":
            if "exaggeration" in controls:
                args.extend(["--exaggeration", str(float(controls["exaggeration"]))])
            if "cfg_weight" in controls:
                args.extend(["--cfg-weight", str(float(controls["cfg_weight"]))])
        return args

    if engine_key.startswith("qwen3_"):
        allowed = set(adapter_supported_controls(engine_key))
        _reject_unknown_controls(engine_key, controls, allowed)
        _append_language(args, language, _QWEN_LANG)
        if inputs.reference:
            args.extend(["--reference", str(inputs.reference)])
        if inputs.voice and engine_key == "qwen3_custom_06b":
            args.extend(["--speaker", inputs.voice])
        if "voice_design" in controls and engine_key == "qwen3_voice_design_17b":
            args.extend(["--instruct", str(controls["voice_design"])])
        if "style" in controls and engine_key == "qwen3_custom_06b":
            args.extend(["--instruct", str(controls["style"])])
        return args

    if engine_key == "voxcpm2":
        _reject_unknown_controls(engine_key, controls, set())
        if inputs.reference:
            args.extend(["--reference", str(inputs.reference)])
        return args

    _reject_unknown_controls(engine_key, controls, set())
    return args


def engine_requires_reference(engine_key: str) -> bool:
    return engine_key == "qwen3_base_06b"


def _append_voice_material(args: list[str], inputs: RuntimeInputs) -> None:
    if inputs.reference is not None:
        args.extend(["--reference", str(inputs.reference)])
    elif inputs.voice_state is not None:
        args.extend(["--voice-state", str(inputs.voice_state)])


def _append_language(args: list[str], language: str | None, mapping: dict[str, str]) -> None:
    if language is None:
        return
    try:
        worker_language = mapping[language]
    except KeyError as exc:
        raise ValueError(f"No verified adapter language mapping for {language!r}") from exc
    args.extend(["--language", worker_language])


def _reject_unknown_controls(engine_key: str, controls: dict[str, Any], allowed: set[str]) -> None:
    unsupported = sorted(set(controls) - allowed)
    if unsupported:
        raise ValueError(
            f"Adapter {engine_key!r} does not translate controls: {', '.join(unsupported)}"
        )
