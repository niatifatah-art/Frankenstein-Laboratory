from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .registry import repository_root


@dataclass(frozen=True, slots=True)
class IsolatedWorker:
    key: str
    project_dir: Path
    runner: Path


WORKERS = {
    "kokoro": ("engines/kokoro", "runner.py"),
}


def get_worker(key: str) -> IsolatedWorker:
    try:
        project_rel, runner_rel = WORKERS[key]
    except KeyError as exc:
        raise KeyError(f"No isolated worker registered for {key!r}") from exc

    root = repository_root()
    project_dir = root / project_rel
    return IsolatedWorker(
        key=key,
        project_dir=project_dir,
        runner=project_dir / runner_rel,
    )


def run_worker(
    key: str,
    *,
    text: str,
    output: Path,
    extra_args: list[str] | None = None,
) -> int:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError(
            "uv is required to run isolated engine workers. "
            "Install it with `python -m pip install uv` or from Astral."
        )

    worker = get_worker(key)
    command = [
        uv,
        "run",
        "--project",
        str(worker.project_dir),
        "python",
        str(worker.runner),
        "--text",
        text,
        "--output",
        str(output),
    ]
    if extra_args:
        command.extend(extra_args)
    return subprocess.run(command, check=False).returncode
