from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from .adapter_args import compile_adapter_args
from .audio import sha256_file
from .isolation import get_worker
from .registry import get_engine
from .voicepack import BackendVoiceState, VoicePack

_SAFE_CONSENT = {"owned", "licensed", "consented", "synthetic"}


def _pocket_language(language: str | None) -> str:
    engine = get_engine("pocket_tts")
    adapter = compile_adapter_args(engine, language=language or "en")
    args = list(adapter.args)
    if "--language" not in args:
        return "english"
    return args[args.index("--language") + 1]


def export_voicepack_state(
    root: Path,
    *,
    engine_key: str = "pocket_tts",
    language: str | None = None,
    catalog_voice: str | None = None,
) -> BackendVoiceState:
    """Build a verified reusable backend voice state without importing the backend into Core.

    Pocket catalog voices can be exported without cloning access. Reference-audio export uses
    Pocket's gated cloning model and therefore requires accepting the upstream model terms and
    authenticating with Hugging Face in the worker environment.
    """
    if engine_key != "pocket_tts":
        raise ValueError("v0.4 only has a verified persistent state exporter for Pocket TTS.")
    pack = VoicePack.load(root)

    source_args: list[str]
    provenance = dict(pack.provenance)
    if catalog_voice:
        source_args = ["--catalog-voice", catalog_voice]
        state_sources = dict(provenance.get("backend_state_sources", {}))
        state_sources[engine_key] = {"kind": "catalog_voice", "voice": catalog_voice}
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
        if reference.sha256 and sha256_file(reference_path) != reference.sha256.lower():
            raise ValueError(
                "VoicePack reference hash mismatch; refusing to export a stale identity state."
            )
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

    engine = get_engine(engine_key)
    state = BackendVoiceState(
        engine=engine_key,
        path=state_rel.as_posix(),
        model_revision=engine.source_revision or engine.version,
        sha256=sha256_file(state_path),
    )
    remaining = tuple(item for item in pack.backend_states if item.engine != engine_key)
    updated = replace(
        pack,
        backend_states=(*remaining, state),
        provenance=provenance,
    )
    updated.save(root)
    return state
