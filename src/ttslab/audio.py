from __future__ import annotations

import hashlib
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WavInfo:
    path: str
    size_bytes: int
    sha256: str
    sample_rate: int
    frames: int
    channels: int
    sample_width_bytes: int
    duration_seconds: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_wav(path: Path, *, min_frames: int = 1) -> WavInfo:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.stat().st_size <= 44:
        raise ValueError(f"WAV file is too small: {path}")
    try:
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
    except wave.Error as exc:
        raise ValueError(f"Invalid PCM WAV: {path}: {exc}") from exc

    if sample_rate <= 0:
        raise ValueError(f"Invalid sample rate in {path}")
    if frames < min_frames:
        raise ValueError(f"WAV has only {frames} frames, expected at least {min_frames}")
    if channels <= 0:
        raise ValueError(f"Invalid channel count in {path}")

    return WavInfo(
        path=str(path),
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
        sample_rate=sample_rate,
        frames=frames,
        channels=channels,
        sample_width_bytes=sample_width,
        duration_seconds=frames / sample_rate,
    )
