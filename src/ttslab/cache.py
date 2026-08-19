from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheEntry:
    key: str
    wav: Path
    metadata: Path


def default_cache_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "FrankensteinTTSLab" / "cache"
    if os.environ.get("XDG_CACHE_HOME"):
        return Path(os.environ["XDG_CACHE_HOME"]) / "frankenstein-tts-lab"
    return Path.home() / ".cache" / "frankenstein-tts-lab"


def cache_key(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def entry_for(root: Path, key: str) -> CacheEntry:
    shard = root / key[:2] / key[2:4]
    return CacheEntry(key=key, wav=shard / f"{key}.wav", metadata=shard / f"{key}.json")


def restore(root: Path, key: str, output: Path) -> dict[str, Any] | None:
    entry = entry_for(root, key)
    if not entry.wav.exists() or not entry.metadata.exists():
        return None
    try:
        metadata = json.loads(entry.metadata.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(entry.wav, output)
    return metadata


def store(root: Path, key: str, wav: Path, metadata: dict[str, Any]) -> CacheEntry:
    entry = entry_for(root, key)
    entry.wav.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wav, entry.wav)
    entry.metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return entry
