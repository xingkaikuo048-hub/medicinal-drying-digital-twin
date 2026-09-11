"""Run and validate the short axisymmetric coupled drying MVP."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import h5py
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "mvp_validation"


def main() -> None:
    completed = subprocess.run(
        [str(PYTHON), str(PROJECT_ROOT / "scripts" / "run_case.py"),
         "--smoke", "--output-root", str(OUTPUT_ROOT)],
        check=True, capture_output=True, text=True,
    )
    status = json.loads(completed.stdout[completed.stdout.rfind("{"):])
    case_dir = OUTPUT_ROOT / status["case_id"]
    stored_status = json.loads((case_dir / "status.json").read_text(encoding="utf-8"))
    assert stored_status["status"] == "SUCCEEDED"
    assert stored_status["snapshots"] == 5
    with h5py.File(case_dir / "fields.h5", "r") as handle:
        time = handle["time_s"][:]
        temperature = handle["temperature_K"][:]
        moisture = handle["moisture_kg_per_kg_dry"][:]
        r = handle["r_m"][:]
        z = handle["z_m"][:]
        connectivity = handle["element_node_indices"][:]
        element_types = handle["element_types"][:]
        assert temperature.shape == moisture.shape == r.shape == z.shape
        assert temperature.shape[0] == 5
        assert connectivity.ndim == 2 and connectivity.shape[0] > 0
        assert element_types.shape[0] == connectivity.shape[0]
        assert np.allclose(time, [0, 30, 60, 90, 120])
        assert np.all(np.isfinite(temperature)) and np.all(np.isfinite(moisture))
        assert np.min(r) >= -1e-14 and np.max(r) <= 0.02 + 1e-14
        assert np.min(z) >= -1e-14 and np.max(z) <= 0.25 + 1e-14
        assert np.mean(moisture[-1]) < np.mean(moisture[0])
        assert np.min(temperature) > 250.0
        assert np.max(temperature) < 370.0
        assert np.min(moisture) >= 0.0
        assert np.max(moisture) <= 3.0
        assert not np.allclose(temperature[-1], temperature[0])
    with (case_dir / "observables.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert float(rows[-1]["mean_moisture_kg_per_kg_dry"]) < float(rows[0]["mean_moisture_kg_per_kg_dry"])
    print("COUPLED_DRYING_MVP=PASS")


if __name__ == "__main__":
    main()
