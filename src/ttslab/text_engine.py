from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .pronunciation import AppliedOverride, PronunciationLexicon


@dataclass(frozen=True, slots=True)
class PreparedText:
    original: str
    normalized: str
    segments: tuple[str, ...]
    script_hints: tuple[str, ...]
    pronunciation_overrides: tuple[AppliedOverride, ...]


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n+ *", "\n", value)
    return value.strip()


def segment_sentences(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    pieces = re.split(r"(?<=[.!?。！？؟])\s+|\n+", text)
    return tuple(piece.strip() for piece in pieces if piece.strip())


def detect_scripts(text: str) -> tuple[str, ...]:
    found: list[str] = []
    checks = (
        ("arabic", lambda c: "\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f"),
        ("cyrillic", lambda c: "\u0400" <= c <= "\u04ff"),
        ("han", lambda c: "\u4e00" <= c <= "\u9fff"),
        ("kana", lambda c: "\u3040" <= c <= "\u30ff"),
        ("hangul", lambda c: "\uac00" <= c <= "\ud7af"),
        ("latin", lambda c: "LATIN" in unicodedata.name(c, "")),
    )
    for name, predicate in checks:
        if any(predicate(char) for char in text):
            found.append(name)
    return tuple(found)


def prepare_text(
    text: str,
    *,
    language: str | None = None,
    lexicon: PronunciationLexicon | None = None,
) -> PreparedText:
    normalized = normalize_text(text)
    result = (lexicon or PronunciationLexicon()).apply(normalized, language=language)
    return PreparedText(
        original=text,
        normalized=result.text,
        segments=segment_sentences(result.text),
        script_hints=detect_scripts(result.text),
        pronunciation_overrides=result.overrides,
    )
