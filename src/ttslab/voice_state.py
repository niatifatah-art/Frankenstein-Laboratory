from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from .adapter_args import compile_adapter_args
from .audio import sha256_file
from .isolation import execute_worker, get_worker
from .registry import get_engine
from .voicepack import BackendVoiceState, VoicePack

_SAFE_CONSENT = {"owned", "licensed", "consented", "synthetic"}
_CHATTERBOX_STATE_ENGINES = {
    "chatterbox_base",
    "chatterbox_nano",
    "chatterbox_turbo",
    "chatterbox_v3",
}


def _pocket_language(language: str | None) -> str:
    engine = get_engine("pocket_tts")
    adapter = compile_adapter_args(engine, language=language or "en")
    args = list(adapter.args)
    if "--language" not in args:
        return "english"
    return args[args.index("--language") + 1]


def _export_pocket_state(
    root: Path,
    *,
    language: str | None,
    catalog_voice: str | None,
) -> BackendVoiceState:
    pack = VoicePack.load(root)
    source_args: list[str]
    provenance = dict(pack.provenance)
    source_reference_sha256: str | None = None
    if catalog_voice:
        source_args = ["--catalog-voice", catalog_voice]
        state_sources = dict(provenance.get("backend_state_sources", {}))
        state_sources["pocket_tts"] = {"kind": "catalog_voice", "voice": catalog_voice}
        provenance["backend_state_sources"] = state_sources
    else:
        reference = next((item for item in pack.references if item.consent in _SAFE_CONSENT), None)
        if reference is None:
            raise ValueError(
                "VoicePack needs an owned/licensed/consented/synthetic reference, or use "
                "--catalog-voice for an upstream catalog identity."
            )
        reference_path = (root / reference.path).resolve()
        if not reference_path.is_relative_to(root.resolve()) or not reference_path.exists():
            raise FileNotFoundError(reference_path)
        digest = sha256_file(reference_path)
        if reference.sha256 and digest != reference.sha256.lower():
            raise ValueError(
                "VoicePack reference hash mismatch; refusing to export a stale identity state."
            )
        source_reference_sha256 = digest
        source_args = ["--reference", str(reference_path)]

    worker = get_worker("pocket_tts")
    exporter = worker.project_dir / "export_voice.py"
    if not exporter.exists():
        raise RuntimeError("Pocket TTS export_voice worker is missing.")
    state_rel = Path("states") / "pocket_tts.safetensors"
    state_path = root / state_rel
    state_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "uv",
        "run",
        "--project",
        str(worker.project_dir),
        "python",
        str(exporter),
        *source_args,
        "--output",
        str(state_path),
        "--language",
        _pocket_language(language or (pack.languages[0] if pack.languages else "en")),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        message = completed.stderr.strip()[-4000:] or completed.stdout.strip()[-4000:]
        lowered = message.casefold()
        if not catalog_voice and (
            "accept the terms" in lowered or "voice cloning" in lowered and "unsupported" in lowered
        ):
            raise RuntimeError(
                "Pocket TTS reference-audio voice-state export requires access to the gated voice-"
                "cloning weights. Accept the terms for kyutai/pocket-tts on Hugging Face and "
                "authenticate the environment (for CI, provide an authorized HF_TOKEN). "
                "Catalog voice states can be exported without cloning access via --catalog-voice."
            )
        raise RuntimeError(message)

    payload = None
    for line in reversed(completed.stdout.splitlines()):
        if line.strip().startswith("{"):
            payload = json.loads(line)
            break
    if payload is None or not state_path.exists():
        raise RuntimeError("Pocket TTS state exporter returned no verifiable output.")

    engine = get_engine("pocket_tts")
    state = BackendVoiceState(
        engine="pocket_tts",
        path=state_rel.as_posix(),
        model_revision=engine.source_revision or engine.version,
        sha256=sha256_file(state_path),
        format="pocket-tts-voice-state-safetensors-v1",
        source_reference_sha256=source_reference_sha256,
        adapter_version="0.4-product",
    )
    remaining = tuple(item for item in pack.backend_states if item.engine != "pocket_tts")
    replace(
        pack,
        backend_states=(*remaining, state),
        provenance=provenance,
    ).save_atomic(root)
    return state


def _export_chatterbox_state(
    root: Path,
    *,
    engine_key: str,
    device: str,
    timeout_seconds: float,
) -> BackendVoiceState:
    pack = VoicePack.load(root)
    errors = pack.validate_files(root, verify_hashes=True)
    if errors:
        raise ValueError(
            f"VoicePack {pack.voice_id!r} is invalid before preparation: " + "; ".join(errors)
        )
    selected = pack.select_reference(root, allow_unknown_consent=False, verify_hash=True)
    engine = get_engine(engine_key)
    if not engine.runnable or not engine.worker:
        raise ValueError(f"Engine {engine_key!r} is not a qualified runnable backend.")
    if not engine.supports("voice_cloning"):
        raise ValueError(f"Engine {engine_key!r} is not qualified for voice cloning.")

    states_root = root / "states"
    states_root.mkdir(parents=True, exist_ok=True)
    state_rel = Path("states") / f"{engine_key}.conds.pt"
    state_path = root / state_rel
    temporary = states_root / f".{engine_key}.{uuid4().hex}.tmp"
    try:
        execution = execute_worker(
            engine.worker,
            prepare_voice=True,
            reference=selected.path,
            state_output=temporary,
            extra_args=["--device", device],
            timeout_seconds=timeout_seconds,
        )
        if execution.returncode != 0:
            tail = "\n".join(execution.stderr.splitlines()[-40:])
            raise RuntimeError(
                f"{engine_key} voice preparation failed ({execution.returncode}):\n{tail}"
            )
        if not temporary.is_file():
            raise RuntimeError(f"{engine_key} reported success but produced no prepared state.")
        payload = execution.payload
        if not isinstance(payload, dict):
            raise TypeError(f"{engine_key} voice preparation returned no structured payload.")
        if payload.get("operation") != "prepare_voice" or payload.get("engine") != engine_key:
            raise RuntimeError("Prepared voice worker returned mismatched operation/engine evidence.")
        reported = Path(str(payload.get("state_path", ""))).resolve()
        if reported != temporary.resolve():
            raise RuntimeError("Prepared voice worker reported a different state output path.")
        state_format = str(payload.get("state_format", "")).strip()
        revision = str(payload.get("upstream_revision", "")).strip()
        adapter_version = str(payload.get("adapter_version", "")).strip()
        if not state_format or not revision or not adapter_version:
            raise RuntimeError("Prepared voice worker omitted format/revision/adapter evidence.")
        if engine.source_revision and revision != engine.source_revision:
            raise RuntimeError(
                f"Prepared voice revision {revision!r} does not match qualified "
                f"revision {engine.source_revision!r}."
            )

        temporary.replace(state_path)
        state = BackendVoiceState(
            engine=engine_key,
            path=state_rel.as_posix(),
            model_revision=revision,
            sha256=sha256_file(state_path),
            format=state_format,
            source_reference_sha256=selected.clip.sha256.lower(),
            adapter_version=adapter_version,
        )
        pack.with_backend_state(state).save_atomic(root)
        return state
    finally:
        temporary.unlink(missing_ok=True)


def export_voicepack_state(
    root: Path,
    *,
    engine_key: str = "pocket_tts",
    language: str | None = None,
    catalog_voice: str | None = None,
    device: str = "cpu",
    timeout_seconds: float = 1800.0,
) -> BackendVoiceState:
    """Build a verified reusable backend voice state without importing backends into Core.

    Pocket uses its official safetensors export. Chatterbox uses upstream-native serialized
    Conditionals. Both remain backend/revision-specific and preserve VoicePack provenance.
    """
    root = root.resolve()
    if engine_key == "pocket_tts":
        return _export_pocket_state(root, language=language, catalog_voice=catalog_voice)
    if engine_key in _CHATTERBOX_STATE_ENGINES:
        if catalog_voice:
            raise ValueError("Chatterbox prepared state requires a consented VoicePack reference.")
        return _export_chatterbox_state(
            root,
            engine_key=engine_key,
            device=device,
            timeout_seconds=timeout_seconds,
        )
    supported = ", ".join(["pocket_tts", *sorted(_CHATTERBOX_STATE_ENGINES)])
    raise ValueError(f"No verified persistent state exporter for {engine_key!r}; supported: {supported}.")
