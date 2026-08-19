from __future__ import annotations

from pathlib import Path

import pytest

import ttslab.isolation as isolation


def test_uv_prefers_path_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(isolation.shutil, "which", lambda name: "C:/tools/uv.exe" if name == "uv" else None)
    assert isolation._uv() == "C:/tools/uv.exe"


def test_uv_falls_back_to_active_windows_venv_scripts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    python = scripts / "python.exe"
    python.write_bytes(b"")
    uv = scripts / "uv.exe"
    uv.write_bytes(b"")

    monkeypatch.setattr(isolation.shutil, "which", lambda _: None)
    monkeypatch.setattr(isolation.sys, "platform", "win32")
    monkeypatch.setattr(isolation.sys, "executable", str(python))
    monkeypatch.setattr(isolation.sys, "prefix", str(tmp_path))

    assert Path(isolation._uv()) == uv.resolve()


def test_uv_missing_error_explains_same_environment_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(isolation.shutil, "which", lambda _: None)
    monkeypatch.setattr(isolation.sys, "platform", "win32")
    monkeypatch.setattr(isolation.sys, "executable", str(tmp_path / "Scripts" / "python.exe"))
    monkeypatch.setattr(isolation.sys, "prefix", str(tmp_path))

    with pytest.raises(RuntimeError, match="same Python environment"):
        isolation._uv()
