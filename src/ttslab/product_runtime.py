from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .pipeline import required_capabilities_for_controls
from .product import PRODUCT_NAME
from .product_contract import GenerationRequest, ResolvedGeneration
from .rendering import choose_render_engine, render_text
from .router import RouteRequest, route_engines
from .voicepack import VoicePack


@dataclass(frozen=True, slots=True)
class ProductGenerationPlan:
    request: GenerationRequest
    engine: str
    controls: dict[str, Any]
    reference: Path | None
    voice_id: str | None
    max_generation_rtf: float | None
    routing_reasons: tuple[str, ...]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "engine": self.engine,
            "controls": dict(self.controls),
            "reference": str(self.reference) if self.reference else None,
            "voice_id": self.voice_id,
            "max_generation_rtf": self.max_generation_rtf,
            "routing_reasons": self.routing_reasons,
            "metadata": dict(self.metadata),
        }


def _quality_rtf_limit(quality: str) -> float | None:
    if quality == "fast":
        return 1.0
    if quality in {"auto", "local"}:
        return None
    if quality == "best":
        raise ValueError(
            "quality='best' is not executable yet because ourTTS does not have a common quality "
            "benchmark score. Use 'auto' until v0.6 quality evidence exists; refusing to label "
            "the fastest backend as the best-sounding backend."
        )
    raise ValueError(f"Unsupported quality mode: {quality!r}")


def _resolve_voicepack(
    request: GenerationRequest,
    root: Path | None,
) -> tuple[Path | None, str | None, dict[str, Any], dict[str, Any]]:
    if root is None:
        if request.voice is not None:
            raise ValueError(
                "A product voice ID requires a VoicePack mapping. Backend-specific voice names are "
                "not accepted by the simple ourTTS product path because another backend could ignore them."
            )
        controls = dict(request.controls)
        if request.style != "natural":
            controls.setdefault("style", request.style)
        return None, None, controls, {}

    root = root.resolve()
    pack = VoicePack.load(root)
    if request.voice is not None and request.voice != pack.voice_id:
        raise ValueError(
            f"Requested voice {request.voice!r} does not match VoicePack identity {pack.voice_id!r}."
        )

    selection = pack.select_reference(root, allow_unknown_consent=False, verify_hash=True)
    controls: dict[str, Any] = {}
    if request.style != "natural":
        if request.style in pack.style_presets:
            controls.update(pack.style_controls(request.style))
        else:
            controls["style"] = request.style
    controls.update(request.controls)

    metadata = {
        "voicepack": {
            "voice_id": pack.voice_id,
            "display_name": pack.display_name,
            "reference": {
                "path": selection.clip.path,
                "sha256": selection.clip.sha256,
                "license": selection.clip.license,
                "source": selection.clip.source,
                "consent": selection.clip.consent,
            },
            "provenance": pack.provenance,
        }
    }
    return selection.path, pack.voice_id, controls, metadata


def _routing_evidence(
    *,
    engine_key: str,
    language: str | None,
    reference: Path | None,
    controls: dict[str, Any],
    max_generation_rtf: float | None,
) -> tuple[str, ...]:
    required = set(required_capabilities_for_controls(controls))
    if reference is not None:
        required.add("voice_cloning")
    candidates = route_engines(
        RouteRequest(
            language=language,
            require=tuple(sorted(required)),
            max_generation_rtf=max_generation_rtf,
        )
    )
    for candidate in candidates:
        if candidate.engine.key == engine_key:
            return candidate.reasons or ("qualified product route",)
    return ("qualified by rendering contract",)


def plan_generation(
    request: GenerationRequest,
    *,
    voicepack_root: Path | None = None,
) -> ProductGenerationPlan:
    max_generation_rtf = _quality_rtf_limit(request.quality)
    reference, voice_id, controls, voicepack_metadata = _resolve_voicepack(
        request,
        voicepack_root,
    )

    engine = choose_render_engine(
        language=request.language,
        explicit_engine=None,
        reference=reference,
        max_generation_rtf=max_generation_rtf,
        controls=controls,
    )
    reasons = _routing_evidence(
        engine_key=engine.key,
        language=request.language,
        reference=reference,
        controls=controls,
        max_generation_rtf=max_generation_rtf,
    )
    metadata: dict[str, Any] = {
        "product": {
            "name": PRODUCT_NAME,
            "request": request.to_dict(),
            "routing": {
                "engine": engine.key,
                "reasons": list(reasons),
                "quality_mode": request.quality,
                "max_generation_rtf": max_generation_rtf,
                "offline_inference_requested": request.offline,
            },
        }
    }
    metadata.update(voicepack_metadata)
    return ProductGenerationPlan(
        request=request,
        engine=engine.key,
        controls=controls,
        reference=reference,
        voice_id=voice_id,
        max_generation_rtf=max_generation_rtf,
        routing_reasons=reasons,
        metadata=metadata,
    )


def generate(
    request: GenerationRequest,
    output: Path,
    *,
    voicepack_root: Path | None = None,
    manifest_path: Path | None = None,
    timeout_seconds: float = 1800.0,
) -> ResolvedGeneration:
    plan = plan_generation(request, voicepack_root=voicepack_root)
    output = output.resolve()
    manifest_path = (manifest_path or output.with_suffix(output.suffix + ".manifest.json")).resolve()

    manifest = render_text(
        request.text,
        output,
        language=request.language,
        engine_key=plan.engine,
        voice=None,
        reference=plan.reference,
        controls=plan.controls,
        max_generation_rtf=plan.max_generation_rtf,
        manifest_path=manifest_path,
        manifest_metadata=plan.metadata,
        timeout_seconds=timeout_seconds,
    )
    if manifest.get("engine") != plan.engine:
        raise RuntimeError("Rendered engine does not match the product routing decision.")

    return ResolvedGeneration(
        request=request,
        engine=plan.engine,
        voice_id=plan.voice_id,
        manifest_path=str(manifest_path),
        output_path=str(output),
        status="completed",
        routing_reasons=plan.routing_reasons,
    )
