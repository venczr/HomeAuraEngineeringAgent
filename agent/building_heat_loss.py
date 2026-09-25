"""Deterministic SP 60 room transmission calculation (no project I/O).

The module deliberately calculates transmission only. Inputs are already
resolved, sourced values supplied by an application adapter; this module does
not read project files, run resolvers, or call the UFH sizing/routing pipeline.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from typing import Literal, TYPE_CHECKING

from pydantic import Field, ValidationError, field_validator, model_validator

from agent.project_models import StrictProjectModel
from agent.sp60_normative_method import SP60_CANONICAL_REVISION, SP60_CANONICAL_REVISION_DIGEST
from agent.ufh_envelope_construction_resolver import EnvelopeConstructionAssembly
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance

if TYPE_CHECKING:
    from agent.ufh_project_adapter import ProjectUfhAdapterResult
    from agent.ufh_questionnaire_resolver_contract import ResolverRequest, ResolverResult


def _decimal(value):
    if value is None:
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("FINITE_DECIMAL_REQUIRED") from exc
    if not result.is_finite():
        raise ValueError("FINITE_DECIMAL_REQUIRED")
    return result


def _digest(value) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


SP60_METHOD_PACKAGE = {
    "canonical_revision": SP60_CANONICAL_REVISION,
    "canonical_revision_digest": SP60_CANONICAL_REVISION_DIGEST,
    "consolidated_amendments": SP60_CANONICAL_REVISION["consolidated_amendments"],
    "amendment_6_effective_from": SP60_CANONICAL_REVISION["amendment_6"]["effective_date"],
    "verified_on": "2026-09-15",
    "climate_dependency": "SP 131.13330.2025",
    "extract_authority": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
    "official_identity_authority": "NORMATIVE_DOCUMENT_IDENTITY_AUTHORITY",
    "text_carrier_role": "TEXT_CARRIER_ONLY",
    "consolidated_text_revision": SP60_CANONICAL_REVISION["consolidated_text_revision"],
    "a4_formula_sha256": "0affc957f4cec3d1a31408867296648079aa6dade35edb34a416a2fc0a6ba0f3",
    "visually_verified_equation_sha256": {"A.2": "c56f98c8d0c5e9907faec20b601a769eeb54da9f73aa6ee6af7a33de5543133a", "A.3": "f96a9f53ac377e7a95c85e07a0db5d79e46063e591eb768dafb91067e3915281"},
    "symbol_units": {"A": "m2", "K": "W/(m2*K)", "U": "W/(m2*K)", "L": "m", "psi": "W/(m*K)", "N": "count", "chi": "W/K", "delta_t": "K", "Q": "W"},
    "internal_partition_omission": {"clause": "A.2 note 1; 6.2.2", "maximum_absolute_delta_c": "4"},
    "formula_records": [
        {
            "formula_id": "SP60_A2_V2020_AMD1_6",
            "semantics": "Q_tr,n=(t_v-t_n)*sum(A_i*K_i); K_i=1/R0_i_reduced",
            "source_clause": "Appendix A, A.2, formulae A.2 and A.4",
            "source_reference": "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i.html",
            "visual_formula_references": [
                "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_428224.png",
                "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_746667.png",
            ],
        },
        {
            "formula_id": "SP60_A3_V2020_AMD1_6",
            "semantics": "Q_tr,n=(t_v-t_n)*(sum(A_i*U_i)+sum(L_j*psi_j)+sum(N_k*chi_k))",
            "source_clause": "Appendix A, A.2, formula A.3",
            "source_reference": "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i.html",
            "visual_formula_reference": "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_681437.png",
        },
    ],
    "source_identity": "Official Rosstandart metadata for document status/amendments; consolidated published text and formula images are text carriers, not claimed official publisher copies.",
    "appendix_a_method_identity": "SP60_APP_A_A2_A3_A4_CONSOLIDATED_AMENDMENTS_1_6",
}
SP60_METHOD_DIGEST = _digest(SP60_METHOD_PACKAGE)


BoundaryKind = Literal[
    "OUTDOOR_AIR", "HEATED_INTERIOR_SPACE", "UNHEATED_INTERIOR_SPACE",
    "GROUND", "VENTILATED_VOID", "UNKNOWN_PROJECT_SPECIFIC",
]
CalculationMode = Literal[
    "A2_REDUCED_FRAGMENT", "PLANAR_TRANSMISSION_ONLY", "DETAILED_TRANSMISSION",
]


class ThermalBridge(StrictProjectModel):
    bridge_id: str = Field(min_length=1, max_length=160)
    boundary_id: str = Field(min_length=1, max_length=160)
    kind: Literal["LINEAR", "POINT"]
    coefficient: Decimal
    quantity: Decimal
    coefficient_units: Literal["W/(m*K)", "W/K"]
    quantity_units: Literal["m", "count"]
    provenance: AuthoringProvenance
    quantity_provenance: AuthoringProvenance

    @field_validator("coefficient", "quantity", mode="before")
    @classmethod
    def decimal_fields(cls, value):
        return _decimal(value)

    @model_validator(mode="after")
    def coherent_units_and_values(self):
        expected = ("W/(m*K)", "m") if self.kind == "LINEAR" else ("W/K", "count")
        if (self.coefficient_units, self.quantity_units) != expected:
            raise ValueError("THERMAL_BRIDGE_UNIT_MISMATCH")
        if self.quantity <= 0:
            raise ValueError("THERMAL_BRIDGE_QUANTITY_MUST_BE_POSITIVE")
        if self.kind == "POINT" and self.quantity != self.quantity.to_integral_value():
            raise ValueError("POINT_BRIDGE_COUNT_MUST_BE_INTEGER")
        if self.provenance.units != self.coefficient_units:
            raise ValueError("THERMAL_BRIDGE_PROVENANCE_UNIT_MISMATCH")
        if self.quantity_provenance.units != self.quantity_units:
            raise ValueError("THERMAL_BRIDGE_QUANTITY_UNIT_MISMATCH")
        return self


class TransmissionBoundaryInput(StrictProjectModel):
    boundary_id: str = Field(min_length=1, max_length=160)
    room_id: str = Field(min_length=1, max_length=128)
    boundary_kind: BoundaryKind
    fragment_kind: Literal["OPAQUE", "WINDOW", "DOOR", "OTHER_OPENING"] = "OPAQUE"
    geometry_reference: str = Field(min_length=1, max_length=512)
    geometry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    area_m2: Decimal | None = None
    area_provenance: AuthoringProvenance | None = None
    construction: EnvelopeConstructionAssembly | None = None
    u_value_w_m2k: Decimal | None = None
    u_value_role: Literal["REDUCED_FRAGMENT", "HOMOGENEOUS_COMPONENT"] | None = None
    u_value_provenance: AuthoringProvenance | None = None
    inside_temperature_c: Decimal | None = None
    inside_temperature_provenance: AuthoringProvenance | None = None
    opposite_temperature_c: Decimal | None = None
    opposite_temperature_provenance: AuthoringProvenance | None = None
    internal_partition: bool = False
    parent_boundary_id: str | None = None
    diagnostics: list[str] = Field(default_factory=list)

    @field_validator("area_m2", "u_value_w_m2k", "inside_temperature_c",
                     "opposite_temperature_c", mode="before")
    @classmethod
    def decimal_fields(cls, value):
        return _decimal(value)

    @model_validator(mode="after")
    def paired_values_and_semantics(self):
        for value, provenance, unit, label in (
            (self.area_m2, self.area_provenance, "m2", "AREA"),
            (self.u_value_w_m2k, self.u_value_provenance, "W/(m2*K)", "U_VALUE"),
            (self.inside_temperature_c, self.inside_temperature_provenance, "°C", "INSIDE_TEMPERATURE"),
            (self.opposite_temperature_c, self.opposite_temperature_provenance, "°C", "OPPOSITE_TEMPERATURE"),
        ):
            if (value is None) != (provenance is None):
                raise ValueError(f"{label}_AND_PROVENANCE_MUST_BE_PAIRED")
            if provenance is not None and provenance.units != unit:
                raise ValueError(f"{label}_UNIT_INVALID")
        if self.area_m2 is not None and self.area_m2 <= 0:
            raise ValueError("BOUNDARY_AREA_MUST_BE_POSITIVE")
        if self.u_value_w_m2k is not None and self.u_value_w_m2k <= 0:
            raise ValueError("U_VALUE_MUST_BE_POSITIVE")
        if self.internal_partition and self.boundary_kind not in {"HEATED_INTERIOR_SPACE", "UNHEATED_INTERIOR_SPACE"}:
            raise ValueError("INTERNAL_PARTITION_SCOPE_INVALID")
        if self.boundary_kind == "GROUND" and self.opposite_temperature_c is not None:
            raise ValueError("GROUND_OPPOSITE_TEMPERATURE_CANNOT_ENABLE_SIMPLE_UA_DELTA_T")
        if self.parent_boundary_id is not None and self.fragment_kind == "OPAQUE":
            raise ValueError("PARENT_LINKED_FRAGMENT_MUST_BE_AN_OPENING")
        if self.parent_boundary_id is None and self.fragment_kind != "OPAQUE":
            raise ValueError("OPENING_MUST_REFERENCE_PARENT_BOUNDARY")
        if self.parent_boundary_id is not None and self.boundary_kind not in {"OUTDOOR_AIR", "HEATED_INTERIOR_SPACE", "UNHEATED_INTERIOR_SPACE", "VENTILATED_VOID"}:
            raise ValueError("OPENING_REQUIRES_NON_GROUND_THERMAL_BOUNDARY")
        if self.u_value_w_m2k is not None and self.u_value_role is None and self.construction is None:
            raise ValueError("U_VALUE_ROLE_REQUIRED")
        if self.u_value_w_m2k is None and self.u_value_role is not None and self.construction is None:
            raise ValueError("U_VALUE_ROLE_WITHOUT_VALUE")
        if self.construction is not None:
            if self.u_value_w_m2k is not None and self.u_value_w_m2k != self.construction.u_value_w_m2k:
                raise ValueError("CONSTRUCTION_U_VALUE_CONFLICT")
            if self.construction.u_value_w_m2k is not None and not self.construction.provenance_references:
                raise ValueError("CONSTRUCTION_PROVENANCE_REQUIRED")
            if self.construction.resistance_scope == "HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE" and self.u_value_role == "REDUCED_FRAGMENT":
                raise ValueError("HOMOGENEOUS_CONSTRUCTION_CANNOT_BE_RELABELLED_REDUCED")
        return self


class BuildingHeatLossInput(StrictProjectModel):
    project_id: str = Field(min_length=1, max_length=128)
    building_id: str = Field(min_length=1, max_length=128)
    level_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    project_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    normative_method_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_mode: CalculationMode
    boundaries: list[TransmissionBoundaryInput]
    boundary_inventory: Literal["UNRESOLVED", "COMPLETE"]
    boundary_inventory_provenance: AuthoringProvenance | None = None
    thermal_bridges: list[ThermalBridge] = Field(default_factory=list)
    thermal_bridge_inventory: Literal["UNRESOLVED", "COMPLETE"]
    thermal_bridge_inventory_provenance: AuthoringProvenance | None = None

    @model_validator(mode="after")
    def validate_inventory_and_identity(self):
        if self.normative_method_digest != SP60_METHOD_DIGEST:
            raise ValueError("SP60_METHOD_REVISION_UNSUPPORTED")
        if self.calculation_mode == "A2_REDUCED_FRAGMENT" and self.thermal_bridges:
            raise ValueError("REDUCED_U_AND_SEPARATE_BRIDGES_WOULD_DOUBLE_COUNT")
        physical_paths = [(b.geometry_reference, b.geometry_digest) for b in self.boundaries]
        if len(set(physical_paths)) != len(physical_paths):
            raise ValueError("DUPLICATE_PHYSICAL_BOUNDARY_PATH")
        if len({item.boundary_id for item in self.boundaries}) != len(self.boundaries):
            raise ValueError("DUPLICATE_BOUNDARY_ID")
        if any(item.room_id != self.room_id for item in self.boundaries):
            raise ValueError("BOUNDARY_ROOM_ID_MISMATCH")
        if len({item.bridge_id for item in self.thermal_bridges}) != len(self.thermal_bridges):
            raise ValueError("DUPLICATE_THERMAL_BRIDGE_ID")
        if self.thermal_bridge_inventory == "COMPLETE":
            if self.thermal_bridge_inventory_provenance is None:
                raise ValueError("THERMAL_BRIDGE_INVENTORY_PROVENANCE_REQUIRED")
        elif self.thermal_bridge_inventory_provenance is not None:
            raise ValueError("UNRESOLVED_BRIDGE_INVENTORY_CANNOT_CLAIM_PROVENANCE")
        if self.boundary_inventory == "COMPLETE":
            if self.boundary_inventory_provenance is None:
                raise ValueError("BOUNDARY_INVENTORY_PROVENANCE_REQUIRED")
        elif self.boundary_inventory_provenance is not None:
            raise ValueError("UNRESOLVED_BOUNDARY_INVENTORY_CANNOT_CLAIM_PROVENANCE")
        if any(item.boundary_id not in {boundary.boundary_id for boundary in self.boundaries}
               for item in self.thermal_bridges):
            raise ValueError("THERMAL_BRIDGE_BOUNDARY_NOT_FOUND")
        self._validate_openings()
        return self

    def _validate_openings(self):
        ids = [item.boundary_id for item in self.boundaries]
        children: dict[str, list[TransmissionBoundaryInput]] = {}
        for boundary in self.boundaries:
            if boundary.parent_boundary_id:
                if boundary.parent_boundary_id not in ids:
                    raise ValueError("OPENING_PARENT_BOUNDARY_NOT_FOUND")
                if boundary.parent_boundary_id == boundary.boundary_id:
                    raise ValueError("OPENING_CANNOT_PARENT_ITSELF")
                children.setdefault(boundary.parent_boundary_id, []).append(boundary)
        for parent_id, openings in children.items():
            parent = next(item for item in self.boundaries if item.boundary_id == parent_id)
            if parent.fragment_kind != "OPAQUE":
                raise ValueError("OPENING_PARENT_MUST_BE_OPAQUE_FRAGMENT")
            if parent.parent_boundary_id is not None:
                raise ValueError("OPENING_PARENT_MUST_BE_GROSS_WALL_FRAGMENT")
            if parent.area_m2 is None:
                raise ValueError("GROSS_PARENT_AREA_REQUIRED")
            if any(item.boundary_kind != parent.boundary_kind for item in openings):
                raise ValueError("OPENING_BOUNDARY_KIND_MISMATCH")
            opening_area = sum((item.area_m2 or Decimal(0) for item in openings), Decimal(0))
            if any(item.area_m2 is None for item in openings):
                raise ValueError("OPENING_AREA_REQUIRED")
            if opening_area > parent.area_m2:
                raise ValueError("OPENING_AREAS_EXCEED_GROSS_AREA")
            for opening in openings:
                for field in ("inside_temperature_c", "opposite_temperature_c"):
                    child_value = getattr(opening, field)
                    parent_value = getattr(parent, field)
                    if child_value is not None and parent_value is not None and child_value != parent_value:
                        raise ValueError("OPENING_BOUNDARY_TEMPERATURE_MISMATCH")


class ProjectTransmissionSource(StrictProjectModel):
    """Already-resolved project/profile values; no source access occurs here."""
    project_id: str
    building_id: str
    level_id: str
    room_id: str
    project_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    indoor_design_temperature_c: Decimal | None = None
    indoor_temperature_provenance: AuthoringProvenance | None = None
    climate_outdoor_design_temperature_c: Decimal | None = None
    climate_temperature_provenance: AuthoringProvenance | None = None
    boundaries: list[TransmissionBoundaryInput]
    boundary_inventory: Literal["UNRESOLVED", "COMPLETE"]
    boundary_inventory_provenance: AuthoringProvenance | None = None
    thermal_bridges: list[ThermalBridge] = Field(default_factory=list)
    thermal_bridge_inventory: Literal["UNRESOLVED", "COMPLETE"]
    thermal_bridge_inventory_provenance: AuthoringProvenance | None = None

    @field_validator("indoor_design_temperature_c", "climate_outdoor_design_temperature_c", mode="before")
    @classmethod
    def decimal_fields(cls, value):
        return _decimal(value)

    @model_validator(mode="after")
    def provenance_pairs(self):
        if (self.indoor_design_temperature_c is None) != (self.indoor_temperature_provenance is None):
            raise ValueError("INDOOR_TEMPERATURE_AND_PROVENANCE_MUST_BE_PAIRED")
        if self.indoor_temperature_provenance and self.indoor_temperature_provenance.units != "°C":
            raise ValueError("INDOOR_TEMPERATURE_UNIT_INVALID")
        if (self.climate_outdoor_design_temperature_c is None) != (self.climate_temperature_provenance is None):
            raise ValueError("CLIMATE_TEMPERATURE_AND_PROVENANCE_MUST_BE_PAIRED")
        if self.climate_temperature_provenance and self.climate_temperature_provenance.units != "°C":
            raise ValueError("CLIMATE_TEMPERATURE_UNIT_INVALID")
        if self.boundary_inventory == "COMPLETE":
            if self.boundary_inventory_provenance is None:
                raise ValueError("BOUNDARY_INVENTORY_PROVENANCE_REQUIRED")
        elif self.boundary_inventory_provenance is not None:
            raise ValueError("UNRESOLVED_BOUNDARY_INVENTORY_CANNOT_CLAIM_PROVENANCE")
        return self


class TransmissionBoundaryResult(StrictProjectModel):
    boundary_id: str
    boundary_kind: BoundaryKind
    gross_area_m2: Decimal | None
    opening_area_m2: Decimal
    net_opaque_area_m2: Decimal | None
    u_value_w_m2k: Decimal | None
    inside_temperature_c: Decimal | None
    opposite_temperature_c: Decimal | None
    delta_t_c: Decimal | None
    planar_heat_flow_w: Decimal | None
    linear_heat_flow_w: Decimal | None
    point_heat_flow_w: Decimal | None
    total_heat_flow_w: Decimal | None
    omitted_by_internal_partition_rule: bool
    diagnostics: list[str]
    provenance_digest: str


class RoomTransmissionHeatLossResult(StrictProjectModel):
    project_id: str
    building_id: str
    level_id: str
    room_id: str
    normative_method_digest: str
    calculation_mode: CalculationMode
    assessment_level: Literal["PLANAR_TRANSMISSION_ONLY", "DETAILED_TRANSMISSION"]
    boundary_results: list[TransmissionBoundaryResult]
    planar_total_w: Decimal | None
    linear_total_w: Decimal | None
    point_total_w: Decimal | None
    room_transmission_heat_loss_w: Decimal | None
    total_design_heating_load_w: None = None
    completeness_status: Literal[
        "COMPLETE_DETAILED", "PLANAR_ONLY", "INCOMPLETE_BOUNDARY_DATA",
        "GROUND_MODEL_REQUIRED", "ADJACENT_TEMPERATURE_REQUIRED",
        "THERMAL_BRIDGE_DATA_REQUIRED", "INVALID_BOUNDARY_DATA",
    ]
    unresolved_dependencies: list[str]
    ventilation_status: Literal["VENTILATION_HEAT_LOSS_NOT_EVALUATED_V1"] = "VENTILATION_HEAT_LOSS_NOT_EVALUATED_V1"
    infiltration_status: Literal["INFILTRATION_NOT_EVALUATED_V1"] = "INFILTRATION_NOT_EVALUATED_V1"
    internal_gains_status: Literal["INTERNAL_GAINS_NOT_EVALUATED_V1"] = "INTERNAL_GAINS_NOT_EVALUATED_V1"
    material_equipment_warming_status: Literal["MATERIAL_EQUIPMENT_WARMING_NOT_EVALUATED_V1"] = "MATERIAL_EQUIPMENT_WARMING_NOT_EVALUATED_V1"
    calculation_digest: str


def build_building_heat_loss_input(
    source: ProjectTransmissionSource,
    *,
    calculation_mode: CalculationMode,
) -> BuildingHeatLossInput:
    """Apply only explicit project/climate inputs to boundary records."""
    mapped = []
    for original in source.boundaries:
        updates = {}
        if original.inside_temperature_c is not None and source.indoor_design_temperature_c is not None and original.inside_temperature_c != source.indoor_design_temperature_c:
            raise ValueError("SOURCE_VALUE_CONFLICT:indoor_design_temperature")
        if original.boundary_kind == "OUTDOOR_AIR" and original.opposite_temperature_c is not None and source.climate_outdoor_design_temperature_c is not None and original.opposite_temperature_c != source.climate_outdoor_design_temperature_c:
            raise ValueError("SOURCE_VALUE_CONFLICT:climate_design_temperature")
        if original.inside_temperature_c is None and source.indoor_design_temperature_c is not None:
            updates["inside_temperature_c"] = source.indoor_design_temperature_c
            updates["inside_temperature_provenance"] = source.indoor_temperature_provenance
        item = original
        if original.boundary_kind == "OUTDOOR_AIR" and original.opposite_temperature_c is None:
            if source.climate_outdoor_design_temperature_c is not None:
                updates["opposite_temperature_c"] = source.climate_outdoor_design_temperature_c
                updates["opposite_temperature_provenance"] = source.climate_temperature_provenance
        if updates:
            item = TransmissionBoundaryInput.model_validate({**original.model_dump(), **updates})
        mapped.append(item)
    return BuildingHeatLossInput(
        project_id=source.project_id, building_id=source.building_id,
        level_id=source.level_id, room_id=source.room_id,
        project_revision_digest=source.project_revision_digest,
        normative_method_digest=SP60_METHOD_DIGEST,
        calculation_mode=calculation_mode, boundaries=mapped,
        boundary_inventory=source.boundary_inventory,
        boundary_inventory_provenance=source.boundary_inventory_provenance,
        thermal_bridges=source.thermal_bridges,
        thermal_bridge_inventory=source.thermal_bridge_inventory,
        thermal_bridge_inventory_provenance=source.thermal_bridge_inventory_provenance,
    )


def project_transmission_source_from_adapter(
    adapter_result: ProjectUfhAdapterResult,
    *,
    boundaries: list[TransmissionBoundaryInput],
    climate_result: ResolverResult | None = None,
    climate_request: ResolverRequest | None = None,
    thermal_bridges: list[ThermalBridge] | None = None,
    bridge_inventory: Literal["UNRESOLVED", "COMPLETE"] = "UNRESOLVED",
    bridge_inventory_provenance: AuthoringProvenance | None = None,
    boundary_inventory: Literal["UNRESOLVED", "COMPLETE"] = "UNRESOLVED",
    boundary_inventory_provenance: AuthoringProvenance | None = None,
) -> ProjectTransmissionSource:
    """Map existing adapter/climate outputs to this core's in-memory contract.

    This function performs no source reads. Room temperature is taken only
    from the adapter's canonical `room.indoor_temperature_c` mapping; the
    outside temperature is taken only from a resolved CLIMATE_RESOLVER result.
    """
    if adapter_result.status == "INVALID":
        raise ValueError("PROJECT_SOURCE_INVALID")
    if not adapter_result.building_id or not adapter_result.level_id:
        raise ValueError("PROJECT_BUILDING_LEVEL_IDENTITY_REQUIRED")
    if not adapter_result.source_digest:
        raise ValueError("PROJECT_SOURCE_REVISION_REQUIRED")

    indoor_value = None
    indoor_provenance = None
    mapped = [item for item in adapter_result.mapped_fields
              if item.target_path == "room.indoor_temperature_c"]
    if len(mapped) > 1:
        raise ValueError("DUPLICATE_PROJECT_INDOOR_TEMPERATURE")
    if mapped:
        item = mapped[0]
        try:
            indoor_value = Decimal(str(item.value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("PROJECT_INDOOR_TEMPERATURE_INVALID") from exc
        kind = item.provenance.source_kind
        if kind not in {"room_extraction", "canonical_project_domain"}:
            raise ValueError("PROJECT_INDOOR_TEMPERATURE_SOURCE_NOT_AUTHORITATIVE")
        indoor_provenance = AuthoringProvenance(
            source_type="project_data", project_source_kind=kind,
            source_reference=item.provenance.source_file,
            source_sha256=item.provenance.source_sha256,
            source_field=item.provenance.source_path,
            transformation=(item.provenance.transformation or "identity mapping") + "; canonical unit °C",
            units="°C",
        )

    outdoor_value = None
    outdoor_provenance = None
    if climate_result is not None:
        if climate_result.status != "RESOLVED":
            # Unresolved climate must not be turned into a value or a generic error.
            pass
        else:
            if climate_request is None:
                raise ValueError("CLIMATE_REQUEST_BINDING_REQUIRED")
            if (climate_request.resolver_type != "CLIMATE_RESOLVER"
                    or climate_request.project_id != adapter_result.project_id
                    or climate_request.room_id != adapter_result.room_id
                    or climate_request.project_source_digest not in {adapter_result.source_digest, adapter_result.adapter_digest}
                    or climate_request.dependency_digest != climate_result.dependency_digest
                    or climate_request.resolver_request_id != climate_result.resolver_request_id):
                raise ValueError("STALE_OR_MISMATCHED_CLIMATE_BINDING")
            climate_matches = [value for value in climate_result.values
                               if value.target_authoring_field == "design_conditions.outdoor_design_temperature_c"]
            if len(climate_matches) != 1:
                raise ValueError("CLIMATE_RESULT_TARGET_INVALID")
            resolved = climate_matches[0]
            authored = resolved.authored_value
            if resolved.authority_class not in {"PROJECT_APPROVED_NORMATIVE_EXTRACT", "NORMATIVE_AUTHORITATIVE"}:
                raise ValueError("CLIMATE_AUTHORITY_NOT_BINDABLE")
            if authored.provenance is None or authored.value is None or authored.unit not in {"degC", "°C"}:
                raise ValueError("CLIMATE_VALUE_PROVENANCE_OR_UNIT_REQUIRED")
            try:
                outdoor_value = Decimal(str(authored.value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("CLIMATE_TEMPERATURE_INVALID") from exc
            outdoor_provenance = authored.provenance.model_copy(update={
                "units": "°C",
                "transformation": authored.provenance.transformation + "; degC/°C unit identity normalization (scale 1, offset 0)",
            })

    return ProjectTransmissionSource(
        project_id=adapter_result.project_id,
        building_id=adapter_result.building_id,
        level_id=adapter_result.level_id,
        room_id=adapter_result.room_id,
        project_revision_digest=adapter_result.source_digest,
        indoor_design_temperature_c=indoor_value,
        indoor_temperature_provenance=indoor_provenance,
        climate_outdoor_design_temperature_c=outdoor_value,
        climate_temperature_provenance=outdoor_provenance,
        boundaries=boundaries,
        boundary_inventory=boundary_inventory,
        boundary_inventory_provenance=boundary_inventory_provenance,
        thermal_bridges=thermal_bridges or [],
        thermal_bridge_inventory=bridge_inventory,
        thermal_bridge_inventory_provenance=bridge_inventory_provenance,
    )


class ProjectHeatLossAdapterResult(StrictProjectModel):
    status: Literal["INPUT_PREPARED", "INCOMPLETE", "INVALID"]
    input_data: BuildingHeatLossInput | None = None
    diagnostics: list[str] = Field(default_factory=list)


def adapt_project_heat_loss(
    adapter_result: ProjectUfhAdapterResult, *,
    boundaries: list[TransmissionBoundaryInput], calculation_mode: CalculationMode,
    climate_result: ResolverResult | None = None, climate_request: ResolverRequest | None = None,
    thermal_bridges: list[ThermalBridge] | None = None,
    bridge_inventory: Literal["UNRESOLVED", "COMPLETE"] = "UNRESOLVED",
    bridge_inventory_provenance: AuthoringProvenance | None = None,
    boundary_inventory: Literal["UNRESOLVED", "COMPLETE"] = "UNRESOLVED",
    boundary_inventory_provenance: AuthoringProvenance | None = None,
) -> ProjectHeatLossAdapterResult:
    """Prepare an input or typed diagnostics; never execute transmission math."""
    try:
        source = project_transmission_source_from_adapter(
            adapter_result, boundaries=boundaries, climate_result=climate_result,
            climate_request=climate_request, thermal_bridges=thermal_bridges,
            bridge_inventory=bridge_inventory, bridge_inventory_provenance=bridge_inventory_provenance,
            boundary_inventory=boundary_inventory,
            boundary_inventory_provenance=boundary_inventory_provenance,
        )
        value = build_building_heat_loss_input(source, calculation_mode=calculation_mode)
    except (ValueError, ValidationError) as error:
        return ProjectHeatLossAdapterResult(status="INVALID", diagnostics=[str(error)])
    missing = []
    if not value.boundaries:
        missing.append("TRANSMISSION_BOUNDARIES_REQUIRED")
    if value.boundary_inventory != "COMPLETE":
        missing.append("ROOM_BOUNDARY_INVENTORY_REQUIRED")
    for boundary in value.boundaries:
        for field, present in (("area", boundary.area_m2 is not None),
                               ("construction_u", _u_value(boundary) is not None),
                               ("indoor_temperature", boundary.inside_temperature_c is not None),
                               ("opposite_temperature", boundary.opposite_temperature_c is not None)):
            if not present:
                missing.append(f"{boundary.boundary_id}:{field}_REQUIRED")
        if boundary.boundary_kind == "GROUND":
            missing.append(f"{boundary.boundary_id}:GROUND_HEAT_LOSS_MODEL_REQUIRED")
    return ProjectHeatLossAdapterResult(status="INCOMPLETE" if missing else "INPUT_PREPARED",
                                       input_data=value, diagnostics=sorted(missing))


def _u_value(boundary: TransmissionBoundaryInput) -> Decimal | None:
    if boundary.construction is not None and boundary.construction.calculation_status not in {"EXPLICIT_U_VALUE_RESOLVED", "LAYERED_RESISTANCE_RESOLVED"}:
        return None
    if boundary.u_value_w_m2k is not None:
        return boundary.u_value_w_m2k
    return boundary.construction.u_value_w_m2k if boundary.construction is not None else None


def _u_role(boundary: TransmissionBoundaryInput) -> str | None:
    if boundary.u_value_role is not None:
        return boundary.u_value_role
    if boundary.construction is None:
        return None
    if boundary.construction.resistance_scope == "HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE":
        return "HOMOGENEOUS_COMPONENT"
    # Explicit U alone does not state if it is reduced K or planar Ui.
    return None


DECIMAL_POLICY = {"precision": 50, "rounding": "ROUND_HALF_EVEN",
                  "area_quantum_m2": "0.01", "length_quantum_m": "0.1",
                  "measurement_rounding": "ROUND_HALF_UP"}


def calculate_room_transmission(input_data: BuildingHeatLossInput) -> RoomTransmissionHeatLossResult:
    """Pure, context-independent signed SP60 transmission evaluation."""
    # Revalidation also prevents unsafe model_copy(update=...) inputs bypassing
    # identity, units or net-area checks at this public calculation boundary.
    checked = BuildingHeatLossInput.model_validate(input_data.model_dump())
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        return _calculate_transmission(checked)


def _calculate_transmission(data: BuildingHeatLossInput) -> RoomTransmissionHeatLossResult:
    boundaries = sorted(data.boundaries, key=lambda b: b.boundary_id)
    bridges = sorted(data.thermal_bridges, key=lambda b: b.bridge_id)
    by_id = {b.boundary_id: b for b in boundaries}
    areas = {b.boundary_id: b.area_m2.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
             if b.area_m2 is not None else None for b in boundaries}
    results = []
    unresolved = set()
    detailed = data.calculation_mode == "DETAILED_TRANSMISSION"
    bridges_known = data.thermal_bridge_inventory == "COMPLETE"
    boundaries_known = data.boundary_inventory == "COMPLETE"
    if not boundaries_known:
        unresolved.add("ROOM_BOUNDARY_INVENTORY_REQUIRED")
    if detailed and not bridges_known:
        unresolved.add("THERMAL_BRIDGE_DATA_REQUIRED")
    if data.calculation_mode == "PLANAR_TRANSMISSION_ONLY" and (not bridges_known or bridges):
        unresolved.add("THERMAL_BRIDGES_NOT_INCLUDED")
    if not boundaries:
        unresolved.add("TRANSMISSION_BOUNDARIES_REQUIRED")

    for boundary in boundaries:
        parent = by_id.get(boundary.parent_boundary_id)
        children = [b for b in boundaries if b.parent_boundary_id == boundary.boundary_id]
        attached = [b for b in bridges if b.boundary_id == boundary.boundary_id]
        gross = areas[boundary.boundary_id]
        opening_area = (sum((areas[b.boundary_id] for b in children), Decimal(0))
                        if all(areas[b.boundary_id] is not None for b in children) else None)
        net = gross - opening_area if gross is not None and opening_area is not None else None
        dt = (boundary.inside_temperature_c - boundary.opposite_temperature_c
              if boundary.inside_temperature_c is not None and boundary.opposite_temperature_c is not None else None)
        internal = boundary.internal_partition or (parent is not None and parent.internal_partition)
        omitted = bool(internal and dt is not None and abs(dt) <= Decimal("4"))
        issues = set(boundary.diagnostics)
        u_value = _u_value(boundary)
        planar = linear = point = total = None

        if boundary.boundary_kind == "GROUND":
            issues.add("GROUND_HEAT_LOSS_MODEL_REQUIRED")
            omitted = False
        elif boundary.boundary_kind == "UNKNOWN_PROJECT_SPECIFIC":
            issues.add("BOUNDARY_SEMANTIC_TYPE_REQUIRED")
        elif omitted:
            planar = Decimal(0)
            if detailed and bridges_known:
                linear = point = Decimal(0)
            total = Decimal(0)
            issues.add("SP60_INTERNAL_PARTITION_OMISSION_RULE")
        else:
            if net is None:
                issues.add("AUTHORITATIVE_BOUNDARY_AREA_REQUIRED")
            elif net < 0 or gross <= 0:
                issues.add("INVALID_NORMALIZED_BOUNDARY_AREA")
            if boundary.inside_temperature_c is None:
                issues.add("INDOOR_DESIGN_TEMPERATURE_REQUIRED")
            if boundary.opposite_temperature_c is None:
                issues.add("CLIMATE_DESIGN_TEMPERATURE_REQUIRED" if boundary.boundary_kind == "OUTDOOR_AIR"
                           else "ADJACENT_SPACE_TEMPERATURE_REQUIRED")
            if u_value is None:
                issues.add("COMPATIBLE_CONSTRUCTION_U_VALUE_REQUIRED")
            role = _u_role(boundary)
            if data.calculation_mode == "A2_REDUCED_FRAGMENT" and role != "REDUCED_FRAGMENT":
                issues.add("SP50_REDUCED_RESISTANCE_REQUIRED_FOR_A2")
            if data.calculation_mode != "A2_REDUCED_FRAGMENT" and role != "HOMOGENEOUS_COMPONENT":
                issues.add("HOMOGENEOUS_U_REQUIRED_FOR_A3")
            if role is None:
                issues.add("U_VALUE_ROLE_REQUIRED")
            if not issues:
                planar = net * u_value * dt
                if detailed and bridges_known:
                    linear = sum((dt * b.coefficient *
                                  b.quantity.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                                  for b in attached if b.kind == "LINEAR"), Decimal(0))
                    point = sum((dt * b.coefficient * b.quantity
                                 for b in attached if b.kind == "POINT"), Decimal(0))
                    total = planar + linear + point
                elif not detailed:
                    total = planar

        unresolved.update(issues - {"SP60_INTERNAL_PARTITION_OMISSION_RULE"})
        if detailed and not bridges_known:
            issues.add("THERMAL_BRIDGE_DATA_REQUIRED")
        if data.calculation_mode == "PLANAR_TRANSMISSION_ONLY" and (not bridges_known or bridges):
            issues.add("THERMAL_BRIDGES_NOT_INCLUDED")
        provenance_payload = {
            "boundary": boundary.model_dump(mode="json"),
            "children": [b.model_dump(mode="json") for b in children],
            "parent_internal_partition": parent.internal_partition if parent else None,
            "bridges": [b.model_dump(mode="json") for b in attached],
            "bridge_inventory": data.thermal_bridge_inventory if detailed else None,
            "bridge_inventory_provenance": (data.thermal_bridge_inventory_provenance.model_dump(mode="json")
                                             if detailed and data.thermal_bridge_inventory_provenance else None),
            "boundary_inventory": data.boundary_inventory,
            "boundary_inventory_provenance": (data.boundary_inventory_provenance.model_dump(mode="json")
                                                if data.boundary_inventory_provenance else None),
            "method": SP60_METHOD_DIGEST, "mode": data.calculation_mode,
            "decimal_policy": DECIMAL_POLICY,
        }
        results.append(TransmissionBoundaryResult(
            boundary_id=boundary.boundary_id, boundary_kind=boundary.boundary_kind,
            gross_area_m2=gross, opening_area_m2=opening_area or Decimal(0),
            net_opaque_area_m2=net, u_value_w_m2k=u_value,
            inside_temperature_c=boundary.inside_temperature_c,
            opposite_temperature_c=boundary.opposite_temperature_c, delta_t_c=dt,
            planar_heat_flow_w=planar, linear_heat_flow_w=linear,
            point_heat_flow_w=point, total_heat_flow_w=total,
            omitted_by_internal_partition_rule=omitted, diagnostics=sorted(issues),
            provenance_digest=_digest(provenance_payload),
        ))

    def complete_sum(field):
        values = [getattr(r, field) for r in results]
        return sum(values, Decimal(0)) if values and all(v is not None for v in values) else None

    planar_total = complete_sum("planar_heat_flow_w")
    linear_total = complete_sum("linear_heat_flow_w") if detailed else None
    point_total = complete_sum("point_heat_flow_w") if detailed else None
    total = complete_sum("total_heat_flow_w")
    if "GROUND_HEAT_LOSS_MODEL_REQUIRED" in unresolved:
        status = "GROUND_MODEL_REQUIRED"
    elif "INVALID_NORMALIZED_BOUNDARY_AREA" in unresolved:
        status = "INVALID_BOUNDARY_DATA"
    elif "ADJACENT_SPACE_TEMPERATURE_REQUIRED" in unresolved:
        status = "ADJACENT_TEMPERATURE_REQUIRED"
    elif planar_total is None or not boundaries_known:
        status = "INCOMPLETE_BOUNDARY_DATA"
    elif detailed and not bridges_known:
        status = "THERMAL_BRIDGE_DATA_REQUIRED"
    elif detailed:
        status = "COMPLETE_DETAILED"
    else:
        status = "PLANAR_ONLY"
    if status not in {"COMPLETE_DETAILED", "PLANAR_ONLY"}:
        total = None
    canonical_input = data.model_dump(mode="json")
    canonical_input["boundaries"] = [b.model_dump(mode="json") for b in boundaries]
    canonical_input["thermal_bridges"] = [b.model_dump(mode="json") for b in bridges]
    body = dict(
        project_id=data.project_id, building_id=data.building_id,
        level_id=data.level_id, room_id=data.room_id,
        normative_method_digest=SP60_METHOD_DIGEST, calculation_mode=data.calculation_mode,
        assessment_level="DETAILED_TRANSMISSION" if detailed else "PLANAR_TRANSMISSION_ONLY",
        boundary_results=results, planar_total_w=planar_total,
        linear_total_w=linear_total, point_total_w=point_total,
        room_transmission_heat_loss_w=total, completeness_status=status,
        unresolved_dependencies=sorted(unresolved),
    )
    result = RoomTransmissionHeatLossResult(**body, calculation_digest="0" * 64)
    return result.model_copy(update={"calculation_digest": _digest({
        "input": canonical_input, "method": SP60_METHOD_DIGEST, "policy": DECIMAL_POLICY,
        "result": result.model_dump(mode="json", exclude={"calculation_digest"}),
    })})
