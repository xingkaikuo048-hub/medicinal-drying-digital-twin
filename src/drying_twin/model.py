"""Axisymmetric coupled heat/moisture finite-element drying MVP."""

from __future__ import annotations

from typing import Any

from pyoomph import Equations, InterfaceEquations, Problem
from pyoomph.equations.generic import InitialCondition, IntegralObservables
from pyoomph.expressions import grad, partial_t, testfunction, var, var_and_test, weak
from pyoomph.meshes.simplemeshes import RectangularQuadMesh


class CoupledDryingEquations(Equations):
    """Constant-property heat and moisture diffusion in the solid."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config

    def define_fields(self) -> None:
        self.define_scalar_field("temperature_K", "C2")
        self.define_scalar_field("moisture_kg_per_kg_dry", "C2")

    def define_residuals(self) -> None:
        material = self.config["material"]
        temperature, temperature_test = var_and_test("temperature_K")
        moisture, moisture_test = var_and_test("moisture_kg_per_kg_dry")
        self.add_residual(
            weak(material["density_dry_kg_per_m3"] * material["heat_capacity_J_per_kgK"]
                 * partial_t(temperature), temperature_test)
            + weak(material["thermal_conductivity_W_per_mK"] * grad(temperature),
                   grad(temperature_test))
        )
        self.add_residual(
            weak(material["density_dry_kg_per_m3"] * partial_t(moisture), moisture_test)
            + weak(material["density_dry_kg_per_m3"]
                   * material["moisture_diffusivity_m2_per_s"] * grad(moisture),
                   grad(moisture_test))
        )


class ConvectiveDryingBoundary(InterfaceEquations):
    """Heat and moisture Robin conditions on air-exposed surfaces."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config

    def define_residuals(self) -> None:
        air = self.config["air"]
        material = self.config["material"]
        transfer = self.config["transfer"]
        temperature = var("temperature_K")
        moisture = var("moisture_kg_per_kg_dry")
        velocity_ratio = air["velocity_m_per_s"] / transfer["reference_velocity_m_per_s"]
        velocity_factor = velocity_ratio ** 0.8
        heat_transfer = transfer["heat_transfer_W_per_m2K"] * velocity_factor
        mass_transfer = transfer["mass_flux_coefficient_kg_per_m2_s_per_moisture"] * velocity_factor
        equilibrium_moisture = transfer["equilibrium_moisture_kg_per_kg_dry"] * (
            air["relative_humidity"] / transfer["reference_relative_humidity"]
        )
        moisture_flux = mass_transfer * (moisture - equilibrium_moisture)
        heat_flux = heat_transfer * (temperature - air["temperature_K"])
        if self.config["model"]["latent_heat_coupling"]:
            heat_flux += material["latent_heat_J_per_kg"] * moisture_flux
        self.add_residual(weak(heat_flux, testfunction("temperature_K")))
        self.add_residual(weak(moisture_flux, testfunction("moisture_kg_per_kg_dry")))


class MedicinalDryingProblem(Problem):
    """Static-mesh axisymmetric cylinder model configured by a case dictionary."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config

    def define_problem(self) -> None:
        geometry = self.config["geometry"]
        numerics = self.config["numerics"]
        initial = self.config["initial"]
        if self.config["shrinkage"]["mode"] != "none":
            raise NotImplementedError(
                "This MVP runner supports shrinkage.mode='none'; prescribed/ALE cases "
                "are reserved for the next validated stage."
            )
        if not self.config["model"]["solve_temperature"] or not self.config["model"]["solve_moisture"]:
            raise NotImplementedError("The current MVP runner solves both fields together")

        self.set_coordinate_system("axisymmetric")
        self.add_mesh(RectangularQuadMesh(
            name="solid",
            size=[geometry["initial_radius_m"], geometry["length_m"]],
            N=[numerics["elements_r"], numerics["elements_z"]],
            lower_left=[0.0, 0.0],
        ))
        equations = CoupledDryingEquations(self.config)
        equations += InitialCondition(
            temperature_K=initial["temperature_K"],
            moisture_kg_per_kg_dry=initial["moisture_kg_per_kg_dry"],
        )
        equations += IntegralObservables(
            _volume=1,
            _temperature_integral=var("temperature_K"),
            _moisture_integral=var("moisture_kg_per_kg_dry"),
            mean_temperature_K=lambda _temperature_integral, _volume: _temperature_integral / _volume,
            mean_moisture_kg_per_kg_dry=lambda _moisture_integral, _volume: _moisture_integral / _volume,
        )
        self.add_equations(equations @ "solid")
        for boundary in ("right", "top", "bottom"):
            self.add_equations(ConvectiveDryingBoundary(self.config) @ f"solid/{boundary}")
