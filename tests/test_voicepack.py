import hashlib
from pathlib import Path

import pytest

from ttslab.voicepack import BackendVoiceState, ReferenceClip, VoicePack


def test_voicepack_roundtrip_and_file_validation(tmp_path: Path) -> None:
    audio = tmp_path / "refs" / "synthetic.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"synthetic-reference")
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    pack = VoicePack(
        voice_id="lab_synthetic_01",
        display_name="Lab Synthetic 01",
        languages=("en",),
        references=(
            ReferenceClip(
                path="refs/synthetic.wav",
                sha256=digest,
                license="generated-in-lab",
                source="Frankenstein Laboratory",
                consent="synthetic",
            ),
        ),
        provenance={"owner": "lab", "synthetic": True},
    )
    pack.save(tmp_path)
    loaded = VoicePack.load(tmp_path)
    assert loaded.voice_id == pack.voice_id
    assert loaded.validate_files(tmp_path) == ()


def test_voicepack_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        BackendVoiceState(engine="pocket_tts", path="../escape.safetensors")
