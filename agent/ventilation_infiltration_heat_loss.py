"""SP 60.13330.2020 ventilation/infiltration heat components.

All functions are deterministic in-memory calculations. Source acquisition,
project discovery, and UFH generation are intentionally outside this module.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Literal

from pydantic import Field, field_validator, model_validator

from agent.project_models import StrictProjectModel
from agent.sp60_normative_method import SP60_CANONICAL_REVISION, SP60_CANONICAL_REVISION_DIGEST
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance


def _d(value):
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
    def jsonable(item):
        if isinstance(item, Decimal):
            return format(item, "f")
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        if isinstance(item, dict):
            return {str(key): jsonable(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [jsonable(val) for val in item]
        return item
    return hashlib.sha256(json.dumps(jsonable(value), sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


SP60_AIR_METHOD_PACKAGE = {
    "canonical_revision": SP60_CANONICAL_REVISION,
    "canonical_revision_digest": SP60_CANONICAL_REVISION_DIGEST,
    "consolidated_revision": SP60_CANONICAL_REVISION["consolidated_text_revision"],
    "amendments": SP60_CANONICAL_REVISION["consolidated_amendments"],
    "amendment_6_effective_from": SP60_CANONICAL_REVISION["amendment_6"]["effective_date"],
    "text_carrier": "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i.html",
    "text_carrier_authority": "TEXT_CARRIER_ONLY",
    "authority_model": "official document identity metadata + revision-pinned published text extract",
    "formula_records": {
        "A.1": {"formula_id": "SP60_A1_2020_AMD1_6", "semantics": "Q_ов^p = sum_n(Q_tr,n + Q_vent,n + Q_inf,n + Q_mts,n)", "units": "W", "visual_sha256": "9e5c640d05e33251943b2e55ed8769a4f10346822e2d71370a20b91f3dc71151"},
        "A.5": {"formula_id": "SP60_A5_2020_AMD1_6", "semantics": "Q_vent=(t_v-t_n)*G_n*c_v*0.28=(t_v-t_n)*L_n*rho_n*c_v*0.28", "units": "W", "visual_sha256": "19fa694926febde8993183d13be8e04fe5437b0dfa39db54821737761a0fc1fa"},
        "A.6": {"formula_id": "SP60_A6_2020_AMD1_6", "semantics": "rho(T)=353/(273+T)", "units": "kg/m3", "visual_sha256": "8e82820ce18faa4cee4de210d3192046d8d6e49b3e05bd9097d6016a8998a6aa"},
        "A.7": {"formula_id": "SP60_A7_2020_AMD1_6", "semantics": "Q_inf=(t_v-t_n)*G_inf*c_v*0.28", "units": "W", "visual_sha256": "aa07e62d0135001b47a03172b25fd19bd23a0e91f327c27547c7aa04aa96e976"},
        "A.8": {"formula_id": "SP60_A8_2020_AMD1_6", "semantics": "G_inf=sum_i((DeltaP/DeltaP0)^(2/3)*A_i/Ru_i)+sum_j((DeltaP/DeltaP0)^(1/2)*A_j/Ru_j)", "units": "kg/h", "visual_sha256": "54b42e1c822c9bd1e5709d0fc3962eb4b915d03939482dafa9227505ac5b6ca6"},
        "A.9": {"formula_id": "SP60_A9_2020_AMD1_6", "semantics": "DeltaP=(H-h)*(rho_n-rho_v)*g+rho_n*v^2/2*(c_n-c_z)*k_z-P_v", "units": "Pa", "visual_sha256": "a6483a608941224d3f12392d8bc54a2dfea5364dcbca9b1db416cfae090f7ed6"},
        "A.10": {"formula_id": "SP60_A10_2020_AMD1_6", "semantics": "P_v=H*(rho_n-rho_v)*g+rho_n*v^2/4*(c_n-c_z)*k_z", "units": "Pa", "visual_sha256": "cbe79974a0857f300d691ab1c0eafe7dd84fac8b400859c668e6f72d3deb4995"},
        "A.11": {"formula_id": "SP60_A11_2020_AMD3_6", "semantics": "Q_mts,n=(t_v,n-t_mts,n)*H_mts,n=sum_m((t_v,n-t_mts,m)*G_mts,m*c_mts,m*beta_m*0.28)", "units": "W", "visual_sha256": "d46beb0df4fea994b6e60fc0b0036d876e188ae3a210348af5b29c27cc77c765a"},
    },
    "normative_constants": {"c_v_kj_kgk": "1", "conversion_factor": "0.28", "density_numerator": "353", "density_temperature_offset_c": "273", "reference_pressure_pa": "10", "gravity_m_s2": "9.81", "window_filter_exponent": "2/3", "door_opening_filter_exponent": "1/2", "rectangular_c_windward": "0.8", "rectangular_c_leeward": "-0.6"},
    "airflow_sources": ["normative air-change rates", "airflow per person", "SP60 7.4.1 calculation"],
    "a1_formula": "Q_ов^p = sum_n(Q_tr,n + Q_vent,n + Q_inf,n + Q_mts,n)",
    "a1_components": ["Q_tr", "Q_vent", "Q_inf", "Q_mts"],
    "a1_internal_gains_term": "NOT_PRESENT_IN_CURRENT_A1_FORMULA",
    "a1_source_reference": "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i.html",
    "a1_formula_image": "https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_927350.png",
    "a1_formula_image_sha256": "9e5c640d05e33251943b2e55ed8769a4f10346822e2d71370a20b91f3dc71151",
    "wind_dependency": "SP 131 climate design wind value, if present, otherwise sourced project/SP20 design input; temperature does not imply wind",
    "aerodynamic_dependency": "SP20.13330 except SP60 A.9 explicit rectangular-building pair",
}
SP60_AIR_METHOD_DIGEST = _digest(SP60_AIR_METHOD_PACKAGE)
NORMATIVE_TEXT_CARRIER = SP60_AIR_METHOD_PACKAGE["text_carrier"]


def _normative_provenance(clause: str, units: str, transformation: str) -> AuthoringProvenance:
    return AuthoringProvenance(
        source_type="project_approved_normative_extract",
        source_reference=NORMATIVE_TEXT_CARRIER,
        source_sha256=SP60_AIR_METHOD_DIGEST,
        source_field=f"SP60.13330.2020/{clause}",
        transformation=transformation,
        units=units,
    )


class SourcedDecimal(StrictProjectModel):
    value: Decimal
    units: str = Field(min_length=1, max_length=64)
    provenance: AuthoringProvenance

    @field_validator("value", mode="before")
    @classmethod
    def decimal_value(cls, value):
        return _d(value)

    @model_validator(mode="after")
    def check_units(self):
        if self.provenance.units != self.units:
            raise ValueError("SOURCED_VALUE_UNIT_MISMATCH")
        return self


class OutdoorAirDensityResult(StrictProjectModel):
    temperature_c: Decimal
    temperature_provenance: AuthoringProvenance
    formula_id: Literal["SP60_A6_2020_AMD1_6"] = "SP60_A6_2020_AMD1_6"
    density_kg_m3: Decimal
    provenance: AuthoringProvenance
    method_digest: str = SP60_AIR_METHOD_DIGEST
    digest: str


def calculate_air_density(temperature: SourcedDecimal) -> OutdoorAirDensityResult:
    if temperature.units != "°C":
        raise ValueError("AIR_DENSITY_TEMPERATURE_MUST_BE_C")
    if Decimal("273") + temperature.value <= 0:
        raise ValueError("AIR_DENSITY_TEMPERATURE_OUT_OF_DOMAIN")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        density = Decimal("353") / (Decimal("273") + temperature.value)
    prov = _normative_provenance("A.6", "kg/m3", "rho=353/(273+T_C); Decimal calculation")
    body = {"temperature_c": temperature.value, "temperature_provenance": temperature.provenance.model_dump(mode="json"), "density_kg_m3": density, "provenance": prov.model_dump(mode="json"), "method_digest": SP60_AIR_METHOD_DIGEST}
    return OutdoorAirDensityResult(**body, digest=_digest(body))


AirflowMode = Literal["PROJECT_DESIGN_AIRFLOW", "NORMATIVE_AIR_CHANGE_RATE", "PER_PERSON_REQUIREMENT", "ENGINEERING_CALCULATION_7_4_1"]


class RequiredVentilationAirflow(StrictProjectModel):
    source_mode: AirflowMode
    direct_airflow_m3_h: Decimal | None = None
    direct_airflow_provenance: AuthoringProvenance | None = None
    design_air_changes_per_h: Decimal | None = None
    air_changes_provenance: AuthoringProvenance | None = None
    air_changes_semantics: Literal["REQUIRED_COLD_PERIOD_DESIGN_AIR_CHANGE_RATE"] | None = None
    room_volume_m3: Decimal | None = None
    room_volume_provenance: AuthoringProvenance | None = None
    design_occupancy: int | None = None
    occupancy_provenance: AuthoringProvenance | None = None
    airflow_per_person_m3_h: Decimal | None = None
    per_person_rate_provenance: AuthoringProvenance | None = None
    pressurization_makeup_airflow_m3_h: Decimal | None = None
    pressurization_makeup_provenance: AuthoringProvenance | None = None

    @field_validator("direct_airflow_m3_h", "design_air_changes_per_h", "room_volume_m3", "airflow_per_person_m3_h", "pressurization_makeup_airflow_m3_h", mode="before")
    @classmethod
    def decimals(cls, value):
        return _d(value)

    @model_validator(mode="after")
    def source_semantics(self):
        direct_group = (self.direct_airflow_m3_h, self.direct_airflow_provenance)
        ach_group = (self.design_air_changes_per_h, self.air_changes_provenance,
                     self.air_changes_semantics, self.room_volume_m3, self.room_volume_provenance)
        person_group = (self.design_occupancy, self.occupancy_provenance,
                        self.airflow_per_person_m3_h, self.per_person_rate_provenance)
        if self.source_mode in {"PROJECT_DESIGN_AIRFLOW", "ENGINEERING_CALCULATION_7_4_1"} and any(v is not None for v in ach_group + person_group):
            raise ValueError("VENTILATION_SOURCE_MODE_FIELDS_CONFLICT")
        if self.source_mode == "NORMATIVE_AIR_CHANGE_RATE" and (any(v is not None for v in direct_group) or any(v is not None for v in person_group)):
            raise ValueError("VENTILATION_SOURCE_MODE_FIELDS_CONFLICT")
        if self.source_mode == "PER_PERSON_REQUIREMENT" and (any(v is not None for v in direct_group) or any(v is not None for v in ach_group)):
            raise ValueError("VENTILATION_SOURCE_MODE_FIELDS_CONFLICT")
        if self.source_mode in {"PROJECT_DESIGN_AIRFLOW", "ENGINEERING_CALCULATION_7_4_1"}:
            if self.direct_airflow_m3_h is None or self.direct_airflow_m3_h <= 0 or self.direct_airflow_provenance is None:
                raise ValueError("VENTILATION_AIRFLOW_SOURCE_REQUIRED")
            if self.direct_airflow_provenance.units != "m3/h":
                raise ValueError("VENTILATION_AIRFLOW_UNIT_INVALID")
        if self.source_mode == "NORMATIVE_AIR_CHANGE_RATE":
            if (self.design_air_changes_per_h is None or self.design_air_changes_per_h <= 0 or self.air_changes_provenance is None
                    or self.air_changes_semantics != "REQUIRED_COLD_PERIOD_DESIGN_AIR_CHANGE_RATE"):
                raise ValueError("VENTILATION_AIRFLOW_SOURCE_REQUIRED")
            if self.air_changes_provenance.units != "1/h":
                raise ValueError("DESIGN_AIR_CHANGE_RATE_UNIT_INVALID")
            if self.room_volume_m3 is None or self.room_volume_m3 <= 0 or self.room_volume_provenance is None or self.room_volume_provenance.units != "m3":
                raise ValueError("AUTHORITATIVE_ROOM_VOLUME_REQUIRED")
        if self.source_mode == "PER_PERSON_REQUIREMENT":
            if (self.design_occupancy is None or self.design_occupancy <= 0 or self.occupancy_provenance is None
                    or self.occupancy_provenance.units != "person"):
                raise ValueError("DESIGN_OCCUPANCY_REQUIRED")
            if self.airflow_per_person_m3_h is None or self.airflow_per_person_m3_h <= 0 or self.per_person_rate_provenance is None or self.per_person_rate_provenance.units != "m3/(h person)":
                raise ValueError("NORMATIVE_PER_PERSON_AIRFLOW_REQUIRED")
        if self.pressurization_makeup_airflow_m3_h is not None:
            if self.pressurization_makeup_airflow_m3_h <= 0 or self.pressurization_makeup_provenance is None or self.pressurization_makeup_provenance.units != "m3/h":
                raise ValueError("PRESSURIZATION_MAKEUP_AIRFLOW_PROVENANCE_REQUIRED")
        elif self.pressurization_makeup_provenance is not None:
            raise ValueError("PRESSURIZATION_MAKEUP_AIRFLOW_PROVENANCE_MISMATCH")
        return self

    def resolve_base_airflow(self) -> tuple[Decimal, list[dict]]:
        if self.source_mode in {"PROJECT_DESIGN_AIRFLOW", "ENGINEERING_CALCULATION_7_4_1"}:
            return self.direct_airflow_m3_h, [self.direct_airflow_provenance.model_dump(mode="json")]
        if self.source_mode == "NORMATIVE_AIR_CHANGE_RATE":
            return self.design_air_changes_per_h * self.room_volume_m3, [self.air_changes_provenance.model_dump(mode="json"), self.room_volume_provenance.model_dump(mode="json")]
        return Decimal(self.design_occupancy) * self.airflow_per_person_m3_h, [self.occupancy_provenance.model_dump(mode="json"), self.per_person_rate_provenance.model_dump(mode="json")]


class RoomVentilationHeatLossResult(StrictProjectModel):
    status: Literal["RESOLVED", "INCOMPLETE"]
    room_id: str
    airflow_source_mode: AirflowMode | None = None
    required_base_airflow_m3_h: Decimal | None = None
    pressurization_makeup_airflow_m3_h: Decimal = Decimal(0)
    total_required_airflow_m3_h: Decimal | None = None
    mass_airflow_kg_h: Decimal | None = None
    air_density: OutdoorAirDensityResult | None = None
    inside_temperature_c: Decimal | None = None
    outside_temperature_c: Decimal | None = None
    delta_t_c: Decimal | None = None
    q_vent_w: Decimal | None = None
    ventilation_provenance: list[AuthoringProvenance] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    digest: str


def calculate_room_ventilation_heat_loss(
    room_id: str,
    airflow: RequiredVentilationAirflow | None,
    inside_temperature: SourcedDecimal | None,
    outside_temperature: SourcedDecimal | None,
) -> RoomVentilationHeatLossResult:
    missing = []
    if airflow is None:
        missing.append("VENTILATION_AIRFLOW_SOURCE_REQUIRED")
    if inside_temperature is None:
        missing.append("INDOOR_DESIGN_TEMPERATURE_REQUIRED")
    elif inside_temperature.units != "°C":
        missing.append("INDOOR_DESIGN_TEMPERATURE_UNIT_INVALID")
    if outside_temperature is None:
        missing.append("CLIMATE_DESIGN_TEMPERATURE_REQUIRED")
    elif outside_temperature.units != "°C":
        missing.append("CLIMATE_DESIGN_TEMPERATURE_UNIT_INVALID")
    if missing:
        body = {"status": "INCOMPLETE", "room_id": room_id, "diagnostics": sorted(set(missing)), "digest": "0" * 64}
        return RoomVentilationHeatLossResult.model_validate({**body, "digest": _digest(body)})
    base, source_refs = airflow.resolve_base_airflow()
    extra = airflow.pressurization_makeup_airflow_m3_h or Decimal(0)
    total_l = base + extra
    density = calculate_air_density(outside_temperature)
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        mass = total_l * density.density_kg_m3
        delta_t = inside_temperature.value - outside_temperature.value
        q = delta_t * mass * Decimal("1") * Decimal("0.28")
    norm = _normative_provenance("A.5", "W", "Qvent=(Ti-To)*G*cv*0.28; G=L*rho; cv=1 kJ/(kg K)")
    provenance = [airflow_provenance for airflow_provenance in (inside_temperature.provenance, outside_temperature.provenance, density.provenance, norm)]
    if airflow.direct_airflow_provenance:
        provenance.append(airflow.direct_airflow_provenance)
    if airflow.air_changes_provenance:
        provenance.append(airflow.air_changes_provenance)
    if airflow.room_volume_provenance:
        provenance.append(airflow.room_volume_provenance)
    if airflow.occupancy_provenance:
        provenance.append(airflow.occupancy_provenance)
    if airflow.per_person_rate_provenance:
        provenance.append(airflow.per_person_rate_provenance)
    if airflow.pressurization_makeup_provenance:
        provenance.append(airflow.pressurization_makeup_provenance)
    body = {"status": "RESOLVED", "room_id": room_id, "airflow_source_mode": airflow.source_mode,
            "required_base_airflow_m3_h": base, "pressurization_makeup_airflow_m3_h": extra,
            "total_required_airflow_m3_h": total_l, "mass_airflow_kg_h": mass,
            "air_density": density, "inside_temperature_c": inside_temperature.value,
            "outside_temperature_c": outside_temperature.value, "delta_t_c": delta_t,
            "q_vent_w": q, "ventilation_provenance": provenance,
            "diagnostics": []}
    return RoomVentilationHeatLossResult.model_validate({**body, "digest": _digest(body)})


class AerodynamicCoefficientModel(StrictProjectModel):
    building_form: Literal["RECTANGULAR", "OTHER"]
    windward_coefficient: Decimal
    leeward_coefficient: Decimal
    provenance: AuthoringProvenance

    @field_validator("windward_coefficient", "leeward_coefficient", mode="before")
    @classmethod
    def decimals(cls, value):
        return _d(value)

    @model_validator(mode="after")
    def rectangular_scope(self):
        if self.provenance.units != "dimensionless":
            raise ValueError("AERODYNAMIC_COEFFICIENT_UNIT_INVALID")
        if self.building_form == "RECTANGULAR" and (self.windward_coefficient != Decimal("0.8") or self.leeward_coefficient != Decimal("-0.6")):
            raise ValueError("RECTANGULAR_SP60_A9_COEFFICIENTS_MISMATCH")
        return self


def rectangular_building_aerodynamic_coefficients(building_form: str, geometry_provenance: AuthoringProvenance) -> AerodynamicCoefficientModel:
    if building_form != "RECTANGULAR":
        raise ValueError("SP20_AERODYNAMIC_MODEL_REQUIRED")
    if not geometry_provenance.source_reference or not geometry_provenance.source_field:
        raise ValueError("RECTANGULAR_BUILDING_GEOMETRY_PROVENANCE_REQUIRED")
    provenance = _normative_provenance("A.9", "dimensionless", "SP60 A.9 rectangular-building values; applicability established by sourced building-form geometry")
    return AerodynamicCoefficientModel(building_form="RECTANGULAR", windward_coefficient=Decimal("0.8"), leeward_coefficient=Decimal("-0.6"), provenance=provenance)


class AirPermeableEnvelopeElement(StrictProjectModel):
    element_id: str = Field(min_length=1, max_length=160)
    element_kind: Literal["WINDOW_OR_TRANSLUCENT", "DOOR_GATE_OR_OPENING", "OTHER_AIR_PERMEABLE"]
    area_m2: Decimal
    area_provenance: AuthoringProvenance
    air_permeability_resistance_ru_m2_h_pa_kg: Decimal
    resistance_provenance: AuthoringProvenance
    center_height_m: Decimal | None = None
    center_height_provenance: AuthoringProvenance | None = None
    wind_height_coefficient: Decimal | None = None
    wind_height_coefficient_provenance: AuthoringProvenance | None = None
    filtering_exponent: Decimal | None = None
    filtering_exponent_provenance: AuthoringProvenance | None = None

    @field_validator("area_m2", "air_permeability_resistance_ru_m2_h_pa_kg", "center_height_m", "wind_height_coefficient", "filtering_exponent", mode="before")
    @classmethod
    def decimals(cls, value):
        return _d(value)

    @model_validator(mode="after")
    def source_values(self):
        if self.area_m2 <= 0 or self.area_provenance.units != "m2":
            raise ValueError("AIR_PERMEABLE_ELEMENT_AREA_INVALID")
        if self.air_permeability_resistance_ru_m2_h_pa_kg <= 0 or self.resistance_provenance.units != "m2*h*Pa/kg":
            raise ValueError("AIR_PERMEABILITY_RESISTANCE_REQUIRED")
        if (self.center_height_m is None) != (self.center_height_provenance is None):
            raise ValueError("ELEMENT_CENTER_HEIGHT_AND_PROVENANCE_MUST_BE_PAIRED")
        if self.center_height_provenance and self.center_height_provenance.units != "m":
            raise ValueError("ELEMENT_CENTER_HEIGHT_UNIT_INVALID")
        if (self.wind_height_coefficient is None) != (self.wind_height_coefficient_provenance is None):
            raise ValueError("WIND_HEIGHT_COEFFICIENT_AND_PROVENANCE_MUST_BE_PAIRED")
        if self.wind_height_coefficient_provenance and self.wind_height_coefficient_provenance.units != "dimensionless":
            raise ValueError("WIND_HEIGHT_COEFFICIENT_UNIT_INVALID")
        if self.element_kind == "OTHER_AIR_PERMEABLE":
            if self.filtering_exponent is None or self.filtering_exponent_provenance is None or self.filtering_exponent_provenance.units != "dimensionless":
                raise ValueError("FILTERING_EXPONENT_SOURCE_REQUIRED")
        elif self.filtering_exponent is not None or self.filtering_exponent_provenance is not None:
            raise ValueError("SP60_A8_FILTERING_EXPONENT_IS_CATEGORY_DEFINED")
        return self

    def effective_filtering_exponent(self) -> tuple[Decimal, AuthoringProvenance]:
        if self.element_kind == "WINDOW_OR_TRANSLUCENT":
            return Decimal(2) / Decimal(3), _normative_provenance("A.8", "dimensionless", "SP60 A.8: translucent/window exponent 2/3")
        if self.element_kind == "DOOR_GATE_OR_OPENING":
            return Decimal(1) / Decimal(2), _normative_provenance("A.8", "dimensionless", "SP60 A.8: entrance doors/gates/openings exponent 1/2")
        return self.filtering_exponent, self.filtering_exponent_provenance


IndoorPressureMode = Literal["NO_ORGANIZED_VENTILATION", "BALANCED_SUPPLY_EXHAUST", "PRESSURIZED_BY_DESIGN", "OTHER_ORGANIZED_VENTILATION"]


class InfiltrationInput(StrictProjectModel):
    room_id: str
    indoor_temperature: SourcedDecimal | None = None
    outdoor_temperature: SourcedDecimal | None = None
    pressure_mode: IndoorPressureMode
    building_height_m: Decimal | None = None
    building_height_provenance: AuthoringProvenance | None = None
    wind_speed_cold_design_m_s: Decimal | None = None
    wind_speed_provenance: AuthoringProvenance | None = None
    aerodynamic_coefficients: AerodynamicCoefficientModel | None = None
    pressure_inventory: Literal["UNRESOLVED", "COMPLETE"]
    pressure_inventory_provenance: AuthoringProvenance | None = None
    elements: list[AirPermeableEnvelopeElement] = Field(default_factory=list)
    indoor_reference_pressure_pa: Decimal | None = None
    indoor_reference_pressure_provenance: AuthoringProvenance | None = None
    pressurization_makeup_airflow_m3_h: Decimal | None = None
    pressurization_makeup_provenance: AuthoringProvenance | None = None

    @field_validator("building_height_m", "wind_speed_cold_design_m_s", "indoor_reference_pressure_pa", "pressurization_makeup_airflow_m3_h", mode="before")
    @classmethod
    def decimals(cls, value):
        return _d(value)

    @model_validator(mode="after")
    def validate_input_pairs(self):
        for value, prov, units, code in (
            (self.building_height_m, self.building_height_provenance, "m", "BUILDING_HEIGHT_REQUIRED"),
            (self.wind_speed_cold_design_m_s, self.wind_speed_provenance, "m/s", "DESIGN_WIND_PARAMETER_REQUIRED"),
            (self.indoor_reference_pressure_pa, self.indoor_reference_pressure_provenance, "Pa", "INDOOR_REFERENCE_PRESSURE_REQUIRED"),
            (self.pressurization_makeup_airflow_m3_h, self.pressurization_makeup_provenance, "m3/h", "PRESSURIZATION_MAKEUP_AIRFLOW_PROVENANCE_REQUIRED"),
        ):
            if (value is None) != (prov is None):
                raise ValueError(code)
            if prov is not None and prov.units != units:
                raise ValueError(f"{code}_UNIT_INVALID")
        if self.building_height_m is not None and self.building_height_m <= 0:
            raise ValueError("BUILDING_HEIGHT_MUST_BE_POSITIVE")
        if self.wind_speed_cold_design_m_s is not None and self.wind_speed_cold_design_m_s < 0:
            raise ValueError("DESIGN_WIND_SPEED_MUST_NOT_BE_NEGATIVE")
        if self.indoor_reference_pressure_pa is not None and abs(self.indoor_reference_pressure_pa) > Decimal("100000"):
            raise ValueError("INDOOR_REFERENCE_PRESSURE_OUT_OF_DOMAIN")
        if self.pressure_inventory == "COMPLETE" and self.pressure_inventory_provenance is None:
            raise ValueError("AIR_PERMEABLE_ELEMENT_INVENTORY_PROVENANCE_REQUIRED")
        if self.pressure_inventory == "UNRESOLVED" and self.pressure_inventory_provenance is not None:
            raise ValueError("UNRESOLVED_AIR_PERMEABLE_INVENTORY_CANNOT_CLAIM_PROVENANCE")
        if len({e.element_id for e in self.elements}) != len(self.elements):
            raise ValueError("DUPLICATE_AIR_PERMEABLE_ELEMENT_ID")
        if self.pressure_mode == "PRESSURIZED_BY_DESIGN":
            if self.pressurization_makeup_airflow_m3_h is None or self.pressurization_makeup_airflow_m3_h <= 0:
                raise ValueError("PRESSURIZATION_DESIGN_EVIDENCE_REQUIRED")
        elif self.pressurization_makeup_airflow_m3_h is not None:
            raise ValueError("PRESSURIZATION_AIRFLOW_ONLY_FOR_PRESSURIZED_MODE")
        return self


class InfiltrationElementResult(StrictProjectModel):
    element_id: str
    pressure_difference_pa: Decimal | None
    pressure_provenance: AuthoringProvenance | None
    filtering_exponent: Decimal | None
    mass_airflow_kg_h: Decimal | None
    source_provenance: list[AuthoringProvenance] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    digest: str


class RoomInfiltrationHeatLossResult(StrictProjectModel):
    status: Literal["RESOLVED", "INCOMPLETE", "INFILTRATION_SUPPRESSED_BY_DESIGN_PRESSURIZATION"]
    room_id: str
    elements: list[InfiltrationElementResult] = Field(default_factory=list)
    indoor_pressure_mode: IndoorPressureMode
    indoor_reference_pressure_pa: Decimal | None = None
    outdoor_air_density_kg_m3: Decimal | None = None
    indoor_air_density_kg_m3: Decimal | None = None
    total_mass_airflow_kg_h: Decimal | None = None
    inside_temperature_c: Decimal | None = None
    outside_temperature_c: Decimal | None = None
    delta_t_c: Decimal | None = None
    q_inf_w: Decimal | None = None
    ventilation_makeup_airflow_required_in_q_vent_m3_h: Decimal | None = None
    diagnostics: list[str] = Field(default_factory=list)
    provenance_digest: str
    digest: str


def _density_raw(temp_c: Decimal) -> Decimal:
    return Decimal("353") / (Decimal("273") + temp_c)


def calculate_room_infiltration_heat_loss(data: InfiltrationInput) -> RoomInfiltrationHeatLossResult:
    checked = InfiltrationInput.model_validate(data.model_dump())
    if checked.pressure_mode == "PRESSURIZED_BY_DESIGN":
        # SP60 A.5 note: infiltration is excluded only for evidenced maintained
        # positive pressure. The make-up flow remains a required ventilation term.
        p = _normative_provenance("A.5 note", "W", "Infiltration term not counted under design positive pressure; excess supply must remain in Q_vent")
        body = {"status": "INFILTRATION_SUPPRESSED_BY_DESIGN_PRESSURIZATION", "room_id": checked.room_id,
                "elements": [], "indoor_pressure_mode": checked.pressure_mode,
                "q_inf_w": Decimal(0), "total_mass_airflow_kg_h": Decimal(0),
                "ventilation_makeup_airflow_required_in_q_vent_m3_h": checked.pressurization_makeup_airflow_m3_h,
                "diagnostics": ["INFILTRATION_SUPPRESSED_BY_DESIGN_PRESSURIZATION", "PRESSURIZATION_MAKEUP_REMAINS_IN_Q_VENT"],
                "provenance_digest": _digest([checked.model_dump(mode="json"), p.model_dump(mode="json")],), "digest": "0" * 64}
        return RoomInfiltrationHeatLossResult.model_validate({**body, "digest": _digest({k: v for k, v in body.items() if k != "digest"})})

    if checked.pressure_inventory == "COMPLETE" and not checked.elements:
        if checked.indoor_temperature is None or checked.outdoor_temperature is None:
            return _infiltration_incomplete(checked, "INDOOR_AND_OUTDOOR_DESIGN_TEMPERATURE_REQUIRED")
        if checked.indoor_temperature.units != "°C" or checked.outdoor_temperature.units != "°C":
            return _infiltration_incomplete(checked, "DESIGN_TEMPERATURE_UNIT_INVALID")
        dt = checked.indoor_temperature.value - checked.outdoor_temperature.value
        prov = _normative_provenance("A.8 empty sum", "kg/h", "No listed permeable elements in provenance-complete inventory; empty A.8 sum")
        body = {"status": "RESOLVED", "room_id": checked.room_id, "elements": [],
                "indoor_pressure_mode": checked.pressure_mode, "total_mass_airflow_kg_h": Decimal(0),
                "inside_temperature_c": checked.indoor_temperature.value,
                "outside_temperature_c": checked.outdoor_temperature.value, "delta_t_c": dt,
                "q_inf_w": Decimal(0), "diagnostics": ["NO_AIR_PERMEABLE_ELEMENTS_IN_COMPLETE_INVENTORY"],
                "provenance_digest": _digest([checked.model_dump(mode="json"), prov.model_dump(mode="json")]), "digest": "0" * 64}
        return RoomInfiltrationHeatLossResult.model_validate({**body, "digest": _digest({k: v for k, v in body.items() if k != "digest"})})

    missing = []
    for name, value, code in (("indoor_temperature", checked.indoor_temperature, "INDOOR_DESIGN_TEMPERATURE_REQUIRED"),
                              ("outdoor_temperature", checked.outdoor_temperature, "CLIMATE_DESIGN_TEMPERATURE_REQUIRED"),
                              ("building_height", checked.building_height_m, "BUILDING_HEIGHT_REQUIRED"),
                              ("wind", checked.wind_speed_cold_design_m_s, "DESIGN_WIND_PARAMETER_REQUIRED"),
                              ("aerodynamics", checked.aerodynamic_coefficients, "SP20_AERODYNAMIC_MODEL_REQUIRED")):
        if value is None:
            missing.append(code)
    if checked.pressure_inventory != "COMPLETE":
        missing.append("AIR_PERMEABLE_ELEMENT_INVENTORY_REQUIRED")
    if checked.pressure_mode == "OTHER_ORGANIZED_VENTILATION" and checked.indoor_reference_pressure_pa is None:
        missing.append("INDOOR_REFERENCE_PRESSURE_REQUIRED")
    if checked.indoor_temperature and checked.indoor_temperature.units != "°C":
        missing.append("INDOOR_DESIGN_TEMPERATURE_UNIT_INVALID")
    if checked.outdoor_temperature and checked.outdoor_temperature.units != "°C":
        missing.append("OUTDOOR_DESIGN_TEMPERATURE_UNIT_INVALID")
    for element in checked.elements:
        if (checked.building_height_m is not None and element.center_height_m is not None
                and not Decimal(0) <= element.center_height_m < checked.building_height_m):
            missing.append(f"{element.element_id}:ELEMENT_HEIGHT_OUTSIDE_BUILDING")
        for value, code in ((element.center_height_m, "ELEMENT_CENTER_HEIGHT_REQUIRED"),
                            (element.wind_height_coefficient, "DESIGN_WIND_HEIGHT_COEFFICIENT_REQUIRED")):
            if value is None:
                missing.append(f"{element.element_id}:{code}")
    if missing:
        body = {"status": "INCOMPLETE", "room_id": checked.room_id, "elements": [], "indoor_pressure_mode": checked.pressure_mode,
                "diagnostics": sorted(set(missing)), "provenance_digest": _digest(checked.model_dump(mode="json")), "digest": "0" * 64}
        return RoomInfiltrationHeatLossResult.model_validate({**body, "digest": _digest({k: v for k, v in body.items() if k != "digest"})})

    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        rho_o = _density_raw(checked.outdoor_temperature.value)
        rho_i = _density_raw(checked.indoor_temperature.value)
        wind = checked.wind_speed_cold_design_m_s
        aero_delta = checked.aerodynamic_coefficients.windward_coefficient - checked.aerodynamic_coefficients.leeward_coefficient
        h_building = checked.building_height_m
        if checked.pressure_mode == "NO_ORGANIZED_VENTILATION":
            pv = h_building * (rho_o - rho_i) * Decimal("9.81") + rho_o * wind * wind / Decimal(4) * aero_delta * (checked.elements[0].wind_height_coefficient or Decimal(0) if checked.elements else Decimal(0))
            # A.10 is room reference pressure; use a sourced representative height coefficient.
            # Different element heights cannot silently share it.
            if checked.elements and len({e.wind_height_coefficient for e in checked.elements}) != 1:
                return _infiltration_incomplete(checked, "A10_ROOM_WIND_HEIGHT_FACTOR_MUST_BE_UNAMBIGUOUS")
            pv_prov = _normative_provenance("A.10", "Pa", "A.10 natural/no-organized-ventilation indoor reference pressure")
        elif checked.pressure_mode == "BALANCED_SUPPLY_EXHAUST":
            pv = Decimal(0)
            pv_prov = _normative_provenance("A.9 text", "Pa", "Balanced supply/exhaust: neglect P_v as expressly permitted")
        else:
            pv = checked.indoor_reference_pressure_pa
            pv_prov = checked.indoor_reference_pressure_provenance
        element_results = []
        total_mass = Decimal(0)
        incomplete = []
        for element in checked.elements:
            if checked.pressure_mode == "NO_ORGANIZED_VENTILATION":
                kz_for_pv = element.wind_height_coefficient
                # A.10's k_z(e) is a room-level term; the explicit equality check above
                # ensures it is not selected heuristically from unrelated element data.
                pv = h_building * (rho_o - rho_i) * Decimal("9.81") + rho_o * wind * wind / Decimal(4) * aero_delta * kz_for_pv
            delta_p = ((h_building - element.center_height_m) * (rho_o - rho_i) * Decimal("9.81")
                       + rho_o * wind * wind / Decimal(2) * aero_delta * element.wind_height_coefficient - pv)
            exponent, exponent_prov = element.effective_filtering_exponent()
            if delta_p <= 0:
                mass = Decimal(0)
                diagnostics = ["NO_INWARD_PRESSURE_FLOW"]
            else:
                if delta_p > Decimal("100000"):
                    incomplete.append(f"{element.element_id}:PRESSURE_OUT_OF_DOMAIN")
                ratio = delta_p / Decimal("10")
                mass = ratio ** exponent * element.area_m2 / element.air_permeability_resistance_ru_m2_h_pa_kg
                diagnostics = []
            pressure_prov = _normative_provenance("A.9", "Pa", "A.9 pressure difference derived from sourced H, h, densities, wind, aerodynamic coefficients, k_z and P_v")
            ebody = {"element_id": element.element_id, "pressure_difference_pa": delta_p,
                     "pressure_provenance": pressure_prov, "filtering_exponent": exponent,
                     "mass_airflow_kg_h": mass, "diagnostics": diagnostics,
                     "source_provenance": [element.area_provenance, element.resistance_provenance,
                                           element.center_height_provenance, element.wind_height_coefficient_provenance,
                                           exponent_prov, pv_prov], "digest": "0" * 64}
            element_results.append(InfiltrationElementResult.model_validate({**ebody, "digest": _digest({k: v for k, v in ebody.items() if k != "digest"})}))
            total_mass += mass
        if incomplete:
            return _infiltration_incomplete(checked, *incomplete)
        dt = checked.indoor_temperature.value - checked.outdoor_temperature.value
        qinf = dt * total_mass * Decimal("1") * Decimal("0.28")
    norm = _normative_provenance("A.7", "W", "Qinf=(Ti-To)*Ginf*cv*0.28; cv=1 kJ/(kg K)")
    sources = [checked.indoor_temperature.provenance, checked.outdoor_temperature.provenance,
               checked.building_height_provenance, checked.wind_speed_provenance,
               checked.aerodynamic_coefficients.provenance, checked.pressure_inventory_provenance, pv_prov, norm]
    sources.extend(p for e in checked.elements for p in (e.area_provenance, e.resistance_provenance, e.center_height_provenance, e.wind_height_coefficient_provenance))
    body = {"status": "RESOLVED", "room_id": checked.room_id, "elements": element_results,
            "indoor_pressure_mode": checked.pressure_mode, "indoor_reference_pressure_pa": pv,
            "outdoor_air_density_kg_m3": rho_o, "indoor_air_density_kg_m3": rho_i,
            "total_mass_airflow_kg_h": total_mass,
            "inside_temperature_c": checked.indoor_temperature.value,
            "outside_temperature_c": checked.outdoor_temperature.value, "delta_t_c": dt,
            "q_inf_w": qinf, "diagnostics": [], "provenance_digest": _digest([p.model_dump(mode="json") for p in sources]), "digest": "0" * 64}
    return RoomInfiltrationHeatLossResult.model_validate({**body, "digest": _digest({k: v for k, v in body.items() if k != "digest"})})


def _infiltration_incomplete(data: InfiltrationInput, *diagnostics: str) -> RoomInfiltrationHeatLossResult:
    body = {"status": "INCOMPLETE", "room_id": data.room_id, "elements": [], "indoor_pressure_mode": data.pressure_mode,
            "diagnostics": sorted(set(diagnostics)), "provenance_digest": _digest(data.model_dump(mode="json")), "digest": "0" * 64}
    return RoomInfiltrationHeatLossResult.model_validate({**body, "digest": _digest({k: v for k, v in body.items() if k != "digest"})})


class A1ComponentInput(StrictProjectModel):
    status: Literal["RESOLVED", "NOT_APPLICABLE", "UNRESOLVED", "INPUT_REQUIRED", "METHOD_REQUIRED"]
    value_w: Decimal | None = None
    provenance: AuthoringProvenance | None = None
    applicability_provenance: AuthoringProvenance | None = None
    reason: str | None = None

    @field_validator("value_w", mode="before")
    @classmethod
    def decimal_value(cls, value):
        return _d(value)

    @model_validator(mode="after")
    def coherent(self):
        if self.status == "RESOLVED" and (self.value_w is None or self.provenance is None or self.provenance.units != "W"):
            raise ValueError("RESOLVED_A1_COMPONENT_REQUIRES_VALUE_AND_PROVENANCE")
        if self.status == "NOT_APPLICABLE" and (self.value_w is not None or self.applicability_provenance is None):
            raise ValueError("NOT_APPLICABLE_COMPONENT_REQUIRES_EXPLICIT_PROVENANCE")
        if self.status in {"UNRESOLVED", "INPUT_REQUIRED", "METHOD_REQUIRED"} and self.value_w is not None:
            raise ValueError("UNRESOLVED_COMPONENT_CANNOT_CARRY_VALUE")
        return self


class MaterialEquipmentWarmingHeatLoadResult(A1ComponentInput):
    """Typed SP60 A.6 handoff; NA is an evidenced applicability decision."""

    status: Literal["RESOLVED", "NOT_APPLICABLE", "INPUT_REQUIRED", "METHOD_REQUIRED"]
    calculation_or_applicability_scope: str | None = None

    @model_validator(mode="after")
    def scope_is_traceable(self):
        if self.status == "NOT_APPLICABLE" and not self.calculation_or_applicability_scope:
            raise ValueError("Q_MTS_NOT_APPLICABLE_REQUIRES_ROOM_SCOPE")
        if self.status in {"INPUT_REQUIRED", "METHOD_REQUIRED"} and not self.reason:
            raise ValueError("Q_MTS_BLOCKER_REQUIRES_REASON")
        return self


class RoomHeatingLoadComponents(StrictProjectModel):
    room_id: str
    q_tr_w: Decimal | None = None
    q_vent_w: Decimal | None = None
    q_inf_w: Decimal | None = None
    q_mts_w: Decimal | None = None
    q_mts_assessment: MaterialEquipmentWarmingHeatLoadResult | A1ComponentInput
    current_a1_internal_gains_semantics: Literal["NOT_PRESENT_IN_CURRENT_A1_FORMULA"] = "NOT_PRESENT_IN_CURRENT_A1_FORMULA"
    internal_gains_assessment: Literal["NOT_AN_A1_COMPONENT"] = "NOT_AN_A1_COMPONENT"
    known_component_subtotal_w: Decimal | None = None
    a1_total_heating_load_w: Decimal | None = None
    total_design_heating_load_w: Decimal | None = None
    completeness_status: Literal["INCOMPLETE", "COMPLETE_SP60_A1_COMPONENTS"]
    normative_method_digest: str
    canonical_revision_digest: str
    input_component_digests: dict[str, str]
    a1_formula_digest: str
    unresolved_components: list[str]
    ventilation_status: str
    infiltration_status: str
    digest: str


def aggregate_sp60_a1_components(
    *, transmission_result,
    ventilation_result: RoomVentilationHeatLossResult,
    infiltration_result: RoomInfiltrationHeatLossResult,
    q_mts: MaterialEquipmentWarmingHeatLoadResult | A1ComponentInput,
    internal_gains_classification_provenance: AuthoringProvenance | None = None,
) -> RoomHeatingLoadComponents:
    """Aggregate only A.1 terms; report other items without inventing terms.

    `internal_gains_classification_provenance` remains an ignored compatibility
    argument for earlier callers; current A.1 has no Q_byt term to classify.
    """
    room_id = transmission_result.room_id
    qtr = transmission_result.room_transmission_heat_loss_w
    unresolved = []
    if ventilation_result.room_id != room_id:
        unresolved.append("VENTILATION_ROOM_ID_MISMATCH")
    if infiltration_result.room_id != room_id:
        unresolved.append("INFILTRATION_ROOM_ID_MISMATCH")
    if qtr is None or transmission_result.completeness_status != "COMPLETE_DETAILED":
        unresolved.append("Q_TR_COMPLETE_RESULT_REQUIRED")
    qvent = ventilation_result.q_vent_w if ventilation_result.status == "RESOLVED" and ventilation_result.room_id == room_id else None
    if qvent is None:
        unresolved.extend(ventilation_result.diagnostics or ["Q_VENT_UNRESOLVED"])
    qinf = infiltration_result.q_inf_w if infiltration_result.status in {"RESOLVED", "INFILTRATION_SUPPRESSED_BY_DESIGN_PRESSURIZATION"} and infiltration_result.room_id == room_id else None
    if qinf is None:
        unresolved.extend(infiltration_result.diagnostics or ["Q_INF_UNRESOLVED"])
    if infiltration_result.status == "INFILTRATION_SUPPRESSED_BY_DESIGN_PRESSURIZATION":
        vent_makeup = ventilation_result.pressurization_makeup_airflow_m3_h if ventilation_result.status == "RESOLVED" else None
        if vent_makeup != infiltration_result.ventilation_makeup_airflow_required_in_q_vent_m3_h:
            unresolved.append("PRESSURIZATION_MAKEUP_MUST_BE_INCLUDED_IN_Q_VENT")
    if q_mts.status in {"UNRESOLVED", "INPUT_REQUIRED", "METHOD_REQUIRED"}:
        unresolved.append(q_mts.reason or ("Q_MTS_INPUT_REQUIRED" if q_mts.status == "INPUT_REQUIRED" else
                                           "Q_MTS_METHOD_REQUIRED" if q_mts.status == "METHOD_REQUIRED" else
                                           "Q_MTS_UNRESOLVED"))
    elif q_mts.status == "RESOLVED":
        qmts = q_mts.value_w
    else:
        qmts = Decimal(0)
        if (not getattr(q_mts, "calculation_or_applicability_scope", None)
                and not q_mts.reason):
            unresolved.append("Q_MTS_NOT_APPLICABLE_SCOPE_REQUIRED")
    if q_mts.status in {"UNRESOLVED", "INPUT_REQUIRED", "METHOD_REQUIRED"}:
        qmts = None
    known = [value for value in (qtr, qvent, qinf, qmts) if value is not None]
    subtotal = sum(known, Decimal(0)) if known else None
    complete = not unresolved and len(known) == 4
    total = subtotal if complete else None
    body = {"room_id": room_id, "q_tr_w": qtr, "q_vent_w": qvent, "q_inf_w": qinf, "q_mts_w": qmts,
            "q_mts_assessment": q_mts,
            "internal_gains_assessment": "NOT_AN_A1_COMPONENT",
            "known_component_subtotal_w": subtotal, "a1_total_heating_load_w": total,
            "total_design_heating_load_w": total,
            "completeness_status": "COMPLETE_SP60_A1_COMPONENTS" if complete else "INCOMPLETE",
            "unresolved_components": sorted(set(unresolved)),
            "ventilation_status": ventilation_result.status,
            "infiltration_status": infiltration_result.status,
            "normative_method_digest": SP60_AIR_METHOD_DIGEST,
            "canonical_revision_digest": SP60_CANONICAL_REVISION_DIGEST,
            "input_component_digests": {
                "q_tr": getattr(transmission_result, "calculation_digest", None) or
                        _digest({"room_id": room_id, "q_tr_w": qtr,
                                 "completeness_status": transmission_result.completeness_status}),
                "q_vent": ventilation_result.digest,
                "q_inf": infiltration_result.digest,
                "q_mts": _digest(q_mts.model_dump(mode="json")),
            },
            "a1_formula_digest": _digest({"formula": SP60_AIR_METHOD_PACKAGE["formula_records"]["A.1"],
                                           "canonical_revision": SP60_CANONICAL_REVISION_DIGEST})}
    return RoomHeatingLoadComponents(**body, digest=_digest(body))


class ProjectAirExchangeObservation(StrictProjectModel):
    status: Literal["UNCLASSIFIED_PROJECT_AIR_EXCHANGE_VALUE", "NOT_FOUND"]
    value: Decimal | None = None
    units: str | None = None
    provenance: AuthoringProvenance | None = None
    promoted_to_ventilation_airflow: Literal[False] = False
    promoted_to_infiltration_airflow: Literal[False] = False


def audit_project_air_exchange(adapter_result) -> ProjectAirExchangeObservation:
    matches = [item for item in adapter_result.mapped_fields
               if item.target_path == "sizing.room.insulation.air_changes_per_hour"]
    if not matches:
        return ProjectAirExchangeObservation(status="NOT_FOUND")
    if len(matches) != 1:
        raise ValueError("DUPLICATE_PROJECT_AIR_EXCHANGE_VALUE")
    item = matches[0]
    value = _d(item.value)
    provenance = AuthoringProvenance(
        source_type="project_data", project_source_kind=item.provenance.source_kind,
        source_reference=item.provenance.source_file, source_sha256=item.provenance.source_sha256,
        source_field=item.provenance.source_path,
        transformation="preserved as project AirExchangeRate observation; not classified as SP60 A.4 required cold-period design airflow",
        units="1/h")
    return ProjectAirExchangeObservation(status="UNCLASSIFIED_PROJECT_AIR_EXCHANGE_VALUE", value=value,
                                         units="1/h", provenance=provenance)


class ProjectAirHeatSource(StrictProjectModel):
    project_id: str
    building_id: str
    level_id: str
    room_id: str
    project_revision_digest: str
    indoor_temperature: SourcedDecimal | None = None
    outdoor_temperature: SourcedDecimal | None = None
    project_air_exchange: ProjectAirExchangeObservation


def project_air_heat_source_from_adapter(adapter_result, *, climate_result=None, climate_request=None) -> ProjectAirHeatSource:
    """Narrow in-memory source binding; intentionally never promotes ACH."""
    from agent.building_heat_loss import project_transmission_source_from_adapter

    transmission_source = project_transmission_source_from_adapter(
        adapter_result, boundaries=[], climate_result=climate_result,
        climate_request=climate_request)
    indoor = (SourcedDecimal(value=transmission_source.indoor_design_temperature_c,
                             units="°C", provenance=transmission_source.indoor_temperature_provenance)
              if transmission_source.indoor_design_temperature_c is not None else None)
    outdoor = (SourcedDecimal(value=transmission_source.climate_outdoor_design_temperature_c,
                              units="°C", provenance=transmission_source.climate_temperature_provenance)
               if transmission_source.climate_outdoor_design_temperature_c is not None else None)
    return ProjectAirHeatSource(
        project_id=transmission_source.project_id,
        building_id=transmission_source.building_id,
        level_id=transmission_source.level_id,
        room_id=transmission_source.room_id,
        project_revision_digest=transmission_source.project_revision_digest,
        indoor_temperature=indoor, outdoor_temperature=outdoor,
        project_air_exchange=audit_project_air_exchange(adapter_result))
