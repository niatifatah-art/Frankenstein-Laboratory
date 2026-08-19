from pathlib import Path

import pytest

from ttslab.adapter_runtime import (
    RuntimeInputs,
    adapter_args,
    adapter_supported_controls,
    adapter_supports_reference,
    engine_requires_reference,
)


def test_language_mapping_is_explicit() -> None:
    assert adapter_args("pocket_tts", RuntimeInputs(language="fr")) == [
        "--language",
        "french_24l",
    ]
    assert adapter_args("kokoro", RuntimeInputs(language="en-gb")) == ["--language", "b"]
    assert adapter_args("melotts", RuntimeInputs(language="ja")) == ["--language", "JP"]
    assert adapter_args("qwen3_custom_06b", RuntimeInputs(language="ru")) == [
        "--language",
        "Russian",
    ]


def test_unknown_verified_mapping_is_rejected() -> None:
    with pytest.raises(ValueError):
        adapter_args("pocket_tts", RuntimeInputs(language="ar"))


def test_reference_and_voice_are_mapped_without_guessing(tmp_path: Path) -> None:
    reference = tmp_path / "voice.wav"
    args = adapter_args(
        "qwen3_base_06b",
        RuntimeInputs(language="en", reference=reference),
    )
    assert args == ["--language", "English", "--reference", str(reference)]
    assert engine_requires_reference("qwen3_base_06b") is True
    assert engine_requires_reference("pocket_tts") is False
    assert adapter_supports_reference("qwen3_base_06b") is True


def test_reference_is_never_silently_ignored(tmp_path: Path) -> None:
    reference = tmp_path / "voice.wav"
    with pytest.raises(ValueError, match="does not consume reference audio"):
        adapter_args("kokoro", RuntimeInputs(language="en", reference=reference))
    with pytest.raises(ValueError, match="does not consume reference audio"):
        adapter_args("pocket_tts", RuntimeInputs(language="en", reference=reference))


def test_normalized_controls_require_real_adapter_mapping() -> None:
    assert adapter_supported_controls("qwen3_custom_06b") == frozenset({"style"})
    assert adapter_args(
        "qwen3_custom_06b",
        RuntimeInputs(language="en", controls={"style": "warm narrator"}),
    ) == ["--language", "English", "--instruct", "warm narrator"]
    with pytest.raises(ValueError, match="does not translate controls"):
        adapter_args("pocket_tts", RuntimeInputs(controls={"style": "warm"}))
