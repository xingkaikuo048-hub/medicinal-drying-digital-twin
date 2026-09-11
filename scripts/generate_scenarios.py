"""Generate fixed boundary, regression, and future shrinkage cases."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drying_twin.config import case_id, load_json, validate_case, with_parameters


def main() -> None:
    base = load_json(PROJECT_ROOT / "configs" / "base_case.json")
    suite = load_json(PROJECT_ROOT / "configs" / "scenario_suite.json")
    output_dir = PROJECT_ROOT / "outputs" / "designs" / "fixed_scenarios"
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for scenario in suite["scenarios"]:
        config = with_parameters(base, scenario["overrides"])
        validate_case(config)
        identifier = case_id(config, prefix="scenario")
        payload = {
            "case_id": identifier,
            "scenario_name": scenario["name"],
            "purpose": scenario["purpose"],
            "dataset_role": "fixed_verification",
            "status": "PENDING",
            "overrides": scenario["overrides"],
            "configuration": config,
        }
        case_path = cases_dir / f"{scenario['name']}.json"
        case_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        rows.append({"scenario_name": scenario["name"], "case_id": identifier,
                     "purpose": scenario["purpose"], "status": "PENDING",
                     "case_file": str(case_path.relative_to(PROJECT_ROOT))})
    with (output_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"status": "PASS", "suite_name": suite["suite_name"],
               "scenario_count": len(rows),
               "scenario_names": [row["scenario_name"] for row in rows]}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
