"""Authoring contract for project-side UFH engineering profile data.

This layer is deliberately separate from project persistence. It validates a
human/machine-authored payload, keeps incomplete templates incomplete, and can
materialize the existing UFHProjectEngineeringProfile only after every physical
value has explicit units and provenance.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from agent import ufh_engineering_kernel as kernel
from agent.floor_heating_models import FloorHeatingPoint
from agent.floor_heating_sizing import (
    FloorConstructionAssumptions,
    HeatLossInsulationAssumptions,
)
from agent.project_models import StrictProjectModel
from agent.ufh_candidate_adapter import CommonCircuitInputs
from agent.ufh_engineering_models import (
    CharacteristicScope,
    EmbeddedLosses,
    FixedLoss,
    Fluid,
    ValveCharacteristic,
    ValveLimitType,
)
from agent.ufh_project_engineering_profile import (
    ProfileValueProvenance,
    default_ufh_routing_policy,
    UFHProjectDesignConditions,
    UFHProjectEngineeringInputs,
    UFHProjectEngineeringProfile,
    UFHProjectRoutingSettings,
)
from agent.ufh_project_adapter import ProjectOwnedEngineeringValues


class AuthoringStatus(str, Enum):
    UNSET = "UNSET"
    EXPLICIT_VALUE = "EXPLICIT_VALUE"
    CATALOG_REFERENCE = "CATALOG_REFERENCE"
    NORMATIVE_REFERENCE = "NORMATIVE_REFERENCE"
    DERIVED = "DERIVED"
    EXPLICIT_EMPTY = "EXPLICIT_EMPTY"


class InputAcquisitionType(str, Enum):
    USER_PROJECT_DECISION = "USER_PROJECT_DECISION"
    NORMATIVE_PROJECT_CONDITION = "NORMATIVE_PROJECT_CONDITION"
    BUILDING_CONSTRUCTION_PROPERTY = "BUILDING_CONSTRUCTION_PROPERTY"
    UFH_PRODUCT_SELECTION = "UFH_PRODUCT_SELECTION"
    FLUID_SELECTION = "FLUID_SELECTION"
    CONTROL_PRODUCT_SELECTION = "CONTROL_PRODUCT_SELECTION"
    EXPLICIT_EMPTY_CONFIRMATION = "EXPLICIT_EMPTY_CONFIRMATION"
    DERIVED_AFTER_SELECTION = "DERIVED_AFTER_SELECTION"
    LEGACY_SYSTEM_POLICY = "LEGACY_SYSTEM_POLICY"


FIELD_AUTHORING_MAP: dict[str, InputAcquisitionType] = {
    "sizing.room.outdoor_design_temperature_c": InputAcquisitionType.NORMATIVE_PROJECT_CONDITION,
    "sizing.room.insulation.floor_boundary_temperature_c": InputAcquisitionType.NORMATIVE_PROJECT_CONDITION,
    "sizing.room.insulation.ceiling_boundary_temperature_c": InputAcquisitionType.NORMATIVE_PROJECT_CONDITION,
    "engineering.theta_below_c": InputAcquisitionType.DERIVED_AFTER_SELECTION,
    "engineering.theta_supply_c": InputAcquisitionType.NORMATIVE_PROJECT_CONDITION,
    "sizing.room.insulation.exterior_wall_u_value_w_m2k": InputAcquisitionType.BUILDING_CONSTRUCTION_PROPERTY,
    "sizing.room.insulation.floor_u_value_w_m2k": InputAcquisitionType.BUILDING_CONSTRUCTION_PROPERTY,
    "sizing.room.insulation.ceiling_u_value_w_m2k": InputAcquisitionType.BUILDING_CONSTRUCTION_PROPERTY,
    "sizing.room.insulation.ventilation_heat_capacity_factor_wh_m3k": InputAcquisitionType.BUILDING_CONSTRUCTION_PROPERTY,
    "sizing.room.insulation.thermal_bridge_allowance_percent": InputAcquisitionType.BUILDING_CONSTRUCTION_PROPERTY,
    "sizing.coverage_request.collector_point.x_mm": InputAcquisitionType.USER_PROJECT_DECISION,
    "sizing.coverage_request.collector_point.y_mm": InputAcquisitionType.USER_PROJECT_DECISION,
    "sizing.coverage_request.spacing_mm": InputAcquisitionType.USER_PROJECT_DECISION,
    "sizing.coverage_request.wall_offset_mm": InputAcquisitionType.USER_PROJECT_DECISION,
    "sizing.room.insulation.design_margin_percent": InputAcquisitionType.USER_PROJECT_DECISION,
    "engineering.area_basis": InputAcquisitionType.USER_PROJECT_DECISION,
    "engineering.mode": InputAcquisitionType.USER_PROJECT_DECISION,
    "engineering.sigma_k": InputAcquisitionType.NORMATIVE_PROJECT_CONDITION,
    "sizing.coverage_request.exclusion_zones": InputAcquisitionType.EXPLICIT_EMPTY_CONFIRMATION,
    "sizing.coverage_request.exterior_wall_segments": InputAcquisitionType.DERIVED_AFTER_SELECTION,
    "sizing.room.exterior_wall_length_mm": InputAcquisitionType.DERIVED_AFTER_SELECTION,
    "sizing.room.openings": InputAcquisitionType.EXPLICIT_EMPTY_CONFIRMATION,
    "sizing.floor_construction.declared_output_at_100mm_w_m2": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "sizing.floor_construction.declared_output_at_200mm_w_m2": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "sizing.floor_construction.output_basis_reference": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.k_h_w_m2k": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.r_o_m2k_w": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.r_u_m2k_w": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.inner_diameter_m": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.roughness_m": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.embedded_losses.continuous_bends_pa": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.embedded_losses.pipe_fittings_pa": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.embedded_losses.other_fixed_pipe_path_pa": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.fixed_manifold_losses": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.common_circuit.manufacturer_max_circuit_pressure_pa": InputAcquisitionType.UFH_PRODUCT_SELECTION,
    "engineering.c_w_j_kgk": InputAcquisitionType.FLUID_SELECTION,
    "engineering.common_circuit.fluid.density_kg_m3": InputAcquisitionType.FLUID_SELECTION,
    "engineering.common_circuit.fluid.dynamic_viscosity_pa_s": InputAcquisitionType.FLUID_SELECTION,
    "engineering.common_circuit.fluid.specific_gravity": InputAcquisitionType.FLUID_SELECTION,
    "engineering.surface_limit_w_m2": InputAcquisitionType.CONTROL_PRODUCT_SELECTION,
    "engineering.common_circuit.control": InputAcquisitionType.CONTROL_PRODUCT_SELECTION,
}


EXPECTED_UNITS = {
    "celsius": "degC",
    "u_value": "W/(m2*K)",
    "ventilation_heat_capacity": "Wh/(m3*K)",
    "percent": "%",
    "mm": "mm",
    "m": "m",
    "pa": "Pa",
    "density": "kg/m3",
    "viscosity": "Pa*s",
    "heat_capacity": "J/(kg*K)",
    "w_m2": "W/m2",
    "kh": "W/(m2*K)",
    "resistance": "m2*K/W",
    "kv": "m3/h",
}


class AuthoringProvenance(StrictProjectModel):
    source_type: Literal[
        "project_decision",
        "normative_source",
        "project_approved_normative_extract",
        "building_construction_data",
        "product_document",
        "fluid_property_source",
        "control_product_document",
        "routing_algorithm_policy",
        "project_data",
        "test_only",
    ]
    project_source_kind: Literal["room_extraction", "canonical_project_domain"] | None = None
    source_reference: str = Field(min_length=1, max_length=512)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_field: str = Field(min_length=1, max_length=512)
    author_or_confirmation: str | None = Field(default=None, max_length=256)
    transformation: str = Field(min_length=1, max_length=512)
    units: str = Field(min_length=1, max_length=64)

    def to_profile(self, path: str) -> ProfileValueProvenance:
        digest = hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True,
                       ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        if self.source_type == "test_only":
            kind = "test_only"
        elif self.source_type == "routing_algorithm_policy":
            kind = "routing_algorithm_policy"
        elif self.source_type == "project_data":
            kind = self.project_source_kind or "canonical_project_domain"
        elif self.source_type == "project_approved_normative_extract":
            kind = "project_approved_normative_extract"
        else:
            kind = "linked_engineering_metadata"
        return ProfileValueProvenance(
            source_file=self.source_reference,
            source_sha256=self.source_sha256 or digest,
            source_path=self.source_field,
            source_kind=kind,
            transformation=f"{self.transformation}; units={self.units}; target={path}",
        )


class AuthoredValue(StrictProjectModel):
    status: Literal[
        "UNSET", "EXPLICIT_VALUE", "CATALOG_REFERENCE",
        "NORMATIVE_REFERENCE", "DERIVED", "EXPLICIT_EMPTY",
    ] = AuthoringStatus.UNSET.value
    value: Any = None
    unit: str | None = None
    provenance: AuthoringProvenance | None = None
    catalog_reference: str | None = Field(default=None, max_length=256)
    normative_reference: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_state(self):
        if self.status in {
            AuthoringStatus.EXPLICIT_VALUE.value,
            AuthoringStatus.CATALOG_REFERENCE.value,
            AuthoringStatus.NORMATIVE_REFERENCE.value,
        }:
            if self.value is None or self.unit is None or self.provenance is None:
                raise ValueError("authored physical value requires value, unit, and provenance")
        if self.status == AuthoringStatus.EXPLICIT_EMPTY.value:
            if self.value != [] or self.provenance is None:
                raise ValueError("explicit empty requires [] and provenance")
        if self.status == AuthoringStatus.UNSET.value and (
            self.value is not None or self.provenance is not None
        ):
            raise ValueError("UNSET field must not carry a value or provenance")
        return self


class AuthoringDiagnostic(StrictProjectModel):
    code: str = Field(min_length=1, max_length=96)
    path: str = Field(min_length=1, max_length=256)
    message: str = Field(min_length=1, max_length=512)


class Test01UfhEngineeringAuthoringTemplate(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    template_id: str = Field(min_length=1, max_length=160)
    project_context: dict[str, Any] = Field(default_factory=dict)
    design_conditions: dict[str, AuthoredValue]
    building_physics: dict[str, AuthoredValue]
    ufh_design_settings: dict[str, AuthoredValue]
    floor_system_product: dict[str, AuthoredValue]
    pipe_product: dict[str, AuthoredValue]
    manifold_product: dict[str, AuthoredValue]
    fluid_definition: dict[str, AuthoredValue]
    control_model: dict[str, AuthoredValue]
    explicit_confirmations: dict[str, AuthoredValue]
    thermal_boundary_conditions: dict[str, AuthoredValue]
    envelope_constructions: dict[str, AuthoredValue] = Field(
        default_factory=lambda: {"selected": AuthoredValue(), "operating_condition": AuthoredValue()}
    )

    @property
    def template_digest(self) -> str:
        raw = json.dumps(self.model_dump(mode="json"), sort_keys=True,
                         ensure_ascii=False, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


class AuthoringLoadResult(StrictProjectModel):
    status: Literal["INCOMPLETE", "READY", "INVALID"]
    template_digest: str
    profile: UFHProjectEngineeringProfile | None = None
    diagnostics: list[AuthoringDiagnostic] = Field(default_factory=list)
    missing_authoring_paths: list[str] = Field(default_factory=list)
    project_owned_values_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def test01_authoring_template_payload() -> dict[str, Any]:
    unset = {"status": "UNSET"}
    return {
        "schema_version": "1.0",
        "template_id": "Test_01:101DAA3:UFH_ENGINEERING_PROFILE_AUTHORING_V1",
        "project_context": {
            "project_id": "Test_01",
            "room_id": "101DAA3",
            "known_from_project": [
                "building_id", "level_id", "room boundary", "room area",
                "indoor room temperature", "air changes per hour",
            ],
            "coordinate_system": "authoritative room boundary integer millimetres",
        },
        "design_conditions": {
            "outdoor_design_temperature_c": unset,
            "floor_boundary_temperature_c": unset,
            "ceiling_boundary_temperature_c": unset,
            "sigma_k": unset,
            "theta_supply_c": unset,
        },
        "building_physics": {
            "exterior_wall_u_value_w_m2k": unset,
            "floor_u_value_w_m2k": unset,
            "ceiling_u_value_w_m2k": unset,
            "ventilation_heat_capacity_factor_wh_m3k": unset,
            "thermal_bridge_allowance_percent": unset,
        },
        "ufh_design_settings": {
            "collector_point_x_mm": unset,
            "collector_point_y_mm": unset,
            "spacing_mm": unset,
            "wall_offset_mm": unset,
            "design_margin_percent": unset,
            "area_basis": unset,
            "mode": unset,
        },
        "floor_system_product": {
            "floor_system_product_id": unset,
            "declared_output_at_100mm_w_m2": unset,
            "declared_output_at_200mm_w_m2": unset,
            "output_basis_reference": unset,
            "k_h_w_m2k": unset,
            "r_o_m2k_w": unset,
            "r_u_m2k_w": unset,
        },
        "pipe_product": {
            "pipe_product_id": unset,
            "inner_diameter_m": unset,
            "roughness_m": unset,
            "embedded_losses_continuous_bends_pa": unset,
            "embedded_losses_pipe_fittings_pa": unset,
            "embedded_losses_other_fixed_pipe_path_pa": unset,
        },
        "manifold_product": {
            "manifold_product_id": unset,
            "fixed_manifold_losses": unset,
            "manufacturer_max_circuit_pressure_pa": unset,
        },
        "fluid_definition": {
            "fluid_definition_id": unset,
            "c_w_j_kgk": unset,
            "density_kg_m3": unset,
            "dynamic_viscosity_pa_s": unset,
            "specific_gravity": unset,
        },
        "control_model": {
            "surface_limit_w_m2": unset,
            "control_characteristic": unset,
        },
        "explicit_confirmations": {
            "exclusion_zones": unset,
            "openings": unset,
        },
        "thermal_boundary_conditions": {
            "below": unset,
            "above": unset,
        },
        "envelope_constructions": {"selected": unset, "operating_condition": unset},
    }


def _value(container: dict[str, AuthoredValue], key: str, path: str,
           unit: str | None, diagnostics: list[AuthoringDiagnostic]) -> Any:
    item = container[key]
    if item.status == AuthoringStatus.UNSET.value:
        diagnostics.append(AuthoringDiagnostic(
            code="AUTHORING_VALUE_UNSET", path=path,
            message="Required authoring value is not supplied.",
        ))
        return None
    if unit is not None and item.unit != unit:
        diagnostics.append(AuthoringDiagnostic(
            code="AUTHORING_UNIT_INVALID", path=path,
            message=f"Expected canonical unit {unit}, got {item.unit!r}.",
        ))
        return None
    return item.value


def _prov(item: AuthoredValue, path: str) -> ProfileValueProvenance:
    assert item.provenance is not None
    return item.provenance.to_profile(path)


def _routing_policy_value(path: str, value: Any, unit: str) -> AuthoredValue:
    policy = default_ufh_routing_policy()
    return AuthoredValue(
        status=AuthoringStatus.DERIVED,
        value=value,
        unit=unit,
        provenance=AuthoringProvenance(
            source_type="routing_algorithm_policy",
            source_reference=f"{policy.policy_id}:{policy.policy_version}",
            source_field=path,
            author_or_confirmation=policy.policy_digest,
            transformation=(
                "versioned HomeAura routing algorithm policy; preserves "
                "existing routing-facing value"
            ),
            units=unit,
        ),
    )


def load_ufh_project_engineering_authoring_template(
    payload: dict[str, Any],
    project_owned_values: ProjectOwnedEngineeringValues | dict[str, AuthoredValue | dict[str, Any]] | None = None,
) -> AuthoringLoadResult:
    diagnostics: list[AuthoringDiagnostic] = []
    try:
        template = Test01UfhEngineeringAuthoringTemplate.model_validate(payload)
    except Exception as error:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        return AuthoringLoadResult(status="INVALID", template_digest=digest,
                                   diagnostics=[AuthoringDiagnostic(
                                       code="AUTHORING_TEMPLATE_INVALID",
                                       path="$", message=str(error)[:512])])
    p: dict[str, ProfileValueProvenance] = {}
    dc, bp = template.design_conditions, template.building_physics
    us, fs = template.ufh_design_settings, template.floor_system_product
    pp, mp = template.pipe_product, template.manifold_product
    fl, cm = template.fluid_definition, template.control_model
    ex = template.explicit_confirmations
    project_owned: dict[str, AuthoredValue] = {}
    project_owned_digest = None
    project_owned_scope: tuple[str, str] | None = None
    if isinstance(project_owned_values, ProjectOwnedEngineeringValues):
        project_owned_digest = project_owned_values.binding_digest
        project_owned_scope = (project_owned_values.project_id, project_owned_values.room_id)
        context_project = template.project_context.get("project_id")
        context_room = template.project_context.get("room_id")
        if ((context_project is not None and context_project != project_owned_scope[0])
                or (context_room is not None and context_room != project_owned_scope[1])):
            diagnostics.append(AuthoringDiagnostic(
                code="PROJECT_OWNED_IDENTITY_MISMATCH",
                path="project_context",
                message="Project-owned bindings belong to a different project or room.",
            ))
        project_items = {}
        for item in project_owned_values.values:
            project_items[item.canonical_field_path] = AuthoredValue(
                status=AuthoringStatus.EXPLICIT_VALUE,
                value=item.value,
                unit=item.units,
                provenance=AuthoringProvenance(
                    source_type="project_data",
                    project_source_kind=item.source_type,
                    source_reference=item.source_reference,
                    source_sha256=item.source_digest,
                    source_field=item.source_field,
                    author_or_confirmation=f"{item.project_id}/{item.room_id}",
                    transformation=item.transformation,
                    units=item.units,
                ),
            )
    else:
        project_items = project_owned_values or {}
        if project_items:
            project_owned_digest = hashlib.sha256(json.dumps(
                {path: (item.model_dump(mode="json") if isinstance(item, AuthoredValue) else item)
                 for path, item in sorted(project_items.items())},
                sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"),
            ).encode()).hexdigest()
    for path, item in project_items.items():
        try:
            if path not in {"sizing.room.insulation.air_changes_per_hour"}:
                raise ValueError("field is not registered as project-owned profile input")
            authored = AuthoredValue.model_validate(item)
            if (authored.status != AuthoringStatus.EXPLICIT_VALUE.value
                    or authored.provenance is None
                    or authored.provenance.source_type != "project_data"):
                raise ValueError("project-owned binding requires explicit project-data provenance")
            project_owned[path] = authored
        except Exception as error:
            diagnostics.append(AuthoringDiagnostic(
                code="PROJECT_OWNED_VALUE_INVALID", path=path,
                message=str(error)[:512],
            ))

    ach_path = "sizing.room.insulation.air_changes_per_hour"
    ach_item = bp.get("air_changes_per_hour")
    bound_ach = project_owned.get(ach_path)
    if bound_ach is not None and ach_item is not None and ach_item.status != AuthoringStatus.UNSET.value:
        if ach_item.value != bound_ach.value or ach_item.unit != bound_ach.unit:
            diagnostics.append(AuthoringDiagnostic(
                code="SOURCE_VALUE_CONFLICT", path=ach_path,
                message="Authoring ACH conflicts with the authoritative project-owned value.",
            ))
        else:
            ach_item = bound_ach
    elif bound_ach is not None:
        ach_item = bound_ach
    if ach_item is None or ach_item.status == AuthoringStatus.UNSET.value:
        diagnostics.append(AuthoringDiagnostic(
            code="AUTHORITATIVE_PROJECT_VALUE_REQUIRED",
            path=ach_path,
            message="ACH must come from the authoritative project source; no production fallback is allowed.",
        ))
    elif ach_item.unit != "1/h":
        diagnostics.append(AuthoringDiagnostic(
            code="AUTHORING_UNIT_INVALID", path=ach_path,
            message=f"Expected canonical unit 1/h, got {ach_item.unit!r}.",
        ))

    mode = _value(us, "mode", "engineering.mode", None, diagnostics)
    sigma = None
    theta_supply = None
    if mode == "solve_supply":
        sigma = _value(dc, "sigma_k", "engineering.sigma_k", "K", diagnostics)
        if dc["theta_supply_c"].status != AuthoringStatus.UNSET.value:
            diagnostics.append(AuthoringDiagnostic(
                code="AUTHORING_MODE_ALTERNATIVE_CONFLICT",
                path="engineering.theta_supply_c",
                message="solve_supply solves supply temperature; do not author theta_supply_c.",
            ))
    elif mode == "solve_return":
        theta_supply = _value(dc, "theta_supply_c", "engineering.theta_supply_c", "degC", diagnostics)
        if dc["sigma_k"].status != AuthoringStatus.UNSET.value:
            diagnostics.append(AuthoringDiagnostic(
                code="AUTHORING_MODE_ALTERNATIVE_CONFLICT",
                path="engineering.sigma_k",
                message="solve_return solves sigma; do not author sigma_k.",
            ))
    elif mode is not None:
        diagnostics.append(AuthoringDiagnostic(
            code="AUTHORING_ENUM_INVALID", path="engineering.mode",
            message="mode must be solve_supply or solve_return.",
        ))

    exclusions = _value(ex, "exclusion_zones", "sizing.coverage_request.exclusion_zones", None, diagnostics)
    openings = _value(ex, "openings", "sizing.room.openings", None, diagnostics)
    for key, value in (("exclusion_zones", exclusions), ("openings", openings)):
        if value is not None and value != []:
            diagnostics.append(AuthoringDiagnostic(
                code="AUTHORING_COLLECTION_UNSUPPORTED",
                path=f"explicit_confirmations.{key}",
                message="V1 template supports only explicit empty confirmation; geometry collections stay project-owned.",
            ))

    values = {
        "outdoor": _value(dc, "outdoor_design_temperature_c", "sizing.room.outdoor_design_temperature_c", "degC", diagnostics),
        "floor_boundary": _value(dc, "floor_boundary_temperature_c", "sizing.room.insulation.floor_boundary_temperature_c", "degC", diagnostics),
        "ceiling_boundary": _value(dc, "ceiling_boundary_temperature_c", "sizing.room.insulation.ceiling_boundary_temperature_c", "degC", diagnostics),
        "wall_u": _value(bp, "exterior_wall_u_value_w_m2k", "sizing.room.insulation.exterior_wall_u_value_w_m2k", "W/(m2*K)", diagnostics),
        "floor_u": _value(bp, "floor_u_value_w_m2k", "sizing.room.insulation.floor_u_value_w_m2k", "W/(m2*K)", diagnostics),
        "ceiling_u": _value(bp, "ceiling_u_value_w_m2k", "sizing.room.insulation.ceiling_u_value_w_m2k", "W/(m2*K)", diagnostics),
        "vent": _value(bp, "ventilation_heat_capacity_factor_wh_m3k", "sizing.room.insulation.ventilation_heat_capacity_factor_wh_m3k", "Wh/(m3*K)", diagnostics),
        "bridge": _value(bp, "thermal_bridge_allowance_percent", "sizing.room.insulation.thermal_bridge_allowance_percent", "%", diagnostics),
        "collector_x": _value(us, "collector_point_x_mm", "sizing.coverage_request.collector_point.x_mm", "mm", diagnostics),
        "collector_y": _value(us, "collector_point_y_mm", "sizing.coverage_request.collector_point.y_mm", "mm", diagnostics),
        "spacing": _value(us, "spacing_mm", "sizing.coverage_request.spacing_mm", "mm", diagnostics),
        "offset": _value(us, "wall_offset_mm", "sizing.coverage_request.wall_offset_mm", "mm", diagnostics),
        "margin": _value(us, "design_margin_percent", "sizing.room.insulation.design_margin_percent", "%", diagnostics),
        "area_basis": _value(us, "area_basis", "engineering.area_basis", None, diagnostics),
        "out100": _value(fs, "declared_output_at_100mm_w_m2", "sizing.floor_construction.declared_output_at_100mm_w_m2", "W/m2", diagnostics),
        "out200": _value(fs, "declared_output_at_200mm_w_m2", "sizing.floor_construction.declared_output_at_200mm_w_m2", "W/m2", diagnostics),
        "basis": _value(fs, "output_basis_reference", "sizing.floor_construction.output_basis_reference", None, diagnostics),
        "kh": _value(fs, "k_h_w_m2k", "engineering.k_h_w_m2k", "W/(m2*K)", diagnostics),
        "ro": _value(fs, "r_o_m2k_w", "engineering.r_o_m2k_w", "m2*K/W", diagnostics),
        "ru": _value(fs, "r_u_m2k_w", "engineering.r_u_m2k_w", "m2*K/W", diagnostics),
        "inner": _value(pp, "inner_diameter_m", "engineering.common_circuit.inner_diameter_m", "m", diagnostics),
        "rough": _value(pp, "roughness_m", "engineering.common_circuit.roughness_m", "m", diagnostics),
        "bend": _value(pp, "embedded_losses_continuous_bends_pa", "engineering.common_circuit.embedded_losses.continuous_bends_pa", "Pa", diagnostics),
        "fit": _value(pp, "embedded_losses_pipe_fittings_pa", "engineering.common_circuit.embedded_losses.pipe_fittings_pa", "Pa", diagnostics),
        "other": _value(pp, "embedded_losses_other_fixed_pipe_path_pa", "engineering.common_circuit.embedded_losses.other_fixed_pipe_path_pa", "Pa", diagnostics),
        "fixed": _value(mp, "fixed_manifold_losses", "engineering.common_circuit.fixed_manifold_losses", None, diagnostics),
        "maxp": _value(mp, "manufacturer_max_circuit_pressure_pa", "engineering.common_circuit.manufacturer_max_circuit_pressure_pa", "Pa", diagnostics),
        "cw": _value(fl, "c_w_j_kgk", "engineering.c_w_j_kgk", "J/(kg*K)", diagnostics),
        "density": _value(fl, "density_kg_m3", "engineering.common_circuit.fluid.density_kg_m3", "kg/m3", diagnostics),
        "visc": _value(fl, "dynamic_viscosity_pa_s", "engineering.common_circuit.fluid.dynamic_viscosity_pa_s", "Pa*s", diagnostics),
        "sg": _value(fl, "specific_gravity", "engineering.common_circuit.fluid.specific_gravity", None, diagnostics),
        "surface": _value(cm, "surface_limit_w_m2", "engineering.surface_limit_w_m2", "W/m2", diagnostics),
        "control": _value(cm, "control_characteristic", "engineering.common_circuit.control", None, diagnostics),
    }
    if diagnostics:
        conflict = any(d.code in {"SOURCE_VALUE_CONFLICT", "PROJECT_OWNED_IDENTITY_MISMATCH",
                                  "PROJECT_OWNED_VALUE_INVALID"}
                       for d in diagnostics)
        return AuthoringLoadResult(
            status="INVALID" if conflict else "INCOMPLETE",
            template_digest=template.template_digest,
            diagnostics=diagnostics,
            missing_authoring_paths=sorted({d.path for d in diagnostics
                                            if d.code not in {"SOURCE_VALUE_CONFLICT", "PROJECT_OWNED_IDENTITY_MISMATCH",
                                                              "PROJECT_OWNED_VALUE_INVALID"}}),
            project_owned_values_digest=project_owned_digest,
        )
    try:
        routing_policy = default_ufh_routing_policy()
        ach = ach_item.value
        routing = UFHProjectRoutingSettings(
            collector_point=FloorHeatingPoint(x_mm=values["collector_x"], y_mm=values["collector_y"]),
            wall_offset_mm=values["offset"], spacing_mm=values["spacing"],
            requested_circuit_count=None, routing_mode=routing_policy.routing_mode,
            turn_radius_mm=routing_policy.turn_radius_mm, field_spacing_mm=None, perimeter_spacing_mm=None,
            perimeter_band_depth_mm=None, preferred_topology=None,
            installation_grid_spacing_mm=None,
            perimeter_priority_mode=routing_policy.perimeter_priority_mode,
        )
        control_payload = dict(values["control"])
        control_payload["characteristic_scope"] = CharacteristicScope(
            control_payload["characteristic_scope"]
        )
        control_payload["limit_type"] = ValveLimitType(
            control_payload["limit_type"]
        )
        control_payload["included_components"] = tuple(
            control_payload["included_components"]
        )
        common = CommonCircuitInputs(
            inner_diameter_m=values["inner"],
            roughness_m=values["rough"],
            fluid=Fluid(density_kg_m3=values["density"], dynamic_viscosity_pa_s=values["visc"],
                        specific_gravity=values["sg"]),
            embedded_losses=EmbeddedLosses(continuous_bends_pa=values["bend"],
                                           pipe_fittings_pa=values["fit"],
                                           other_fixed_pipe_path_pa=values["other"]),
            fixed_manifold_losses=tuple(FixedLoss.model_validate(v) for v in values["fixed"]),
            manufacturer_max_circuit_pressure_pa=values["maxp"],
            control=ValveCharacteristic.model_validate(control_payload),
        )
        engineering = UFHProjectEngineeringInputs(
            area_basis=values["area_basis"], k_h_w_m2k=values["kh"],
            surface_limit_w_m2=values["surface"], r_o_m2k_w=values["ro"],
            r_u_m2k_w=values["ru"], c_w_j_kgk=values["cw"], mode=mode,
            sigma_k=sigma, theta_supply_c=theta_supply, common_circuit=common,
        )
        design_conditions = UFHProjectDesignConditions(
            outdoor_design_temperature_c=values["outdoor"],
        )
        building_physics = HeatLossInsulationAssumptions(
            exterior_wall_u_value_w_m2k=values["wall_u"],
            floor_u_value_w_m2k=values["floor_u"],
            ceiling_u_value_w_m2k=values["ceiling_u"],
            air_changes_per_hour=ach,
            ventilation_heat_capacity_factor_wh_m3k=values["vent"],
            thermal_bridge_allowance_percent=values["bridge"],
            design_margin_percent=values["margin"],
            floor_boundary_temperature_c=values["floor_boundary"],
            ceiling_boundary_temperature_c=values["ceiling_boundary"],
        )
        floor_construction = FloorConstructionAssumptions(
            declared_output_at_100mm_w_m2=values["out100"],
            declared_output_at_200mm_w_m2=values["out200"],
            output_basis_reference=values["basis"],
        )
        profile_shell = UFHProjectEngineeringProfile.model_construct(
            design_conditions=design_conditions,
            building_physics=building_physics,
            floor_construction=floor_construction,
            routing_policy=routing_policy,
            routing_settings=routing,
            engineering_inputs=engineering,
            provenance={},
        )
        prov_sources = {
            "sizing.room.outdoor_design_temperature_c": dc["outdoor_design_temperature_c"],
            "sizing.room.insulation.exterior_wall_u_value_w_m2k": bp["exterior_wall_u_value_w_m2k"],
            "sizing.room.insulation.floor_u_value_w_m2k": bp["floor_u_value_w_m2k"],
            "sizing.room.insulation.ceiling_u_value_w_m2k": bp["ceiling_u_value_w_m2k"],
            "sizing.room.insulation.air_changes_per_hour": ach_item,
            "sizing.room.insulation.ventilation_heat_capacity_factor_wh_m3k": bp["ventilation_heat_capacity_factor_wh_m3k"],
            "sizing.room.insulation.thermal_bridge_allowance_percent": bp["thermal_bridge_allowance_percent"],
            "sizing.room.insulation.design_margin_percent": us["design_margin_percent"],
            "sizing.room.insulation.floor_boundary_temperature_c": dc["floor_boundary_temperature_c"],
            "sizing.room.insulation.ceiling_boundary_temperature_c": dc["ceiling_boundary_temperature_c"],
            "sizing.floor_construction.declared_output_at_100mm_w_m2": fs["declared_output_at_100mm_w_m2"],
            "sizing.floor_construction.declared_output_at_200mm_w_m2": fs["declared_output_at_200mm_w_m2"],
            "sizing.floor_construction.output_basis_reference": fs["output_basis_reference"],
            "sizing.coverage_request.collector_point.x_mm": us["collector_point_x_mm"],
            "sizing.coverage_request.collector_point.y_mm": us["collector_point_y_mm"],
            "sizing.coverage_request.wall_offset_mm": us["wall_offset_mm"],
            "sizing.coverage_request.spacing_mm": us["spacing_mm"],
            "sizing.coverage_request.requested_circuit_count": _routing_policy_value("requested_circuit_count_semantics", None, "none"),
            "sizing.coverage_request.routing_mode": _routing_policy_value("routing_mode", routing_policy.routing_mode, "none"),
            "sizing.coverage_request.turn_radius_mm": _routing_policy_value("turn_radius_mm", routing_policy.turn_radius_mm, "mm"),
            "sizing.coverage_request.field_spacing_mm": _routing_policy_value("field_spacing_mm", None, "none"),
            "sizing.coverage_request.perimeter_spacing_mm": _routing_policy_value("perimeter_spacing_mm", None, "none"),
            "sizing.coverage_request.perimeter_band_depth_mm": _routing_policy_value("perimeter_band_depth_mm", None, "none"),
            "sizing.coverage_request.preferred_topology": _routing_policy_value("preferred_topology", None, "none"),
            "sizing.coverage_request.installation_grid_spacing_mm": _routing_policy_value("installation_grid_spacing_mm", None, "none"),
            "sizing.coverage_request.perimeter_priority_mode": _routing_policy_value("perimeter_priority_mode", routing_policy.perimeter_priority_mode, "none"),
            "engineering.area_basis": us["area_basis"],
            "engineering.k_h_w_m2k": fs["k_h_w_m2k"],
            "engineering.surface_limit_w_m2": cm["surface_limit_w_m2"],
            "engineering.r_o_m2k_w": fs["r_o_m2k_w"],
            "engineering.r_u_m2k_w": fs["r_u_m2k_w"],
            "engineering.c_w_j_kgk": fl["c_w_j_kgk"],
            "engineering.mode": us["mode"],
            "engineering.common_circuit.inner_diameter_m": pp["inner_diameter_m"],
            "engineering.common_circuit.roughness_m": pp["roughness_m"],
            "engineering.common_circuit.fluid.density_kg_m3": fl["density_kg_m3"],
            "engineering.common_circuit.fluid.dynamic_viscosity_pa_s": fl["dynamic_viscosity_pa_s"],
            "engineering.common_circuit.fluid.specific_gravity": fl["specific_gravity"],
            "engineering.common_circuit.embedded_losses.continuous_bends_pa": pp["embedded_losses_continuous_bends_pa"],
            "engineering.common_circuit.embedded_losses.pipe_fittings_pa": pp["embedded_losses_pipe_fittings_pa"],
            "engineering.common_circuit.embedded_losses.other_fixed_pipe_path_pa": pp["embedded_losses_other_fixed_pipe_path_pa"],
            "engineering.common_circuit.fixed_manifold_losses": mp["fixed_manifold_losses"],
            "engineering.common_circuit.manufacturer_max_circuit_pressure_pa": mp["manufacturer_max_circuit_pressure_pa"],
            "engineering.common_circuit.control": cm["control_characteristic"],
        }
        if mode == "solve_supply":
            prov_sources["engineering.sigma_k"] = dc["sigma_k"]
        else:
            prov_sources["engineering.theta_supply_c"] = dc["theta_supply_c"]
        parent_provenance = {path: _prov(item, path) for path, item in prov_sources.items()}

        def leaves(value: Any, prefix: str) -> list[str]:
            if isinstance(value, dict) and value:
                return [leaf for key, child in value.items()
                        for leaf in leaves(child, f"{prefix}.{key}")]
            if isinstance(value, (list, tuple)) and value:
                return [leaf for index, child in enumerate(value)
                        for leaf in leaves(child, f"{prefix}[{index}]")]
            return [prefix]

        expected_paths = leaves(profile_shell.sizing_fragment(), "sizing")
        expected_paths.extend(leaves(profile_shell.engineering_fragment(), "engineering"))
        provenance: dict[str, ProfileValueProvenance] = {}
        for path in expected_paths:
            source = parent_provenance.get(path)
            if source is None:
                parents = [key for key in parent_provenance
                           if path.startswith(f"{key}.") or path.startswith(f"{key}[")]
                if parents:
                    source = parent_provenance[max(parents, key=len)]
            if source is not None:
                provenance[path] = source
        profile = UFHProjectEngineeringProfile.model_validate({
            "design_conditions": design_conditions.model_dump(mode="python"),
            "building_physics": building_physics.model_dump(mode="python"),
            "floor_construction": floor_construction.model_dump(mode="python"),
            "routing_policy": routing_policy.model_dump(mode="python"),
            "routing_settings": routing.model_dump(mode="python"),
            "engineering_inputs": engineering.model_dump(mode="python"),
            "provenance": {key: value.model_dump(mode="python")
                           for key, value in provenance.items()},
        })
    except Exception as error:
        return AuthoringLoadResult(status="INVALID", template_digest=template.template_digest,
                                   diagnostics=[AuthoringDiagnostic(
                                       code="AUTHORING_PROFILE_INVALID", path="$",
                                       message=str(error)[:512])])
    return AuthoringLoadResult(status="READY", template_digest=template.template_digest,
                               profile=profile,
                               project_owned_values_digest=project_owned_digest)


def synthetic_complete_authoring_payload() -> dict[str, Any]:
    payload = test01_authoring_template_payload()

    def v(value: Any, unit: str, source_field: str = "fixture"):
        return {
            "status": "EXPLICIT_VALUE",
            "value": value,
            "unit": unit,
            "provenance": {
                "source_type": "test_only",
                "source_reference": "tests/test_ufh_project_engineering_profile_authoring.py#synthetic",
                "source_field": source_field,
                "author_or_confirmation": "test fixture",
                "transformation": "direct test-only value",
                "units": unit,
            },
        }

    payload["design_conditions"] = {
        "outdoor_design_temperature_c": v(-26.0, "degC"),
        "floor_boundary_temperature_c": v(5.0, "degC"),
        "ceiling_boundary_temperature_c": v(15.0, "degC"),
        "sigma_k": v(5.0, "K"),
        "theta_supply_c": {"status": "UNSET"},
    }
    payload["building_physics"] = {
        "exterior_wall_u_value_w_m2k": v(0.3, "W/(m2*K)"),
        "floor_u_value_w_m2k": v(0.2, "W/(m2*K)"),
        "ceiling_u_value_w_m2k": v(0.15, "W/(m2*K)"),
        "air_changes_per_hour": v(0.4, "1/h"),
        "ventilation_heat_capacity_factor_wh_m3k": v(0.33, "Wh/(m3*K)"),
        "thermal_bridge_allowance_percent": v(5.0, "%"),
    }
    payload["ufh_design_settings"] = {
        "collector_point_x_mm": v(500, "mm"),
        "collector_point_y_mm": v(500, "mm"),
        "spacing_mm": v(200, "mm"),
        "wall_offset_mm": v(100, "mm"),
        "design_margin_percent": v(10.0, "%"),
        "area_basis": v("ACKNOWLEDGED_COVERAGE_ESTIMATE", "none"),
        "mode": v("solve_supply", "none"),
    }
    payload["floor_system_product"] = {
        "floor_system_product_id": v("test-floor-system", "none"),
        "declared_output_at_100mm_w_m2": v(120.0, "W/m2"),
        "declared_output_at_200mm_w_m2": v(80.0, "W/m2"),
        "output_basis_reference": v("test output table", "none"),
        "k_h_w_m2k": v(10.8, "W/(m2*K)"),
        "r_o_m2k_w": v(0.0, "m2*K/W"),
        "r_u_m2k_w": v(0.1, "m2*K/W"),
    }
    payload["pipe_product"] = {
        "pipe_product_id": v("test-pipe", "none"),
        "inner_diameter_m": v(0.012, "m"),
        "roughness_m": v(0.000007, "m"),
        "embedded_losses_continuous_bends_pa": v(0.0, "Pa"),
        "embedded_losses_pipe_fittings_pa": v(0.0, "Pa"),
        "embedded_losses_other_fixed_pipe_path_pa": v(0.0, "Pa"),
    }
    payload["manifold_product"] = {
        "manifold_product_id": v("test-manifold", "none"),
        "fixed_manifold_losses": v([{"component_id": "manifold", "pressure_pa": 0.0}], "none"),
        "manufacturer_max_circuit_pressure_pa": v(40000.0, "Pa"),
    }
    payload["fluid_definition"] = {
        "fluid_definition_id": v("water-test", "none"),
        "c_w_j_kgk": v(kernel.WATER_CP_J_KG_K, "J/(kg*K)"),
        "density_kg_m3": v(998.0, "kg/m3"),
        "dynamic_viscosity_pa_s": v(0.001, "Pa*s"),
        "specific_gravity": v(1.0, "none"),
    }
    payload["control_model"] = {
        "surface_limit_w_m2": v(100.0, "W/m2"),
        "control_characteristic": v({
            "manufacturer": "Synthetic",
            "product_family": "Regression only",
            "product_version": "1",
            "document_reference": "test",
            "document_revision": "1",
            "characteristic_scope": CharacteristicScope.SINGLE_CONTROL_VALVE.value,
            "included_components": ["control"],
            "kv_min_m3h": 0.05,
            "kv_max_m3h": 1.0,
            "setting_min": 1.0,
            "setting_max": 5.0,
            "limit_type": ValveLimitType.PUBLISHED_CURVE_LIMIT.value,
            "source_confidence": "test",
        }, "none"),
    }
    payload["explicit_confirmations"] = {
        "exclusion_zones": {
            "status": "EXPLICIT_EMPTY", "value": [],
            "provenance": v([], "none")["provenance"],
        },
        "openings": {
            "status": "EXPLICIT_EMPTY", "value": [],
            "provenance": v([], "none")["provenance"],
        },
    }
    return payload


__all__ = [
    "AuthoringDiagnostic",
    "AuthoringLoadResult",
    "AuthoringProvenance",
    "AuthoringStatus",
    "AuthoredValue",
    "FIELD_AUTHORING_MAP",
    "InputAcquisitionType",
    "Test01UfhEngineeringAuthoringTemplate",
    "load_ufh_project_engineering_authoring_template",
    "synthetic_complete_authoring_payload",
    "test01_authoring_template_payload",
]
