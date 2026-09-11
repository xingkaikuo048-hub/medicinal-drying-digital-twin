"""Exercise the project's data, plotting, HDF5, Excel, and PyTorch stack."""

from __future__ import annotations

import importlib.metadata as metadata
import json
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
import scipy
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "dependency_validation"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    array = np.linspace(0.0, 1.0, 11)
    frame = pd.DataFrame({"x": array, "x_squared": array**2})

    excel_path = OUTPUT_DIR / "table.xlsx"
    frame.to_excel(excel_path, index=False)
    restored_excel = pd.read_excel(excel_path, engine="openpyxl")
    assert np.allclose(restored_excel["x_squared"], array**2)
    assert openpyxl.load_workbook(excel_path).active.max_row == 12

    h5_path = OUTPUT_DIR / "array.h5"
    with h5py.File(h5_path, "w") as handle:
        handle.create_dataset("x", data=array)
    with h5py.File(h5_path, "r") as handle:
        assert np.allclose(handle["x"][:], array)

    figure_path = OUTPUT_DIR / "plot.png"
    figure, axis = plt.subplots(figsize=(4, 3))
    axis.plot(array, array**2)
    axis.set(xlabel="x", ylabel="x^2")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=120)
    plt.close(figure)
    assert figure_path.stat().st_size > 1000

    cuda_available = torch.cuda.is_available()
    torch_device = torch.device("cuda" if cuda_available else "cpu")
    tensor = torch.tensor([1.0, 2.0, 3.0], device=torch_device)
    tensor_result = float(torch.sum(tensor * tensor).cpu())
    assert tensor_result == 14.0

    result = {
        "status": "PASS",
        "versions": {
            name: metadata.version(name)
            for name in [
                "numpy",
                "scipy",
                "pandas",
                "matplotlib",
                "openpyxl",
                "h5py",
                "pyoomph",
                "torch",
            ]
        },
        "excel_roundtrip": "PASS",
        "hdf5_roundtrip": "PASS",
        "matplotlib_render": "PASS",
        "torch_tensor_result": tensor_result,
        "cuda_available": cuda_available,
        "torch_cuda_build": torch.version.cuda,
        "cuda_device": torch.cuda.get_device_name(0) if cuda_available else None,
        "cuda_device_capability": (
            list(torch.cuda.get_device_capability(0)) if cuda_available else None
        ),
        "scipy_version": scipy.__version__,
    }
    (OUTPUT_DIR / "metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
