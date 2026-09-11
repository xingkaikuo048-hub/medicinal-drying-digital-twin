"""Validated, hashable simulation case configuration."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def set_nested(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    keys = dotted_key.split(".")
    target = config
    for key in keys[:-1]:
        if key not in target or not isinstance(target[key], dict):
            raise KeyError(f"Unknown configuration path: {dotted_key}")
        target = target[key]
    if keys[-1] not in target:
        raise KeyError(f"Unknown configuration path: {dotted_key}")
    target[keys[-1]] = value


def with_parameters(base: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in parameters.items():
        set_nested(result, key, value)
    return result


def case_id(config: dict[str, Any], prefix: str = "case") -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def validate_case(config: dict[str, Any]) -> None:
    required_groups = {
        "geometry", "initial", "air", "material", "transfer", "shrinkage",
        "model", "numerics", "output"
    }
    missing = sorted(required_groups - config.keys())
    if missing:
        raise ValueError(f"Missing configuration groups: {missing}")

    def positive(path: str, value: float) -> None:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{path} must be finite and positive")

    geometry = config["geometry"]
    positive("geometry.length_m", geometry["length_m"])
    positive("geometry.initial_radius_m", geometry["initial_radius_m"])
    if geometry["coordinate_system"] != "axisymmetric":
        raise ValueError("MVP geometry must use the axisymmetric coordinate system")

    initial = config["initial"]
    positive("initial.temperature_K", initial["temperature_K"])
    positive("initial.moisture_kg_per_kg_dry", initial["moisture_kg_per_kg_dry"])

    air = config["air"]
    positive("air.temperature_K", air["temperature_K"])
    positive("air.velocity_m_per_s", air["velocity_m_per_s"])
    positive("air.pressure_Pa", air["pressure_Pa"])
    if not 0.0 <= air["relative_humidity"] <= 1.0:
        raise ValueError("air.relative_humidity must be between 0 and 1")

    for key, value in config["material"].items():
        positive(f"material.{key}", value)
    for key, value in config["transfer"].items():
        positive(f"transfer.{key}", value)

    shrinkage = config["shrinkage"]
    if shrinkage["mode"] not in {"none", "prescribed", "ale"}:
        raise ValueError("shrinkage.mode must be none, prescribed, or ale")
    for key in ("radial_coefficient", "axial_coefficient"):
        if shrinkage[key] < 0:
            raise ValueError(f"shrinkage.{key} cannot be negative")
    if not 0.0 < shrinkage["minimum_radius_fraction"] <= 1.0:
        raise ValueError("shrinkage.minimum_radius_fraction must be in (0, 1]")

    numerics = config["numerics"]
    for key in ("elements_r", "elements_z", "element_order"):
        if not isinstance(numerics[key], int) or numerics[key] <= 0:
            raise ValueError(f"numerics.{key} must be a positive integer")
    for key in ("end_time_s", "initial_dt_s", "output_interval_s",
                "relative_tolerance", "absolute_tolerance"):
        positive(f"numerics.{key}", numerics[key])
    if numerics["output_interval_s"] > numerics["end_time_s"]:
        raise ValueError("output interval cannot exceed end time")
