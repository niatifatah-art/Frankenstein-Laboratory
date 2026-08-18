from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_ALLOWED_EVENT_TYPES = {
    "pause",
    "style",
    "emotion",
    "pace",
    "pitch",
    "volume",
    "emphasis",
    "whisper",
    "nonverbal",
}


@dataclass(frozen=True, slots=True)
class ProsodyEvent:
    at_ms: int
    kind: str
    value: Any
    end_ms: int | None = None

    def __post_init__(self) -> None:
        if self.at_ms < 0:
            raise ValueError("Prosody event time must be non-negative.")
        if self.kind not in _ALLOWED_EVENT_TYPES:
            raise ValueError(f"Unsupported prosody event: {self.kind!r}")
        if self.end_ms is not None and self.end_ms < self.at_ms:
            raise ValueError("Prosody end_ms must not precede at_ms.")
        if self.kind == "pause" and (not isinstance(self.value, int) or self.value < 0):
            raise ValueError("Pause value must be a non-negative integer number of milliseconds.")


@dataclass(frozen=True, slots=True)
class ProsodyTimeline:
    events: tuple[ProsodyEvent, ...]

    def __post_init__(self) -> None:
        if tuple(sorted(self.events, key=lambda event: event.at_ms)) != self.events:
            raise ValueError("Prosody events must be sorted by at_ms.")

    @classmethod
    def from_json(cls, path: Path) -> "ProsodyTimeline":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != 1:
            raise ValueError("Unsupported prosody timeline schema.")
        events = tuple(ProsodyEvent(**item) for item in raw.get("events", []))
        return cls(events=events)

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "events": [asdict(event) for event in self.events]}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class ControlMarker:
    char_offset: int
    kind: str
    value: Any


_MARKER = re.compile(r"\[\[(?P<kind>[a-z_]+):(?P<value>.*?)\]\]")


def parse_control_markup(text: str) -> tuple[str, tuple[ControlMarker, ...]]:
    """Parse neutral OurTTS controls without pretending they are native model markup."""
    output: list[str] = []
    markers: list[ControlMarker] = []
    cursor = 0
    for match in _MARKER.finditer(text):
        output.append(text[cursor:match.start()])
        kind = match.group("kind")
        if kind not in _ALLOWED_EVENT_TYPES:
            raise ValueError(f"Unsupported control marker: {kind!r}")
        offset = sum(len(part) for part in output)
        markers.append(ControlMarker(offset, kind, _parse_marker_value(kind, match.group("value"))))
        cursor = match.end()
    output.append(text[cursor:])
    return "".join(output), tuple(markers)


def _parse_marker_value(kind: str, raw: str) -> Any:
    value = raw.strip()
    if kind == "pause":
        match = re.fullmatch(r"(\d+)(?:ms)?", value)
        if not match:
            raise ValueError(f"Invalid pause marker value: {raw!r}")
        return int(match.group(1))
    if kind in {"pace", "pitch", "volume"}:
        return float(value)
    if kind == "whisper":
        if value.casefold() not in {"true", "false"}:
            raise ValueError("whisper marker must be true or false")
        return value.casefold() == "true"
    return value
