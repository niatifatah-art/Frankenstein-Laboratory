from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

_ALLOWED_QUALITY = {"auto", "fast", "best", "local"}


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    text: str
    voice: str | None = None
    language: str | None = None
    style: str = "natural"
    quality: str = "auto"
    offline: bool = False
    controls: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if self.quality not in _ALLOWED_QUALITY:
            choices = ", ".join(sorted(_ALLOWED_QUALITY))
            raise ValueError(f"quality must be one of: {choices}")
        if not self.style.strip():
            raise ValueError("style must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResolvedGeneration:
    request: GenerationRequest
    engine: str
    model_revision: str | None = None
    voice_id: str | None = None
    manifest_path: str | None = None
    output_path: str | None = None
    status: str = "planned"
    routing_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.engine.strip():
            raise ValueError("resolved engine must not be empty")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["request"] = self.request.to_dict()
        return payload


def request_example() -> dict[str, Any]:
    return GenerationRequest(
        text="Hello from ourTTS.",
        voice="creator_voice",
        language="en",
        style="energetic",
        quality="auto",
        offline=True,
    ).to_dict()
