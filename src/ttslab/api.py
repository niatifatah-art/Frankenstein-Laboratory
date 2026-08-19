from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .pipeline import SynthesisPlan, build_synthesis_plan
from .profiles import SynthesisProfile, list_profiles
from .synthesis import SynthesisRequest, SynthesisResult, synthesize


class OurTTS:
    """Stable product-facing Python facade for ACE, Studio and direct applications."""

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir

    def speak(self, request: SynthesisRequest) -> SynthesisResult:
        if self.cache_dir is not None and request.cache_dir is None:
            request = replace(request, cache_dir=self.cache_dir)
        return synthesize(request)

    def plan(self, text: str, **kwargs) -> SynthesisPlan:
        return build_synthesis_plan(text, **kwargs)

    def profiles(self) -> tuple[SynthesisProfile, ...]:
        return list_profiles()
