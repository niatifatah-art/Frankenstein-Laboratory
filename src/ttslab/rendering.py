from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .adapter_runtime import (
    RuntimeInputs,
    adapter_args,
    adapter_supported_controls,
    engine_requires_reference,
)
from .audio import inspect_wav
from .audio_timeline import AudioPart, concatenate_pcm_wavs
from .isolation import execute_worker
from .pipeline import required_capabilities_for_controls
from .pronunciation import PronunciationLexicon
from .prosody import parse_control_markup
from .registry import EngineRecord, get_engine
from .router import RouteRequest, route_engines
from .text_engine import prepare_text


@dataclass(frozen=True, slots=True)
class RenderChunk:
    text: str
    pause_after_ms: int = 0


@dataclass(frozen=True, slots=True)
class RenderScript:
    clean_text: str
    leading_silence_ms: int
    chunks: tuple[RenderChunk, ...]


def parse_render_script(text: str) -> RenderScript:
    clean, markers = parse_control_markup(text)
    unsupported = sorted({marker.kind for marker in markers if marker.kind != "pause"})
    if unsupported:
        raise ValueError(
            "Inline rendering currently supports exact pause markers only; "
            f"unsupported markers: {', '.join(unsupported)}"
        )

    chunks: list[RenderChunk] = []
    leading_silence_ms = 0
    cursor = 0
    for marker in markers:
        segment = clean[cursor : marker.char_offset]
        pause_ms = int(marker.value)
        if segment.strip():
            chunks.append(RenderChunk(segment, pause_ms))
        elif chunks:
            previous = chunks[-1]
            chunks[-1] = RenderChunk(previous.text, previous.pause_after_ms + pause_ms)
        else:
            leading_silence_ms += pause_ms
        cursor = marker.char_offset

    tail = clean[cursor:]
    if tail.strip():
        chunks.append(RenderChunk(tail, 0))
    if not chunks:
        raise ValueError("Rendering requires at least one non-empty text segment.")
    return RenderScript(clean_text=clean, leading_silence_ms=leading_silence_ms, chunks=tuple(chunks))


def _validate_engine_controls(engine: EngineRecord, controls: dict[str, Any]) -> None:
    if "pause" in controls:
        raise ValueError(
            "Global pause control is ambiguous during rendering; use inline [[pause:320ms]] markers."
        )
    required = required_capabilities_for_controls(controls)
    missing_capabilities = sorted(capability for capability in required if not engine.supports(capability))
    if missing_capabilities:
        raise ValueError(
            f"Engine {engine.key!r} does not advertise required capabilities: "
            f"{', '.join(missing_capabilities)}"
        )
    adapter_controls = adapter_supported_controls(engine.key)
    missing_adapter_mappings = sorted(set(controls) - set(adapter_controls))
    if missing_adapter_mappings:
        raise ValueError(
            f"Engine {engine.key!r} may expose upstream controls, but its OurTTS adapter does not "
            f"translate these normalized controls yet: {', '.join(missing_adapter_mappings)}"
        )


def choose_render_engine(
    *,
    language: str | None,
    explicit_engine: str | None,
    reference: Path | None,
    max_generation_rtf: float | None,
    controls: dict[str, Any] | None = None,
) -> EngineRecord:
    requested_controls = dict(controls or {})
    if "pause" in requested_controls:
        raise ValueError(
            "Global pause control is ambiguous during rendering; use inline [[pause:320ms]] markers."
        )

    if explicit_engine:
        engine = get_engine(explicit_engine)
        if not engine.runnable or engine.kind != "tts":
            raise ValueError(f"Engine {explicit_engine!r} is not a qualified runnable TTS backend.")
        if not engine.supports_language(language):
            raise ValueError(f"Engine {explicit_engine!r} does not support language {language!r}.")
        if engine_requires_reference(engine.key) and reference is None:
            raise ValueError(f"Engine {explicit_engine!r} requires a reference voice.")
        _validate_engine_controls(engine, requested_controls)
        return engine

    candidates = route_engines(
        RouteRequest(
            language=language,
            require=required_capabilities_for_controls(requested_controls),
            max_generation_rtf=max_generation_rtf,
        )
    )
    for candidate in candidates:
        engine = candidate.engine
        if engine_requires_reference(engine.key) and reference is None:
            continue
        try:
            _validate_engine_controls(engine, requested_controls)
        except ValueError:
            continue
        return engine
    if requested_controls:
        raise ValueError(
            "No qualified TTS backend has both the requested capabilities and a verified OurTTS "
            "adapter mapping for all requested controls."
        )
    raise ValueError("No qualified TTS backend satisfies the rendering request.")


def render_text(
    text: str,
    output: Path,
    *,
    language: str | None = None,
    engine_key: str | None = None,
    voice: str | None = None,
    reference: Path | None = None,
    controls: dict[str, Any] | None = None,
    lexicon: PronunciationLexicon | None = None,
    max_generation_rtf: float | None = None,
    engine_args: list[str] | None = None,
    manifest_path: Path | None = None,
    manifest_metadata: dict[str, Any] | None = None,
    keep_parts: bool = False,
    timeout_seconds: float = 1800.0,
) -> dict[str, Any]:
    requested_controls = dict(controls or {})
    script = parse_render_script(text)
    engine = choose_render_engine(
        language=language,
        explicit_engine=engine_key,
        reference=reference,
        max_generation_rtf=max_generation_rtf,
        controls=requested_controls,
    )
    runtime_args = adapter_args(
        engine.key,
        RuntimeInputs(
            language=language,
            voice=voice,
            reference=reference,
            controls=requested_controls,
        ),
    )
    runtime_args.extend(engine_args or [])

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_path or output.with_suffix(output.suffix + ".manifest.json")

    executions: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ourtts-render-") as temp_name:
        temp_root = Path(temp_name)
        audio_parts: list[AudioPart] = []
        retained_parts: list[str] = []
        for index, chunk in enumerate(script.chunks):
            prepared = prepare_text(chunk.text, language=language, lexicon=lexicon)
            phoneme_overrides = [
                item for item in prepared.pronunciation_overrides if item.mode == "phoneme"
            ]
            if phoneme_overrides:
                terms = ", ".join(item.term for item in phoneme_overrides)
                raise ValueError(
                    "Mixed text/phoneme override rendering is not integrated yet; "
                    f"refusing to ignore overrides for: {terms}"
                )
            if not prepared.normalized:
                raise ValueError(f"Text segment {index} became empty after preprocessing.")

            part_path = temp_root / f"part-{index:03d}.wav"
            execution = execute_worker(
                engine.worker or engine.key,
                text=prepared.normalized,
                output=part_path,
                extra_args=runtime_args,
                timeout_seconds=timeout_seconds,
            )
            if execution.returncode != 0:
                tail = "\n".join(execution.stderr.splitlines()[-30:])
                raise RuntimeError(
                    f"{engine.key} failed while rendering segment {index} "
                    f"with exit code {execution.returncode}:\n{tail}"
                )
            if not part_path.exists():
                raise RuntimeError(f"{engine.key} returned success but produced no audio for segment {index}.")
            info = inspect_wav(part_path)
            audio_parts.append(AudioPart(part_path, chunk.pause_after_ms))
            executions.append(
                {
                    "index": index,
                    "input": chunk.text,
                    "normalized": prepared.normalized,
                    "pause_after_ms": chunk.pause_after_ms,
                    "pronunciation_overrides": [
                        asdict(item) for item in prepared.pronunciation_overrides
                    ],
                    "worker_payload": execution.payload,
                    "audio": asdict(info),
                }
            )

        final_info = concatenate_pcm_wavs(
            audio_parts,
            output,
            leading_silence_ms=script.leading_silence_ms,
        )

        if keep_parts:
            parts_dir = output.parent / f"{output.stem}.parts"
            parts_dir.mkdir(parents=True, exist_ok=True)
            for index, part in enumerate(audio_parts):
                destination = parts_dir / f"part-{index:03d}.wav"
                shutil.copy2(part.path, destination)
                retained_parts.append(str(destination))

    manifest: dict[str, Any] = {
        "schema_version": 2,
        "engine": engine.key,
        "source_text": text,
        "clean_text": script.clean_text,
        "language": language,
        "voice": voice,
        "reference": str(reference.resolve()) if reference else None,
        "controls": requested_controls,
        "leading_silence_ms": script.leading_silence_ms,
        "segments": executions,
        "final_audio": asdict(final_info),
        "retained_parts": retained_parts,
        "adapter_args": runtime_args,
        "metadata": dict(manifest_metadata or {}),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
