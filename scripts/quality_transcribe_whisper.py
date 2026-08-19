from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from typing import Any


def _resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def transcribe_samples(
    payload: dict[str, Any],
    *,
    model_name: str,
    device: str,
    revision: str,
) -> tuple[dict[str, Any], int]:
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Whisper is not installed in this evaluator environment. "
            "Install the pinned evaluator revision before running this script."
        ) from exc

    resolved_device = _resolve_device(device)
    model = whisper.load_model(model_name, device=resolved_device)
    errors = 0
    samples = payload.get("samples")
    if not isinstance(samples, list):
        raise TypeError("quality sample manifest must contain a samples list")

    for item in samples:
        item.pop("evaluation_error", None)
        if item.get("status") != "passed" or not item.get("audio_path"):
            continue
        audio_path = Path(str(item["audio_path"]))
        language = str(item.get("language") or "").strip()
        if language in {"", "mixed", "multilingual"}:
            language = None
        try:
            result = model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe",
                fp16=resolved_device == "cuda",
                verbose=False,
            )
            item["hypothesis_text"] = str(result.get("text", "")).strip()
        except Exception as exc:  # noqa: BLE001 - isolate one evaluator sample, retain the cast
            errors += 1
            item["hypothesis_text"] = None
            item["evaluation_error"] = f"{type(exc).__name__}: {exc}"

    payload["evaluator"] = {
        "type": "asr",
        "implementation": "openai/whisper",
        "revision": revision,
        "model": model_name,
        "device": resolved_device,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    return payload, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe a generated ourTTS quality cast with a pinned OpenAI Whisper evaluator."
    )
    parser.add_argument("samples", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="turbo")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--revision", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(args.samples.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("quality sample manifest root must be a JSON object")
        payload, errors = transcribe_samples(
            payload,
            model_name=args.model,
            device=args.device,
            revision=args.revision,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 2
    print(json.dumps({"output": str(args.output), "evaluation_errors": errors}))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
