import json
import wave
from pathlib import Path

import pytest

from ttslab.isolation import WorkerExecution
from ttslab.pronunciation import PronunciationEntry, PronunciationLexicon
from ttslab.rendering import parse_render_script, render_text


def _write_pcm(path: Path, *, frames: int = 100, rate: int = 1000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x01\x00" * frames)


def test_render_script_preserves_leading_middle_and_trailing_pauses() -> None:
    script = parse_render_script(
        "[[pause:50ms]] Hello [[pause:200ms]][[pause:50ms]] world [[pause:75ms]]"
    )
    assert script.leading_silence_ms == 50
    assert [chunk.pause_after_ms for chunk in script.chunks] == [250, 75]
    assert [chunk.text.strip() for chunk in script.chunks] == ["Hello", "world"]


def test_non_pause_inline_control_is_not_silently_ignored() -> None:
    with pytest.raises(ValueError, match="unsupported markers"):
        parse_render_script("Hello [[emotion:happy]] world")


def test_owned_renderer_selects_backend_preprocesses_and_inserts_exact_silence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = []

    def fake_execute(key, *, text, output, extra_args, timeout_seconds):
        calls.append((key, text, tuple(extra_args)))
        _write_pcm(output)
        return WorkerExecution(
            command=("fake",),
            returncode=0,
            stdout='{"ok": true}',
            stderr="",
            payload={"ok": True, "text": text},
        )

    monkeypatch.setattr("ttslab.rendering.execute_worker", fake_execute)
    lexicon = PronunciationLexicon([PronunciationEntry("DevShelf", "dev shelf")])
    output = tmp_path / "final.wav"
    manifest = render_text(
        "[[pause:50ms]] DevShelf speaks. [[pause:250ms]] Again.",
        output,
        language="en",
        lexicon=lexicon,
        max_generation_rtf=2.0,
    )

    assert manifest["engine"] == "pocket_tts"
    assert calls[0][1] == "dev shelf speaks."
    assert calls[0][2] == ("--language", "english")
    assert manifest["schema_version"] == 2
    assert manifest["leading_silence_ms"] == 50
    assert manifest["segments"][0]["pause_after_ms"] == 250
    assert manifest["final_audio"]["frames"] == 50 + 100 + 250 + 100
    assert output.exists()
    saved = json.loads(output.with_suffix(".wav.manifest.json").read_text())
    assert saved["final_audio"]["sha256"] == manifest["final_audio"]["sha256"]


def test_reference_requires_a_real_cloning_adapter(tmp_path: Path, monkeypatch) -> None:
    def should_not_run(*args, **kwargs):
        raise AssertionError("worker must not run when reference audio would be ignored")

    monkeypatch.setattr("ttslab.rendering.execute_worker", should_not_run)
    reference = tmp_path / "voice.wav"
    reference.write_bytes(b"reference")
    with pytest.raises(ValueError, match="does not consume reference audio"):
        render_text(
            "hello",
            tmp_path / "never.wav",
            language="en",
            engine_key="pocket_tts",
            reference=reference,
        )


def test_verified_normalized_style_control_reaches_worker(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_execute(key, *, text, output, extra_args, timeout_seconds):
        calls.append((key, text, tuple(extra_args)))
        _write_pcm(output)
        return WorkerExecution(
            command=("fake",),
            returncode=0,
            stdout='{"ok": true}',
            stderr="",
            payload={"ok": True},
        )

    monkeypatch.setattr("ttslab.rendering.execute_worker", fake_execute)
    manifest = render_text(
        "hello",
        tmp_path / "styled.wav",
        language="en",
        engine_key="qwen3_custom_06b",
        controls={"style": "warm narrator"},
    )
    assert calls[0][0] == "qwen3_custom_06b"
    assert calls[0][2] == ("--language", "English", "--instruct", "warm narrator")
    assert manifest["controls"] == {"style": "warm narrator"}


def test_mixed_phoneme_override_is_refused_until_adapter_support_is_real(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def should_not_run(*args, **kwargs):
        raise AssertionError("worker must not run when a phoneme override cannot be rendered")

    monkeypatch.setattr("ttslab.rendering.execute_worker", should_not_run)
    lexicon = PronunciationLexicon(
        [PronunciationEntry("Yessss", "jɛːs", mode="phoneme")]
    )
    with pytest.raises(ValueError, match="not integrated"):
        render_text(
            "Yessss!",
            tmp_path / "never.wav",
            language="en",
            lexicon=lexicon,
            max_generation_rtf=2.0,
        )
