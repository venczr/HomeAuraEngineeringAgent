"""Fail-closed mapping from project-derived room records to UFH inputs.

This module deliberately does not infer design assumptions. Explicit UFH and
engineering values must arrive with a source reference for each effective
field before they can become production request models.
"""
from __future__ import annotations

import hashlib
import json
import copy
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal, get_args, get_origin

from pydantic import Field, JsonValue, ValidationError, model_validator
from pydantic.main import BaseModel
from pydantic_core import to_jsonable_python

from agent.domain_models import DomainDocument
from agent.floor_heating_sizing import UFHSizingRequest
from agent.project_models import StrictProjectModel
from agent.rooms_api import MagiCadRoom, RoomBoundary, RoomExportReport
from agent.ufh_candidate_adapter import UFHEngineeringIntegrationInputs
from agent.ufh_project_engineering_profile import (
    ClassifiedInputGap,
    FIELD_CLASSIFICATION,
    LEGACY_POLICY_FIELDS,
    ProfileValueProvenance,
    STRUCTURAL_DEFAULT_FIELDS,
    default_ufh_routing_policy,
    UFHProjectEngineeringProfile,
)


SHA256 = r"^[0-9a-f]{64}$"


class ProjectFieldProvenance(StrictProjectModel):
    source_kind: Literal[
        "canonical_project_domain",
        "room_extraction",
        "linked_engineering_metadata",
        "routing_algorithm_policy",
        "test_only",
        "SYSTEM_STRUCTURAL_DEFAULT",
        "SYSTEM_ROUTING_POLICY",
    ]
    source_file: str = Field(min_length=1, max_length=1024)
    source_sha256: str = Field(pattern=SHA256)
    source_path: str = Field(min_length=1, max_length=512)
    transformation: str | None = Field(default=None, max_length=512)


class ProjectRoomUfhSource(StrictProjectModel):
    """One identified project room plus separately sourced UFH design data."""

    project_id: str = Field(min_length=1, max_length=128)
    building_id: str | None = Field(default=None, max_length=128)
    level_id: str | None = Field(default=None, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    room_source_handle: str | None = Field(default=None, max_length=128)
    room_export: RoomExportReport
    project_domain: DomainDocument | None = None
    project_domain_source_file: str | None = Field(default=None, max_length=1024)
    project_domain_sha256: str | None = Field(default=None, pattern=SHA256)
    selected_room: MagiCadRoom
    source_file: str = Field(min_length=1, max_length=1024)
    source_sha256: str = Field(pattern=SHA256)
    source_kind: Literal["room_extraction", "test_only"] = (
        "room_extraction"
    )
    identity_provenance: dict[str, ProjectFieldProvenance] = Field(
        default_factory=dict
    )
    # Explicit linked source fragments in the same shape as the destination
    # models. Every supplied leaf (including null/empty values) needs provenance.
    sizing_inputs: Any = Field(default_factory=dict)
    engineering_inputs: Any = Field(default_factory=dict)
    engineering_profile: UFHProjectEngineeringProfile | None = None
    input_provenance: dict[str, ProjectFieldProvenance] = Field(
        default_factory=dict
    )
    authoritative_boundary: RoomBoundary | None = None
    boundary_provenance: ProjectFieldProvenance | None = None

    @model_validator(mode="after")
    def require_domain_source_reference(self) -> "ProjectRoomUfhSource":
        if (self.authoritative_boundary is None) != (self.boundary_provenance is None):
            raise ValueError("authoritative boundary requires its source provenance")
        if self.authoritative_boundary is not None and self.selected_room.Boundary is not None:
            raise ValueError("cannot override an existing extracted room boundary")
        if self.project_domain is None and (
            self.project_domain_source_file is not None
            or self.project_domain_sha256 is not None
        ):
            raise ValueError("project domain source reference has no domain object")
        if self.project_domain is not None and (
            self.project_domain_source_file is None
            or self.project_domain_sha256 is None
        ):
            raise ValueError("project domain object requires its source file and digest")
        return self


class MappedProjectField(StrictProjectModel):
    target_path: str = Field(min_length=1, max_length=256)
    value: JsonValue
    provenance: ProjectFieldProvenance
    applied_to_request: bool


class ProjectAdapterDiagnostic(StrictProjectModel):
    code: str = Field(min_length=1, max_length=96)
    path: str | None = Field(default=None, max_length=256)
    message: str = Field(min_length=1, max_length=512)


class ProjectUfhAdapterResult(StrictProjectModel):
    status: Literal["READY", "INCOMPLETE", "INVALID"]
    project_id: str
    building_id: str | None
    level_id: str | None
    room_id: str
    source_file: str
    source_digest: str = Field(pattern=SHA256)
    project_domain_digest: str | None = Field(default=None, pattern=SHA256)
    identity_provenance: dict[str, ProjectFieldProvenance] = Field(
        default_factory=dict
    )
    room_geometry_digest: str | None = Field(default=None, pattern=SHA256)
    sizing_request: UFHSizingRequest | None = None
    engineering_inputs: UFHEngineeringIntegrationInputs | None = None
    mapped_fields: list[MappedProjectField] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    classified_gaps: list[ClassifiedInputGap] = Field(default_factory=list)
    diagnostics: list[ProjectAdapterDiagnostic] = Field(default_factory=list)
    adapter_digest: str = Field(pattern=SHA256)


class ProjectOwnedEngineeringValue(StrictProjectModel):
    """One project-owned value eligible for profile authoring."""

    canonical_field_path: str = Field(min_length=1, max_length=256)
    value: JsonValue
    units: str = Field(min_length=1, max_length=64)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    source_type: Literal["room_extraction", "canonical_project_domain"]
    source_reference: str = Field(min_length=1, max_length=1024)
    source_field: str = Field(min_length=1, max_length=512)
    source_digest: str = Field(pattern=SHA256)
    transformation: str = Field(min_length=1, max_length=512)
    authority_class: Literal["PROJECT_DATA_VALUE"]


class ProjectOwnedEngineeringValues(StrictProjectModel):
    """Validated project-to-profile binding set, scoped to one room source."""

    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    values: list[ProjectOwnedEngineeringValue] = Field(default_factory=list)

    @model_validator(mode="after")
    def values_match_scope_and_are_unique(self):
        paths = [item.canonical_field_path for item in self.values]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate project-owned engineering field")
        if any(item.project_id != self.project_id or item.room_id != self.room_id
               for item in self.values):
            raise ValueError("project-owned engineering value identity mismatch")
        return self

    @property
    def binding_digest(self) -> str:
        return _canonical_digest(self.model_dump(mode="json"))


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# This registry binds only values whose meaning and project ownership are
# already established by the project engineering contract. Add fields here
# only with an authoritative adapter mapping, canonical units, and provenance.
PROJECT_OWNED_PROFILE_BINDINGS: dict[str, tuple[str, str, str]] = {
    "room.insulation.air_changes_per_hour": (
        "sizing.room.insulation.air_changes_per_hour",
        "1/h",
        "BUILDING_PHYSICS",
    ),
    "sizing.room.insulation.air_changes_per_hour": (
        "sizing.room.insulation.air_changes_per_hour",
        "1/h",
        "BUILDING_PHYSICS",
    ),
}


def collect_project_owned_ufh_values(
    adapter_result: ProjectUfhAdapterResult,
) -> ProjectOwnedEngineeringValues:
    """Collect only explicitly registered project-owned values from adapter output."""
    bound: dict[str, ProjectOwnedEngineeringValue] = {}
    if adapter_result.status == "INVALID":
        return ProjectOwnedEngineeringValues(
            project_id=adapter_result.project_id,
            room_id=adapter_result.room_id,
            values=[],
        )
    for field in adapter_result.mapped_fields:
        binding = PROJECT_OWNED_PROFILE_BINDINGS.get(field.target_path)
        if binding is None:
            continue
        canonical_path, units, expected_owner = binding
        if FIELD_CLASSIFICATION.get(canonical_path) != expected_owner:
            continue
        if field.provenance.source_kind not in {
            "room_extraction", "canonical_project_domain",
        }:
            continue
        if (isinstance(field.value, bool)
                or not isinstance(field.value, (int, float))
                or not math.isfinite(float(field.value))):
            continue
        candidate = ProjectOwnedEngineeringValue(
            canonical_field_path=canonical_path,
            value=field.value,
            units=units,
            project_id=adapter_result.project_id,
            room_id=adapter_result.room_id,
            source_type=field.provenance.source_kind,
            source_reference=field.provenance.source_file,
            source_field=field.provenance.source_path,
            source_digest=field.provenance.source_sha256,
            transformation=field.provenance.transformation or "direct authoritative project mapping",
            authority_class="PROJECT_DATA_VALUE",
        )
        previous = bound.get(canonical_path)
        if previous is not None and previous != candidate:
            raise ValueError(f"PROJECT_OWNED_VALUE_CONFLICT:{canonical_path}")
        bound[canonical_path] = candidate
    return ProjectOwnedEngineeringValues(
        project_id=adapter_result.project_id,
        room_id=adapter_result.room_id,
        values=[bound[path] for path in sorted(bound)],
    )


def _source_fragment(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return {}


def _field_model(annotation: Any) -> type[BaseModel] | None:
    if get_origin(annotation) in (list, tuple, dict):
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if get_origin(annotation) is not None:
        args = get_args(annotation)
        if type(None) in args:
            return None
        models = [item for item in args
                  if isinstance(item, type) and issubclass(item, BaseModel)]
        if len(models) == 1:
            return models[0]
    return None


def _list_model(annotation: Any) -> type[BaseModel] | None:
    if get_origin(annotation) not in (list, tuple):
        return None
    for item in get_args(annotation):
        if isinstance(item, type) and issubclass(item, BaseModel):
            return item
    return None


def _missing_model_fields(
    model_type: type[BaseModel], value: Any, prefix: str,
) -> list[str]:
    if not isinstance(value, dict):
        return [prefix]
    missing: list[str] = []
    for name, field in model_type.model_fields.items():
        path = f"{prefix}.{name}" if prefix else name
        # Only schema tags have a harmless, non-physical system-owned default.
        # Other model defaults can affect geometry or engineering and remain
        # fail-closed until explicitly sourced.
        full_path = f"{prefix}.{name}" if prefix else name
        if (f"sizing.{full_path}" in STRUCTURAL_DEFAULT_FIELDS
                or f"sizing.{full_path}" in LEGACY_POLICY_FIELDS):
            continue
        # The kernel computes one temperature result per solve mode; the
        # opposite optional field is therefore not a required external input.
        if model_type is UFHEngineeringIntegrationInputs:
            mode = value.get("mode")
            if (name == "sigma_k" and mode == "solve_return") or (
                name == "theta_supply_c" and mode == "solve_supply"
            ):
                continue
        list_nested = _list_model(field.annotation)
        nested = _field_model(field.annotation)
        if name not in value:
            if nested is not None:
                missing.extend(_missing_model_fields(nested, {}, path))
            else:
                missing.append(path)
            continue
        child = value[name]
        if child is None:
            continue
        if list_nested is not None and isinstance(child, list):
            for index, item in enumerate(child):
                missing.extend(
                    _missing_model_fields(list_nested, item, f"{path}[{index}]")
                )
            continue
        if nested is not None:
            missing.extend(_missing_model_fields(nested, child, path))
    return missing


def _leaf_paths(value: Any, prefix: str) -> list[str]:
    if isinstance(value, dict) and value:
        return [path for key, child in value.items()
                for path in _leaf_paths(child, f"{prefix}.{key}")]
    if isinstance(value, (list, tuple)) and value:
        return [path for index, child in enumerate(value)
                for path in _leaf_paths(child, f"{prefix}[{index}]")]
    return [prefix]


def _set_path(target: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor = target
    for part in parts[:-1]:
        current = cursor.get(part)
        if current is None:
            current = {}
            cursor[part] = current
        if not isinstance(current, dict):
            raise ValueError(f"incompatible source mapping at {part}")
        cursor = current
    cursor[parts[-1]] = value


def _get_path(source: dict[str, Any], dotted: str) -> Any:
    cursor: Any = source
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _has_path(source: dict[str, Any], dotted: str) -> bool:
    cursor: Any = source
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return False
        cursor = cursor[part]
    return True


def _integer_mm_from_m2(value: float) -> int:
    # Explicit decimal half-up conversion, not Python's banker's rounding.
    return int((Decimal(str(value)) * Decimal(1_000_000)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP,
    ))


def _boundary_points_mm(boundary: Any) -> list[dict[str, int]]:
    """Convert selected room boundary coordinates to integer millimetres."""
    unit = boundary.DrawingUnits.strip().lower()
    if unit in {"mm", "millimeter", "millimeters", "millimetre", "millimetres"}:
        factor = Decimal(1)
    elif unit in {"m", "meter", "meters", "metre", "metres"}:
        factor = Decimal(1000)
    elif boundary.MetersPerDrawingUnit is not None:
        factor = Decimal(str(boundary.MetersPerDrawingUnit)) * Decimal(1000)
    else:
        raise ValueError("boundary drawing units have no explicit mm conversion")
    points = [
        {
            "x_mm": int((Decimal(str(vertex.X)) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
            "y_mm": int((Decimal(str(vertex.Y)) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        }
        for vertex in boundary.Vertices
    ]
    if any(
        "SegmentType" not in vertex.model_fields_set
        or "Bulge" not in vertex.model_fields_set
        or vertex.SegmentType != "Line"
        or vertex.Bulge != 0.0
        for vertex in boundary.Vertices
    ):
        raise ValueError(
            "curved or underspecified boundary segments are not linearized by this adapter"
        )
    if len(points) < 3:
        raise ValueError("room boundary has fewer than three vertices")
    if points[0] != points[-1]:
        points.append(dict(points[0]))
    return points


def _polygon_area_mm2(points: list[dict[str, int]]) -> int:
    doubled = sum(
        points[index]["x_mm"] * points[index + 1]["y_mm"]
        - points[index + 1]["x_mm"] * points[index]["y_mm"]
        for index in range(len(points) - 1)
    )
    return abs(doubled) // 2


def _selected_room_matches(source: ProjectRoomUfhSource) -> bool:
    source_handle = source.room_source_handle or source.room_id
    if source.selected_room.SourceHandle != source_handle:
        return False
    report_room = next(
        (room for room in source.room_export.Rooms
         if room.SourceHandle == source_handle),
        None,
    )
    return (
        report_room is not None
        and report_room.model_dump(mode="json")
        == source.selected_room.model_dump(mode="json")
    )


def _project_domain_matches(source: ProjectRoomUfhSource) -> bool:
    document = source.project_domain
    if document is None:
        return True
    if source.project_id not in {document.project.name, str(document.project.stable_id)}:
        return False
    for building in document.project.buildings:
        if str(building.stable_id) != source.building_id:
            continue
        for level in building.levels:
            if str(level.stable_id) != source.level_id:
                continue
            for room in level.rooms:
                if (source.room_id in {
                            str(room.stable_id), room.source_handle,
                            (room.source_handle or "").upper(),
                        }
                        and (room.source_handle or "").casefold()
                        == (source.room_source_handle
                            or source.selected_room.SourceHandle).casefold()):
                    return True
    return False


def _room_provenance(
    source: ProjectRoomUfhSource, json_path: str, transformation: str | None = None,
) -> ProjectFieldProvenance:
    return ProjectFieldProvenance(
        source_kind=source.source_kind,
        source_file=source.source_file,
        source_sha256=source.source_sha256,
        source_path=json_path,
        transformation=transformation,
    )


def _map_selected_room(
    source: ProjectRoomUfhSource,
) -> tuple[dict[str, Any], list[MappedProjectField], str | None,
           dict[str, ProjectFieldProvenance], list[ProjectAdapterDiagnostic]]:
    room = source.selected_room
    values: dict[str, Any] = {}
    fields: list[MappedProjectField] = []
    provenance: dict[str, ProjectFieldProvenance] = {}
    diagnostics: list[ProjectAdapterDiagnostic] = []

    # IDs use actual extraction identities; absent Building/Level identities
    # are never replaced with the DOMAIN adapter's provisional placeholders.
    identity_provenance = dict(source.identity_provenance)
    if source.project_domain is not None:
        domain_fields = {
            "identity.project_id": "$.project.name",
            "identity.building_id": "$.project.buildings[].stable_id",
            "identity.level_id": "$.project.buildings[].levels[].stable_id",
            "identity.room_id": "$.project.buildings[].levels[].rooms[].source_handle",
        }
        for identity_path, json_path in domain_fields.items():
            identity_provenance.setdefault(
                identity_path,
                ProjectFieldProvenance(
                    source_kind=(
                        "test_only" if source.source_kind == "test_only"
                        else "canonical_project_domain"
                    ),
                    source_file=source.project_domain_source_file,
                    source_sha256=source.project_domain_sha256,
                    source_path=json_path,
                ),
            )
    p_project = identity_provenance.get("identity.project_id") or (
        _room_provenance(source, "$.DrawingName", "use drawing/project label as source identifier")
    )
    p_room = identity_provenance.get("identity.room_id") or (
        _room_provenance(source, "$.Rooms[].SourceHandle", "use persistent DWG source handle")
    )
    identity_provenance.setdefault("identity.project_id", p_project)
    identity_provenance.setdefault("identity.room_id", p_room)
    for target, value, prov in (
        ("coverage_request.project_id", source.project_id, p_project),
        ("coverage_request.room_id", source.room_id, p_room),
    ):
        _set_path(values, target, value)
        provenance[f"sizing.{target}"] = prov
        fields.append(MappedProjectField(
            target_path=target, value=value, provenance=prov,
            applied_to_request=True,
        ))

    for identity_name, identity_value in (
        ("building_id", source.building_id), ("level_id", source.level_id),
    ):
        identity_path = f"identity.{identity_name}"
        if identity_value is None:
            diagnostics.append(ProjectAdapterDiagnostic(
                code=f"MISSING_{identity_name.upper()}", path=identity_path,
                message=f"No authoritative {identity_name.replace('_', ' ')} is present in the selected room source.",
            ))
        else:
            prov = identity_provenance.get(identity_path)
            if prov is None:
                diagnostics.append(ProjectAdapterDiagnostic(
                    code="MISSING_PROVENANCE", path=identity_path,
                    message="Identity value lacks a source reference.",
                ))

    explicit = set(room.model_fields_set)
    raw = room.model_dump(mode="json", by_alias=True)
    area_prov = _room_provenance(
        source, "$.Rooms[].NetAreaM2",
        "NetAreaM2 × 1,000,000; round half up to integer mm²",
    ) if "NetAreaM2" in explicit and room.NetAreaM2 is not None else None
    if area_prov is not None:
        area = _integer_mm_from_m2(room.NetAreaM2)
        fields.append(MappedProjectField(
            target_path="room.room_area_mm2", value=area,
            provenance=area_prov, applied_to_request=False,
        ))

    direct_mappings = (
        ("RoomHeightMm", "room.room_height_mm", "mm value rounded half up to integer mm"),
        ("HeatingTemperatureC", "room.indoor_temperature_c", None),
        ("AirExchangeRate", "room.insulation.air_changes_per_hour", None),
    )
    for source_field, target, transform in direct_mappings:
        if source_field not in explicit or raw.get(source_field) is None:
            continue
        value = raw[source_field]
        if target.endswith("room_height_mm"):
            value = int(Decimal(str(value)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP,
            ))
        _set_path(values, target, value)
        prov = _room_provenance(
            source, f"$.Rooms[].{source_field}", transform,
        )
        provenance[f"sizing.{target}"] = prov
        fields.append(MappedProjectField(
            target_path=target, value=value, provenance=prov,
            applied_to_request=True,
        ))

    # Room extraction records outdoor temperature, not its design-condition
    # semantics; do not alias it to outdoor_design_temperature_c.
    for field_name in (
        "OutdoorTemperatureC", "SupplyAirflowLs", "SupplyAirflowM3H",
        "TotalHeatLossW", "HeatLossWM2", "StructuralHeatLossW",
    ):
        if field_name in explicit and raw.get(field_name) is not None:
            fields.append(MappedProjectField(
                target_path=f"room_source.{field_name}",
                value=raw[field_name],
                provenance=_room_provenance(
                    source, f"$.Rooms[].{field_name}",
                ),
            applied_to_request=False,
        ))

    if source.authoritative_boundary is not None or ("Boundary" in explicit and room.Boundary is not None):
        boundary = source.authoritative_boundary or room.Boundary
        geometry_dict = boundary.model_dump(mode="json", by_alias=True)
        geometry_digest = _canonical_digest(geometry_dict)
        # Geometry is not silently promoted: closed/valid/selected geometry
        # still needs linked UFH collector, exterior-side and routing inputs.
        if not (boundary.IsClosed and boundary.IsPlanar
                and boundary.Diagnostics.IsValid
                and boundary.Diagnostics.IsSupported):
            diagnostics.append(ProjectAdapterDiagnostic(
                code="INVALID_ROOM_BOUNDARY", path="room.Boundary",
                message="Extracted room boundary is not both supported, valid, and closed.",
            ))
        else:
            try:
                points = _boundary_points_mm(boundary)
                area_mm2 = _polygon_area_mm2(points)
                if area_mm2 <= 0:
                    raise ValueError("room boundary area is not positive")
                boundary_value = {"points": points}
                boundary_provenance = source.boundary_provenance or _room_provenance(
                    source,
                    "$.Rooms[].Boundary.Vertices",
                    "convert drawing units to mm using explicit unit scale; round each coordinate half up to 1 mm; close polygon if needed",
                )
                _set_path(values, "coverage_request.boundary", boundary_value)
                _set_path(values, "room.room_area_mm2", area_mm2)
                for leaf_path in _leaf_paths(
                    boundary_value, "sizing.coverage_request.boundary",
                ):
                    provenance[leaf_path] = boundary_provenance
                provenance["sizing.room.room_area_mm2"] = boundary_provenance.model_copy(update={
                    "transformation": "shoelace area from mapped integer-mm boundary",
                })
                fields.extend((
                    MappedProjectField(
                        target_path="coverage_request.boundary",
                        value=boundary_value,
                        provenance=boundary_provenance,
                        applied_to_request=True,
                    ),
                    MappedProjectField(
                        target_path="room.room_area_mm2",
                        value=area_mm2,
                        provenance=provenance["sizing.room.room_area_mm2"],
                        applied_to_request=True,
                    ),
                ))
            except (ValueError, ArithmeticError) as error:
                diagnostics.append(ProjectAdapterDiagnostic(
                    code="INVALID_ROOM_BOUNDARY",
                    path="room.Boundary",
                    message=str(error)[:512],
                ))
    else:
        geometry_digest = None
        diagnostics.append(ProjectAdapterDiagnostic(
            code="MISSING_ROOM_BOUNDARY", path="coverage_request.boundary",
            message="No boundary is attached to the selected room export record.",
        ))

    return values, fields, geometry_digest, provenance, diagnostics, identity_provenance


def _explicit_provenance_diagnostics(
    values: dict[str, Any], provenance: dict[str, ProjectFieldProvenance],
    prefix: str,
) -> list[ProjectAdapterDiagnostic]:
    result: list[ProjectAdapterDiagnostic] = []
    if not values:
        return result
    for path in _leaf_paths(values, prefix):
        if path not in provenance:
            result.append(ProjectAdapterDiagnostic(
                code="MISSING_PROVENANCE", path=path,
                message="Mapped input has no source file, digest, and field reference.",
            ))
    return result


def _profile_provenance_to_project(
    provenance: ProfileValueProvenance,
    path: str,
    diagnostics: list[ProjectAdapterDiagnostic],
) -> ProjectFieldProvenance | None:
    if provenance.source_kind not in {
        "canonical_project_domain",
        "room_extraction",
        "linked_engineering_metadata",
        "routing_algorithm_policy",
        "test_only",
    }:
        diagnostics.append(ProjectAdapterDiagnostic(
            code="PROVENANCE_TYPE_UNSUPPORTED",
            path=path,
            message="Profile provenance source kind cannot be represented as project-field provenance.",
        ))
        return None
    try:
        return ProjectFieldProvenance(
            source_kind=provenance.source_kind,
            source_file=provenance.source_file,
            source_sha256=provenance.source_sha256,
            source_path=provenance.source_path,
            transformation=provenance.transformation,
        )
    except ValidationError as error:
        diagnostics.append(ProjectAdapterDiagnostic(
            code="PROFILE_PROVENANCE_INVALID",
            path=path,
            message=str(error)[:512],
        ))
        return None


def build_ufh_sizing_request_from_project_room(
    source: ProjectRoomUfhSource,
) -> ProjectUfhAdapterResult:
    """Map available project fields and fail closed on every absent UFH input.

    ``sizing_inputs`` and ``engineering_inputs`` are explicit linked-source
    fragments. All effective fields (including defaulted/null/empty fields)
    must be present and have provenance before typed production models issue.
    """
    diagnostics: list[ProjectAdapterDiagnostic] = []
    if not _selected_room_matches(source):
        diagnostics.append(ProjectAdapterDiagnostic(
            code="ROOM_IDENTITY_MISMATCH", path="identity.room_id",
            message="Selected room handle does not match the requested project room or report.",
        ))

    (mapped, mapped_fields, geometry_digest, auto_provenance, room_diags,
     identity_provenance) = (
        _map_selected_room(source)
    )
    diagnostics.extend(room_diags)
    if (source.project_domain is not None
            and _canonical_digest(source.project_domain.model_dump(mode="json"))
            != source.project_domain_sha256):
        diagnostics.append(ProjectAdapterDiagnostic(
            code="PROJECT_DOMAIN_DIGEST_MISMATCH",
            path="project_domain",
            message="Supplied project-domain SHA-256 does not match its canonical serialized content.",
        ))
    if (source.source_kind == "room_extraction"
            and "identity.project_id" not in source.identity_provenance):
        drawing_project = source.room_export.DrawingName.rsplit(".", 1)[0]
        if source.project_id != drawing_project:
            diagnostics.append(ProjectAdapterDiagnostic(
                code="PROJECT_ID_MISMATCH", path="identity.project_id",
                message="Project identifier does not match the source drawing name and has no canonical identity reference.",
            ))

    profile_sizing = (
        source.engineering_profile.sizing_fragment()
        if source.engineering_profile is not None else {}
    )
    sizing_values = profile_sizing
    sizing_provenance = (
        dict(source.engineering_profile.provenance)
        if source.engineering_profile is not None else {}
    )
    explicit_sizing_values = _source_fragment(source.sizing_inputs)
    # Explicit request fragments supersede a bundled profile only when equal;
    # conflicting sources are never silently blended.
    def merge(target: dict[str, Any], src: dict[str, Any], prefix: str = "") -> None:
        for key, value in src.items():
            path = f"{prefix}.{key}" if prefix else key
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                merge(target[key], value, path)
            elif target[key] != value:
                diagnostics.append(ProjectAdapterDiagnostic(
                    code="SOURCE_VALUE_CONFLICT", path=f"sizing.{path}",
                    message="Explicit sizing input conflicts with the project engineering profile.",
                ))
    merge(sizing_values, explicit_sizing_values)
    sizing_provenance = {
        **sizing_provenance,
        **{path: provenance for path, provenance in source.input_provenance.items()
           if path.startswith("sizing.")},
    }
    # Extraction values have higher priority than linked engineering settings.
    merge(sizing_values, mapped)
    sizing_provenance = {**sizing_provenance, **auto_provenance}

    # The report itself contains only one source room identity; if the caller
    # passed a cloned/constructed room, ensure it matches its persisted entry.
    if not _selected_room_matches(source):
        diagnostics.append(ProjectAdapterDiagnostic(
            code="ROOM_NOT_FOUND", path="room_export.Rooms",
            message="Requested room handle is absent from the source report.",
        ))
    if not _project_domain_matches(source):
        diagnostics.append(ProjectAdapterDiagnostic(
            code="PROJECT_DOMAIN_IDENTITY_MISMATCH",
            path="project_domain.project.buildings[].levels[].rooms[]",
            message="Project/building/level/room identifiers do not resolve to the selected source handle in the supplied domain object.",
        ))

    missing = [
        f"sizing.{path}"
        for path in _missing_model_fields(UFHSizingRequest, sizing_values, "")
    ]
    missing.extend(
        f"identity.{name}"
        for name, value in (("building_id", source.building_id), ("level_id", source.level_id))
        if value is None
    )
    diagnostics.extend(_explicit_provenance_diagnostics(
        sizing_values, sizing_provenance, "sizing",
    ))
    missing.extend(
        item.path for item in diagnostics
        if item.code == "MISSING_PROVENANCE" and item.path is not None
    )

    engineering_values = (
        source.engineering_profile.engineering_fragment()
        if source.engineering_profile is not None else {}
    )
    explicit_engineering_values = _source_fragment(source.engineering_inputs)
    merge(engineering_values, explicit_engineering_values)
    engineering_provenance = {
        **({path: provenance for path, provenance in source.engineering_profile.provenance.items()
            if path.startswith("engineering.")} if source.engineering_profile is not None else {}),
        **{path: provenance for path, provenance in source.input_provenance.items()
           if path.startswith("engineering.")},
    }
    derived_engineering_fields: list[MappedProjectField] = []
    for engineering_field, sizing_path, sizing_provenance_path, transform in (
        ("theta_indoor_c", "room.indoor_temperature_c",
         "sizing.room.indoor_temperature_c",
         "reuse the explicitly sourced room indoor design setpoint"),
        ("theta_below_c", "room.insulation.floor_boundary_temperature_c",
         "sizing.room.insulation.floor_boundary_temperature_c",
         "reuse the explicitly sourced floor-boundary design condition"),
    ):
        if engineering_field in engineering_values or not _has_path(sizing_values, sizing_path):
            continue
        value = _get_path(sizing_values, sizing_path)
        _set_path(engineering_values, engineering_field, value)
        source_provenance = sizing_provenance.get(sizing_provenance_path)
        if source_provenance is not None:
            linked_provenance = source_provenance.model_copy(update={
                "transformation": transform,
            })
            engineering_provenance[f"engineering.{engineering_field}"] = linked_provenance
            mapped_provenance = (
                _profile_provenance_to_project(
                    linked_provenance, f"engineering.{engineering_field}",
                    diagnostics,
                )
                if isinstance(linked_provenance, ProfileValueProvenance)
                else linked_provenance
            )
            if mapped_provenance is not None:
                derived_engineering_fields.append(MappedProjectField(
                    target_path=f"engineering.{engineering_field}",
                    value=value,
                    provenance=mapped_provenance,
                    applied_to_request=True,
                ))

    # Explicitly materialize only the non-physical schema tags. Their
    # provenance identifies the system rule, not a project source.
    routing_policy = default_ufh_routing_policy()
    system_defaults = {
        "sizing.schema_version": "1.0",
        "sizing.coverage_request.schema_version": "1.0",
        "sizing.coverage_request.requested_circuit_count": None,
        "sizing.coverage_request.request_reference": None,
        "sizing.coverage_request.turn_radius_mm": routing_policy.turn_radius_mm,
        "sizing.coverage_request.routing_mode": routing_policy.routing_mode,
        "sizing.coverage_request.field_spacing_mm": None,
        "sizing.coverage_request.perimeter_spacing_mm": None,
        "sizing.coverage_request.perimeter_band_depth_mm": None,
        "sizing.coverage_request.preferred_topology": None,
        "sizing.coverage_request.installation_grid_spacing_mm": None,
        "sizing.coverage_request.perimeter_priority_mode": routing_policy.perimeter_priority_mode,
        "sizing.coverage_request.minimum_circuit_length_mm": routing_policy.minimum_circuit_length_mm,
        "sizing.coverage_request.maximum_circuit_length_mm": routing_policy.maximum_circuit_length_mm,
    }
    routing_policy_fields = {
        "sizing.coverage_request.requested_circuit_count",
        "sizing.coverage_request.routing_mode",
        "sizing.coverage_request.turn_radius_mm",
        "sizing.coverage_request.perimeter_priority_mode",
    }
    for path, model_value in system_defaults.items():
        short_path = path.removeprefix("sizing.")
        if _has_path(sizing_values, short_path):
            continue
        _set_path(sizing_values, short_path, model_value)
        source_kind = (
            "SYSTEM_ROUTING_POLICY"
            if path in LEGACY_POLICY_FIELDS or path in routing_policy_fields
            else "SYSTEM_STRUCTURAL_DEFAULT"
        )
        source_label = (
            "LEGACY_MVP_ROUTING_POLICY" if path in LEGACY_POLICY_FIELDS
            else f"{routing_policy.policy_id}:{routing_policy.policy_version}"
            if path in routing_policy_fields else "SYSTEM_STRUCTURAL_DEFAULT"
        )
        default_digest = _canonical_digest({
            "source": source_label,
            "policy_digest": (
                routing_policy.policy_digest
                if path in LEGACY_POLICY_FIELDS or path in routing_policy_fields
                else None
            ),
            "path": path,
            "value": model_value,
        })
        default_prov = ProjectFieldProvenance(
            source_kind=source_kind,
            source_file=source_label,
            source_sha256=default_digest,
            source_path=(
                f"$policy.{path}"
                if path in LEGACY_POLICY_FIELDS or path in routing_policy_fields
                else f"$defaults.{path}"
            ),
            transformation=("materialize fixed schema tag; no physical calculation effect"
                            if path.endswith("schema_version") else
                            "materialize fixed 40-80 m legacy routing policy; not an EN 1264 limit"
                            if path in LEGACY_POLICY_FIELDS else
                            "materialize versioned HomeAura routing algorithm policy"
                            if path in routing_policy_fields else
                            "materialize documented API/routing structural default; provenance retained"),
        )
        sizing_provenance[path] = default_prov
        mapped_fields.append(MappedProjectField(
            target_path=path.removeprefix("sizing."), value=model_value,
            provenance=default_prov, applied_to_request=True,
        ))
    missing.extend(
        f"engineering.{path}"
        for path in _missing_model_fields(
            UFHEngineeringIntegrationInputs, engineering_values, "",
        )
    )
    diagnostics.extend(_explicit_provenance_diagnostics(
        engineering_values, engineering_provenance, "engineering",
    ))
    missing.extend(
        item.path for item in diagnostics
        if item.code == "MISSING_PROVENANCE" and item.path is not None
    )

    request: UFHSizingRequest | None = None
    engineering: UFHEngineeringIntegrationInputs | None = None
    validation_failed = False
    if not any(item.code == "SOURCE_VALUE_CONFLICT" for item in diagnostics):
        if not any(path.startswith("sizing.") for path in missing):
            try:
                request = UFHSizingRequest.model_validate(sizing_values)
            except ValidationError as error:  # preserve source errors; never repair
                validation_failed = True
                diagnostics.append(ProjectAdapterDiagnostic(
                    code="PROJECT_UFH_INPUT_INVALID", path="sizing",
                    message=str(error)[:512],
                ))
        if not any(path.startswith("engineering.") for path in missing):
            try:
                engineering = UFHEngineeringIntegrationInputs.model_validate(
                    engineering_values
                )
            except ValidationError as error:
                validation_failed = True
                diagnostics.append(ProjectAdapterDiagnostic(
                    code="PROJECT_ENGINEERING_INPUT_INVALID", path="engineering",
                    message=str(error)[:512],
                ))
    if request is not None and engineering is not None:
        if (engineering.theta_indoor_c != request.room.indoor_temperature_c
                or engineering.theta_below_c != request.room.insulation.floor_boundary_temperature_c):
            validation_failed = True
            diagnostics.append(ProjectAdapterDiagnostic(
                code="ENGINEERING_SIZING_TEMPERATURE_MISMATCH",
                path="engineering.theta_indoor_c",
                message="Engineering temperatures must match explicit sizing-room boundary inputs.",
            ))
            request = None
            engineering = None

    if (missing or any(item.code == "MISSING_PROVENANCE" for item in diagnostics)
            or any(item.code.startswith("MISSING_") for item in diagnostics)):
        diagnostics.append(ProjectAdapterDiagnostic(
            code="PROJECT_UFH_INPUT_INCOMPLETE", path=None,
            message="Required project/UFH/engineering values or authoritative identities are absent.",
        ))
        status: Literal["READY", "INCOMPLETE", "INVALID"] = "INCOMPLETE"
        request = None
        engineering = None
    elif (validation_failed
          or any(item.code.endswith("_MISMATCH") for item in diagnostics)
          or any(item.code == "PROJECT_ID_MISMATCH" for item in diagnostics)
          or any(item.code == "PROJECT_DOMAIN_DIGEST_MISMATCH" for item in diagnostics)
          or any(item.code == "INVALID_ROOM_BOUNDARY" for item in diagnostics)
          or any(item.code == "SOURCE_VALUE_CONFLICT" for item in diagnostics)):
        status = "INVALID"
        request = None
        engineering = None
    else:
        status = "READY"

    # Include explicitly linked request fields for audit visibility.
    source_sizing_json = (
        source.sizing_inputs.model_dump(mode="json")
        if isinstance(source.sizing_inputs, BaseModel)
        else to_jsonable_python(source.sizing_inputs)
    )
    if source.engineering_profile is not None:
        profile_sizing_json = to_jsonable_python(
            source.engineering_profile.sizing_fragment()
        )
        for path in _leaf_paths(profile_sizing_json, "sizing"):
            prov = source.engineering_profile.provenance.get(path)
            if prov is not None:
                mapped_prov = _profile_provenance_to_project(prov, path, diagnostics)
                if mapped_prov is not None:
                    mapped_fields.append(MappedProjectField(
                        target_path=path,
                        value=_get_path(profile_sizing_json, path.removeprefix("sizing.")),
                        provenance=mapped_prov,
                        applied_to_request=status == "READY",
                    ))
    for path, value in sorted((source_sizing_json or {}).items()):
        # Nested typed request fields remain in the source payload; top-level
        # audit entries are complemented by provenance at each leaf.
        for leaf_path in _leaf_paths({path: value}, "sizing"):
            prov = source.input_provenance.get(leaf_path)
            if prov is not None:
                mapped_fields.append(MappedProjectField(
                    target_path=leaf_path,
                    value=_get_path({path: value}, leaf_path.removeprefix("sizing.")),
                    provenance=prov,
                    applied_to_request=status == "READY",
                ))

    source_engineering_json = (
        source.engineering_inputs.model_dump(mode="json")
        if isinstance(source.engineering_inputs, BaseModel)
        else to_jsonable_python(source.engineering_inputs)
    )
    if source.engineering_profile is not None:
        profile_engineering_json = to_jsonable_python(
            source.engineering_profile.engineering_fragment()
        )
        for path in _leaf_paths(profile_engineering_json, "engineering"):
            prov = source.engineering_profile.provenance.get(path)
            if prov is not None:
                mapped_prov = _profile_provenance_to_project(prov, path, diagnostics)
                if mapped_prov is not None:
                    mapped_fields.append(MappedProjectField(
                        target_path=path,
                        value=_get_path(profile_engineering_json, path.removeprefix("engineering.")),
                        provenance=mapped_prov,
                        applied_to_request=status == "READY",
                    ))
    for path, value in sorted((source_engineering_json or {}).items()):
        for leaf_path in _leaf_paths({path: value}, "engineering"):
            prov = source.input_provenance.get(leaf_path)
            if prov is not None:
                mapped_fields.append(MappedProjectField(
                    target_path=leaf_path,
                    value=_get_path({path: value}, leaf_path.removeprefix("engineering.")),
                    provenance=prov,
                    applied_to_request=status == "READY",
                ))

    if geometry_digest is None:
        boundary = _get_path(sizing_values, "coverage_request.boundary")
        if boundary is not None:
            geometry_digest = _canonical_digest(boundary)

    mapped_fields.extend(derived_engineering_fields)
    if any(item.code in {"PROFILE_PROVENANCE_INVALID", "PROVENANCE_TYPE_UNSUPPORTED"}
           for item in diagnostics):
        status = "INVALID"
        request = None
        engineering = None
    mapped_fields = [
        field.model_copy(update={
            "applied_to_request": status == "READY" and field.applied_to_request,
        })
        for field in mapped_fields
    ]
    payload = {
        "status": status,
        "project_id": source.project_id,
        "building_id": source.building_id,
        "level_id": source.level_id,
        "room_id": source.room_id,
        "source_file": source.source_file,
        "source_digest": source.source_sha256,
        "project_domain_digest": source.project_domain_sha256,
        "identity_provenance": identity_provenance,
        "room_geometry_digest": geometry_digest,
        "sizing_request": request.model_dump(mode="json") if request else None,
        "engineering_inputs": engineering,
        "mapped_fields": [field.model_dump(mode="json") for field in mapped_fields],
        "missing_inputs": sorted(set(missing)),
        "classified_gaps": [
            ClassifiedInputGap(
                path=path,
                source_class=FIELD_CLASSIFICATION.get(path, "UNKNOWN"),
                owner=("room/project source" if FIELD_CLASSIFICATION.get(path) in {
                    "ROOM_GEOMETRY", "STRUCTURAL_METADATA"} else
                    "project engineering profile"),
                action=(
                    "reuse sizing.room.insulation.floor_boundary_temperature_c with provenance"
                    if path == "engineering.theta_below_c" else
                    "source authoritative value" if FIELD_CLASSIFICATION.get(path) not in {
                        "CALCULATED", "OPTIONAL_EXPLICIT_EMPTY", "STRUCTURAL_METADATA"} else
                    "derive from source geometry or materialize explicit structural semantics"
                ),
                required_externally=(
                    path != "engineering.theta_below_c"
                    and FIELD_CLASSIFICATION.get(path) not in {
                        "CALCULATED", "STRUCTURAL_METADATA",
                    }
                ),
                default_allowed=False,
            ).model_dump(mode="json")
            for path in sorted(set(missing))
        ],
        "diagnostics": [item.model_dump(mode="json") for item in diagnostics],
    }
    digest_payload = {
        **payload,
        "identity_provenance": {
            key: value.model_dump(mode="json")
            for key, value in identity_provenance.items()
        },
        "sizing_source_values": to_jsonable_python(sizing_values),
        "engineering_source_values": to_jsonable_python(engineering_values),
        "input_provenance": {
            key: value.model_dump(mode="json")
            for key, value in source.input_provenance.items()
        },
        "engineering_inputs": (
            engineering.model_dump(mode="json") if engineering else None
        ),
    }
    return ProjectUfhAdapterResult(
        **payload,
        adapter_digest=_canonical_digest(digest_payload),
    )


__all__ = [
    "MappedProjectField",
    "ProjectAdapterDiagnostic",
    "ProjectFieldProvenance",
    "ProjectOwnedEngineeringValue",
    "ProjectOwnedEngineeringValues",
    "ProjectRoomUfhSource",
    "ProjectUfhAdapterResult",
    "PROJECT_OWNED_PROFILE_BINDINGS",
    "collect_project_owned_ufh_values",
    "build_ufh_sizing_request_from_project_room",
]
