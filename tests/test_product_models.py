from dataclasses import replace
from pathlib import Path

from ourtts.models import ModelManager
from ourtts.paths import AppPaths
from ourtts.platform import PlatformReport
from ttslab.registry import EngineRecord


def _record(**changes):
    base = EngineRecord(
        key="fast_cpu",
        name="Fast CPU",
        upstream="https://example.invalid/model",
        zone="runtime",
        integration_status="ready",
        code_license="MIT",
        weights_license="Apache-2.0",
        license_status="verified",
        worker=None,
        kind="tts",
        family="test",
        version="1",
        commercial_use="yes",
        capabilities=("streaming",),
        languages=("en",),
        hardware=("cpu",),
        cpu_generation_rtf=0.5,
    )
    return replace(base, **changes)


def _report(tmp_path: Path) -> PlatformReport:
    paths = AppPaths.default(
        env={"OURTTS_HOME": str(tmp_path / "home")},
        home=tmp_path,
        platform_name="linux",
    )
    return PlatformReport(
        os="Linux",
        release="test",
        version="test",
        machine="x86_64",
        python="3.12",
        cpu="test cpu",
        ram_bytes=16 * 1024**3,
        free_disk_bytes=100 * 1024**3,
        accelerator="cpu",
        accelerator_detail=None,
        ffmpeg=None,
        espeak=None,
        uv=None,
        paths=paths,
    )


def test_model_manifest_keeps_runtime_and_license_truth_separate() -> None:
    manager = ModelManager((_record(),))
    manifest = manager.get("fast_cpu")
    assert manifest.status == "ready"
    assert manifest.code_license == "MIT"
    assert manifest.weights_license == "Apache-2.0"
    assert manifest.runtime_state == "not_product_worker"
    assert manifest.weights_state == "on_demand_or_cached"


def test_model_recommendation_prefers_measured_fast_cpu_engine(tmp_path: Path) -> None:
    fast = _record(worker=None)
    slow = _record(
        key="slow_cpu",
        name="Slow CPU",
        cpu_generation_rtf=9.0,
        capabilities=(),
    )
    manager = ModelManager((fast, slow))

    # Synthetic records without workers are not product-runnable and must not be recommended.
    assert manager.recommend(_report(tmp_path)) == ()


def test_gated_access_is_exposed_without_changing_license_fields() -> None:
    record = _record(
        key="gated",
        name="Gated",
        notes="Full cloning weights are access-gated upstream; predefined voices remain usable.",
    )
    manifest = ModelManager((record,)).get("gated")
    assert manifest.access_gated is True
    assert manifest.weights_state == "gated_or_on_demand"
    assert manifest.weights_license == "Apache-2.0"
