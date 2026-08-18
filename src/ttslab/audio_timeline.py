from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

from .audio import WavInfo, inspect_wav


@dataclass(frozen=True, slots=True)
class AudioPart:
    path: Path
    silence_after_ms: int = 0

    def __post_init__(self) -> None:
        if self.silence_after_ms < 0:
            raise ValueError("silence_after_ms must be non-negative.")


def silence_frames(milliseconds: int, sample_rate: int) -> int:
    if milliseconds < 0:
        raise ValueError("milliseconds must be non-negative")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    return round(sample_rate * milliseconds / 1000)


def concatenate_pcm_wavs(parts: tuple[AudioPart, ...] | list[AudioPart], output: Path) -> WavInfo:
    """Concatenate compatible PCM WAVs and insert exact zero-valued silence.

    Hidden resampling is deliberately refused so timing and benchmark provenance remain explicit.
    """
    if not parts:
        raise ValueError("At least one audio part is required.")

    payloads: list[tuple[bytes, int]] = []
    params: tuple[int, int, int] | None = None
    for part in parts:
        with wave.open(str(part.path), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise ValueError(f"Only uncompressed PCM WAV is supported: {part.path}")
            current = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate())
            if params is None:
                params = current
            elif current != params:
                raise ValueError(f"WAV format mismatch for {part.path}: {current} != {params}")
            payloads.append((wav.readframes(wav.getnframes()), part.silence_after_ms))

    assert params is not None
    channels, sample_width, sample_rate = params
    zero_frame = b"\x00" * channels * sample_width
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sample_width)
        out.setframerate(sample_rate)
        for payload, silence_ms in payloads:
            out.writeframes(payload)
            if silence_ms:
                out.writeframes(zero_frame * silence_frames(silence_ms, sample_rate))

    return inspect_wav(output)
