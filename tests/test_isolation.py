from pathlib import Path

import pytest
from ttslab.isolation import get_worker
from ttslab.registry import get_engine

REGISTRY = Path(__file__).parents[1] / "registry" / "engines.toml"


def test_kokoro_worker_is_registered() -> None:
    record = get_engine("kokoro", REGISTRY)
    assert record.worker == "kokoro"
    assert record.integration_status == "adapter_ready"


def test_unknown_worker_fails_explicitly() -> None:
    with pytest.raises(KeyError):
        get_worker("definitely-not-real")
