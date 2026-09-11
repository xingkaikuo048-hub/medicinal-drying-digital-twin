"""Validate the fixed boundary and future shrinkage scenario suite."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def main() -> None:
    subprocess.run(
        [str(PYTHON), str(PROJECT_ROOT / "scripts" / "generate_scenarios.py")],
        check=True,
    )
    output = PROJECT_ROOT / "outputs" / "designs" / "fixed_scenarios"
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    with (output / "manifest.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert summary["scenario_count"] == 11
    assert len(rows) == 11
    assert len({row["case_id"] for row in rows}) == 11
    assert "ale_shrinkage_candidate" in summary["scenario_names"]
    assert all((PROJECT_ROOT / row["case_file"]).is_file() for row in rows)
    print("SCENARIO_GENERATION=PASS")


if __name__ == "__main__":
    main()
