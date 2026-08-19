from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .voicepack import VoicePack


@dataclass(frozen=True, slots=True)
class VoiceSummary:
    voice_id: str
    display_name: str
    languages: tuple[str, ...]
    styles: tuple[str, ...]
    ready: bool
    references: int = 0
    prepared_states: int = 0
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class VoiceLibrary:
    """A small, local, managed VoicePack directory.

    The product API accepts a stable voice ID and resolves it inside this library instead of
    accepting arbitrary filesystem paths from browser clients.
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def list(self) -> tuple[VoiceSummary, ...]:
        voices: list[VoiceSummary] = []
        seen: set[str] = set()
        directories = sorted((item for item in self.root.iterdir() if item.is_dir()), key=lambda p: p.name)
        for directory in directories:
            manifest = directory / "voicepack.json"
            if not manifest.is_file():
                continue
            try:
                pack = VoicePack.load(directory)
                errors = pack.validate_files(directory, verify_hashes=True)
            except (KeyError, OSError, TypeError, ValueError) as exc:
                voices.append(
                    VoiceSummary(
                        voice_id=directory.name,
                        display_name=directory.name,
                        languages=(),
                        styles=(),
                        ready=False,
                        errors=(str(exc),),
                    )
                )
                continue
            if pack.voice_id in seen:
                errors = (*errors, f"duplicate voice_id: {pack.voice_id}")
            seen.add(pack.voice_id)
            voices.append(
                VoiceSummary(
                    voice_id=pack.voice_id,
                    display_name=pack.display_name,
                    languages=pack.languages,
                    styles=tuple(sorted(pack.style_presets)),
                    ready=not errors and bool(pack.references or pack.backend_states),
                    references=len(pack.references),
                    prepared_states=len(pack.backend_states),
                    errors=tuple(errors),
                )
            )
        return tuple(voices)

    def resolve(self, voice_id: str) -> Path:
        matches: list[Path] = []
        directories = sorted((item for item in self.root.iterdir() if item.is_dir()), key=lambda p: p.name)
        for directory in directories:
            manifest = directory / "voicepack.json"
            if not manifest.is_file():
                continue
            try:
                pack = VoicePack.load(directory)
            except (KeyError, OSError, TypeError, ValueError):
                continue
            if pack.voice_id == voice_id:
                matches.append(directory.resolve())
        if not matches:
            raise ValueError(f"Unknown ourTTS voice: {voice_id!r}")
        if len(matches) > 1:
            raise ValueError(f"Duplicate VoicePack identity in local library: {voice_id!r}")
        return matches[0]
