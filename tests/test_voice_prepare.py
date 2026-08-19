import hashlib
from pathlib import Path

import pytest

from ttslab.isolation import WorkerExecution
from ttslab.voice_prepare import prepare_voicepack_state
from ttslab.voicepack import BackendVoiceState, ReferenceClip, VoicePack

REVISION = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"


def _pack(root: Path) -> VoicePack:
    reference = root / "refs" / "voice.wav"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"controlled-synthetic-reference")
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    pack = VoicePack(
        voice_id="creator",
        display_name="Creator",
        languages=("en",),
        references=(
            ReferenceClip(
                path="refs/voice.wav",
                sha256=digest,
                license="test-only",
                source="unit test synthetic",
                consent="synthetic",
            ),
        ),
        provenance={"synthetic": True},
    )
    pack.save(root)
    return pack


def test_prepare_voicepack_state_registers_verified_backend_state(monkeypatch, tmp_path: Path) -> None:
    pack = _pack(tmp_path)

    def fake_execute_worker(key, **kwargs):
        assert key == "chatterbox_nano"
        assert kwargs["prepare_voice"] is True
        assert kwargs["reference"].name == "voice.wav"
        state_output = kwargs["state_output"]
        state_output.write_bytes(b"prepared-conditionals")
        payload = {
            "schema_version": 1,
            "operation": "prepare_voice",
            "engine": "chatterbox_nano",
            "adapter_version": "0.2.0",
            "state_path": str(state_output.resolve()),
            "state_format": "chatterbox-conditionals-pt-v1",
            "upstream_revision": REVISION,
        }
        return WorkerExecution(("fake",), 0, "", "", payload)

    monkeypatch.setattr("ttslab.voice_prepare.execute_worker", fake_execute_worker)
    result = prepare_voicepack_state(tmp_path, "chatterbox_nano")

    assert result.voice_id == "creator"
    assert result.engine == "chatterbox_nano"
    assert result.format == "chatterbox-conditionals-pt-v1"
    assert result.model_revision == REVISION
    assert result.source_reference_sha256 == pack.references[0].sha256

    loaded = VoicePack.load(tmp_path)
    selection = loaded.resolve_backend_state(tmp_path, "chatterbox_nano")
    assert selection is not None
    assert selection.path.read_bytes() == b"prepared-conditionals"
    assert selection.state.sha256 == hashlib.sha256(b"prepared-conditionals").hexdigest()
    assert selection.state.source_reference_sha256 == pack.references[0].sha256


def test_failed_prepare_keeps_existing_registered_state(monkeypatch, tmp_path: Path) -> None:
    pack = _pack(tmp_path)
    existing = tmp_path / "backend_states" / "chatterbox_nano.conds.pt"
    existing.parent.mkdir()
    existing.write_bytes(b"old-good-state")
    old_digest = hashlib.sha256(existing.read_bytes()).hexdigest()
    pack = pack.with_backend_state(
        BackendVoiceState(
            engine="chatterbox_nano",
            path="backend_states/chatterbox_nano.conds.pt",
            model_revision=REVISION,
            sha256=old_digest,
            format="chatterbox-conditionals-pt-v1",
        )
    )
    pack.save(tmp_path)

    def fake_failure(key, **kwargs):
        kwargs["state_output"].write_bytes(b"partial-bad-state")
        return WorkerExecution(("fake",), 5, "", "worker exploded", None)

    monkeypatch.setattr("ttslab.voice_prepare.execute_worker", fake_failure)
    with pytest.raises(RuntimeError, match="worker exploded"):
        prepare_voicepack_state(tmp_path, "chatterbox_nano")

    assert existing.read_bytes() == b"old-good-state"
    loaded = VoicePack.load(tmp_path)
    assert loaded.backend_state("chatterbox_nano").sha256 == old_digest


def test_prepare_rejects_unintegrated_engine_before_worker(tmp_path: Path) -> None:
    _pack(tmp_path)
    with pytest.raises(ValueError, match="not integrated"):
        prepare_voicepack_state(tmp_path, "pocket_tts")


def test_prepare_rejects_worker_revision_mismatch(monkeypatch, tmp_path: Path) -> None:
    _pack(tmp_path)

    def fake_execute_worker(key, **kwargs):
        state_output = kwargs["state_output"]
        state_output.write_bytes(b"state")
        return WorkerExecution(
            ("fake",),
            0,
            "",
            "",
            {
                "operation": "prepare_voice",
                "engine": "chatterbox_nano",
                "adapter_version": "0.2.0",
                "state_path": str(state_output.resolve()),
                "state_format": "chatterbox-conditionals-pt-v1",
                "upstream_revision": "wrong-revision",
            },
        )

    monkeypatch.setattr("ttslab.voice_prepare.execute_worker", fake_execute_worker)
    with pytest.raises(RuntimeError, match="does not match qualified revision"):
        prepare_voicepack_state(tmp_path, "chatterbox_nano")
    assert VoicePack.load(tmp_path).backend_state("chatterbox_nano") is None
