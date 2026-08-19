from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeInputs:
    language: str | None = None
    voice: str | None = None
    reference: Path | None = None
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


def adapter_args(engine_key: str, inputs: RuntimeInputs) -> list[str]:
    """Translate normalized OurTTS inputs into one worker's explicit CLI arguments.

    This mapping is deliberately small and auditable. Unknown controls are not silently converted.
    """
    args: list[str] = []
    language = inputs.language.casefold() if inputs.language else None
    controls = inputs.controls or {}

    if engine_key == "pocket_tts":
        _append_language(args, language, _POCKET_LANG)
        if inputs.voice:
            args.extend(["--voice", inputs.voice])
        return args

    if engine_key == "kokoro":
        _append_language(args, language, _KOKORO_LANG)
        if inputs.voice:
            args.extend(["--voice", inputs.voice])
        if "pace" in controls:
            args.extend(["--speed", str(float(controls["pace"]))])
        return args

    if engine_key == "melotts":
        _append_language(args, language, _MELO_LANG)
        if "pace" in controls:
            args.extend(["--speed", str(float(controls["pace"]))])
        return args

    if engine_key == "chatterbox_v3":
        if language:
            args.extend(["--language", language])
        if inputs.reference:
            args.extend(["--reference", str(inputs.reference)])
        return args

    if engine_key in {"chatterbox_base", "chatterbox_nano", "chatterbox_turbo"}:
        if inputs.reference:
            args.extend(["--reference", str(inputs.reference)])
        if engine_key == "chatterbox_base":
            if "exaggeration" in controls:
                args.extend(["--exaggeration", str(float(controls["exaggeration"]))])
            if "cfg_weight" in controls:
                args.extend(["--cfg-weight", str(float(controls["cfg_weight"]))])
        return args

    if engine_key.startswith("qwen3_"):
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
        if inputs.reference:
            args.extend(["--reference", str(inputs.reference)])
        return args

    return args


def engine_requires_reference(engine_key: str) -> bool:
    return engine_key == "qwen3_base_06b"


def _append_language(args: list[str], language: str | None, mapping: dict[str, str]) -> None:
    if language is None:
        return
    try:
        worker_language = mapping[language]
    except KeyError as exc:
        raise ValueError(f"No verified adapter language mapping for {language!r}") from exc
    args.extend(["--language", worker_language])
