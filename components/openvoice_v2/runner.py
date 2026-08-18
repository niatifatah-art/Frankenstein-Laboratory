from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SOURCE_REPO = "https://github.com/myshell-ai/OpenVoice.git"
SOURCE_REVISION = "74a1d147b17a8c3092dd5430504bd83ef6c7eb23"
CHECKPOINT_REPO = "myshell-ai/OpenVoiceV2"
CHECKPOINT_REVISION = "fd981100305a0e4291f93a9ad169c6d9f7bed54a"


def describe() -> dict[str, object]:
    return {
        "schema_version": 1,
        "component": "openvoice_v2",
        "component_kind": "voice_conversion",
        "adapter_version": "0.1.0",
        "source_revision": SOURCE_REVISION,
        "checkpoint_repo": CHECKPOINT_REPO,
        "checkpoint_revision": CHECKPOINT_REVISION,
        "capabilities": {
            "voice_conversion": True,
            "cross_lingual": True,
            "speaker_embedding": True,
            "watermark": "wavmark-0.0.3 upstream default",
        },
    }


def _run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def ensure_runtime(runtime_dir: Path) -> tuple[Path, Path]:
    source_dir = runtime_dir / "source"
    checkpoint_dir = runtime_dir / "checkpoint"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    if not (source_dir / ".git").exists():
        _run(["git", "clone", SOURCE_REPO, str(source_dir)])
    current = subprocess.run(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current != SOURCE_REVISION:
        _run(["git", "-C", str(source_dir), "fetch", "origin", SOURCE_REVISION])
        _run(["git", "-C", str(source_dir), "checkout", "--detach", SOURCE_REVISION])

    config = checkpoint_dir / "converter" / "config.json"
    checkpoint = checkpoint_dir / "converter" / "checkpoint.pth"
    if not (config.exists() and checkpoint.exists()):
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=CHECKPOINT_REPO,
            revision=CHECKPOINT_REVISION,
            allow_patterns=["converter/*"],
            local_dir=checkpoint_dir,
        )
    return source_dir, checkpoint_dir


def convert(args: argparse.Namespace) -> int:
    source_audio = args.source.resolve()
    target_reference = args.target_reference.resolve()
    output = args.output.resolve()
    runtime = args.runtime_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if not source_audio.exists():
        raise FileNotFoundError(source_audio)
    if not target_reference.exists():
        raise FileNotFoundError(target_reference)

    started = time.perf_counter()
    runtime_started = time.perf_counter()
    source_dir, checkpoint_dir = ensure_runtime(runtime)
    runtime_prepare_seconds = time.perf_counter() - runtime_started

    sys.path.insert(0, str(source_dir))
    from openvoice.api import ToneColorConverter

    converter_dir = checkpoint_dir / "converter"
    load_started = time.perf_counter()
    converter = ToneColorConverter(str(converter_dir / "config.json"), device=args.device)
    converter.load_ckpt(str(converter_dir / "checkpoint.pth"))
    model_load_seconds = time.perf_counter() - load_started

    embedding_started = time.perf_counter()
    source_embedding = converter.extract_se(str(source_audio))
    target_embedding = converter.extract_se(str(target_reference))
    embedding_seconds = time.perf_counter() - embedding_started

    conversion_started = time.perf_counter()
    converter.convert(
        audio_src_path=str(source_audio),
        src_se=source_embedding,
        tgt_se=target_embedding,
        output_path=str(output),
        tau=args.tau,
        message=args.message,
    )
    conversion_seconds = time.perf_counter() - conversion_started

    import soundfile as sf

    info = sf.info(output)
    result = {
        "schema_version": 1,
        "component": "openvoice_v2",
        "output_path": str(output),
        "sample_rate": info.samplerate,
        "audio_duration_seconds": info.duration,
        "runtime_prepare_seconds": runtime_prepare_seconds,
        "model_load_seconds": model_load_seconds,
        "embedding_seconds": embedding_seconds,
        "conversion_seconds": conversion_seconds,
        "total_seconds": time.perf_counter() - started,
        "source_revision": SOURCE_REVISION,
        "checkpoint_repo": CHECKPOINT_REPO,
        "checkpoint_revision": CHECKPOINT_REVISION,
        "device": args.device,
        "tau": args.tau,
        "watermark": "wavmark-0.0.3 upstream default",
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Isolated OpenVoice V2 tone-color converter.")
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--target-reference", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/openvoice-v2.wav"))
    parser.add_argument("--runtime-dir", type=Path, default=Path("components/openvoice_v2/.runtime"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--tau", type=float, default=0.3)
    parser.add_argument("--message", default="FrankensteinLab")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(describe(), ensure_ascii=False))
        return 0
    if args.source is None or args.target_reference is None:
        print("--source and --target-reference are required", file=sys.stderr)
        return 2
    try:
        return convert(args)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
