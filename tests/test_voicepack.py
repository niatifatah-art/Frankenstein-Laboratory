import hashlib
from pathlib import Path

import pytest

from ttslab.voicepack import BackendVoiceState, ReferenceClip, VoicePack


def _clip(path: str, audio: Path, *, consent: str = "synthetic") -> ReferenceClip:
    return ReferenceClip(
        path=path,
        sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
        license="generated-in-lab",
        source="Frankenstein Laboratory",
        consent=consent,
    )


def test_voicepack_roundtrip_and_file_validation(tmp_path: Path) -> None:
    audio = tmp_path / "refs" / "synthetic.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"synthetic-reference")
    pack = VoicePack(
        voice_id="lab_synthetic_01",
        display_name="Lab Synthetic 01",
        languages=("en",),
        references=(_clip("refs/synthetic.wav", audio),),
        style_presets={"calm": {"style": "calm"}},
        provenance={"owner": "lab", "synthetic": True},
    )
    pack.save(tmp_path)
    loaded = VoicePack.load(tmp_path)
    assert loaded.voice_id == pack.voice_id
    assert loaded.validate_files(tmp_path) == ()
    assert loaded.style_controls("calm") == {"style": "calm"}


def test_voicepack_selects_hash_valid_consented_reference(tmp_path: Path) -> None:
    audio = tmp_path / "refs" / "synthetic.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"synthetic-reference")
    pack = VoicePack(
        voice_id="lab_synthetic_01",
        display_name="Lab Synthetic 01",
        references=(_clip("refs/synthetic.wav", audio),),
    )
    selected = pack.select_reference(tmp_path)
    assert selected.path == audio.resolve()
    assert selected.clip.consent == "synthetic"


def test_voicepack_unknown_consent_requires_explicit_override(tmp_path: Path) -> None:
    audio = tmp_path / "refs" / "unknown.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"unknown-reference")
    pack = VoicePack(
        voice_id="unknown_voice",
        display_name="Unknown Voice",
        references=(_clip("refs/unknown.wav", audio, consent="unknown"),),
    )
    with pytest.raises(ValueError, match="no usable reference"):
        pack.select_reference(tmp_path)
    assert pack.select_reference(tmp_path, allow_unknown_consent=True).path == audio.resolve()


def test_voicepack_rejects_reference_hash_mismatch(tmp_path: Path) -> None:
    audio = tmp_path / "refs" / "voice.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"one-version")
    clip = _clip("refs/voice.wav", audio)
    audio.write_bytes(b"changed-after-registration")
    pack = VoicePack(
        voice_id="changed_voice",
        display_name="Changed Voice",
        references=(clip,),
    )
    with pytest.raises(ValueError, match="sha256 mismatch"):
        pack.select_reference(tmp_path)


def test_voicepack_style_preset_is_explicit() -> None:
    pack = VoicePack(
        voice_id="style_voice",
        display_name="Style Voice",
        style_presets={"excited": {"style": "excited", "pace": 1.05}},
    )
    controls = pack.style_controls("excited")
    controls["pace"] = 0.5
    assert pack.style_controls("excited")["pace"] == 1.05
    with pytest.raises(ValueError, match="Unknown style preset"):
        pack.style_controls("missing")


def test_voicepack_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        BackendVoiceState(engine="pocket_tts", path="../escape.safetensors")
