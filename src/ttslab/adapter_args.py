from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .registry import EngineRecord


@dataclass(frozen=True, slots=True)
class AdapterArguments:
    args: tuple[str, ...]
    unsupported: tuple[str, ...] = ()
    effective_language: str | None = None


_KOKORO_LANG = {
    "en": "a",
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "ja": "j",
    "pt": "p",
    "pt-br": "p",
    "zh": "z",
}
_POCKET_LANG = {
    "en": "english",
    "fr": "french_24l",
    "de": "german_24l",
    "pt": "portuguese",
    "it": "italian",
    "es": "spanish_24l",
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
_MELO_LANG = {"en": "EN", "es": "ES", "fr": "FR", "zh": "ZH", "ja": "JP", "ko": "KR"}


def _lang(language: str | None, mapping: dict[str, str]) -> str | None:
    if language is None:
        return None
    key = language.strip().casefold().replace("_", "-")
    if key in mapping:
        return mapping[key]
    primary = key.split("-", 1)[0]
    return mapping.get(primary)


def _add_path(args: list[str], flag: str, value: Path | None) -> None:
    if value is not None:
        args.extend([flag, str(value.resolve())])


def compile_adapter_args(
    engine: EngineRecord,
    *,
    language: str | None = None,
    voice: str | None = None,
    reference: Path | None = None,
    reference_text: str | None = None,
    voice_design: str | None = None,
    style: str | None = None,
    speed: float | None = None,
    device: str | None = None,
) -> AdapterArguments:
    """Translate stable OurTTS concepts into one worker's explicit CLI contract.

    Unsupported concepts are returned rather than silently discarded.
    """
    key = engine.key
    args: list[str] = []
    unsupported: list[str] = []
    effective_language: str | None = None

    if language:
        if key == "kokoro":
            effective_language = _lang(language, _KOKORO_LANG)
            if effective_language:
                args += ["--language", effective_language]
            else:
                unsupported.append("language")
        elif key == "pocket_tts":
            effective_language = _lang(language, _POCKET_LANG)
            if effective_language:
                args += ["--language", effective_language]
            else:
                unsupported.append("language")
        elif key.startswith("qwen3_"):
            effective_language = _lang(language, _QWEN_LANG)
            if effective_language:
                args += ["--language", effective_language]
            else:
                unsupported.append("language")
        elif key == "melotts":
            effective_language = _lang(language, _MELO_LANG)
            if effective_language:
                args += ["--language", effective_language]
            else:
                unsupported.append("language")
        elif key == "chatterbox_v3":
            effective_language = language.strip().casefold().split("-", 1)[0]
            args += ["--language", effective_language]
        elif key.startswith("chatterbox_"):
            if language.strip().casefold().split("-", 1)[0] != "en":
                unsupported.append("language")
            else:
                effective_language = "en"
        elif key == "voxcpm2":
            effective_language = language
        else:
            effective_language = language

    if voice:
        if key == "kokoro" or (key == "pocket_tts" and reference is None):
            args += ["--voice", voice]
        elif key == "qwen3_custom_06b":
            args += ["--speaker", voice]
        else:
            unsupported.append("voice")

    if reference is not None:
        if key == "pocket_tts":
            if voice:
                unsupported.append("voice_with_reference")
            args += ["--voice", str(reference.resolve())]
        elif key.startswith("chatterbox_") or key in {"qwen3_base_06b", "voxcpm2"}:
            _add_path(args, "--reference", reference)
        else:
            unsupported.append("reference")

    if reference_text:
        if key in {"qwen3_base_06b", "voxcpm2"}:
            args += ["--reference-text", reference_text]
        else:
            unsupported.append("reference_text")

    design = voice_design or style
    if design:
        if key == "qwen3_voice_design_17b":
            args += ["--instruct", design]
        elif key == "qwen3_custom_06b" and style:
            args += ["--instruct", style]
        elif key == "voxcpm2":
            args += ["--voice-design", design]
        else:
            unsupported.append("voice_design" if voice_design else "style")

    if speed is not None:
        if key in {"kokoro", "melotts"}:
            args += ["--speed", str(speed)]
        else:
            unsupported.append("speed")

    if device and device != "auto":
        if key.startswith("chatterbox_") or key.startswith("qwen3_") or key in {"voxcpm2", "melotts"}:
            args += ["--device", device]
        elif device != "cpu":
            unsupported.append("device")

    return AdapterArguments(
        args=tuple(args),
        unsupported=tuple(sorted(set(unsupported))),
        effective_language=effective_language,
    )


def render_kokoro_phoneme_overrides(text: str, overrides: tuple[object, ...]) -> str:
    """Render generic structured phoneme overrides using Kokoro's documented inline syntax."""
    phonemes = [item for item in overrides if getattr(item, "mode", None) == "phoneme"]
    rendered = text
    for item in sorted(phonemes, key=lambda entry: int(getattr(entry, "start")), reverse=True):
        start = int(getattr(item, "start"))
        end = int(getattr(item, "end"))
        replacement = str(getattr(item, "replacement"))
        surface = rendered[start:end]
        if not surface:
            continue
        rendered = rendered[:start] + f"[{surface}](/{replacement}/)" + rendered[end:]
    return rendered
