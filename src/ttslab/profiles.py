from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SynthesisProfile:
    key: str
    description: str
    require: tuple[str, ...] = ()
    prefer: tuple[str, ...] = ()
    device: str = "auto"
    max_generation_rtf: float | None = None


_PROFILES: dict[str, SynthesisProfile] = {
    "auto": SynthesisProfile(
        key="auto",
        description="Choose a qualified commercial-safe backend for the detected device.",
        prefer=("streaming",),
    ),
    "fast_cpu": SynthesisProfile(
        key="fast_cpu",
        description="Prefer measured near-realtime CPU backends.",
        prefer=("streaming", "cpu"),
        device="cpu",
        max_generation_rtf=2.0,
    ),
    "balanced_cpu": SynthesisProfile(
        key="balanced_cpu",
        description="Allow slower CPU backends when they provide useful extra capability.",
        prefer=("streaming",),
        device="cpu",
        max_generation_rtf=6.0,
    ),
    "quality": SynthesisProfile(
        key="quality",
        description="Prefer expressive/multilingual capability without an artificial CPU RTF ceiling.",
        prefer=("style_control", "multilingual"),
    ),
    "voice_clone": SynthesisProfile(
        key="voice_clone",
        description="Require a qualified backend with voice-cloning capability.",
        require=("voice_cloning",),
        prefer=("multilingual", "streaming"),
    ),
    "voice_design": SynthesisProfile(
        key="voice_design",
        description="Require natural-language Voice Design.",
        require=("voice_design",),
        prefer=("multilingual",),
    ),
    "multilingual": SynthesisProfile(
        key="multilingual",
        description="Require a qualified multilingual backend.",
        require=("multilingual",),
        prefer=("voice_cloning", "style_control"),
    ),
}


def get_profile(key: str) -> SynthesisProfile:
    try:
        return _PROFILES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown synthesis profile: {key!r}") from exc


def list_profiles() -> tuple[SynthesisProfile, ...]:
    return tuple(_PROFILES[key] for key in sorted(_PROFILES))
