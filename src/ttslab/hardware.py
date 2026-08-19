from __future__ import annotations

import os
import platform
import shutil


def detect_device() -> str:
    """Best-effort accelerator detection without importing a heavyweight ML framework."""
    override = os.environ.get("OURTTS_DEVICE", "").strip().lower()
    if override:
        return override
    if shutil.which("nvidia-smi"):
        return "cuda"
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "mps"
    return "cpu"


def resolve_device(requested: str | None) -> str:
    value = (requested or "auto").strip().lower()
    return detect_device() if value == "auto" else value
