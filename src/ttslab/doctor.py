from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DoctorReport:
    python: str
    platform: str
    ffmpeg: str | None
    uv: str | None

    @property
    def ok(self) -> bool:
        return sys.version_info >= (3, 11)


def _find_uv() -> str | None:
    path = shutil.which("uv")
    if path is not None:
        return path

    names = ("uv.exe", "uv") if sys.platform == "win32" else ("uv",)
    roots = (
        Path(sys.executable).resolve().parent,
        Path(sys.prefix) / ("Scripts" if sys.platform == "win32" else "bin"),
    )
    for root in roots:
        for name in names:
            candidate = root / name
            if candidate.is_file():
                return str(candidate)
    return None


def inspect_environment() -> DoctorReport:
    return DoctorReport(
        python=platform.python_version(),
        platform=platform.platform(),
        ffmpeg=shutil.which("ffmpeg"),
        uv=_find_uv(),
    )
