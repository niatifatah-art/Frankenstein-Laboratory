from __future__ import annotations

import json
from pathlib import Path

from ttslab.batch import run_batch
from ttslab.cache import cache_key, restore, store
from ttslab.synthesis import SynthesisRequest, SynthesisResult


def _fake_result(request: SynthesisRequest) -> SynthesisResult:
    request.output.parent.mkdir(parents=True, exist_ok=True)
    request.output.write_bytes(b"RIFFfake")
    return SynthesisResult(
        schema_version=1,
        engine=request.engine or "fake",
        profile=request.profile,
        device=request.device or "cpu",
        output_path=str(request.output),
        cached=False,
        audio={"sha256": "fake", "duration_seconds": 1.0},
        segments=1,
        exact_pause_ms=0,
        native_controls=(),
        degraded_controls=(),
        reference_provenance=None,
        cache_key="fake-key",
    )


def test_batch_preserves_success_and_individual_failure(tmp_path: Path) -> None:
    manifest = tmp_path / "batch.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jobs": [
                    {"id": "ok", "text": "hello", "output": "ok.wav"},
                    {"id": "bad", "text": "boom", "output": "bad.wav"},
                ],
            }
        ),
        encoding="utf-8",
    )

    def synth(request: SynthesisRequest) -> SynthesisResult:
        if request.text == "boom":
            raise RuntimeError("expected failure")
        return _fake_result(request)

    result = run_batch(manifest, output_root=tmp_path / "out", synth=synth)
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["results"][0]["status"] == "passed"
    assert result["results"][1]["message"] == "expected failure"


def test_cache_key_is_content_addressed_and_reference_sensitive() -> None:
    base = {"engine": "pocket", "text": "hello", "reference_sha256": "a" * 64}
    same = dict(base)
    changed = dict(base, reference_sha256="b" * 64)
    assert cache_key(base) == cache_key(same)
    assert cache_key(base) != cache_key(changed)


def test_cache_store_restore_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"RIFFcached")
    root = tmp_path / "cache"
    key = cache_key({"engine": "fake", "text": "hello"})
    metadata = {"engine": "fake", "segments": 2, "exact_pause_ms": 320}
    entry = store(root, key, source, metadata)
    assert entry.wav.exists()
    target = tmp_path / "restored.wav"
    restored = restore(root, key, target)
    assert restored == metadata
    assert target.read_bytes() == source.read_bytes()
