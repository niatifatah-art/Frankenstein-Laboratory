from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    languages: tuple[str, ...] = ()
    cpu: bool | None = None
    gpu: bool | None = None
    streaming: bool | None = None
    voice_cloning: bool | None = None
    voice_design: bool | None = None
    phoneme_input: bool | None = None
    long_form: bool | None = None
    dialogue: bool | None = None


@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    text: str
    output_path: Path
    voice: str | Path | None = None
    language: str | None = None
    controls: Mapping[str, Any] = field(default_factory=dict)
    stream: bool = False


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    engine: str
    output_path: Path
    sample_rate: int | None = None
    duration_seconds: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class TTSEngine(Protocol):
    @property
    def name(self) -> str: ...

    def capabilities(self) -> EngineCapabilities: ...

    def health(self) -> Mapping[str, Any]: ...

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult: ...
