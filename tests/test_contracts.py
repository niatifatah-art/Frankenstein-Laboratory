from pathlib import Path

from ttslab.contracts import EngineCapabilities, SynthesisRequest


def test_request_defaults_are_safe() -> None:
    request = SynthesisRequest(text="hello", output_path=Path("out.wav"))
    assert request.controls == {}
    assert request.stream is False


def test_capabilities_can_be_unknown() -> None:
    caps = EngineCapabilities()
    assert caps.cpu is None
    assert caps.voice_cloning is None
