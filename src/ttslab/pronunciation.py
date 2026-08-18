from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_ALLOWED_MODES = {"text", "phoneme"}


@dataclass(frozen=True, slots=True)
class PronunciationEntry:
    term: str
    replacement: str
    mode: str = "text"
    language: str | None = None
    case_sensitive: bool = False
    whole_word: bool = True
    source: str = "user"

    def __post_init__(self) -> None:
        if not self.term:
            raise ValueError("Pronunciation term must not be empty.")
        if not self.replacement:
            raise ValueError("Pronunciation replacement must not be empty.")
        if self.mode not in _ALLOWED_MODES:
            raise ValueError(f"Unsupported pronunciation mode: {self.mode!r}")


@dataclass(frozen=True, slots=True)
class AppliedOverride:
    term: str
    replacement: str
    mode: str
    language: str | None
    source: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class PronunciationResult:
    text: str
    overrides: tuple[AppliedOverride, ...]


class PronunciationLexicon:
    def __init__(self, entries: tuple[PronunciationEntry, ...] | list[PronunciationEntry] = ()) -> None:
        self.entries = tuple(entries)

    @classmethod
    def from_json(cls, path: Path) -> PronunciationLexicon:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != 1:
            raise ValueError("Unsupported pronunciation lexicon schema.")
        return cls([PronunciationEntry(**item) for item in raw.get("entries", [])])

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "entries": [asdict(item) for item in self.entries]}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def apply(self, text: str, *, language: str | None = None) -> PronunciationResult:
        candidates = [
            item
            for item in self.entries
            if item.language is None
            or language is None
            or item.language.casefold() == language.casefold()
        ]
        candidates.sort(key=lambda item: len(item.term), reverse=True)
        if not candidates or not text:
            return PronunciationResult(text=text, overrides=())

        output: list[str] = []
        overrides: list[AppliedOverride] = []
        cursor = 0

        while cursor < len(text):
            match = self._best_match(text, cursor, candidates)
            if match is None:
                output.append(text[cursor])
                cursor += 1
                continue

            entry, end = match
            start_out = sum(len(part) for part in output)
            rendered = entry.replacement if entry.mode == "text" else text[cursor:end]
            output.append(rendered)
            overrides.append(
                AppliedOverride(
                    term=text[cursor:end],
                    replacement=entry.replacement,
                    mode=entry.mode,
                    language=entry.language,
                    source=entry.source,
                    start=start_out,
                    end=start_out + len(rendered),
                )
            )
            cursor = end

        return PronunciationResult(text="".join(output), overrides=tuple(overrides))

    @staticmethod
    def _best_match(
        text: str,
        start: int,
        entries: list[PronunciationEntry],
    ) -> tuple[PronunciationEntry, int] | None:
        for entry in entries:
            end = start + len(entry.term)
            if end > len(text):
                continue
            chunk = text[start:end]
            same = chunk == entry.term if entry.case_sensitive else chunk.casefold() == entry.term.casefold()
            if not same:
                continue
            if entry.whole_word and not _whole_word_boundary(text, start, end):
                continue
            return entry, end
        return None


def _whole_word_boundary(text: str, start: int, end: int) -> bool:
    left_ok = start == 0 or not _word_char(text[start - 1])
    right_ok = end == len(text) or not _word_char(text[end])
    return left_ok and right_ok


def _word_char(char: str) -> bool:
    return bool(re.match(r"[\w]", char, flags=re.UNICODE))
