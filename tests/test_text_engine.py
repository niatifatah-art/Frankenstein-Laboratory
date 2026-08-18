from ttslab.pronunciation import PronunciationEntry, PronunciationLexicon
from ttslab.text_engine import prepare_text


def test_prepare_text_normalizes_segments_and_scripts() -> None:
    prepared = prepare_text(" Hello   world! \n مرحبا بالعالم؟ ")
    assert prepared.normalized == "Hello world!\nمرحبا بالعالم؟"
    assert prepared.segments == ("Hello world!", "مرحبا بالعالم؟")
    assert prepared.script_hints == ("arabic", "latin")


def test_prepare_text_applies_safe_text_override() -> None:
    lexicon = PronunciationLexicon([PronunciationEntry("DevShelf", "dev shelf")])
    prepared = prepare_text("DevShelf works.", lexicon=lexicon)
    assert prepared.normalized == "dev shelf works."
    assert len(prepared.pronunciation_overrides) == 1
