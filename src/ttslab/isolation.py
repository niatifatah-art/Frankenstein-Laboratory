from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .registry import repository_root


@dataclass(frozen=True, slots=True)
class WorkerSpec:
    key: str
    project_dir: Path
    runner: Path
    default_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkerExecution:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    payload: dict[str, Any] | None


_WORKER_LAYOUT: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "kokoro": ("engines/kokoro", "runner.py", ()),
    "pocket_tts": ("engines/pocket_tts", "runner.py", ()),
    "chatterbox_base": ("engines/chatterbox", "runner.py", ("--variant", "base")),
    "chatterbox_nano": ("engines/chatterbox", "runner.py", ("--variant", "nano")),
    "chatterbox_turbo": ("engines/chatterbox", "runner.py", ("--variant", "turbo")),
    "chatterbox_v3": ("engines/chatterbox", "runner.py", ("--variant", "v3")),
    "qwen3_custom_06b": ("engines/qwen3_tts", "runner.py", ("--variant", "custom")),
    "qwen3_base_06b": ("engines/qwen3_tts", "runner.py", ("--variant", "base")),
    "qwen3_voice_design_17b": (
        "engines/qwen3_tts",
        "runner.py",
        ("--variant", "voice_design"),
    ),
    "voxcpm2": ("engines/voxcpm2", "runner.py", ()),
    "vibevoice_realtime": ("engines/vibevoice_realtime", "runner.py", ()),
    "melotts": ("engines/melotts", "runner.py", ()),
}


def get_worker(key: str) -> WorkerSpec:
    try:
        project_rel, runner_rel, default_args = _WORKER_LAYOUT[key]
    except KeyError as exc:
        raise KeyError(f"No isolated worker registered for {key!r}") from exc

    root = repository_root()
    project_dir = root / project_rel
    return WorkerSpec(
        key=key,
        project_dir=project_dir,
        runner=project_dir / runner_rel,
        default_args=default_args,
    )


def _uv() -> str:
    """Resolve uv without requiring the caller to activate its virtual environment.

    On Windows it is common to invoke `.venv\\Scripts\\ourtts.exe` directly from Explorer,
    PowerShell, a `.cmd` launcher, or another application. In that case the venv's Scripts
    directory is not necessarily on PATH even though `uv.exe` is installed next to the active
    interpreter. Prefer PATH when available, then fall back to the active interpreter directory.
    """
    uv = shutil.which("uv")
    if uv is not None:
        return uv

    interpreter_dir = Path(sys.executable).resolve().parent
    names = ("uv.exe", "uv") if sys.platform == "win32" else ("uv",)
    for name in names:
        candidate = interpreter_dir / name
        if candidate.is_file():
            return str(candidate)

    prefix_bin = Path(sys.prefix) / ("Scripts" if sys.platform == "win32" else "bin")
    for name in names:
        candidate = prefix_bin / name
        if candidate.is_file():
            return str(candidate)

    raise RuntimeError(
        "uv is required to run isolated engine workers. Install it into the same Python "
        "environment as ourTTS with `python -m pip install uv`, or install uv system-wide."
    )


def build_worker_command(
    key: str,
    *,
    text: str | None = None,
    phonemes: str | None = None,
    output: Path | None = None,
    describe: bool = False,
    prepare_voice: bool = False,
    reference: Path | None = None,
    state_output: Path | None = None,
    extra_args: list[str] | None = None,
) -> tuple[str, ...]:
    modes = int(describe) + int(prepare_voice)
    if modes > 1:
        raise ValueError("Worker operation must be describe, prepare_voice, or synthesis, not multiple.")
    if text is not None and phonemes is not None:
        raise ValueError("Worker input must be text or raw phonemes, not both.")

    worker = get_worker(key)
    command = [
        _uv(),
        "run",
        "--project",
        str(worker.project_dir),
        "python",
        str(worker.runner),
        *worker.default_args,
    ]
    if describe:
        if any(value is not None for value in (text, phonemes, output, reference, state_output)):
            raise ValueError("Describe operation does not accept synthesis or voice-preparation inputs.")
        command.append("--describe")
    elif prepare_voice:
        if text is not None or phonemes is not None or output is not None:
            raise ValueError("Voice preparation does not accept text, phonemes, or audio output.")
        if reference is None or state_output is None:
            raise ValueError("Voice preparation requires reference and state_output.")
        command.extend(
            [
                "--prepare-voice",
                "--reference",
                str(reference),
                "--state-output",
                str(state_output),
            ]
        )
    else:
        if reference is not None or state_output is not None:
            raise ValueError(
                "reference/state_output are voice-preparation command fields; "
                "pass synthesis reference/state through adapter extra_args instead."
            )
        if output is None or (text is None and phonemes is None):
            raise ValueError("text or phonemes plus output are required for synthesis")
        if phonemes is not None:
            command.extend(["--phonemes", phonemes])
        else:
            command.extend(["--text", text or ""])
        command.extend(["--output", str(output)])
    if extra_args:
        command.extend(extra_args)
    return tuple(command)


def _last_json_object(text: str) -> dict[str, Any] | None:
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def execute_worker(
    key: str,
    *,
    text: str | None = None,
    phonemes: str | None = None,
    output: Path | None = None,
    describe: bool = False,
    prepare_voice: bool = False,
    reference: Path | None = None,
    state_output: Path | None = None,
    extra_args: list[str] | None = None,
    timeout_seconds: float | None = None,
) -> WorkerExecution:
    command = build_worker_command(
        key,
        text=text,
        phonemes=phonemes,
        output=output,
        describe=describe,
        prepare_voice=prepare_voice,
        reference=reference,
        state_output=state_output,
        extra_args=extra_args,
    )
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return WorkerExecution(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        payload=_last_json_object(completed.stdout),
    )


def run_worker(
    key: str,
    *,
    text: str,
    output: Path,
    extra_args: list[str] | None = None,
) -> int:
    command = build_worker_command(key, text=text, output=output, extra_args=extra_args)
    return subprocess.run(command, check=False).returncode
