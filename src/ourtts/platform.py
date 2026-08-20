from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import AppPaths


@dataclass(frozen=True, slots=True)
class PlatformReport:
    os: str
    release: str
    version: str
    machine: str
    python: str
    cpu: str
    ram_bytes: int | None
    free_disk_bytes: int | None
    accelerator: str
    accelerator_detail: str | None
    ffmpeg: str | None
    espeak: str | None
    uv: str | None
    paths: AppPaths

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["paths"] = self.paths.to_dict()
        return payload


def _memory_bytes() -> int | None:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        try:
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        except (AttributeError, OSError):
            return None
        return int(status.ullTotalPhys) if ok else None

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None
    return int(page_size) * int(pages)


def _find_uv() -> str | None:
    direct = shutil.which("uv")
    if direct:
        return direct
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


def _nvidia_summary() -> tuple[str, str | None] | None:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    line = next((item.strip() for item in completed.stdout.splitlines() if item.strip()), "")
    return ("cuda", line or None)


def _accelerator() -> tuple[str, str | None]:
    nvidia = _nvidia_summary()
    if nvidia is not None:
        return nvidia
    if sys.platform == "darwin" and platform.machine().casefold() in {"arm64", "aarch64"}:
        return "mps_candidate", "Apple Silicon detected; backend-specific MPS support is not assumed."
    return "cpu", None


def inspect_platform(paths: AppPaths | None = None) -> PlatformReport:
    resolved_paths = (paths or AppPaths.default()).ensure()
    accelerator, accelerator_detail = _accelerator()
    try:
        free_disk = shutil.disk_usage(resolved_paths.root).free
    except OSError:
        free_disk = None
    cpu = platform.processor().strip() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown")
    return PlatformReport(
        os=platform.system() or sys.platform,
        release=platform.release(),
        version=platform.version(),
        machine=platform.machine() or "unknown",
        python=platform.python_version(),
        cpu=cpu,
        ram_bytes=_memory_bytes(),
        free_disk_bytes=free_disk,
        accelerator=accelerator,
        accelerator_detail=accelerator_detail,
        ffmpeg=shutil.which("ffmpeg"),
        espeak=shutil.which("espeak-ng") or shutil.which("espeak"),
        uv=_find_uv(),
        paths=resolved_paths,
    )
