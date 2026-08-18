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
    "qualified_component",
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
    source_revision: str | None = None
    qualification_run: int | None = None
    artifact_id: int | None = None
    artifact_digest: str | None = None
    cpu_generation_rtf: float | None = None
    cpu_ttfa_seconds: float | None = None
    cpu_cold_start_seconds: float | None = None

    @property
    def runnable(self) -> bool:
        return self.integration_status == "ready" and self.worker is not None

    @property
    def qualified_component(self) -> bool:
        return self.integration_status == "qualified_component"

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


def _optional_float(raw: dict[str, object], key: str) -> float | None:
    value = raw.get(key)
    return float(value) if value is not None else None


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
        source_revision=(
            str(raw["source_revision"]) if raw.get("source_revision") is not None else None
        ),
        qualification_run=(
            int(raw["qualification_run"])
            if raw.get("qualification_run") is not None
            else None
        ),
        artifact_id=int(raw["artifact_id"]) if raw.get("artifact_id") is not None else None,
        artifact_digest=(
            str(raw["artifact_digest"]) if raw.get("artifact_digest") is not None else None
        ),
        cpu_generation_rtf=_optional_float(raw, "cpu_generation_rtf"),
        cpu_ttfa_seconds=_optional_float(raw, "cpu_ttfa_seconds"),
        cpu_cold_start_seconds=_optional_float(raw, "cpu_cold_start_seconds"),
    )


def _overlay(path: Path, section: str) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        str(key): dict(value)
        for key, value in data.get(section, {}).items()
        if isinstance(value, dict)
    }


def _static_registry_files(primary_path: Path) -> tuple[Path, ...]:
    files = [primary_path]
    research = primary_path.with_name("research.toml")
    if research.exists():
        files.append(research)
    return tuple(files)


def load_registry(path: Path | None = None) -> tuple[EngineRecord, ...]:
    registry_path = path or repository_root() / "registry" / "engines.toml"
    qualifications = _overlay(registry_path.with_name("qualifications.toml"), "qualification")
    source_verifications = _overlay(
        registry_path.with_name("source_verifications.toml"), "source"
    )
    license_overrides = _overlay(registry_path.with_name("license_overrides.toml"), "license")
    raw_records: dict[str, dict[str, object]] = {}
    for static_path in _static_registry_files(registry_path):
        data = tomllib.loads(static_path.read_text(encoding="utf-8"))
        for key, base_raw in data.get("engine", {}).items():
            if key in raw_records:
                raise ValueError(f"Duplicate engine key across registry files: {key}")
            raw_records[key] = dict(base_raw)

    records = []
    for key, base_raw in raw_records.items():
        merged = dict(base_raw)
        merged.update(source_verifications.get(key, {}))
        merged.update(license_overrides.get(key, {}))
        merged.update(qualifications.get(key, {}))
        records.append(_record_from_raw(key, merged))
    return tuple(sorted(records, key=lambda item: item.key))


def validate_registry(path: Path | None = None) -> tuple[str, ...]:
    errors: list[str] = []
    seen: set[str] = set()
    try:
        records = load_registry(path)
    except ValueError as exc:
        return (str(exc),)
    for record in records:
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
        if record.integration_status == "qualified_component" and record.kind == "tts":
            errors.append(f"{record.key}: qualified_component should not be kind='tts'")
        if record.artifact_digest and not record.artifact_digest.startswith("sha256:"):
            errors.append(f"{record.key}: artifact_digest must use sha256: prefix")
        for metric_name, value in (
            ("cpu_generation_rtf", record.cpu_generation_rtf),
            ("cpu_ttfa_seconds", record.cpu_ttfa_seconds),
            ("cpu_cold_start_seconds", record.cpu_cold_start_seconds),
        ):
            if value is not None and value < 0:
                errors.append(f"{record.key}: {metric_name} must be non-negative")
    return tuple(errors)


def get_engine(key: str, path: Path | None = None) -> EngineRecord:
    for record in load_registry(path):
        if record.key == key:
            return record
    raise KeyError(key)
