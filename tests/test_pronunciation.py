from pathlib import Path

from ttslab.pronunciation import PronunciationEntry, PronunciationLexicon


def test_text_and_phoneme_overrides_remain_distinct(tmp_path: Path) -> None:
    lexicon = PronunciationLexicon(
        [
            PronunciationEntry("DevShelf", "dev shelf"),
            PronunciationEntry("Yessss", "jɛːs", mode="phoneme"),
        ]
    )
    result = lexicon.apply("DevShelf says Yessss.")
    assert result.text == "dev shelf says Yessss."
    assert [item.mode for item in result.overrides] == ["text", "phoneme"]

    path = tmp_path / "lexicon.json"
    lexicon.to_json(path)
    loaded = PronunciationLexicon.from_json(path)
    assert loaded.entries == lexicon.entries


def test_longest_pronunciation_entry_wins() -> None:
    lexicon = PronunciationLexicon(
        [
            PronunciationEntry("Open", "wrong"),
            PronunciationEntry("OpenAI", "open A I"),
        ]
    )
    assert lexicon.apply("OpenAI").text == "open A I"
