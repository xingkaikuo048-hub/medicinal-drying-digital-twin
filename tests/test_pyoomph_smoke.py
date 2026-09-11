"""Small transient heat/diffusion FEM smoke test for pyoomph."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from pyoomph import DirichletBC, InitialCondition, MeshFileOutput, Problem
from pyoomph.expressions import sin, var
from pyoomph.equations.poisson import DiffusionEquation
from pyoomph.meshes.simplemeshes import LineMesh


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "smoke"


class TransientDiffusionProblem(Problem):
    def define_problem(self) -> None:
        self.add_mesh(LineMesh(minimum=0.0, size=1.0, N=12))

        x = var("coordinate_x")
        equations = DiffusionEquation(name="temperature", diffusivity=1.0, space="C2")
        # Manufactured initial field sin(pi*x); exact solution decays as exp(-pi^2*t).
        equations += InitialCondition(temperature=sin(math.pi * x))
        equations += DirichletBC(temperature=0.0) @ "left"
        equations += DirichletBC(temperature=0.0) @ "right"
        equations += MeshFileOutput()

        self.add_equations(equations @ "domain")



def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with TransientDiffusionProblem() as problem:
        problem.set_c_compiler("tcc")
        problem.set_output_directory(str(OUTPUT_DIR))
        problem.run(

                endtime=0.02,
                timestep=0.001,
                outstep=0.01,
                out_initially=True,
                temporal_error=None,
            )
        final_time = problem.get_current_time(as_float=True)

        data = problem.get_cached_mesh_data("domain")
        x = np.asarray(data.get_data("coordinate_x"), dtype=float)
        temperature = np.asarray(data.get_data("temperature"), dtype=float)
        exact = np.sin(np.pi * x) * np.exp(-(np.pi**2) * final_time)
        max_error = float(np.max(np.abs(temperature - exact)))

        assert x.size >= 13, "mesh did not produce enough nodes"
        assert np.all(np.isfinite(temperature)), "solution contains non-finite values"
        assert abs(final_time - 0.02) < 1.0e-12, "transient solver stopped early"
        assert abs(temperature[np.argmin(x)]) < 1.0e-10, "left boundary failed"
        assert abs(temperature[np.argmax(x)]) < 1.0e-10, "right boundary failed"
        assert 0.0 < float(np.max(temperature)) < 1.0, "field did not decay"
        assert max_error < 5.0e-4, f"manufactured-solution error too large: {max_error}"

        order = np.argsort(x)
        np.savetxt(
            OUTPUT_DIR / "final_solution.csv",
            np.column_stack((x[order], temperature[order], exact[order])),
            delimiter=",",
            header="x,temperature_fem,temperature_exact",
            comments="",
        )
        metrics = {
            "status": "PASS",
            "equation": "dT/dt - d2T/dx2 = 0",
            "compiler": "tcc",
            "elements": 12,
            "final_time": final_time,
            "nodes": int(x.size),
            "max_temperature": float(np.max(temperature)),
            "max_absolute_error": max_error,
        }
        (OUTPUT_DIR / "metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
