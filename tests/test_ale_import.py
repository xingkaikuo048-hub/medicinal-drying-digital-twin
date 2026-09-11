"""Verify that pyoomph's ALE/moving-mesh API is importable."""

from __future__ import annotations

import importlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "ale_import.json"


def main() -> None:
    module = importlib.import_module("pyoomph.equations.ALE")
    required = [
        "BaseMovingMeshEquations",
        "LaplaceSmoothedMesh",
        "PseudoElasticMesh",
        "PrescribedMovingMesh",
    ]
    missing = [name for name in required if not hasattr(module, name)]
    assert not missing, f"missing ALE APIs: {missing}"

    base = module.BaseMovingMeshEquations
    for class_name in required[1:]:
        assert issubclass(getattr(module, class_name), base), class_name

    instance = module.LaplaceSmoothedMesh()
    assert isinstance(instance, base)
    result = {
        "status": "PASS",
        "module": module.__name__,
        "module_file": str(Path(module.__file__).resolve()),
        "moving_mesh_classes": required,
        "instantiation": type(instance).__name__,
    }
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
