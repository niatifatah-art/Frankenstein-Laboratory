from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Cross-platform persistent locations owned by ourTTS.

    `OURTTS_HOME` relocates the complete application state. `OURTTS_MODELS_DIR`
    may relocate only the model storage to another disk/SSD.
    """

    root: Path
    config: Path
    models: Path
    voices: Path
    projects: Path
    cache: Path
    history: Path
    logs: Path
    temp: Path
    database: Path
    artifacts: Path

    @classmethod
    def default(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        home: Path | None = None,
        platform_name: str | None = None,
    ) -> AppPaths:
        values = os.environ if env is None else env
        user_home = (home or Path.home()).expanduser().resolve()
        platform_value = platform_name or sys.platform

        explicit_root = values.get("OURTTS_HOME")
        if explicit_root:
            root = Path(explicit_root).expanduser().resolve()
        elif platform_value == "win32":
            base = Path(values.get("LOCALAPPDATA") or (user_home / "AppData" / "Local"))
            root = (base / "ourTTS").resolve()
        elif platform_value == "darwin":
            root = (user_home / "Library" / "Application Support" / "ourTTS").resolve()
        else:
            base = Path(values.get("XDG_DATA_HOME") or (user_home / ".local" / "share"))
            root = (base / "ourtts").resolve()

        models_override = values.get("OURTTS_MODELS_DIR")
        models = (
            Path(models_override).expanduser().resolve()
            if models_override
            else root / "models"
        )
        return cls(
            root=root,
            config=root / "config",
            models=models,
            voices=root / "voices",
            projects=root / "projects",
            cache=root / "cache",
            history=root / "history",
            logs=root / "logs",
            temp=root / "temp",
            database=root / "ourtts.sqlite3",
            artifacts=root / "history" / "artifacts",
        )

    def ensure(self) -> AppPaths:
        for path in (
            self.root,
            self.config,
            self.models,
            self.voices,
            self.projects,
            self.cache,
            self.history,
            self.logs,
            self.temp,
            self.artifacts,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def to_dict(self) -> dict[str, str]:
        raw = asdict(self)
        return {key: str(value) for key, value in raw.items()}
