from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SAMPLE_RATE = 24_000
VOICE = "bm_fable"
LANGUAGE = "b"

SEGMENTS = [
    "I had a terrible idea.",
    "What if, instead of choosing one open-source TTS, I just used all of them?",
    "So I made a repository called Frankenstein Laboratory.",
    "And somehow...",
    "it already speaks.",
]

# (speed per segment, exact digital silence after each segment in milliseconds)
VARIANTS: dict[str, dict[str, list[float] | list[int]]] = {
    "01-natural": {
        "speeds": [0.94, 0.98, 0.96, 0.91, 0.90],
        "pauses_ms": [380, 280, 360, 650, 0],
    },
    "02-shorts": {
        "speeds": [0.98, 1.04, 1.02, 0.95, 0.94],
        "pauses_ms": [260, 180, 240, 460, 0],
    },
    "03-story": {
        "speeds": [0.90, 0.95, 0.92, 0.86, 0.86],
        "pauses_ms": [520, 380, 520, 900, 0],
    },
    "04-comedic": {
        "speeds": [0.98, 1.03, 1.00, 0.88, 0.92],
        "pauses_ms": [470, 220, 330, 1050, 0],
    },
    "05-calm": {
        "speeds": [0.88, 0.92, 0.90, 0.84, 0.84],
        "pauses_ms": [430, 350, 430, 760, 0],
    },
}


def _to_numpy(audio):
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "numpy"):
        audio = audio.numpy()
    return np.asarray(audio, dtype=np.float32)


def render_segment(pipeline: KPipeline, text: str, speed: float) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(
        text,
        voice=VOICE,
        speed=speed,
        split_pattern=r"\n+",
    ):
        chunks.append(_to_numpy(audio))
    if not chunks:
        raise RuntimeError(f"Kokoro produced no audio for segment: {text!r}")
    return np.concatenate(chunks)


def silence(milliseconds: int) -> np.ndarray:
    frames = round(SAMPLE_RATE * milliseconds / 1000)
    return np.zeros(frames, dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/fable-v2"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    pipeline = KPipeline(lang_code=LANGUAGE)
    model_ready_seconds = time.perf_counter() - started

    manifest: dict[str, object] = {
        "engine": "kokoro",
        "voice": VOICE,
        "language": LANGUAGE,
        "sample_rate": SAMPLE_RATE,
        "model_ready_seconds": model_ready_seconds,
        "segments": SEGMENTS,
        "variants": {},
    }

    for name, config in VARIANTS.items():
        speeds = config["speeds"]
        pauses_ms = config["pauses_ms"]
        pieces: list[np.ndarray] = []
        segment_meta: list[dict[str, object]] = []
        variant_started = time.perf_counter()

        for text, speed, pause_ms in zip(SEGMENTS, speeds, pauses_ms, strict=True):
            segment_started = time.perf_counter()
            audio = render_segment(pipeline, text, float(speed))
            segment_seconds = time.perf_counter() - segment_started
            pieces.append(audio)
            if int(pause_ms) > 0:
                pieces.append(silence(int(pause_ms)))
            segment_meta.append(
                {
                    "text": text,
                    "speed": speed,
                    "pause_after_ms": pause_ms,
                    "speech_duration_seconds": len(audio) / SAMPLE_RATE,
                    "generation_seconds": segment_seconds,
                }
            )

        waveform = np.concatenate(pieces)
        output = args.output_dir / f"{name}-bm-fable.wav"
        sf.write(output, waveform, SAMPLE_RATE, subtype="PCM_16")
        manifest["variants"][name] = {
            "output": str(output),
            "duration_seconds": len(waveform) / SAMPLE_RATE,
            "render_seconds": time.perf_counter() - variant_started,
            "segments": segment_meta,
        }

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
