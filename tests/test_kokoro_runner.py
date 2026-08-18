import json
from pathlib import Path
import subprocess
import sys


RUNNER = Path(__file__).parents[1] / "engines" / "kokoro" / "runner.py"


def test_kokoro_describe_does_not_require_model_dependencies() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--describe"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["engine"] == "kokoro"
    assert payload["schema_version"] == 1
    assert payload["capabilities"]["cpu"] is True
