from __future__ import annotations

import json
import shutil
import subprocess
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
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError(
            "uv is required to run isolated engine workers. "
            "Install it with `python -m pip install uv` or from Astral."
        )
    return uv


def build_worker_command(
    key: str,
    *,
    text: str | None = None,
    output: Path | None = None,
    describe: bool = False,
    prepare_voice: bool = False,
    reference: Path | None = None,
    state_output: Path | None = None,
    extra_args: list[str] | None = None,
) -> tuple[str, ...]:
    if describe and prepare_voice:
        raise ValueError("Worker command cannot describe and prepare a voice in the same operation.")

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
        command.append("--describe")
    elif prepare_voice:
        if reference is None or state_output is None:
            raise ValueError("reference and state_output are required for voice preparation")
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
        if text is None or output is None:
            raise ValueError("text and output are required for synthesis")
        command.extend(["--text", text, "--output", str(output)])
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
