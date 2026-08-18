import wave
from pathlib import Path

from ttslab.audio_timeline import AudioPart, concatenate_pcm_wavs, silence_frames


def _wav(path: Path, frames: int, rate: int = 1000) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x01\x00" * frames)


def test_silence_frame_count_is_deterministic() -> None:
    assert silence_frames(320, 24000) == 7680


def test_pcm_concatenation_inserts_exact_silence(tmp_path: Path) -> None:
    first = tmp_path / "a.wav"
    second = tmp_path / "b.wav"
    output = tmp_path / "joined.wav"
    _wav(first, 100)
    _wav(second, 200)
    info = concatenate_pcm_wavs(
        [AudioPart(first, silence_after_ms=250), AudioPart(second)],
        output,
    )
    assert info.sample_rate == 1000
    assert info.frames == 100 + 250 + 200
