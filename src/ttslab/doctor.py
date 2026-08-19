from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DoctorReport:
    python: str
    platform: str
    ffmpeg: str | None
    uv: str | None

    @property
    def ok(self) -> bool:
        return sys.version_info >= (3, 11)


def inspect_environment() -> DoctorReport:
    return DoctorReport(
        python=platform.python_version(),
        platform=platform.platform(),
        ffmpeg=shutil.which("ffmpeg"),
        uv=shutil.which("uv"),
    )
