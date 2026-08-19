from pathlib import Path

import pytest

from ttslab.isolation import build_worker_command, get_worker
from ttslab.registry import get_engine

REGISTRY = Path(__file__).parents[1] / "registry" / "engines.toml"


def test_kokoro_worker_is_registered_and_ready() -> None:
    record = get_engine("kokoro", REGISTRY)
    assert record.worker == "kokoro"
    assert record.integration_status == "ready"


def test_pocket_worker_is_registered_and_ready() -> None:
    record = get_engine("pocket_tts", REGISTRY)
    assert record.worker == "pocket_tts"
    assert record.integration_status == "ready"


def test_unknown_worker_fails_explicitly() -> None:
    with pytest.raises(KeyError):
        get_worker("definitely-not-real")


def test_raw_phonemes_and_text_are_mutually_exclusive(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ttslab.isolation._uv", lambda: "uv")
    output = tmp_path / "phoneme.wav"
    command = build_worker_command("kokoro", phonemes="həlˈO", output=output)
    assert "--phonemes" in command
    assert "--text" not in command
    with pytest.raises(ValueError):
        build_worker_command("kokoro", text="hello", phonemes="həlˈO", output=output)


def test_voice_preparation_is_a_distinct_worker_operation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ttslab.isolation._uv", lambda: "uv")
    reference = tmp_path / "reference.wav"
    state = tmp_path / "state.pt"
    command = build_worker_command(
        "chatterbox_nano",
        prepare_voice=True,
        reference=reference,
        state_output=state,
    )
    assert "--prepare-voice" in command
    assert command[command.index("--reference") + 1] == str(reference)
    assert command[command.index("--state-output") + 1] == str(state)
    assert "--text" not in command
    assert "--output" not in command


def test_voice_preparation_requires_reference_and_state(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ttslab.isolation._uv", lambda: "uv")
    with pytest.raises(ValueError, match="requires reference and state_output"):
        build_worker_command(
            "chatterbox_nano",
            prepare_voice=True,
            reference=tmp_path / "reference.wav",
        )


def test_worker_modes_cannot_be_combined(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ttslab.isolation._uv", lambda: "uv")
    with pytest.raises(ValueError, match="not multiple"):
        build_worker_command(
            "chatterbox_nano",
            describe=True,
            prepare_voice=True,
            reference=tmp_path / "reference.wav",
            state_output=tmp_path / "state.pt",
        )
