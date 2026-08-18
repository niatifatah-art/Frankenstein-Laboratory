from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_ALLOWED_CONSENT = {"owned", "licensed", "consented", "synthetic", "unknown"}


@dataclass(frozen=True, slots=True)
class ReferenceClip:
    path: str
    sha256: str
    license: str
    source: str
    consent: str

    def __post_init__(self) -> None:
        _validate_relative_path(self.path)
        if self.consent not in _ALLOWED_CONSENT:
            raise ValueError(f"Unknown consent status: {self.consent!r}")
        if self.sha256 and (
            len(self.sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.sha256.lower())
        ):
            raise ValueError("Reference sha256 must be a 64-character hex digest.")


@dataclass(frozen=True, slots=True)
class BackendVoiceState:
    engine: str
    path: str
    model_revision: str | None = None
    sha256: str | None = None

    def __post_init__(self) -> None:
        _validate_relative_path(self.path)


@dataclass(frozen=True, slots=True)
class VoicePack:
    voice_id: str
    display_name: str
    languages: tuple[str, ...] = ()
    references: tuple[ReferenceClip, ...] = ()
    backend_states: tuple[BackendVoiceState, ...] = ()
    pronunciation_lexicon: str | None = None
    style_presets: dict[str, dict[str, Any]] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Unsupported VoicePack schema version.")
        if not self.voice_id or any(char.isspace() for char in self.voice_id):
            raise ValueError("voice_id must be a non-empty whitespace-free identifier.")
        if self.pronunciation_lexicon:
            _validate_relative_path(self.pronunciation_lexicon)

    @classmethod
    def load(cls, root: Path) -> "VoicePack":
        raw = json.loads((root / "voicepack.json").read_text(encoding="utf-8"))
        return cls(
            voice_id=raw["voice_id"],
            display_name=raw["display_name"],
            languages=tuple(raw.get("languages", [])),
            references=tuple(ReferenceClip(**item) for item in raw.get("references", [])),
            backend_states=tuple(BackendVoiceState(**item) for item in raw.get("backend_states", [])),
            pronunciation_lexicon=raw.get("pronunciation_lexicon"),
            style_presets=dict(raw.get("style_presets", {})),
            provenance=dict(raw.get("provenance", {})),
            schema_version=int(raw.get("schema_version", 1)),
        )

    def save(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.schema_version,
            "voice_id": self.voice_id,
            "display_name": self.display_name,
            "languages": list(self.languages),
            "references": [asdict(item) for item in self.references],
            "backend_states": [asdict(item) for item in self.backend_states],
            "pronunciation_lexicon": self.pronunciation_lexicon,
            "style_presets": self.style_presets,
            "provenance": self.provenance,
        }
        (root / "voicepack.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def validate_files(self, root: Path, *, verify_hashes: bool = True) -> tuple[str, ...]:
        errors: list[str] = []
        for item in (*self.references, *self.backend_states):
            path = (root / item.path).resolve()
            if not path.is_relative_to(root.resolve()):
                errors.append(f"path escapes VoicePack root: {item.path}")
                continue
            if not path.exists():
                errors.append(f"missing file: {item.path}")
                continue
            expected = getattr(item, "sha256", None)
            if verify_hashes and expected and _sha256(path) != expected.lower():
                errors.append(f"sha256 mismatch: {item.path}")
        if self.pronunciation_lexicon and not (root / self.pronunciation_lexicon).exists():
            errors.append(f"missing pronunciation lexicon: {self.pronunciation_lexicon}")
        return tuple(errors)


def _validate_relative_path(value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"VoicePack paths must stay relative to the pack root: {value!r}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
