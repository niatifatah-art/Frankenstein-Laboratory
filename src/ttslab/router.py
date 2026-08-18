from __future__ import annotations

from dataclasses import dataclass

from .registry import EngineRecord, load_registry


@dataclass(frozen=True, slots=True)
class RouteRequest:
    language: str | None = None
    require: tuple[str, ...] = ()
    prefer: tuple[str, ...] = ()
    allow_restricted_commercial_use: bool = False


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    engine: EngineRecord
    score: int
    reasons: tuple[str, ...]


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
        if (
            not request.allow_restricted_commercial_use
            and engine.commercial_use in {"restricted", "research_only", "prohibited"}
        ):
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
        if "cpu" in engine.hardware:
            score += 1
            reasons.append("CPU-qualified")
        candidates.append(RouteCandidate(engine=engine, score=score, reasons=tuple(reasons)))

    return tuple(sorted(candidates, key=lambda item: (-item.score, item.engine.key)))
