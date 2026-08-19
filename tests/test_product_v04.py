from __future__ import annotations

import wave
from pathlib import Path

import pytest

from ttslab.adapter_args import compile_adapter_args, render_kokoro_phoneme_overrides
from ttslab.audio_timeline import AudioPart, concatenate_pcm_wavs, silence_frames
from ttslab.profiles import get_profile
from ttslab.pronunciation import PronunciationEntry, PronunciationLexicon
from ttslab.prosody import parse_control_markup
from ttslab.registry import EngineRecord, get_engine
from ttslab.router import RouteRequest, route_engines
from ttslab.synthesis import SynthesisRequest, _pause_layout, _resolve_reference


def _engine(
    key: str,
    *,
    hardware: tuple[str, ...] = ("cpu",),
    capabilities: tuple[str, ...] = (),
    commercial_use: str = "allowed",
    rtf: float = 1.0,
) -> EngineRecord:
    return EngineRecord(
        key=key,
        name=key,
        upstream="https://example.invalid",
        zone="runtime",
        integration_status="ready",
        code_license="MIT",
        weights_license="MIT",
        license_status="verified",
        worker=key,
        kind="tts",
        commercial_use=commercial_use,
        capabilities=capabilities,
        languages=("en",),
        hardware=hardware,
        cpu_generation_rtf=rtf,
    )


def _write_pcm(path: Path, frames: int, rate: int = 1000) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x01\x00" * frames)


def test_fast_cpu_profile_has_measured_ceiling() -> None:
    profile = get_profile("fast_cpu")
    assert profile.device == "cpu"
    assert profile.max_generation_rtf == 2.0


def test_router_filters_device_and_unsafe_commercial_state() -> None:
    cpu = _engine("cpu", hardware=("cpu",), rtf=0.5)
    gpu = _engine("gpu", hardware=("cuda",), rtf=0.1)
    uncertain = _engine("uncertain", commercial_use="checkpoint_dependent", rtf=0.1)
    result = route_engines(RouteRequest(device="cpu"), (gpu, uncertain, cpu))
    assert [item.engine.key for item in result] == ["cpu"]


def test_kokoro_adapter_maps_human_language() -> None:
    adapter = compile_adapter_args(_engine("kokoro"), language="fr", voice="ff_siwis", speed=0.95)
    assert adapter.args == ("--language", "f", "--voice", "ff_siwis", "--speed", "0.95")
    assert adapter.unsupported == ()


def test_kokoro_phoneme_override_is_rendered_not_lost() -> None:
    lexicon = PronunciationLexicon([PronunciationEntry("Yessss", "jɛːs", mode="phoneme")])
    result = lexicon.apply("Yessss!", language="en")
    rendered = render_kokoro_phoneme_overrides(result.text, result.overrides)
    assert rendered == "[Yessss](/jɛːs/)!"


def test_inline_pause_layout_is_exact() -> None:
    clean, markers = parse_control_markup("hello[[pause:320ms]]world[[pause:80ms]]")
    leading, parts = _pause_layout(clean, markers)
    assert leading == 0
    assert parts == (("hello", 320), ("world", 80))


def test_audio_timeline_supports_exact_leading_and_trailing_silence(tmp_path: Path) -> None:
    source = tmp_path / "a.wav"
    output = tmp_path / "out.wav"
    _write_pcm(source, 100, rate=1000)
    info = concatenate_pcm_wavs(
        [AudioPart(source, silence_after_ms=20)], output, leading_silence_ms=30
    )
    assert silence_frames(30, 1000) == 30
    assert info.frames == 150


def test_pocket_reference_is_compiled_as_voice_state_or_audio(tmp_path: Path) -> None:
    reference = tmp_path / "voice.safetensors"
    reference.write_bytes(b"state")
    adapter = compile_adapter_args(
        _engine("pocket_tts", capabilities=("voice_cloning",)),
        language="en",
        reference=reference,
    )
    assert adapter.unsupported == ()
    assert adapter.args[-2:] == ("--voice", str(reference.resolve()))


def test_cpu_voice_design_prefers_measured_faster_candidate() -> None:
    qwen = _engine(
        "qwen",
        hardware=("cpu",),
        capabilities=("voice_design", "multilingual"),
        rtf=47.0,
    )
    vox = _engine(
        "vox",
        hardware=("cpu",),
        capabilities=("voice_design", "multilingual"),
        rtf=5.4,
    )
    result = route_engines(
        RouteRequest(device="cpu", require=("voice_design",), prefer=("multilingual",)),
        (qwen, vox),
    )
    assert result[0].engine.key == "vox"


def test_unknown_explicit_voice_reference_is_blocked_by_default(tmp_path: Path) -> None:
    reference = tmp_path / "voice.wav"
    _write_pcm(reference, 100)
    request = SynthesisRequest(text="hello", output=tmp_path / "out.wav", reference=reference)
    with pytest.raises(ValueError, match="rights are not verified"):
        _resolve_reference(request)


def test_explicit_owned_reference_records_hash(tmp_path: Path) -> None:
    reference = tmp_path / "voice.wav"
    _write_pcm(reference, 100)
    request = SynthesisRequest(
        text="hello",
        output=tmp_path / "out.wav",
        reference=reference,
        reference_consent="owned",
    )
    selected, provenance, _ = _resolve_reference(request)
    assert selected == reference.resolve()
    assert provenance and provenance["consent"] == "owned"
    assert len(provenance["sha256"]) == 64


def test_cosyvoice_real_evidence_is_not_mislabeled_as_runnable() -> None:
    cosy = get_engine("cosyvoice3")
    assert cosy.integration_status == "qualified_external"
    assert cosy.evidence_qualified
    assert not cosy.runnable
    assert cosy.qualification_run == 32189153493
