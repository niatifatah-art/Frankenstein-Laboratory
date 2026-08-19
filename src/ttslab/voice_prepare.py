from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from .isolation import execute_worker
from .registry import get_engine
from .voicepack import BackendVoiceState, VoicePack

_PREPARED_STATE_ENGINES = frozenset(
    {
        "chatterbox_base",
        "chatterbox_nano",
        "chatterbox_turbo",
        "chatterbox_v3",
    }
)


@dataclass(frozen=True, slots=True)
class VoicePreparationResult:
    voice_id: str
    engine: str
    state_path: str
    sha256: str
    format: str
    model_revision: str
    adapter_version: str
    source_reference_sha256: str
    worker_payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def supports_prepared_voice(engine_key: str) -> bool:
    return engine_key in _PREPARED_STATE_ENGINES


def prepare_voicepack_state(
    voicepack_root: Path,
    engine_key: str,
    *,
    timeout_seconds: float = 1800.0,
    engine_args: list[str] | None = None,
) -> VoicePreparationResult:
    """Prepare one backend-specific reusable voice state and register it atomically.

    The source VoicePack/reference is verified before execution. The existing registered state is
    left untouched if preparation fails. Prepared state remains backend/revision-specific rather
    than being presented as a universal ourTTS speaker embedding.
    """
    if not supports_prepared_voice(engine_key):
        supported = ", ".join(sorted(_PREPARED_STATE_ENGINES))
        raise ValueError(
            f"Prepared VoicePack state is not integrated for {engine_key!r}; supported: {supported}"
        )

    root = voicepack_root.resolve()
    pack = VoicePack.load(root)
    validation_errors = pack.validate_files(root, verify_hashes=True)
    if validation_errors:
        raise ValueError(
            f"VoicePack {pack.voice_id!r} is invalid before preparation: "
            + "; ".join(validation_errors)
        )
    reference = pack.select_reference(root, allow_unknown_consent=False, verify_hash=True)

    engine = get_engine(engine_key)
    if not engine.runnable or engine.kind != "tts" or engine.worker is None:
        raise ValueError(f"Engine {engine_key!r} is not a qualified runnable TTS backend.")
    if not engine.supports("voice_cloning"):
        raise ValueError(f"Engine {engine_key!r} is not qualified for voice cloning.")

    states_root = root / "backend_states"
    states_root.mkdir(parents=True, exist_ok=True)
    final_path = states_root / f"{engine_key}.conds.pt"
    temporary_path = states_root / f".{engine_key}.{uuid4().hex}.tmp"

    try:
        execution = execute_worker(
            engine.worker,
            prepare_voice=True,
            reference=reference.path,
            state_output=temporary_path,
            extra_args=engine_args,
            timeout_seconds=timeout_seconds,
        )
        if execution.returncode != 0:
            tail = "\n".join(execution.stderr.splitlines()[-30:])
            raise RuntimeError(
                f"{engine_key} failed while preparing VoicePack {pack.voice_id!r} "
                f"with exit code {execution.returncode}:\n{tail}"
            )
        if not temporary_path.is_file():
            raise RuntimeError(
                f"{engine_key} reported successful voice preparation but produced no state file."
            )
        payload = execution.payload
        if not isinstance(payload, dict):
            raise RuntimeError(f"{engine_key} voice preparation returned no structured payload.")
        _validate_payload(engine_key, engine.source_revision, temporary_path, payload)

        state_format = str(payload["state_format"])
        model_revision = str(payload["upstream_revision"])
        adapter_version = str(payload["adapter_version"])
        digest = _sha256(temporary_path)

        temporary_path.replace(final_path)
        relative_path = final_path.relative_to(root).as_posix()
        state = BackendVoiceState(
            engine=engine_key,
            path=relative_path,
            model_revision=model_revision,
            sha256=digest,
            format=state_format,
            source_reference_sha256=reference.clip.sha256.lower(),
            adapter_version=adapter_version,
        )
        updated = pack.with_backend_state(state)
        updated.save_atomic(root)
        resolved = updated.resolve_backend_state(root, engine_key, verify_hash=True)
        if resolved is None:
            raise RuntimeError("Prepared state registration disappeared after VoicePack update.")

        return VoicePreparationResult(
            voice_id=pack.voice_id,
            engine=engine_key,
            state_path=relative_path,
            sha256=digest,
            format=state_format,
            model_revision=model_revision,
            adapter_version=adapter_version,
            source_reference_sha256=reference.clip.sha256.lower(),
            worker_payload=payload,
        )
    finally:
        temporary_path.unlink(missing_ok=True)


def _validate_payload(
    engine_key: str,
    qualified_revision: str | None,
    state_path: Path,
    payload: dict[str, object],
) -> None:
    if payload.get("operation") != "prepare_voice":
        raise RuntimeError(f"{engine_key} returned the wrong worker operation payload.")
    if payload.get("engine") != engine_key:
        raise RuntimeError(
            f"Prepared-state engine mismatch: requested {engine_key!r}, got {payload.get('engine')!r}."
        )
    reported_path = Path(str(payload.get("state_path", ""))).resolve()
    if reported_path != state_path.resolve():
        raise RuntimeError("Prepared-state worker reported a different output path.")
    for field in ("state_format", "upstream_revision", "adapter_version"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Prepared-state worker omitted {field!r}.")
    worker_revision = str(payload["upstream_revision"])
    if qualified_revision and worker_revision != qualified_revision:
        raise RuntimeError(
            f"Prepared-state model revision {worker_revision!r} does not match qualified "
            f"revision {qualified_revision!r}."
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
