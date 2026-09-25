"""Typed minimum intake after project-source exhaustion; no calculations."""
from typing import Any, Literal
from pydantic import Field
from agent.project_models import StrictProjectModel


MINIMUM_ENGINEERING_AUTHORITY_FIELDS: tuple[str, ...] = (
    "exterior_wall",
    "first_floor_boundary",
    "mansard_roof_or_ceiling",
    "clear_room_height_mm",
    "openings",
    "winter_air_basis",
    "climate_normative_binding_reference",
)


class MinimumEngineeringIntakeReadiness(StrictProjectModel):
    status: Literal["AUTHORITY_INPUT_REQUIRED", "READY_FOR_RESOLVER_VALIDATION"]
    missing_authority_fields: tuple[str, ...]


def assess_minimum_engineering_intake(payload: dict[str, Any]) -> MinimumEngineeringIntakeReadiness:
    """List absent owner/source fields; never infer values or run a resolver."""
    missing = tuple(field for field in MINIMUM_ENGINEERING_AUTHORITY_FIELDS
                    if field not in payload or payload[field] is None)
    return MinimumEngineeringIntakeReadiness(
        status="AUTHORITY_INPUT_REQUIRED" if missing else "READY_FOR_RESOLVER_VALIDATION",
        missing_authority_fields=missing,
    )

class LayerInput(StrictProjectModel):
    material: str = Field(min_length=1)
    thickness_mm: float = Field(gt=0)
    product_or_source: str | None = None

class ConstructionInput(StrictProjectModel):
    input_mode: Literal["KNOWN_U_VALUE", "LAYER_ASSEMBLY"]
    u_value_w_m2k: float | None = Field(default=None, gt=0)
    layers: tuple[LayerInput, ...] = ()
    source_reference: str = Field(min_length=1)

class OpeningThermalInput(StrictProjectModel):
    opening_reference: str
    height_mm: float = Field(gt=0)
    input_mode: Literal["KNOWN_U_VALUE", "PRODUCT_OR_LAYER_DATA"]
    u_value_w_m2k: float | None = Field(default=None, gt=0)
    product_or_construction: str | None = None

class WholeBuildingEngineeringIntake(StrictProjectModel):
    exterior_wall: ConstructionInput
    first_floor_boundary: ConstructionInput
    mansard_roof_or_ceiling: ConstructionInput
    other_envelope_constructions: tuple[ConstructionInput, ...] = ()
    clear_room_height_mm: float = Field(gt=0)
    openings: tuple[OpeningThermalInput, ...]
    winter_air_basis: dict
    climate_normative_binding_reference: str
    status: Literal["USER_AUTHORED_INPUT_REQUIRES_RESOLVER_VALIDATION"] = "USER_AUTHORED_INPUT_REQUIRES_RESOLVER_VALIDATION"

class ClimateBindingAssessment(StrictProjectModel):
    observed_locality: str
    resolver_exact_match_available: bool
    status: Literal["NORMATIVE_LOCALITY_BINDING_REQUIRED"] = "NORMATIVE_LOCALITY_BINDING_REQUIRED"
    reason: str

def assess_uzigonty_climate_binding(dataset) -> ClimateBindingAssessment:
    target="узигонты"
    values={record.locality.casefold() for record in dataset.records}
    values.update(alias.casefold() for record in dataset.records for alias in record.aliases)
    return ClimateBindingAssessment(observed_locality="дер. Узигонты",
        resolver_exact_match_available=target in values,
        reason="Existing SP131 resolver is exact-match and contains no Узигонты record; proximity substitution is prohibited.")
