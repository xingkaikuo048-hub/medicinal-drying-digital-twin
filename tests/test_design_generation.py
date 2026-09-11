"""Validation for reproducible parameter-space generation."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
OUTPUT = PROJECT_ROOT / "outputs" / "designs" / "validation"


def main() -> None:
    command = [
        str(PYTHON), str(PROJECT_ROOT / "scripts" / "generate_design.py"),
        "--output", str(OUTPUT)
    ]
    subprocess.run(command, check=True)
    manifest = OUTPUT / "manifest.csv"
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    summary = json.loads((OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert len(rows) == 128
    assert len({row["case_id"] for row in rows}) == 128
    assert sum(summary["split_counts"].values()) == 128
    assert all((PROJECT_ROOT / row["case_file"]).is_file() for row in rows)
    assert all(row["status"] == "PENDING" for row in rows)
    assert all(0.05 <= float(row["air.relative_humidity"]) <= 0.5 for row in rows)
    assert all(1e-10 <= float(row["material.moisture_diffusivity_m2_per_s"]) <= 1e-8 for row in rows)
    first_ids = [row["case_id"] for row in rows]
    subprocess.run(command, check=True)
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        second_ids = [row["case_id"] for row in csv.DictReader(handle)]
    assert first_ids == second_ids, "fixed seed did not reproduce the same design"
    print("DESIGN_GENERATION=PASS")


if __name__ == "__main__":
    main()
