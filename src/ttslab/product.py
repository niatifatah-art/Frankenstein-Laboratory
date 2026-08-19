from __future__ import annotations

from dataclasses import asdict, dataclass

PRODUCT_NAME = "ourTTS"
LAB_NAME = "Frankenstein Laboratory"
PRODUCT_TAGLINE = "Simple speech creation, serious engineering underneath."


@dataclass(frozen=True, slots=True)
class ModelProfile:
    key: str
    display_name: str
    purpose: str
    target_parameters_millions: int | None
    target_weight_mb_fp16: int | None
    priority: tuple[str, ...]
    deliberately_not_required: tuple[str, ...] = ()
    status: str = "research_target"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


MODEL_FAMILY: tuple[ModelProfile, ...] = (
    ModelProfile(
        key="atom",
        display_name="ourTTS Atom",
        purpose="Tiny, excellent-sounding local speech for constrained CPU/on-device use.",
        target_parameters_millions=80,
        target_weight_mb_fp16=160,
        priority=("naturalness", "pronunciation", "low_memory", "cpu", "fast_start"),
        deliberately_not_required=("voice_design", "dialogue", "large_language_coverage"),
    ),
    ModelProfile(
        key="nano",
        display_name="ourTTS Nano",
        purpose="Fast local generation with a small feature set and lightweight voice identity support.",
        target_parameters_millions=150,
        target_weight_mb_fp16=300,
        priority=("naturalness", "streaming", "low_latency", "cpu", "voice_identity"),
    ),
    ModelProfile(
        key="mini",
        display_name="ourTTS Mini",
        purpose="Balanced local model for multilingual speech, styles, and everyday creator workflows.",
        target_parameters_millions=400,
        target_weight_mb_fp16=800,
        priority=("quality", "multilingual", "style", "voice_identity", "local"),
    ),
    ModelProfile(
        key="core",
        display_name="ourTTS Core",
        purpose="Default general-purpose model balancing quality, control, cloning, and performance.",
        target_parameters_millions=1000,
        target_weight_mb_fp16=2000,
        priority=("quality", "cloning", "multilingual", "prosody", "long_form"),
    ),
    ModelProfile(
        key="pro",
        display_name="ourTTS Pro",
        purpose="Creator-focused high-quality synthesis with expressive control and strong voice identity.",
        target_parameters_millions=2250,
        target_weight_mb_fp16=4500,
        priority=("maximum_quality", "cloning", "voice_design", "expressiveness", "long_form"),
    ),
    ModelProfile(
        key="omni",
        display_name="ourTTS Omni",
        purpose="Highest-capability experience; initially may orchestrate specialists before becoming a checkpoint.",
        target_parameters_millions=None,
        target_weight_mb_fp16=None,
        priority=("best_available", "auto_routing", "dialogue", "voice_design", "all_controls"),
        status="system_target",
    ),
)


def model_profile(key: str) -> ModelProfile:
    normalized = key.casefold()
    for profile in MODEL_FAMILY:
        if profile.key == normalized:
            return profile
    raise KeyError(key)


def product_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "product": PRODUCT_NAME,
        "laboratory": LAB_NAME,
        "tagline": PRODUCT_TAGLINE,
        "models": [profile.to_dict() for profile in MODEL_FAMILY],
        "truth_rules": [
            "A target profile is not a released checkpoint.",
            "A checkpoint is released only after measured target-baseline acceptance.",
            "External engines keep their own licensing and provenance identity.",
            "Unsupported controls are never silently ignored.",
        ],
    }
