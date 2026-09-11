"""Exercise one real case plus resumable skipping in the batch runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
MANIFEST = PROJECT_ROOT / "outputs" / "designs" / "validation" / "manifest.csv"
OUTPUT = PROJECT_ROOT / "outputs" / "batch_validation"


def run_batch() -> dict:
    subprocess.run(
        [str(PYTHON), str(PROJECT_ROOT / "scripts" / "run_batch.py"),
         str(MANIFEST), "--max-cases", "1", "--smoke",
         "--output-root", str(OUTPUT)],
        check=True, capture_output=True, text=True,
    )
    return json.loads((OUTPUT / "batch_summary.json").read_text(encoding="utf-8"))


def main() -> None:
    first = run_batch()
    assert first["requested"] == 1
    assert first["failed"] == 0
    assert first["succeeded"] + first["skipped"] == 1
    second = run_batch()
    assert second["requested"] == 1
    assert second["failed"] == 0
    assert second["skipped"] == 1
    status_files = list(OUTPUT.glob("*/status.json"))
    assert len(status_files) == 1
    status = json.loads(status_files[0].read_text(encoding="utf-8"))
    assert status["status"] == "SUCCEEDED"
    print("BATCH_RUNNER=PASS")


if __name__ == "__main__":
    main()
