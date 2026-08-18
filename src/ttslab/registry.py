from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_ZONES = {"runtime", "research", "product"}
_ALLOWED_STATUSES = {
    "ready",
    "adapter_ready",
    "install_verified",
    "component",
    "researching",
    "planned",
    "blocked",
    "rejected",
}


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
    kind: str = "tts"
    family: str = ""
    version: str = "unknown"
    verified_on: str = "unknown"
    commercial_use: str = "unknown"
    attribution: str = "unknown"
    dataset_notes: str = "unknown"
    capabilities: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    hardware: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()

    @property
    def runnable(self) -> bool:
        return self.integration_status == "ready" and self.worker is not None

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def supports_language(self, language: str | None) -> bool:
        if language is None:
            return True
        requested = language.casefold()
        return "*" in self.languages or requested in {item.casefold() for item in self.languages}


def repository_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "registry").exists():
            return candidate
    raise RuntimeError("Could not locate repository root containing pyproject.toml and registry/")


def _record_from_raw(key: str, raw: dict[str, object]) -> EngineRecord:
    return EngineRecord(
        key=key,
        name=str(raw["name"]),
        upstream=str(raw["upstream"]),
        zone=str(raw["zone"]),
        integration_status=str(raw["integration_status"]),
        code_license=str(raw.get("code_license", "unknown")),
        weights_license=str(raw.get("weights_license", "unknown")),
        license_status=str(raw.get("license_status", "unverified")),
        worker=raw.get("worker") if isinstance(raw.get("worker"), str) else None,
        notes=str(raw.get("notes", "")),
        kind=str(raw.get("kind", "tts")),
        family=str(raw.get("family", "")),
        version=str(raw.get("version", "unknown")),
        verified_on=str(raw.get("verified_on", "unknown")),
        commercial_use=str(raw.get("commercial_use", "unknown")),
        attribution=str(raw.get("attribution", "unknown")),
        dataset_notes=str(raw.get("dataset_notes", "unknown")),
        capabilities=tuple(str(item) for item in raw.get("capabilities", [])),
        languages=tuple(str(item) for item in raw.get("languages", [])),
        hardware=tuple(str(item) for item in raw.get("hardware", [])),
        restrictions=tuple(str(item) for item in raw.get("restrictions", [])),
    )


def load_registry(path: Path | None = None) -> tuple[EngineRecord, ...]:
    registry_path = path or repository_root() / "registry" / "engines.toml"
    data = tomllib.loads(registry_path.read_text(encoding="utf-8"))
    records = [_record_from_raw(key, raw) for key, raw in data.get("engine", {}).items()]
    return tuple(sorted(records, key=lambda item: item.key))


def validate_registry(path: Path | None = None) -> tuple[str, ...]:
    errors: list[str] = []
    seen: set[str] = set()
    for record in load_registry(path):
        if record.key in seen:
            errors.append(f"duplicate engine key: {record.key}")
        seen.add(record.key)
        if record.zone not in _ALLOWED_ZONES:
            errors.append(f"{record.key}: unknown zone {record.zone!r}")
        if record.integration_status not in _ALLOWED_STATUSES:
            errors.append(
                f"{record.key}: unknown integration_status {record.integration_status!r}"
            )
        if not record.code_license:
            errors.append(f"{record.key}: missing code_license")
        if not record.weights_license:
            errors.append(f"{record.key}: missing weights_license")
        if record.integration_status == "ready" and not record.worker:
            errors.append(f"{record.key}: ready engine has no worker")
        if record.integration_status == "ready" and record.license_status == "unverified":
            errors.append(f"{record.key}: ready engine has unverified license status")
    return tuple(errors)


def get_engine(key: str, path: Path | None = None) -> EngineRecord:
    for record in load_registry(path):
        if record.key == key:
            return record
    raise KeyError(key)
