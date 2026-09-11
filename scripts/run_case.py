"""Run one configured medicinal-drying FEM case and write training-ready data."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drying_twin.config import case_id, load_json, validate_case
from drying_twin.dataset import write_case_dataset
from drying_twin.model import MedicinalDryingProblem


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_case(path: Path) -> dict:
    payload = load_json(path)
    return payload["configuration"] if "configuration" in payload else payload


def snapshot(problem: MedicinalDryingProblem) -> dict:
    data = problem.get_cached_mesh_data("solid")
    r = np.asarray(data.get_data("coordinate_x"), dtype=float)
    z = np.asarray(data.get_data("coordinate_y"), dtype=float)
    temperature = np.asarray(data.get_data("temperature_K"), dtype=float)
    moisture = np.asarray(data.get_data("moisture_kg_per_kg_dry"), dtype=float)
    mesh = problem.get_mesh("solid")
    return {
        "time_s": problem.get_current_time(as_float=True),
        "r_m": r, "z_m": z,
        "temperature_K": temperature,
        "moisture_kg_per_kg_dry": moisture,
        "element_node_indices": np.asarray(data.elem_indices, dtype=np.int64),
        "element_types": np.asarray(data.elem_types, dtype=np.int64),
        "mean_temperature_K": float(mesh.evaluate_observable("mean_temperature_K")),
        "mean_moisture_kg_per_kg_dry": float(mesh.evaluate_observable("mean_moisture_kg_per_kg_dry")),
        "min_temperature_K": float(np.min(temperature)),
        "max_temperature_K": float(np.max(temperature)),
        "min_moisture_kg_per_kg_dry": float(np.min(moisture)),
        "max_moisture_kg_per_kg_dry": float(np.max(moisture)),
    }


def make_smoke_config(config: dict) -> dict:
    copied = json.loads(json.dumps(config))
    copied["case_name"] = copied.get("case_name", "case") + "_mvp_smoke"
    copied["numerics"].update({"elements_r": 4, "elements_z": 8,
                                "end_time_s": 120.0, "initial_dt_s": 10.0,
                                "output_interval_s": 30.0,
                                "adaptive_time_stepping": False})
    return copied


def run(config: dict, output_root: Path, identifier: str) -> dict:
    validate_case(config)
    output_dir = output_root / identifier
    output_dir.mkdir(parents=True, exist_ok=True)
    status = {"case_id": identifier, "status": "RUNNING", "started_utc": utc_now()}
    (output_dir / "case.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    try:
        numerics = config["numerics"]
        dt = float(numerics["initial_dt_s"])
        end_time = float(numerics["end_time_s"])
        interval = float(numerics["output_interval_s"])
        output_times = list(np.arange(0.0, end_time, interval)) + [end_time]
        snapshots = []
        with MedicinalDryingProblem(config) as problem:
            problem.set_c_compiler("tcc")
            problem.set_output_directory(str(output_dir / "pyoomph"))
            problem.initialise()
            problem.initialise_dt(dt)
            problem.set_initial_condition()
            snapshots.append(snapshot(problem))
            for target_time in output_times[1:]:
                problem.run(endtime=float(target_time), timestep=dt, outstep=False,
                            do_not_set_IC=True,
                            temporal_error=(numerics["relative_tolerance"]
                                            if numerics["adaptive_time_stepping"] else None))
                snapshots.append(snapshot(problem))
        write_case_dataset(output_dir, config, identifier, snapshots)
        status.update({"status": "SUCCEEDED", "finished_utc": utc_now(),
                       "snapshots": len(snapshots), "nodes": int(len(snapshots[0]["r_m"])),
                       "final_mean_temperature_K": snapshots[-1]["mean_temperature_K"],
                       "final_mean_moisture_kg_per_kg_dry": snapshots[-1]["mean_moisture_kg_per_kg_dry"]})
    except Exception as error:
        status.update({"status": "FAILED", "finished_utc": utc_now(),
                       "error_type": type(error).__name__, "error": str(error),
                       "traceback": traceback.format_exc()})
        (output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        raise
    (output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path, nargs="?", default=PROJECT_ROOT / "configs" / "base_case.json")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "outputs" / "simulations")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = load_case(args.case)
    if args.smoke:
        config = make_smoke_config(config)
    identifier = case_id(config, prefix="simulation")
    print(json.dumps(run(config, args.output_root, identifier), indent=2))


if __name__ == "__main__":
    main()
