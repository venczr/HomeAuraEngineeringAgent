"""Typed, provenance-bearing project/system inputs for UFH sizing.

Room identity and geometry deliberately remain owned by the project room
source. This profile contains only project/building design and UFH system
configuration; it supplies no defaults for physical values.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from agent.floor_heating_sizing import (
    FloorConstructionAssumptions,
    HeatLossInsulationAssumptions,
)
from agent.floor_heating_models import FloorHeatingPoint
from agent.project_models import StrictProjectModel
from agent.ufh_candidate_adapter import CommonCircuitInputs
from agent.ufh_engineering_models import Finite, Nonnegative, Positive
from agent import ufh_engineering_kernel as kernel


class ProfileValueProvenance(StrictProjectModel):
    source_file: str = Field(min_length=1, max_length=1024)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_path: str = Field(min_length=1, max_length=512)
    source_kind: Literal[
        "canonical_project_domain",
        "room_extraction",
        "linked_engineering_metadata",
        "project_approved_normative_extract",
        "routing_algorithm_policy",
        "test_only",
    ]
    transformation: str | None = Field(default=None, max_length=512)


class UFHProjectDesignConditions(StrictProjectModel):
    outdoor_design_temperature_c: float


class UFHProjectRoutingSettings(StrictProjectModel):
    """Non-geometric routing choices; room boundary/walls stay with the room."""

    collector_point: FloorHeatingPoint
    wall_offset_mm: int
    spacing_mm: Literal[100, 150, 200]
    requested_circuit_count: Literal[1, 2, 3] | None
    routing_mode: Literal["legacy", "non_crossing_visual"]
    turn_radius_mm: int
    field_spacing_mm: Literal[100, 150, 200] | None
    perimeter_spacing_mm: Literal[100] | None
    perimeter_band_depth_mm: int | None
    preferred_topology: Literal["HYBRID_PERIMETER_SERPENTINE_COUNTERFLOW_SPIRAL"] | None
    installation_grid_spacing_mm: Literal[100] | None
    perimeter_priority_mode: bool


class UFHRoutingPolicy(StrictProjectModel):
    """Versioned algorithmic routing policy, not a physical design source."""

    policy_id: Literal["HOMEAURA_UFH_ROUTING_POLICY"]
    policy_version: Literal["V1"]
    routing_mode: Literal["legacy", "non_crossing_visual"]
    turn_radius_mm: int
    perimeter_priority_mode: bool
    minimum_circuit_length_mm: int
    maximum_circuit_length_mm: int
    requested_circuit_count_semantics: Literal["AUTO_WHEN_NONE_EXACT_1_TO_3"]
    source: Literal["HomeAura routing policy"]
    compatibility_note: str

    @property
    def policy_digest(self) -> str:
        raw = json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def default_ufh_routing_policy() -> UFHRoutingPolicy:
    return UFHRoutingPolicy(
        policy_id="HOMEAURA_UFH_ROUTING_POLICY",
        policy_version="V1",
        routing_mode="legacy",
        turn_radius_mm=100,
        perimeter_priority_mode=True,
        minimum_circuit_length_mm=40_000,
        maximum_circuit_length_mm=80_000,
        requested_circuit_count_semantics="AUTO_WHEN_NONE_EXACT_1_TO_3",
        source="HomeAura routing policy",
        compatibility_note=(
            "Preserves existing legacy routing behavior; 40-80 m is "
            "LEGACY_MVP_ROUTING_POLICY, not an EN1264 physical limit."
        ),
    )


class UFHProjectEngineeringInputs(StrictProjectModel):
    """Project-owned engineering inputs; indoor temperature remains room-owned."""

    area_basis: Literal["ACKNOWLEDGED_COVERAGE_ESTIMATE", "EXACT_SERVED_AREA_REQUIRED"]
    k_h_w_m2k: Positive
    surface_limit_w_m2: Positive
    r_o_m2k_w: Nonnegative
    r_u_m2k_w: Positive
    c_w_j_kgk: Positive
    mode: Literal["solve_supply", "solve_return"]
    sigma_k: Positive | None = None
    theta_supply_c: Finite | None = None
    common_circuit: CommonCircuitInputs

    @model_validator(mode="after")
    def validate_mode_and_fluid(self):
        if self.c_w_j_kgk != kernel.WATER_CP_J_KG_K:
            raise ValueError("Kernel V1 supports only its explicit water heat-capacity constant")
        if self.mode == "solve_return":
            if self.theta_supply_c is None or self.sigma_k is not None:
                raise ValueError("solve_return requires supply only")
        elif self.sigma_k is None or self.theta_supply_c is not None:
            raise ValueError("solve_supply requires sigma only")
        return self


class UFHProjectEngineeringProfile(StrictProjectModel):
    """Project-side engineering settings, with one provenance per leaf."""

    design_conditions: UFHProjectDesignConditions
    building_physics: HeatLossInsulationAssumptions
    floor_construction: FloorConstructionAssumptions
    routing_policy: UFHRoutingPolicy = Field(default_factory=default_ufh_routing_policy)
    routing_settings: UFHProjectRoutingSettings
    engineering_inputs: UFHProjectEngineeringInputs
    provenance: dict[str, ProfileValueProvenance] = Field(min_length=1)

    @property
    def profile_digest(self) -> str:
        payload = self.model_dump(mode="json")
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @model_validator(mode="after")
    def complete_leaf_provenance(self) -> "UFHProjectEngineeringProfile":
        def leaves(value, prefix):
            if isinstance(value, dict) and value:
                return [item for key, child in value.items()
                        for item in leaves(child, f"{prefix}.{key}")]
            if isinstance(value, (list, tuple)) and value:
                return [item for index, child in enumerate(value)
                        for item in leaves(child, f"{prefix}[{index}]")]
            return [prefix]

        expected = set(leaves(self.sizing_fragment(), "sizing"))
        expected.update(leaves(self.engineering_fragment(), "engineering"))
        absent = sorted(expected - set(self.provenance))
        if absent:
            raise ValueError(f"profile leaf provenance missing: {', '.join(absent)}")
        extra = sorted(set(self.provenance) - expected)
        if extra:
            raise ValueError(f"profile provenance has unowned paths: {', '.join(extra)}")
        return self

    def sizing_fragment(self) -> dict:
        return {
            "room": {
                "outdoor_design_temperature_c": self.design_conditions.outdoor_design_temperature_c,
                "insulation": self.building_physics.model_dump(mode="python"),
            },
            "floor_construction": self.floor_construction.model_dump(mode="python"),
            "coverage_request": self.routing_settings.model_dump(mode="python"),
        }

    def engineering_fragment(self) -> dict:
        result = self.engineering_inputs.model_dump(mode="python")
        # The room source is the sole owner of the indoor design setpoint.
        result.pop("theta_indoor_c", None)
        result.pop("theta_below_c", None)
        # This output is computed by the kernel in the corresponding mode.
        if self.engineering_inputs.mode == "solve_supply":
            result.pop("theta_supply_c", None)
        else:
            result.pop("sigma_k", None)
        return result


# Ownership registry for every field requested by the sizing and integration
# model walkers. Entries are intentionally not inferred from Pydantic defaults.
FIELD_CLASSIFICATION: dict[str, str] = {
    "identity.project_id": "STRUCTURAL_METADATA",
    "identity.building_id": "STRUCTURAL_METADATA",
    "identity.level_id": "STRUCTURAL_METADATA",
    "identity.room_id": "STRUCTURAL_METADATA",
    "sizing.schema_version": "STRUCTURAL_METADATA",
    "sizing.room.room_area_mm2": "CALCULATED",
    "sizing.room.room_height_mm": "ROOM_GEOMETRY",
    "sizing.room.exterior_wall_length_mm": "ROOM_GEOMETRY",
    "sizing.room.openings": "ROOM_GEOMETRY",
    "sizing.room.insulation.exterior_wall_u_value_w_m2k": "BUILDING_PHYSICS",
    "sizing.room.insulation.floor_u_value_w_m2k": "BUILDING_PHYSICS",
    "sizing.room.insulation.ceiling_u_value_w_m2k": "BUILDING_PHYSICS",
    "sizing.room.insulation.air_changes_per_hour": "BUILDING_PHYSICS",
    "sizing.room.insulation.ventilation_heat_capacity_factor_wh_m3k": "BUILDING_PHYSICS",
    "sizing.room.insulation.thermal_bridge_allowance_percent": "BUILDING_PHYSICS",
    "sizing.room.insulation.design_margin_percent": "UFH_DESIGN_SETTING",
    "sizing.room.insulation.floor_boundary_temperature_c": "DESIGN_CONDITION",
    "sizing.room.insulation.ceiling_boundary_temperature_c": "DESIGN_CONDITION",
    "sizing.room.indoor_temperature_c": "DESIGN_CONDITION",
    "sizing.room.outdoor_design_temperature_c": "DESIGN_CONDITION",
    "sizing.coverage_request.schema_version": "STRUCTURAL_METADATA",
    "sizing.coverage_request.project_id": "STRUCTURAL_METADATA",
    "sizing.coverage_request.room_id": "STRUCTURAL_METADATA",
    "sizing.coverage_request.boundary.points": "ROOM_GEOMETRY",
    "sizing.coverage_request.exclusion_zones": "OPTIONAL_EXPLICIT_EMPTY",
    "sizing.coverage_request.collector_point.x_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.collector_point.y_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.wall_offset_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.spacing_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.maximum_circuit_length_mm": "LEGACY_ROUTING_POLICY",
    "sizing.coverage_request.minimum_circuit_length_mm": "LEGACY_ROUTING_POLICY",
    "sizing.coverage_request.turn_radius_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.routing_mode": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.requested_circuit_count": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.request_reference": "STRUCTURAL_METADATA",
    "sizing.coverage_request.field_spacing_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.perimeter_spacing_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.perimeter_band_depth_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.exterior_wall_segments": "ROOM_GEOMETRY",
    "sizing.coverage_request.preferred_topology": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.installation_grid_spacing_mm": "UFH_DESIGN_SETTING",
    "sizing.coverage_request.perimeter_priority_mode": "UFH_DESIGN_SETTING",
    "sizing.floor_construction.declared_output_at_100mm_w_m2": "PRODUCT_PROPERTY",
    "sizing.floor_construction.declared_output_at_200mm_w_m2": "PRODUCT_PROPERTY",
    "sizing.floor_construction.output_basis_reference": "PRODUCT_PROPERTY",
    "engineering.area_basis": "UFH_DESIGN_SETTING",
    "engineering.k_h_w_m2k": "PRODUCT_PROPERTY",
    "engineering.surface_limit_w_m2": "CONTROL_PROPERTY",
    "engineering.theta_indoor_c": "DESIGN_CONDITION",
    "engineering.theta_below_c": "DESIGN_CONDITION",
    "engineering.r_o_m2k_w": "PRODUCT_PROPERTY",
    "engineering.r_u_m2k_w": "PRODUCT_PROPERTY",
    "engineering.c_w_j_kgk": "FLUID_PROPERTY",
    "engineering.mode": "UFH_DESIGN_SETTING",
    "engineering.sigma_k": "UFH_DESIGN_SETTING",
    "engineering.theta_supply_c": "DESIGN_CONDITION",
    "engineering.common_circuit.inner_diameter_m": "PRODUCT_PROPERTY",
    "engineering.common_circuit.roughness_m": "PRODUCT_PROPERTY",
    "engineering.common_circuit.fluid.density_kg_m3": "FLUID_PROPERTY",
    "engineering.common_circuit.fluid.dynamic_viscosity_pa_s": "FLUID_PROPERTY",
    "engineering.common_circuit.fluid.specific_gravity": "FLUID_PROPERTY",
    "engineering.common_circuit.embedded_losses.continuous_bends_pa": "PRODUCT_PROPERTY",
    "engineering.common_circuit.embedded_losses.pipe_fittings_pa": "PRODUCT_PROPERTY",
    "engineering.common_circuit.embedded_losses.other_fixed_pipe_path_pa": "PRODUCT_PROPERTY",
    "engineering.common_circuit.fixed_manifold_losses": "PRODUCT_PROPERTY",
    "engineering.common_circuit.manufacturer_max_circuit_pressure_pa": "PRODUCT_PROPERTY",
    "engineering.common_circuit.control": "CONTROL_PROPERTY",
}

for _path, _source_class in {
    "sizing.room.openings[].opening_id": "ROOM_GEOMETRY",
    "sizing.room.openings[].kind": "ROOM_GEOMETRY",
    "sizing.room.openings[].width_mm": "ROOM_GEOMETRY",
    "sizing.room.openings[].height_mm": "ROOM_GEOMETRY",
    "sizing.room.openings[].u_value_w_m2k": "BUILDING_PHYSICS",
    "sizing.coverage_request.boundary.points[].x_mm": "ROOM_GEOMETRY",
    "sizing.coverage_request.boundary.points[].y_mm": "ROOM_GEOMETRY",
    "sizing.coverage_request.exclusion_zones[].points[].x_mm": "OPTIONAL_EXPLICIT_EMPTY",
    "sizing.coverage_request.exclusion_zones[].points[].y_mm": "OPTIONAL_EXPLICIT_EMPTY",
    "sizing.coverage_request.exterior_wall_segments[].reference": "ROOM_GEOMETRY",
    "sizing.coverage_request.exterior_wall_segments[].start.x_mm": "ROOM_GEOMETRY",
    "sizing.coverage_request.exterior_wall_segments[].start.y_mm": "ROOM_GEOMETRY",
    "sizing.coverage_request.exterior_wall_segments[].end.x_mm": "ROOM_GEOMETRY",
    "sizing.coverage_request.exterior_wall_segments[].end.y_mm": "ROOM_GEOMETRY",
    "engineering.common_circuit.fixed_manifold_losses[].component_id": "PRODUCT_PROPERTY",
    "engineering.common_circuit.fixed_manifold_losses[].pressure_pa": "PRODUCT_PROPERTY",
    "engineering.common_circuit.control.manufacturer": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.product_family": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.product_version": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.document_reference": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.document_revision": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.characteristic_scope": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.included_components[]": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.kv_min_m3h": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.kv_max_m3h": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.setting_min": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.setting_max": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.limit_type": "CONTROL_PROPERTY",
    "engineering.common_circuit.control.source_confidence": "CONTROL_PROPERTY",
}.items():
    FIELD_CLASSIFICATION[_path] = _source_class


STRUCTURAL_DEFAULT_FIELDS = frozenset({
    "sizing.schema_version",
    "sizing.coverage_request.schema_version",
    "sizing.coverage_request.requested_circuit_count",
    "sizing.coverage_request.request_reference",
    "sizing.coverage_request.turn_radius_mm",
    "sizing.coverage_request.routing_mode",
    "sizing.coverage_request.field_spacing_mm",
    "sizing.coverage_request.perimeter_spacing_mm",
    "sizing.coverage_request.perimeter_band_depth_mm",
    "sizing.coverage_request.preferred_topology",
    "sizing.coverage_request.installation_grid_spacing_mm",
    "sizing.coverage_request.perimeter_priority_mode",
})

LEGACY_POLICY_FIELDS = frozenset({
    "sizing.coverage_request.minimum_circuit_length_mm",
    "sizing.coverage_request.maximum_circuit_length_mm",
})


class ClassifiedInputGap(StrictProjectModel):
    path: str = Field(min_length=1, max_length=256)
    source_class: Literal[
        "ROOM_GEOMETRY", "BUILDING_PHYSICS", "DESIGN_CONDITION",
        "UFH_DESIGN_SETTING", "PRODUCT_PROPERTY", "FLUID_PROPERTY",
        "CONTROL_PROPERTY", "CALCULATED", "STRUCTURAL_METADATA",
        "OPTIONAL_EXPLICIT_EMPTY", "LEGACY_ROUTING_POLICY", "UNKNOWN",
    ]
    owner: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=160)
    required_externally: bool
    default_allowed: bool
