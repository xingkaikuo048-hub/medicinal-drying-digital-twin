"""Stable HDF5/CSV representation for one transient FEM case."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np


def write_case_dataset(output_dir: Path, config: dict[str, Any], identifier: str,
                       snapshots: list[dict[str, Any]]) -> None:
    if not snapshots:
        raise ValueError("At least one snapshot is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    times = np.asarray([row["time_s"] for row in snapshots], dtype=float)
    arrays = {name: np.stack([row[name] for row in snapshots]) for name in
              ("r_m", "z_m", "temperature_K", "moisture_kg_per_kg_dry")}
    expected = (times.size, arrays["r_m"].shape[1])
    if any(value.shape != expected for value in arrays.values()):
        raise ValueError("Snapshot arrays have inconsistent shapes")
    with h5py.File(output_dir / "fields.h5", "w") as handle:
        handle.attrs["schema_version"] = "1.0"
        handle.attrs["case_id"] = identifier
        handle.attrs["coordinate_system"] = "axisymmetric"
        handle.attrs["configuration_json"] = json.dumps(config, sort_keys=True)
        handle.create_dataset("time_s", data=times)
        for name, value in arrays.items():
            handle.create_dataset(name, data=value, compression="gzip")
        handle.create_dataset("element_node_indices", data=snapshots[0]["element_node_indices"])
        handle.create_dataset("element_types", data=snapshots[0]["element_types"])
    fields = ["time_s", "mean_temperature_K", "mean_moisture_kg_per_kg_dry",
              "min_temperature_K", "max_temperature_K",
              "min_moisture_kg_per_kg_dry", "max_moisture_kg_per_kg_dry"]
    with (output_dir / "observables.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in snapshots:
            writer.writerow({key: row[key] for key in fields})
