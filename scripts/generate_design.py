"""Generate reproducible simulation cases without running the expensive PDE solver."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import qmc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drying_twin.config import case_id, load_json, validate_case, with_parameters


def scale_sample(unit_value: float, specification: dict) -> float:
    minimum = float(specification["min"])
    maximum = float(specification["max"])
    if not minimum < maximum:
        raise ValueError(f"Invalid bounds: {minimum}, {maximum}")
    scale = specification.get("scale", "linear")
    if scale == "linear":
        return minimum + unit_value * (maximum - minimum)
    if scale == "log10":
        if minimum <= 0:
            raise ValueError("Log-scaled bounds must be positive")
        return 10 ** (math.log10(minimum) + unit_value * (math.log10(maximum) - math.log10(minimum)))
    raise ValueError(f"Unknown sampling scale: {scale}")


def allocate_splits(count: int, fractions: dict[str, float], seed: int) -> list[str]:
    names = list(fractions)
    values = np.asarray([fractions[name] for name in names], dtype=float)
    if np.any(values < 0) or not np.isclose(values.sum(), 1.0):
        raise ValueError("Dataset split fractions must be nonnegative and sum to 1")
    raw = values * count
    sizes = np.floor(raw).astype(int)
    for index in np.argsort(-(raw - sizes))[: count - int(sizes.sum())]:
        sizes[index] += 1
    labels = [name for name, size in zip(names, sizes) for _ in range(int(size))]
    generator = np.random.default_rng(seed + 1)
    generator.shuffle(labels)
    return labels


def generate(base_path: Path, design_path: Path, output_dir: Path) -> dict:
    base = load_json(base_path)
    design = load_json(design_path)
    validate_case(base)
    parameter_names = list(design["parameters"])
    sample_count = int(design["samples"])
    seed = int(design["seed"])
    if design["method"] != "latin_hypercube":
        raise ValueError("Only latin_hypercube is currently supported")

    unit_samples = qmc.LatinHypercube(d=len(parameter_names), seed=seed).random(sample_count)
    split_labels = allocate_splits(sample_count, design["splits"], seed)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    ids = set()
    for sample_index, (unit_row, split) in enumerate(zip(unit_samples, split_labels)):
        parameters = {
            name: scale_sample(float(value), design["parameters"][name])
            for name, value in zip(parameter_names, unit_row)
        }
        case = with_parameters(base, parameters)
        validate_case(case)
        identifier = case_id(case)
        if identifier in ids:
            raise RuntimeError(f"Duplicate case ID: {identifier}")
        ids.add(identifier)
        payload = {
            "case_id": identifier,
            "sample_index": sample_index,
            "dataset_split": split,
            "design_name": design["design_name"],
            "seed": seed,
            "status": "PENDING",
            "parameters": parameters,
            "configuration": case,
        }
        case_path = cases_dir / f"{identifier}.json"
        case_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        rows.append({
            "case_id": identifier,
            "sample_index": sample_index,
            "dataset_split": split,
            "status": "PENDING",
            **parameters,
            "case_file": str(case_path.relative_to(PROJECT_ROOT)),
        })

    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "PASS",
        "design_name": design["design_name"],
        "method": design["method"],
        "seed": seed,
        "samples": sample_count,
        "parameters": parameter_names,
        "split_counts": {name: split_labels.count(name) for name in design["splits"]},
        "manifest": str(manifest_path.relative_to(PROJECT_ROOT)),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=PROJECT_ROOT / "configs" / "base_case.json")
    parser.add_argument("--design", type=Path, default=PROJECT_ROOT / "configs" / "doe_default.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "outputs" / "designs" / "default")
    args = parser.parse_args()
    print(json.dumps(generate(args.base, args.design, args.output), indent=2))


if __name__ == "__main__":
    main()
