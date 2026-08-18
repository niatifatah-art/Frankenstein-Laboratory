from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EngineRecord:
    key: str
    name: str
    upstream: str
    zone: str
    integration_status: str
    code_license: str
    weights_license: str
    license_status: str
    worker: str | None = None
    notes: str = ""


def repository_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "registry").exists():
            return candidate
    raise RuntimeError("Could not locate repository root containing pyproject.toml and registry/")


def load_registry(path: Path | None = None) -> tuple[EngineRecord, ...]:
    registry_path = path or repository_root() / "registry" / "engines.toml"
    data = tomllib.loads(registry_path.read_text(encoding="utf-8"))
    records = []
    for key, raw in data.get("engine", {}).items():
        records.append(
            EngineRecord(
                key=key,
                name=raw["name"],
                upstream=raw["upstream"],
                zone=raw["zone"],
                integration_status=raw["integration_status"],
                code_license=raw.get("code_license", "unknown"),
                weights_license=raw.get("weights_license", "unknown"),
                license_status=raw.get("license_status", "unverified"),
                worker=raw.get("worker"),
                notes=raw.get("notes", ""),
            )
        )
    return tuple(sorted(records, key=lambda item: item.key))


def get_engine(key: str, path: Path | None = None) -> EngineRecord:
    for record in load_registry(path):
        if record.key == key:
            return record
    raise KeyError(key)
