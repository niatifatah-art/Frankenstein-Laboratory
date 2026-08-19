from __future__ import annotations

from dataclasses import dataclass

from .registry import EngineRecord, load_registry

_COMMERCIAL_SAFE = {"allowed", "allowed_with_attribution", "commercial_allowed"}


@dataclass(frozen=True, slots=True)
class RouteRequest:
    language: str | None = None
    require: tuple[str, ...] = ()
    prefer: tuple[str, ...] = ()
    allow_restricted_commercial_use: bool = False
    max_generation_rtf: float | None = None
    device: str | None = None


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    engine: EngineRecord
    score: int
    reasons: tuple[str, ...]


def _supports_device(engine: EngineRecord, device: str | None) -> bool:
    if not device or device == "auto":
        return True
    requested = device.casefold().split(":", 1)[0]
    hardware = {item.casefold() for item in engine.hardware}
    if requested == "cpu":
        return any(item == "cpu" or item.startswith("cpu_") for item in hardware)
    if requested == "cuda":
        return any(item == "cuda" or item.startswith("cuda_") for item in hardware)
    if requested == "mps":
        return "mps" in hardware
    return requested in hardware


def route_engines(
    request: RouteRequest,
    records: tuple[EngineRecord, ...] | None = None,
) -> tuple[RouteCandidate, ...]:
    candidates: list[RouteCandidate] = []
    for engine in records or load_registry():
        if not engine.runnable or engine.kind != "tts":
            continue
        if not engine.supports_language(request.language):
            continue
        if any(not engine.supports(capability) for capability in request.require):
            continue
        if not _supports_device(engine, request.device):
            continue
        if not request.allow_restricted_commercial_use and engine.commercial_use not in _COMMERCIAL_SAFE:
            continue
        if request.max_generation_rtf is not None:
            if engine.cpu_generation_rtf is None:
                continue
            if engine.cpu_generation_rtf > request.max_generation_rtf:
                continue

        score = 0
        reasons: list[str] = []
        for capability in request.prefer:
            if engine.supports(capability):
                score += 10
                reasons.append(f"supports preferred capability {capability}")
        if request.language and engine.supports_language(request.language):
            score += 3
            reasons.append(f"supports language {request.language}")
        if request.device and _supports_device(engine, request.device):
            score += 3
            reasons.append(f"supports device {request.device}")

        if engine.cpu_generation_rtf is not None:
            if engine.cpu_generation_rtf <= 0.5:
                score += 20
                reasons.append("measured CPU generation faster than 2x realtime")
            elif engine.cpu_generation_rtf <= 1.0:
                score += 15
                reasons.append("measured CPU generation realtime-or-better")
            elif engine.cpu_generation_rtf <= 2.0:
                score += 8
                reasons.append("measured CPU generation near realtime")
            elif engine.cpu_generation_rtf <= 5.0:
                score += 2
                reasons.append("measured CPU generation below 5x realtime latency")
            else:
                penalty = min(20, max(1, int(engine.cpu_generation_rtf // 5)))
                score -= penalty
                reasons.append(f"CPU-qualified but measured slow (-{penalty})")

        candidates.append(RouteCandidate(engine=engine, score=score, reasons=tuple(reasons)))

    return tuple(sorted(candidates, key=lambda item: (-item.score, item.engine.key)))
