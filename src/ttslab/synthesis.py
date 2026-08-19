from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .adapter_args import compile_adapter_args, render_kokoro_phoneme_overrides
from .audio import inspect_wav, sha256_file
from .audio_timeline import AudioPart, concatenate_pcm_wavs
from .cache import cache_key, default_cache_dir, restore, store
from .hardware import resolve_device
from .isolation import execute_worker
from .pipeline import build_synthesis_plan
from .profiles import get_profile
from .pronunciation import PronunciationLexicon
from .prosody import ControlMarker, parse_control_markup
from .registry import EngineRecord, get_engine
from .router import RouteRequest, route_engines
from .text_engine import prepare_text, segment_sentences
from .voicepack import VoicePack

_SAFE_CONSENT = {"owned", "licensed", "consented", "synthetic"}
_NATIVE_NONVERBAL = {"laugh", "cough", "chuckle"}


@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    text: str
    output: Path
    language: str | None = None
    engine: str | None = None
    profile: str = "auto"
    voice: str | None = None
    reference: Path | None = None
    reference_text: str | None = None
    reference_consent: str = "unknown"
    voice_design: str | None = None
    style: str | None = None
    speed: float | None = None
    device: str | None = None
    lexicon: Path | None = None
    voicepack_root: Path | None = None
    controls: dict[str, Any] = field(default_factory=dict)
    allow_unknown_voice_rights: bool = False
    allow_restricted_models: bool = False
    allow_degraded: bool = False
    use_cache: bool = True
    cache_dir: Path | None = None
    timeout_seconds: float = 1800.0
    engine_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    schema_version: int
    engine: str
    profile: str
    device: str
    output_path: str
    cached: bool
    audio: dict[str, Any]
    segments: int
    exact_pause_ms: int
    native_controls: tuple[str, ...]
    degraded_controls: tuple[str, ...]
    reference_provenance: dict[str, Any] | None
    cache_key: str


def _lexicon(path: Path | None) -> PronunciationLexicon | None:
    return PronunciationLexicon.from_json(path) if path else None


def _select_engine(request: SynthesisRequest, *, has_reference: bool, device: str) -> EngineRecord:
    profile = get_profile(request.profile)
    required = list(profile.require)
    preferred = list(profile.prefer)
    if has_reference:
        required.append("voice_cloning")
    if request.voice_design:
        required.append("voice_design")
    if request.style:
        preferred.append("style_control")

    if request.engine:
        engine = get_engine(request.engine)
        explicit = route_engines(
            RouteRequest(
                language=request.language,
                require=tuple(dict.fromkeys(required)),
                device=device,
                allow_restricted_commercial_use=request.allow_restricted_models,
            ),
            (engine,),
        )
        if not explicit:
            raise ValueError(
                f"Engine {request.engine!r} is not a qualified safe match for the requested "
                f"language/capabilities/device. Use only an explicit opt-in for restricted models."
            )
        return engine

    max_rtf = profile.max_generation_rtf
    candidates = route_engines(
        RouteRequest(
            language=request.language,
            require=tuple(dict.fromkeys(required)),
            prefer=tuple(dict.fromkeys(preferred)),
            max_generation_rtf=max_rtf,
            device=device,
            allow_restricted_commercial_use=request.allow_restricted_models,
        )
    )
    if not candidates:
        raise ValueError(
            f"No qualified commercial-safe backend matches profile={request.profile!r}, "
            f"language={request.language!r}, device={device!r}."
        )
    return candidates[0].engine


def _resolve_voicepack_style(pack: VoicePack | None, style: str | None) -> str | None:
    if not pack or not style or style not in pack.style_presets:
        return style
    preset = pack.style_presets[style]
    value = preset.get("description") or preset.get("prompt") or preset.get("style")
    return str(value) if value is not None else style


def _resolve_reference(
    request: SynthesisRequest,
) -> tuple[Path | None, dict[str, Any] | None, VoicePack | None]:
    pack = VoicePack.load(request.voicepack_root) if request.voicepack_root else None
    reference = request.reference.resolve() if request.reference else None
    provenance: dict[str, Any] | None = None

    if reference is not None:
        consent = request.reference_consent.casefold()
        if consent not in _SAFE_CONSENT and not request.allow_unknown_voice_rights:
            raise ValueError(
                "Voice cloning reference rights are not verified. Set --reference-consent to "
                "owned/licensed/consented/synthetic, or explicitly allow unknown rights."
            )
        if not reference.exists():
            raise FileNotFoundError(reference)
        provenance = {
            "source": "explicit",
            "path": str(reference),
            "consent": consent,
            "sha256": sha256_file(reference),
        }
        return reference, provenance, pack

    if pack:
        for clip in pack.references:
            if clip.consent in _SAFE_CONSENT or request.allow_unknown_voice_rights:
                candidate = (request.voicepack_root / clip.path).resolve()
                if not candidate.is_relative_to(request.voicepack_root.resolve()):
                    continue
                if not candidate.exists():
                    continue
                provenance = {
                    "source": "voicepack",
                    "voice_id": pack.voice_id,
                    "path": clip.path,
                    "consent": clip.consent,
                    "license": clip.license,
                    "origin": clip.source,
                    "sha256": sha256_file(candidate),
                }
                return candidate, provenance, pack
        if pack.references:
            raise ValueError("VoicePack has references, but none have usable consent/provenance.")

    return None, None, pack


def _pause_layout(text: str, markers: tuple[ControlMarker, ...]) -> tuple[int, tuple[tuple[str, int], ...]]:
    pauses: dict[int, int] = {}
    for marker in markers:
        if marker.kind == "pause":
            pauses[marker.char_offset] = pauses.get(marker.char_offset, 0) + int(marker.value)
    if not pauses:
        return 0, ((text, 0),)

    leading = pauses.pop(0, 0)
    positions = sorted(pauses)
    parts: list[tuple[str, int]] = []
    cursor = 0
    for pos in positions:
        if pos < cursor or pos > len(text):
            continue
        chunk = text[cursor:pos]
        delay = pauses[pos]
        if chunk:
            parts.append((chunk, delay))
        elif parts:
            prev_text, prev_delay = parts[-1]
            parts[-1] = (prev_text, prev_delay + delay)
        else:
            leading += delay
        cursor = pos
    tail = text[cursor:]
    if tail:
        parts.append((tail, 0))
    if not parts:
        parts.append(("", 0))
    return leading, tuple(parts)


def _markers_in_span(
    markers: tuple[ControlMarker, ...], start: int, end: int
) -> tuple[ControlMarker, ...]:
    return tuple(
        ControlMarker(marker.char_offset - start, marker.kind, marker.value)
        for marker in markers
        if marker.kind != "pause" and start <= marker.char_offset <= end
    )


def _render_nonverbal(
    text: str, markers: tuple[ControlMarker, ...], engine: EngineRecord
) -> tuple[str, tuple[str, ...]]:
    unsupported: list[str] = []
    rendered = text
    for marker in sorted(markers, key=lambda item: item.char_offset, reverse=True):
        if marker.kind != "nonverbal":
            unsupported.append(f"inline_{marker.kind}")
            continue
        value = str(marker.value).strip().casefold()
        if not engine.supports("paralinguistic_tags") or value not in _NATIVE_NONVERBAL:
            unsupported.append(f"nonverbal:{value}")
            continue
        rendered = rendered[: marker.char_offset] + f"[{value}]" + rendered[marker.char_offset :]
    return rendered, tuple(sorted(set(unsupported)))


def _build_segments(
    clean_text: str,
    markers: tuple[ControlMarker, ...],
    *,
    engine: EngineRecord,
    inter_sentence_pause_ms: int,
) -> tuple[int, tuple[tuple[str, int], ...], tuple[str, ...]]:
    non_pause = tuple(marker for marker in markers if marker.kind != "pause")
    if any(marker.kind == "pause" for marker in markers):
        leading, raw_parts = _pause_layout(clean_text, markers)
        parts: list[tuple[str, int]] = []
        unsupported: list[str] = []
        cursor = 0
        for text, delay in raw_parts:
            end = cursor + len(text)
            local_markers = _markers_in_span(non_pause, cursor, end)
            rendered, missing = _render_nonverbal(text, local_markers, engine)
            parts.append((rendered, delay))
            unsupported.extend(missing)
            cursor = end
        return leading, tuple(parts), tuple(sorted(set(unsupported)))

    rendered, unsupported = _render_nonverbal(clean_text, non_pause, engine)
    if inter_sentence_pause_ms <= 0:
        return 0, ((rendered, 0),), unsupported
    sentences = segment_sentences(rendered)
    if len(sentences) <= 1:
        return 0, ((rendered, 0),), unsupported
    return 0, tuple(
        (sentence, inter_sentence_pause_ms if index < len(sentences) - 1 else 0)
        for index, sentence in enumerate(sentences)
    ), unsupported


def _collapse_silent_text_parts(
    leading_silence_ms: int, parts: tuple[tuple[str, int], ...]
) -> tuple[int, tuple[tuple[str, int], ...]]:
    leading = leading_silence_ms
    output: list[tuple[str, int]] = []
    for text, delay in parts:
        if text.strip():
            output.append((text, delay))
        elif output:
            previous, previous_delay = output[-1]
            output[-1] = (previous, previous_delay + delay)
        else:
            leading += delay
    return leading, tuple(output)


def _execute_segment(
    engine: EngineRecord,
    text: str,
    output: Path,
    *,
    language: str | None,
    lexicon: PronunciationLexicon | None,
    adapter_args: tuple[str, ...],
    engine_args: tuple[str, ...],
    timeout_seconds: float,
) -> dict[str, Any]:
    prepared = prepare_text(text, language=language, lexicon=lexicon)
    worker_text = prepared.normalized
    phoneme_overrides = tuple(
        item for item in prepared.pronunciation_overrides if item.mode == "phoneme"
    )
    if phoneme_overrides:
        if engine.key == "kokoro":
            worker_text = render_kokoro_phoneme_overrides(worker_text, phoneme_overrides)
        elif not engine.supports("phoneme_input"):
            raise ValueError(
                f"Engine {engine.key!r} cannot apply the requested phoneme pronunciation override."
            )
        else:
            raise ValueError(
                f"Engine {engine.key!r} advertises phoneme input but has no verified OurTTS compiler yet."
            )

    execution = execute_worker(
        engine.worker or "",
        text=worker_text,
        output=output,
        extra_args=[*adapter_args, *engine_args],
        timeout_seconds=timeout_seconds,
    )
    if execution.returncode != 0:
        message = execution.stderr.strip()[-2000:] or execution.stdout.strip()[-2000:]
        raise RuntimeError(f"{engine.key} worker failed ({execution.returncode}): {message}")
    info = inspect_wav(output, min_frames=100)
    return {
        "prepared_text": prepared.normalized,
        "worker_text": worker_text,
        "worker_result": execution.payload,
        "audio": info.as_dict(),
    }


def _voicepack_state_for_engine(
    pack: VoicePack | None, root: Path | None, engine: EngineRecord
) -> tuple[Path | None, str | None]:
    if pack is None or root is None:
        return None, None
    for state in pack.backend_states:
        if state.engine != engine.key:
            continue
        path = (root / state.path).resolve()
        if not path.is_relative_to(root.resolve()) or not path.exists():
            continue
        digest = sha256_file(path)
        if state.sha256 and digest != state.sha256.lower():
            raise ValueError(f"VoicePack backend state hash mismatch for {state.engine}.")
        return path, digest
    return None, None


def synthesize(request: SynthesisRequest) -> SynthesisResult:
    if not request.text.strip():
        raise ValueError("Text must not be empty.")
    if request.speed is not None and request.speed <= 0:
        raise ValueError("speed must be positive.")

    profile = get_profile(request.profile)
    device = resolve_device(request.device or profile.device)
    reference, reference_provenance, pack = _resolve_reference(request)
    style = _resolve_voicepack_style(pack, request.style)
    engine = _select_engine(request, has_reference=reference is not None, device=device)
    backend_state, backend_state_hash = _voicepack_state_for_engine(
        pack, request.voicepack_root, engine
    )
    adapter_reference = backend_state or reference
    if backend_state is not None and reference_provenance is not None:
        reference_provenance = dict(reference_provenance)
        reference_provenance["backend_state"] = {
            "engine": engine.key,
            "path": str(backend_state),
            "sha256": backend_state_hash,
        }

    lexicon_path = request.lexicon
    if lexicon_path is None and pack and pack.pronunciation_lexicon and request.voicepack_root:
        lexicon_path = request.voicepack_root / pack.pronunciation_lexicon

    clean_text, markers = parse_control_markup(request.text)
    controls = dict(request.controls)
    if request.voice_design:
        controls["voice_design"] = request.voice_design
    if style:
        controls["style"] = style
    if any(marker.kind == "pause" for marker in markers):
        controls.setdefault("pause", True)

    plan = build_synthesis_plan(
        clean_text,
        language=request.language,
        explicit_engine=engine.key,
        controls={
            key: value
            for key, value in controls.items()
            if key
            in {"style", "emotion", "phoneme", "voice_design", "nonverbal", "pause"}
        },
        lexicon=_lexicon(lexicon_path),
        max_generation_rtf=profile.max_generation_rtf,
    )

    adapter = compile_adapter_args(
        engine,
        language=request.language,
        voice=request.voice,
        reference=adapter_reference,
        reference_text=request.reference_text,
        voice_design=request.voice_design,
        style=style,
        speed=request.speed,
        device=device,
    )

    pause_value = controls.get("pause", 0)
    inter_sentence_pause_ms = int(pause_value) if isinstance(pause_value, int) else 0
    leading_pause, segments, marker_unsupported = _build_segments(
        clean_text,
        markers,
        engine=engine,
        inter_sentence_pause_ms=inter_sentence_pause_ms,
    )
    leading_pause, segments = _collapse_silent_text_parts(leading_pause, segments)
    degraded = tuple(
        sorted(set(plan.controls.unsupported) | set(adapter.unsupported) | set(marker_unsupported))
    )
    if degraded and not request.allow_degraded:
        raise ValueError(
            "Requested controls are not fully supported by the selected backend: "
            + ", ".join(degraded)
        )

    ref_hash = backend_state_hash or (
        reference_provenance.get("sha256") if reference_provenance else None
    )
    key_payload = {
        "schema_version": 1,
        "engine": engine.key,
        "engine_version": engine.version,
        "source_revision": engine.source_revision,
        "text": request.text,
        "language": request.language,
        "profile": request.profile,
        "voice": request.voice,
        "reference_sha256": ref_hash,
        "reference_text": request.reference_text,
        "allow_restricted_models": request.allow_restricted_models,
        "voice_design": request.voice_design,
        "style": style,
        "speed": request.speed,
        "device": device,
        "controls": controls,
        "adapter_args": list(adapter.args),
        "engine_args": list(request.engine_args),
    }
    key = cache_key(key_payload)
    cache_root = request.cache_dir or default_cache_dir()
    output = request.output.resolve()
    if request.use_cache:
        metadata = restore(cache_root, key, output)
        if metadata is not None:
            info = inspect_wav(output, min_frames=100)
            return SynthesisResult(
                schema_version=1,
                engine=engine.key,
                profile=request.profile,
                device=device,
                output_path=str(output),
                cached=True,
                audio=info.as_dict(),
                segments=int(metadata.get("segments", 1)),
                exact_pause_ms=int(metadata.get("exact_pause_ms", 0)),
                native_controls=tuple(metadata.get("native_controls", [])),
                degraded_controls=tuple(metadata.get("degraded_controls", [])),
                reference_provenance=reference_provenance,
                cache_key=key,
            )

    lexicon = _lexicon(lexicon_path)
    total_pause = leading_pause + sum(delay for _, delay in segments)
    with tempfile.TemporaryDirectory(prefix="ourtts-") as temp_dir:
        temp = Path(temp_dir)
        parts: list[AudioPart] = []
        segment_results: list[dict[str, Any]] = []
        for index, (segment_text, silence_after) in enumerate(segments):
            if not segment_text.strip():
                continue
            segment_path = temp / f"segment-{index:04d}.wav"
            result = _execute_segment(
                engine,
                segment_text,
                segment_path,
                language=request.language,
                lexicon=lexicon,
                adapter_args=adapter.args,
                engine_args=request.engine_args,
                timeout_seconds=request.timeout_seconds,
            )
            segment_results.append(result)
            parts.append(AudioPart(segment_path, silence_after_ms=silence_after))

        if not parts:
            raise RuntimeError("No speakable text remained after control processing.")
        if len(parts) == 1 and leading_pause == 0 and parts[0].silence_after_ms == 0:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(parts[0].path.read_bytes())
            info = inspect_wav(output, min_frames=100)
        else:
            info = concatenate_pcm_wavs(parts, output, leading_silence_ms=leading_pause)

    metadata = {
        "schema_version": 1,
        "engine": engine.key,
        "segments": len(parts),
        "exact_pause_ms": total_pause,
        "native_controls": list(plan.controls.native),
        "degraded_controls": list(degraded),
        "reference_provenance": reference_provenance,
        "segment_results": segment_results,
        "audio": info.as_dict(),
    }
    if request.use_cache:
        store(cache_root, key, output, metadata)

    return SynthesisResult(
        schema_version=1,
        engine=engine.key,
        profile=request.profile,
        device=device,
        output_path=str(output),
        cached=False,
        audio=info.as_dict(),
        segments=len(parts),
        exact_pause_ms=total_pause,
        native_controls=plan.controls.native,
        degraded_controls=degraded,
        reference_provenance=reference_provenance,
        cache_key=key,
    )
