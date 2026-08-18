import pytest

from ttslab.prosody import ProsodyEvent, ProsodyTimeline, parse_control_markup


def test_control_markup_is_engine_neutral() -> None:
    text, markers = parse_control_markup("Hello [[pause:320ms]]world [[emotion:happy]]today.")
    assert text == "Hello world today."
    assert markers[0].kind == "pause"
    assert markers[0].value == 320
    assert markers[1].kind == "emotion"


def test_timeline_rejects_unsorted_or_negative_events() -> None:
    with pytest.raises(ValueError):
        ProsodyEvent(-1, "pause", 10)
    with pytest.raises(ValueError):
        ProsodyTimeline((ProsodyEvent(100, "style", "calm"), ProsodyEvent(0, "pause", 20)))
