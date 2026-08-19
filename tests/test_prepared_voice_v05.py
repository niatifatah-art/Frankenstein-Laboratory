from __future__ import annotations

import hashlib
from pathlib import Path

from ttslab.adapter_args import compile_adapter_args
from ttslab.isolation import WorkerExecution
from ttslab.registry import get_engine
from ttslab.voice_state import export_voicepack_state
from ttslab.voicepack import BackendVoiceState, ReferenceClip, VoicePack


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_chatterbox_cached_state_compiles_as_state_not_audio(tmp_path: Path) -> None:
    state = tmp_path / "chatterbox_nano.conds.pt"
    state.write_bytes(b"prepared")
    adapter = compile_adapter_args(
        get_engine("chatterbox_nano"),
        language="en",
        reference=state,
        device="cpu",
    )
    assert "--voice-state" in adapter.args
    assert "--reference" not in adapter.args
    assert str(state.resolve()) in adapter.args


def test_voicepack_backend_state_roundtrip_keeps_provenance(tmp_path: Path) -> None:
    state_path = tmp_path / "states" / "chatterbox_nano.conds.pt"
    state_path.parent.mkdir()
    state_path.write_bytes(b"state")
    source_hash = "a" * 64
    state = BackendVoiceState(
        engine="chatterbox_nano",
        path="states/chatterbox_nano.conds.pt",
        model_revision="revision-1",
        sha256=_sha(state_path),
        format="chatterbox-conditionals-pt-v1",
        source_reference_sha256=source_hash,
        adapter_version="0.2.0",
    )
    VoicePack(
        voice_id="demo",
        display_name="Demo",
        backend_states=(state,),
    ).save_atomic(tmp_path)
    loaded = VoicePack.load(tmp_path)
    assert loaded.backend_state("chatterbox_nano") == state
    assert loaded.validate_files(tmp_path) == ()


def test_chatterbox_state_export_is_atomic_and_revision_bound(tmp_path: Path, monkeypatch) -> None:
    reference = tmp_path / "refs" / "voice.wav"
    reference.parent.mkdir()
    reference.write_bytes(b"synthetic-reference")
    pack = VoicePack(
        voice_id="synthetic_demo",
        display_name="Synthetic Demo",
        languages=("en",),
        references=(
            ReferenceClip(
                path="refs/voice.wav",
                sha256=_sha(reference),
                license="generated-in-test",
                source="unit-test",
                consent="synthetic",
            ),
        ),
    )
    pack.save(tmp_path)
    engine = get_engine("chatterbox_nano")
    assert engine.source_revision

    def fake_execute(
        key,
        *,
        text=None,
        output=None,
        describe=False,
        prepare_voice=False,
        reference=None,
        state_output=None,
        extra_args=None,
        timeout_seconds=None,
    ):
        assert key == engine.worker
        assert prepare_voice is True
        assert reference == (tmp_path / "refs" / "voice.wav").resolve()
        assert state_output is not None
        state_output.write_bytes(b"native-conditionals")
        return WorkerExecution(
            command=("fake",),
            returncode=0,
            stdout="{}",
            stderr="",
            payload={
                "schema_version": 1,
                "operation": "prepare_voice",
                "engine": "chatterbox_nano",
                "adapter_version": "0.2.0",
                "state_path": str(state_output.resolve()),
                "state_format": "chatterbox-conditionals-pt-v1",
                "upstream_revision": engine.source_revision,
            },
        )

    monkeypatch.setattr("ttslab.voice_state.execute_worker", fake_execute)
    state = export_voicepack_state(
        tmp_path,
        engine_key="chatterbox_nano",
        device="cpu",
    )
    assert state.engine == "chatterbox_nano"
    assert state.format == "chatterbox-conditionals-pt-v1"
    assert state.model_revision == engine.source_revision
    assert state.source_reference_sha256 == _sha(reference)
    assert state.adapter_version == "0.2.0"
    assert (tmp_path / state.path).read_bytes() == b"native-conditionals"
    loaded = VoicePack.load(tmp_path)
    assert loaded.backend_state("chatterbox_nano") == state
