"""Solve a scalar PDE on an actual axisymmetric r-z finite-element domain."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from pyoomph import DirichletBC, MeshFileOutput, Problem
from pyoomph.equations.poisson import PoissonEquation
from pyoomph.meshes.simplemeshes import RectangularQuadMesh


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "axisymmetric"


class AxisymmetricPoissonProblem(Problem):
    def define_problem(self) -> None:
        # coordinate_x is radial r, coordinate_y is axial z.
        self.set_coordinate_system("axisymmetric")
        self.add_mesh(
            RectangularQuadMesh(
                name="rz_domain", size=[1.0, 1.0], N=[5, 4], lower_left=[0.0, 0.0]
            )
        )
        equations = PoissonEquation(name="u", source=4.0, space="C2")
        equations += DirichletBC(u=0.0) @ "right"
        equations += MeshFileOutput()
        self.add_equations(equations @ "rz_domain")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with AxisymmetricPoissonProblem() as problem:
        problem.set_c_compiler("tcc")
        problem.set_output_directory(str(OUTPUT_DIR))
        problem.solve()
        problem.output()

        coordinate_system = problem.get_coordinate_system()
        data = problem.get_cached_mesh_data("rz_domain")
        r = np.asarray(data.get_data("coordinate_x"), dtype=float)
        z = np.asarray(data.get_data("coordinate_y"), dtype=float)
        u = np.asarray(data.get_data("u"), dtype=float)
        exact = 1.0 - r**2
        max_error = float(np.max(np.abs(u - exact)))

        assert "Axisymmetric" in str(coordinate_system), str(coordinate_system)
        assert r.size >= 30, "r-z mesh did not produce enough nodes"
        assert np.all(r >= -1.0e-14), "radial coordinates crossed the symmetry axis"
        assert np.all(np.isfinite(u)), "solution contains non-finite values"
        assert max_error < 1.0e-10, f"axisymmetric manufactured error: {max_error}"

        order = np.lexsort((r, z))
        np.savetxt(
            OUTPUT_DIR / "solution.csv",
            np.column_stack((r[order], z[order], u[order], exact[order])),
            delimiter=",",
            header="r,z,u_fem,u_exact",
            comments="",
        )
        metrics = {
            "status": "PASS",
            "coordinate_system": str(coordinate_system),
            "equation": "-axisymmetric_laplacian(u) = 4",
            "exact_solution": "u(r,z) = 1-r^2",
            "compiler": "tcc",
            "elements_r": 5,
            "elements_z": 4,
            "nodes": int(r.size),
            "max_absolute_error": max_error,
        }
        (OUTPUT_DIR / "metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
