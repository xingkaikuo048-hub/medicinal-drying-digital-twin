"""Verify that sampled air conditions change the coupled FEM response."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
FIXED = PROJECT_ROOT / "outputs" / "designs" / "fixed_scenarios" / "cases"
OUTPUT = PROJECT_ROOT / "outputs" / "condition_validation"


def run_scenario(name: str) -> dict:
    subprocess.run(
        [str(PYTHON), str(PROJECT_ROOT / "scripts" / "run_case.py"),
         str(FIXED / f"{name}.json"), "--smoke", "--output-root", str(OUTPUT)],
        check=True, capture_output=True, text=True,
    )
    candidates = []
    for status_path in OUTPUT.glob("*/status.json"):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        case = json.loads((status_path.parent / "case.json").read_text(encoding="utf-8"))
        if name in case.get("case_name", ""):
            candidates.append(status)
    # Generated scenario configurations retain the base case_name, so select via air values.
    if not candidates:
        for status_path in OUTPUT.glob("*/status.json"):
            status = json.loads(status_path.read_text(encoding="utf-8"))
            case = json.loads((status_path.parent / "case.json").read_text(encoding="utf-8"))
            target = json.loads((FIXED / f"{name}.json").read_text(encoding="utf-8"))["configuration"]
            if case["air"] == target["air"]:
                candidates.append(status)
    assert len(candidates) == 1, (name, candidates)
    return candidates[0]


def main() -> None:
    cool = run_scenario("cool_humid_slow_air")
    hot = run_scenario("hot_dry_fast_air")
    assert hot["status"] == cool["status"] == "SUCCEEDED"
    assert hot["final_mean_temperature_K"] > cool["final_mean_temperature_K"]
    assert hot["final_mean_moisture_kg_per_kg_dry"] < cool["final_mean_moisture_kg_per_kg_dry"]
    print("OPERATING_CONDITION_SENSITIVITY=PASS")


if __name__ == "__main__":
    main()
