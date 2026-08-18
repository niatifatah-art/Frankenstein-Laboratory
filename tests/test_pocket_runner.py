import json
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).parents[1] / "engines" / "pocket_tts" / "runner.py"


def test_pocket_describe_does_not_require_model_dependencies() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--describe"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["engine"] == "pocket_tts"
    assert payload["schema_version"] == 1
    assert payload["capabilities"]["cpu"] is True
    assert payload["capabilities"]["streaming"] is True
