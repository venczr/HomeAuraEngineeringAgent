"""Read-only SP 60 source binding/readiness for Test_01 room 101.

This module inventories provenance-bearing project evidence and prepares a
compact question plan. It deliberately does not invoke any SP 60 calculation,
UFH sizing, routing, kernel, coverage, or retry entrypoint.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from agent.project_models import StrictProjectModel
from agent.test01_geometry_source_authority import assess_test01_geometry_authority
from agent.test01_pdf_project_source_ingestion import load_test01_pdf_project_source_ingestion
from agent.ufh_project_adapter import (
    ProjectUfhAdapterResult,
    build_ufh_sizing_request_from_project_room,
    collect_project_owned_ufh_values,
)
from agent.ufh_project_engineering_source_completion import (
    complete_project_engineering_profile_sources,
)


BindingStatus = Literal[
    "RESOLVED", "DERIVED", "UNRESOLVED", "NOT_APPLICABLE",
    "BLOCKED_BY_PARENT_DEPENDENCY",
]
Readiness = Literal["READY", "NOT_READY", "CONDITIONAL"]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_jsonable(value), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class BindingEvidence(StrictProjectModel):
    source_reference: str = Field(min_length=1, max_length=1024)
    source_field: str = Field(min_length=1, max_length=512)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transformation: str = Field(min_length=1, max_length=512)


class SP60InputBinding(StrictProjectModel):
    input_id: str = Field(min_length=1, max_length=96)
    status: BindingStatus
    value: Any = None
    units: str | None = Field(default=None, max_length=64)
    evidence: list[BindingEvidence] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=512)


class Test01MinimumInputQuestion(StrictProjectModel):
    question_id: str = Field(min_length=1, max_length=96)
    group: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=512)
    answer_type: Literal["location", "choice", "source_package", "structured"]
    options: list[str] = Field(default_factory=list)
    reuses_question_id: str | None = None
    dependency_conditions: dict[str, list[str]] = Field(default_factory=dict)
    resolves_inputs: list[str] = Field(min_length=1)
    follow_up_is_conditional: bool = False


class Test01QuestionDependencyRule(StrictProjectModel):
    parent_question_id: str = Field(min_length=1, max_length=96)
    trigger_kind: Literal["ANSWER", "RESOLVER_RESULT"] = "ANSWER"
    when_answers: list[str] = Field(min_length=1)
    activate_input_groups: list[str] = Field(min_length=1)
    reuse_question_ids: list[str] = Field(default_factory=list)
    note: str = Field(min_length=1, max_length=512)


class Test01MinimumRequiredInputSet(StrictProjectModel):
    questions: list[Test01MinimumInputQuestion]
    dependency_rules: list[Test01QuestionDependencyRule]
    deferred_conditional_inputs: list[str]
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    def as_questionnaire_questions(self):
        """Adapt this readiness plan to the existing UI-neutral Question model."""
        from agent.ufh_pre_generation_questionnaire import Question

        converted = []
        for item in self.questions:
            answer_type = "structured" if item.answer_type == "source_package" else item.answer_type
            converted.append(Question(
                question_id=item.reuses_question_id or item.question_id,
                group=item.group,
                prompt=item.prompt,
                answer_type=answer_type,
                allowed_options=item.options,
                required=True,
                why_required="Required to resolve SP60 room-load source readiness; does not itself assign a physical property.",
                targets=item.resolves_inputs,
                dependency_conditions=item.dependency_conditions,
            ))
        return converted


class Test01SP60ReadinessAssessment(StrictProjectModel):
    resolved_input_count: int = Field(ge=0)
    derived_input_count: int = Field(ge=0)
    unresolved_input_count: int = Field(ge=0)
    blocked_input_count: int = Field(ge=0)
    blocking_dependency_groups: list[str]
    q_tr: Readiness
    q_vent: Readiness
    q_inf: Readiness
    q_mts: Readiness
    a1: Readiness
    ufh_handoff: Readiness
    reasons: list[str]


class Test01SP60EngineeringBinding(StrictProjectModel):
    project_id: str
    room_id: str
    room_code: str | None = None
    room_name: str | None = None
    authority_status: str
    source_inventory: dict[str, Any]
    adapter_status: str
    adapter_missing_input_count: int
    adapter_digest: str | None = None
    project_owned_binding_digest: str | None = None
    input_matrix: list[SP60InputBinding]
    minimum_required_input_set: Test01MinimumRequiredInputSet
    readiness: Test01SP60ReadinessAssessment
    diagnostics: list[str] = Field(default_factory=list)
    source_set_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _evidence(reference: str, field: str, digest: str,
              transformation: str = "direct source observation; no value conversion") -> BindingEvidence:
    return BindingEvidence(source_reference=reference, source_field=field,
                           source_sha256=digest, transformation=transformation)


def _matrix_item(input_id: str, status: BindingStatus, reason: str, *, value=None,
                 units: str | None = None,
                 evidence: list[BindingEvidence] | None = None) -> SP60InputBinding:
    return SP60InputBinding(input_id=input_id, status=status, value=value,
                            units=units, evidence=evidence or [], reason=reason)


def _minimum_inputs(unresolved: set[str]) -> Test01MinimumRequiredInputSet:
    """Collapse dependent field gaps to human-level project questions."""
    definitions = [
        Test01MinimumInputQuestion(
            question_id="sp60.climate.locality", group="CLIMATE",
            prompt="В каком населённом пункте и регионе расположен проект?",
            answer_type="location", reuses_question_id="climate",
            resolves_inputs=["CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE", "DESIGN_WIND_SOURCE"],
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.room.use_and_qmts_scope", group="ROOM_USE",
            prompt="Как используется помещение и связаны ли с ним процессы нагрева поступающих материалов, оборудования или транспорта?",
            answer_type="choice", options=["OCCUPIED_ROOM_NO_WARMING_PROCESS", "WARMING_PROCESS_PRESENT", "UNKNOWN"],
            resolves_inputs=["ROOM_USE", "QMTS_APPLICABILITY"],
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.boundary.below", group="BOUNDARY_CONDITIONS",
            prompt="Что находится непосредственно под помещением (по проекту: отапливаемое помещение, неотапливаемое пространство, грунт, улица, вентилируемая полость или другое)?",
            answer_type="choice", options=["HEATED_ROOM", "UNHEATED_SPACE", "GROUND", "OUTDOOR", "VENTILATED_VOID", "OTHER"],
            reuses_question_id="below", resolves_inputs=["BELOW_BOUNDARY_SEMANTICS"],
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.boundary.above", group="BOUNDARY_CONDITIONS",
            prompt="Что находится непосредственно над помещением (по проекту: отапливаемое помещение, неотапливаемое пространство, кровля/улица, вентилируемая полость или другое)?",
            answer_type="choice", options=["HEATED_ROOM", "UNHEATED_SPACE", "ROOF_OUTDOOR", "VENTILATED_VOID", "OTHER"],
            reuses_question_id="above", resolves_inputs=["ABOVE_BOUNDARY_SEMANTICS"],
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.openings.inventory", group="OPENINGS",
            prompt="Предоставьте проектный перечень окон, дверей и иных проёмов на границах помещения либо явно подтвердите их отсутствие.",
            answer_type="choice", options=["PROJECT_INVENTORY", "EXPLICIT_NONE", "UNKNOWN"],
            resolves_inputs=["OPENING_INVENTORY", "NET_BOUNDARY_AREAS"],
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.envelope.construction_sources", group="CONSTRUCTION",
            prompt="Какой проектный источник описывает конструкции стен, пола и потолка/покрытия для этого помещения?",
            answer_type="source_package", reuses_question_id="envelope",
            resolves_inputs=["CONSTRUCTION_ASSEMBLIES", "U_VALUES"],
            follow_up_is_conditional=True,
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.ventilation.design_basis", group="VENTILATION",
            prompt="Какой проектный расчёт или нормативный источник задаёт требуемый наружный расход воздуха для этого помещения?",
            answer_type="choice", options=["PROJECT_DESIGN_AIRFLOW", "NORMATIVE_AIR_CHANGE_RATE", "PER_PERSON", "SP60_7_4_1", "UNKNOWN"],
            resolves_inputs=["DESIGN_VENTILATION_AIRFLOW", "VENTILATION_AIRFLOW_SEMANTICS"],
            follow_up_is_conditional=True,
        ),
        Test01MinimumInputQuestion(
            question_id="sp60.infiltration.source_package", group="INFILTRATION",
            prompt="Предоставьте расчёт/испытание воздухопроницаемости ограждений и проектные данные о высоте здания, ветре, положении элементов и режиме вентиляции либо укажите источник этих данных.",
            answer_type="source_package",
            resolves_inputs=["INFILTRATION_ELEMENT_INVENTORY", "RU_VALUES", "ELEMENT_ELEVATIONS", "BUILDING_HEIGHT", "DESIGN_WIND", "KZ", "AERODYNAMIC_MODEL", "PRESSURE_MODE"],
            follow_up_is_conditional=True,
        ),
    ]
    # Questions are shown only while their owning group has unresolved inputs.
    group_members = {
        "sp60.climate.locality": {"CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE", "DESIGN_WIND_SOURCE"},
        "sp60.room.use_and_qmts_scope": {"ROOM_USE", "QMTS_APPLICABILITY"},
        "sp60.boundary.below": {"BOUNDARY_SEMANTICS", "BELOW_BOUNDARY_SEMANTICS"},
        "sp60.boundary.above": {"BOUNDARY_SEMANTICS", "ABOVE_BOUNDARY_SEMANTICS"},
        "sp60.openings.inventory": {"OPENING_INVENTORY", "BOUNDARY_AREAS", "NET_BOUNDARY_AREAS"},
        "sp60.envelope.construction_sources": {"CONSTRUCTION_ASSEMBLIES", "U_VALUES", "THERMAL_BRIDGES"},
        "sp60.ventilation.design_basis": {"DESIGN_VENTILATION_AIRFLOW", "VENTILATION_AIRFLOW_SEMANTICS"},
        "sp60.infiltration.source_package": {"INFILTRATION_ELEMENT_INVENTORY", "RU_VALUES", "ELEMENT_ELEVATIONS", "BUILDING_HEIGHT", "DESIGN_WIND", "KZ", "AERODYNAMIC_MODEL", "PRESSURE_MODE"},
    }
    questions = [q for q in definitions if group_members[q.question_id] & unresolved]
    dependency_rules = [
        Test01QuestionDependencyRule(parent_question_id="sp60.envelope.construction_sources",
            when_answers=["PROJECT_ASSEMBLY", "CATALOG_SYSTEM", "LAYERED_CUSTOM_ASSEMBLY", "EXPLICIT_U_VALUE_WITH_PROVENANCE"],
            activate_input_groups=["CONSTRUCTION_SOURCE_DETAILS", "ASSEMBLY_OR_U_VALUE_PROVENANCE"],
            note="Ask for layers, material identity and properties only if the selected source/method requires them."),
        Test01QuestionDependencyRule(parent_question_id="sp60.envelope.construction_sources",
            trigger_kind="RESOLVER_RESULT", when_answers=["INSULATION_LAYER_PRESENT"],
            activate_input_groups=["INDOOR_DESIGN_RELATIVE_HUMIDITY", "CONSTRUCTION_MOISTURE_ZONE"],
            reuse_question_ids=["indoor_rh", "moisture_zone"],
            note="Needed only when an exterior insulation path requires an SP50 operating condition."),
        Test01QuestionDependencyRule(parent_question_id="sp60.ventilation.design_basis",
            when_answers=["PROJECT_DESIGN_AIRFLOW"],
            activate_input_groups=["DIRECT_REQUIRED_OUTDOOR_AIRFLOW_SOURCE"],
            note="Requires explicit required design outside-air airflow, not an unclassified supply observation."),
        Test01QuestionDependencyRule(parent_question_id="sp60.ventilation.design_basis",
            when_answers=["NORMATIVE_AIR_CHANGE_RATE", "PER_PERSON", "SP60_7_4_1"],
            activate_input_groups=["SELECTED_NORMATIVE_OR_DESIGN_VENTILATION_INPUTS"],
            note="Request only the inputs applicable to the chosen, provenance-bearing airflow basis."),
        Test01QuestionDependencyRule(parent_question_id="sp60.infiltration.source_package",
            when_answers=["SOURCE_PACKAGE_AVAILABLE"],
            activate_input_groups=["ELEMENT_RU_ELEVATION_BUILDING_HEIGHT_WIND_KZ_PRESSURE_MODE"],
            note="No individual infiltration value is inferred from ACH or room height."),
        Test01QuestionDependencyRule(parent_question_id="sp60.room.use_and_qmts_scope",
            when_answers=["WARMING_PROCESS_PRESENT"],
            activate_input_groups=["QMTS_METHOD_AND_PROCESS_INPUTS"],
            note="Applicable specialized Q_mts cases remain unresolved until the normative method inputs exist."),
        Test01QuestionDependencyRule(parent_question_id="sp60.openings.inventory",
            when_answers=["PROJECT_INVENTORY"],
            activate_input_groups=["OPENING_GEOMETRY_PARENT_LINKAGE_AREAS"],
            note="An explicit empty inventory is accepted only with project/user confirmation provenance."),
    ]
    deferred = ["INDOOR_DESIGN_RELATIVE_HUMIDITY", "CONSTRUCTION_MOISTURE_ZONE",
                "SP345_INSULATION_OPERATING_CONDITION", "MATERIAL_LAYER_PROPERTIES",
                "THERMAL_BRIDGE_PSI_CHI_DETAILS"]
    body = {"questions": [q.model_dump(mode="json") for q in questions],
            "dependency_rules": [rule.model_dump(mode="json") for rule in dependency_rules],
            "deferred_conditional_inputs": deferred}
    return Test01MinimumRequiredInputSet(
        questions=questions, dependency_rules=dependency_rules,
        deferred_conditional_inputs=deferred, digest=_digest(body))


def _unavailable_binding(project_id: str, room_id: str, decision, reason: str):
    matrix = [
        _matrix_item("IDENTITY", "UNRESOLVED", reason),
        _matrix_item("ROOM_BOUNDARY_GEOMETRY", "UNRESOLVED", reason),
    ]
    minimum = _minimum_inputs({"CLIMATE_LOCALITY", "ROOM_USE", "BOUNDARY_SEMANTICS",
                               "OPENING_INVENTORY", "CONSTRUCTION_ASSEMBLIES",
                               "DESIGN_VENTILATION_AIRFLOW", "INFILTRATION_ELEMENT_INVENTORY"})
    readiness = Test01SP60ReadinessAssessment(resolved_input_count=0, derived_input_count=0,
        unresolved_input_count=len(matrix), blocked_input_count=0,
        blocking_dependency_groups=["AUTHORITATIVE_GEOMETRY_AND_IDENTITY"],
        q_tr="NOT_READY", q_vent="NOT_READY", q_inf="NOT_READY", q_mts="NOT_READY",
        a1="NOT_READY", ufh_handoff="NOT_READY",
        reasons=[reason])
    body = {"project_id": project_id, "room_id": room_id, "room_code": None,
            "room_name": None, "authority_status": decision.status,
            "source_inventory": {}, "adapter_status": "NOT_RUN",
            "adapter_missing_input_count": 0, "adapter_digest": None,
            "project_owned_binding_digest": None,
            "input_matrix": [x.model_dump(mode="json") for x in matrix],
            "minimum_required_input_set": minimum.model_dump(mode="json"),
            "readiness": readiness.model_dump(mode="json"), "diagnostics": [reason],
            "source_set_digest": _digest(decision.model_dump(mode="json"))}
    return Test01SP60EngineeringBinding(**body, digest=_digest(body))


def build_test01_sp60_engineering_binding(
    project_directory: Path,
    ifc_directory: Path,
    *,
    authoring_template_path: Path | None = None,
) -> Test01SP60EngineeringBinding:
    """Read Test_01 evidence and return a typed source/readiness binding only."""
    project_directory = project_directory.resolve()
    ifc_directory = ifc_directory.resolve()
    decision = assess_test01_geometry_authority(project_directory, ifc_directory)
    if decision.status != "AUTHORITATIVE" or decision.ufh_source is None:
        return _unavailable_binding("Test_01", "101DAA3", decision,
                                    "AUTHORITATIVE_TEST01_GEOMETRY_BINDING_REQUIRED")

    source = decision.ufh_source
    adapter = build_ufh_sizing_request_from_project_room(source)
    source_completion = complete_project_engineering_profile_sources(source, project_directory)
    project_owned = collect_project_owned_ufh_values(adapter)
    pdf_source_package = load_test01_pdf_project_source_ingestion(project_directory)
    pdf_source_package_payload = (
        pdf_source_package.model_dump(mode="json") if pdf_source_package is not None else None
    )
    room = source.selected_room
    room_file = Path(source.source_file)
    room_digest = source.source_sha256
    snapshot = project_directory / "exports/model_snapshot.json"
    snapshot_digest = _sha256(snapshot)
    authoring_template_path = authoring_template_path or (
        project_directory.parent.parent / "docs/Test_01_UFH_engineering_profile_authoring_template.json")
    template_digest = _sha256(authoring_template_path)
    profile_candidates = [project_directory / name for name in (
        "ufh_project_engineering_profile.json",
        "exports/engineering/ufh_project_engineering_profile.json",
        "exports/ufh/ufh_project_engineering_profile.json",
    )]
    profile_sources = [{"path": str(path), "status": "PRESENT" if path.is_file() else "NOT_FOUND",
                        "sha256": _sha256(path)} for path in profile_candidates]

    ifc_path = ifc_directory / "Test_01_rooms_ifc4.ifc"
    try:
        import ifcopenshell
        model = ifcopenshell.open(str(ifc_path))
        ifc_counts = {name: len(model.by_type(name)) for name in (
            "IfcSpace", "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcCovering",
            "IfcWindow", "IfcDoor", "IfcOpeningElement", "IfcRelSpaceBoundary",
            "IfcRelSpaceBoundary1stLevel", "IfcRelSpaceBoundary2ndLevel", "IfcMaterial",
            "IfcMaterialLayerSet", "IfcMaterialLayerSetUsage")}
    except Exception:
        ifc_counts = {}

    room_boundary = source.authoritative_boundary
    points = room_boundary.Vertices
    distinct = points[:-1] if len(points) > 1 and points[0].X == points[-1].X and points[0].Y == points[-1].Y else points
    with localcontext() as ctx:
        ctx.prec = 48
        perimeter = Decimal(0)
        for index, point in enumerate(distinct):
            other = distinct[(index + 1) % len(distinct)]
            dx = Decimal(str(other.X)) - Decimal(str(point.X))
            dy = Decimal(str(other.Y)) - Decimal(str(point.Y))
            perimeter += (dx * dx + dy * dy).sqrt()
    geometry_area = decision.evidence.get("ifc_area_m2")
    net_area = Decimal(str(room.NetAreaM2)) if room.NetAreaM2 is not None else None
    height_m = Decimal(str(room.RoomHeightMm)) / Decimal(1000) if room.RoomHeightMm is not None else None
    derived_volume = net_area * height_m if net_area is not None and height_m is not None else None

    evidence_rooms = _evidence(str(room_file), "$.Rooms[].NetAreaM2", room_digest)
    evidence_height = _evidence(str(room_file), "$.Rooms[].RoomHeightMm", room_digest,
                                "convert millimetres to metres exactly by division by 1000")
    evidence_boundary = _evidence(str(ifc_path), "IfcSpace #31.Representation -> #33 WorldVertices",
                                  decision.evidence["hashes"]["ifc"],
                                  "existing production IFC importer; accepted closed CCW boundary")
    evidence_identity = [
        _evidence(str(ifc_path), "IfcSpace #31 -> IfcBuildingStorey GlobalId", decision.evidence["hashes"]["ifc"],
                  "existing reviewed IfcRelAggregates chain"),
        _evidence(str(ifc_path), "IfcSpace #31 -> IfcBuilding GlobalId", decision.evidence["hashes"]["ifc"],
                  "existing reviewed IfcRelAggregates chain"),
    ]
    ach = next((item for item in project_owned.values
                if item.canonical_field_path == "sizing.room.insulation.air_changes_per_hour"), None)
    mapped_indoor = next((item for item in adapter.mapped_fields
                          if item.target_path == "room.indoor_temperature_c"), None)
    mapped_height = next((item for item in adapter.mapped_fields
                          if item.target_path == "room.room_height_mm"), None)
    indoor_ev = (_evidence(mapped_indoor.provenance.source_file, mapped_indoor.provenance.source_path,
                           mapped_indoor.provenance.source_sha256,
                           mapped_indoor.provenance.transformation or "direct mapped room design setpoint")
                 if mapped_indoor is not None else None)
    height_ev = (_evidence(mapped_height.provenance.source_file, mapped_height.provenance.source_path,
                           mapped_height.provenance.source_sha256,
                           mapped_height.provenance.transformation or "direct mapped room height")
                 if mapped_height is not None else evidence_height)
    ach_ev = (_evidence(ach.source_reference, ach.source_field, ach.source_digest, ach.transformation)
              if ach is not None else None)

    # The DWG snapshot has four MagiCAD exterior-wall references whose extents
    # touch the four accepted room-boundary sides. They are retained as
    # candidates, not promoted to a complete thermal boundary inventory: the
    # IFC has no room-boundary relationship, faces, or opening relationships.
    exterior_candidates = []
    if snapshot.is_file():
        snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))
        for entity in snapshot_payload.get("Entities", []):
            if entity.get("Layer") == "MAGIEXTERIORWALLS":
                exterior_candidates.append({"handle": entity.get("Handle"),
                                            "entity_type": entity.get("RxClassName"),
                                            "extents": entity.get("Extents")})
    ifc_has_boundaries = any(ifc_counts.get(key, 0) for key in (
        "IfcRelSpaceBoundary", "IfcRelSpaceBoundary1stLevel", "IfcRelSpaceBoundary2ndLevel"))
    ifc_has_opening_types = any(ifc_counts.get(key, 0) for key in (
        "IfcWindow", "IfcDoor", "IfcOpeningElement"))
    snapshot_has_opening_objects = any(
        entity.get("Layer") in {"MAGIWINDOWS", "MAGIDOORS"}
        for entity in snapshot_payload.get("Entities", [])
    ) if snapshot.is_file() else False

    matrix: list[SP60InputBinding] = [
        _matrix_item("IDENTITY", "RESOLVED", "Authoritative project, building, level and room identities are revision-bound.",
                     value={"project_id": adapter.project_id, "building_id": adapter.building_id,
                            "level_id": adapter.level_id, "room_id": adapter.room_id},
                     evidence=evidence_identity),
        _matrix_item("ROOM_BOUNDARY_GEOMETRY", "RESOLVED", "Accepted, closed, planar, non-self-intersecting IFC room boundary; no thermal meaning inferred from geometry alone.",
                     value={"vertex_count": room_boundary.Diagnostics.DistinctVertexCount if hasattr(room_boundary.Diagnostics, "DistinctVertexCount") else len(distinct),
                            "closed": room_boundary.IsClosed, "orientation": room_boundary.Direction,
                            "area_m2": geometry_area}, units="m, m2", evidence=[evidence_boundary]),
        _matrix_item("ROOM_AREA", "RESOLVED", "MagiCAD NetAreaM2 is retained as the source room area; IFC contour area is reported separately because the two differ.",
                     value={"net_area_m2": net_area, "authoritative_boundary_contour_area_m2": geometry_area,
                            "difference_m2": (Decimal(str(geometry_area)) - net_area) if geometry_area is not None and net_area is not None else None},
                     units="m2", evidence=[evidence_rooms, evidence_boundary]),
        _matrix_item("ROOM_PERIMETER", "DERIVED", "Perimeter derived from ordered vertices of the accepted authoritative boundary.",
                     value=perimeter, units="m", evidence=[evidence_boundary]),
        _matrix_item("ROOM_HEIGHT", "RESOLVED" if room.RoomHeightMm is not None else "UNRESOLVED",
                     "RoomHeightMm is an explicit MagiCAD room-extraction field and existing adapter mapping; it is not building height.",
                     value=room.RoomHeightMm, units="mm", evidence=[height_ev] if height_ev else []),
        _matrix_item("ROOM_VOLUME", "DERIVED" if derived_volume is not None else "BLOCKED_BY_PARENT_DEPENDENCY",
                     "Derived as source NetAreaM2 × source RoomHeightMm; exported NetVolumeM3 is comparison-only and not used as the derivation input.",
                     value=derived_volume, units="m3", evidence=[evidence_rooms, height_ev] if height_ev else [evidence_rooms]),
        _matrix_item("ROOM_USE", "UNRESOLVED", "Room name is a generic test label; no authoritative room-use/process classification is present."),
        _matrix_item("INDOOR_DESIGN_TEMPERATURE", "RESOLVED" if mapped_indoor else "UNRESOLVED",
                     "Reused from the existing project-owned HeatingTemperatureC adapter mapping; no numeric default added.",
                     value=room.HeatingTemperatureC, units="°C", evidence=[indoor_ev] if indoor_ev else []),
        _matrix_item("CLIMATE_LOCALITY", "UNRESOLVED", "No explicit project/questionnaire locality answer is persisted; no geographic inference used."),
        _matrix_item("OUTDOOR_DESIGN_TEMPERATURE", "BLOCKED_BY_PARENT_DEPENDENCY", "Requires explicit climate locality and existing SP131.2025 resolver result."),
        _matrix_item("THERMAL_BOUNDARY_INVENTORY", "UNRESOLVED",
                     "IFC contains no IfcRelSpaceBoundary/IfcWall family. DWG snapshot has four MAGIEXTERIORWALLS candidates touching room edges, but no persisted room-boundary relationship; floor/ceiling inventory also remains unclassified.",
                     value={"ifc_relationships_present": ifc_has_boundaries,
                            "dwg_exterior_wall_candidates": exterior_candidates,
                            "candidate_count": len(exterior_candidates)},
                     evidence=[evidence_boundary, _evidence(str(snapshot), "$.Entities[].Layer= MAGIEXTERIORWALLS", snapshot_digest,
                                                            "read-only object inventory; candidates only, no thermal linkage promoted")] if snapshot_digest else [evidence_boundary]),
        _matrix_item("BOUNDARY_SEMANTICS", "UNRESOLVED", "Candidate exterior-wall labels do not establish a complete thermal boundary inventory or adjacent-zone semantics; above/below remain unknown."),
        _matrix_item("BOUNDARY_AREAS", "BLOCKED_BY_PARENT_DEPENDENCY", "No confirmed thermal fragments and net areas; do not multiply room perimeter by height or count gross areas without opening subtraction."),
        _matrix_item("OPENING_INVENTORY", "UNRESOLVED", "No IFC windows/doors/opening elements and no MagiCAD window/door objects in the current model snapshot; absence in these exports is not an explicit project confirmation of no openings.",
                     value={"ifc_opening_types_present": ifc_has_opening_types,
                            "dwg_window_door_objects_present": snapshot_has_opening_objects},
                     evidence=[evidence_boundary, _evidence(str(snapshot), "$.ModelSpaceEntityCount/Entities", snapshot_digest,
                                                            "current read-only full model snapshot inspected")] if snapshot_digest else [evidence_boundary]),
        _matrix_item("CONSTRUCTION_ASSEMBLIES", "UNRESOLVED", "No authoritative wall/floor/ceiling construction assembly, layer stack, product or catalog assignment exists in inspected project sources."),
        _matrix_item("U_VALUES", "BLOCKED_BY_PARENT_DEPENDENCY", "No construction assemblies/material properties or opening U-values; no U-value is inferred."),
        _matrix_item("THERMAL_BRIDGES", "BLOCKED_BY_PARENT_DEPENDENCY", "Boundary geometry and construction interfaces are not fully bound; no ψ/χ inventory exists."),
        _matrix_item("DESIGN_VENTILATION_AIRFLOW", "UNRESOLVED", "SupplyAirflowM3H/ExtractAirflowM3H exist only as room-extraction observations without accepted SP60 required-outdoor-air semantics."),
        _matrix_item("VENTILATION_AIRFLOW_SEMANTICS", "UNRESOLVED", "The project export does not classify airflow fields as required cold-period outside-air design airflow or establish recirculation treatment."),
        _matrix_item("PROJECT_ACH", "RESOLVED", "AirExchangeRate is bound as project data only; it is not promoted to SP60 design ventilation or infiltration airflow.",
                     value=ach.value if ach else room.AirExchangeRate, units="1/h", evidence=[ach_ev] if ach_ev else [evidence_rooms]),
        _matrix_item("INFILTRATION_ELEMENT_INVENTORY", "BLOCKED_BY_PARENT_DEPENDENCY", "No complete authoritative exterior air-permeable-element inventory or verified opening list."),
        _matrix_item("RU_VALUES", "UNRESOLVED", "No element-specific air-permeability resistance or test source is present."),
        _matrix_item("ELEMENT_ELEVATIONS", "UNRESOLVED", "No elevations of the centers of air-permeable elements are associated with the room."),
        _matrix_item("BUILDING_HEIGHT", "UNRESOLVED", "Room height is not building height; building object has no source-bound total height in the reviewed evidence."),
        _matrix_item("DESIGN_WIND", "BLOCKED_BY_PARENT_DEPENDENCY", "SP131.2025 package currently stores the coldest-five-day temperature parameter only; it has no wind-speed record."),
        _matrix_item("KZ", "UNRESOLVED", "No height-dependent wind-pressure coefficient is bound for the building/elements."),
        _matrix_item("AERODYNAMIC_MODEL", "UNRESOLVED", "Reviewed evidence does not establish the whole-building form/scope required for the simplified SP60 rectangular-building coefficient pair or a resolved SP20 model."),
        _matrix_item("PRESSURE_MODE", "UNRESOLVED", "Supply/extract room observations do not prove balanced ventilation or design pressurization; mode remains unknown."),
        _matrix_item("QMTS_APPLICABILITY", "UNRESOLVED", "Room use/process scope is not authoritatively classified; no blanket zero/not-applicable result is emitted."),
    ]

    unresolved = {item.input_id for item in matrix if item.status in {"UNRESOLVED", "BLOCKED_BY_PARENT_DEPENDENCY"}}
    minimum = _minimum_inputs(unresolved)
    readiness = Test01SP60ReadinessAssessment(
        resolved_input_count=sum(item.status == "RESOLVED" for item in matrix),
        derived_input_count=sum(item.status == "DERIVED" for item in matrix),
        unresolved_input_count=sum(item.status == "UNRESOLVED" for item in matrix),
        blocked_input_count=sum(item.status == "BLOCKED_BY_PARENT_DEPENDENCY" for item in matrix),
        blocking_dependency_groups=["CLIMATE_AND_DESIGN_OUTDOOR", "THERMAL_BOUNDARIES_AND_OPENINGS",
                                    "CONSTRUCTION_AND_THERMAL_BRIDGES", "VENTILATION_AIRFLOW",
                                    "INFILTRATION_PRESSURE_MODEL", "QMTS_APPLICABILITY"],
        q_tr="NOT_READY", q_vent="NOT_READY", q_inf="NOT_READY",
        q_mts="NOT_READY", a1="NOT_READY", ufh_handoff="NOT_READY",
        reasons=["THERMAL_BOUNDARY_AND_NET_AREA_INCOMPLETE", "CONSTRUCTION_U_VALUES_AND_THERMAL_BRIDGES_UNRESOLVED",
                 "CLIMATE_LOCALITY_UNRESOLVED", "VENTILATION_AIRFLOW_SEMANTICS_UNRESOLVED",
                 "INFILTRATION_PRESSURE_INPUTS_UNRESOLVED", "QMTS_APPLICABILITY_UNRESOLVED"],
    )
    source_set = {"authority_decision_digest": decision.decision_digest,
                  "project_revision_digest": adapter.source_sha256 if hasattr(adapter, "source_sha256") else adapter.adapter_digest,
                  "adapter_digest": adapter.adapter_digest,
                  "project_owned_values_digest": project_owned.binding_digest,
                  "rooms_sha256": room_digest, "snapshot_sha256": snapshot_digest,
                  "authoring_template_sha256": template_digest,
                  "profile_sources": profile_sources, "ifc_counts": ifc_counts,
                  "source_completion_status": source_completion.status,
                  "source_completion_digest": source_completion.source_after_digest,
                  "new_authoritative_bindings": len(source_completion.new_bindings),
                  "pdf_project_source_ingestion_digest": (
                      pdf_source_package.manifest_digest if pdf_source_package is not None else None
                  )}
    body = {
        "project_id": adapter.project_id, "room_id": adapter.room_id,
        "room_code": room.Code, "room_name": room.Name,
        "authority_status": decision.status,
        "source_inventory": {**source_set,
            "rooms_export": {"path": str(room_file), "status": "PRESENT", "sha256": room_digest},
            "dwg_binding": {"status": decision.status, "evidence": decision.evidence},
            "ifc_binding": {"path": str(ifc_path), "status": decision.status,
                             "sha256": decision.evidence["hashes"]["ifc"], "entity_counts": ifc_counts},
            "project_engineering_profiles": profile_sources,
            "authoring_template": {"path": str(authoring_template_path),
                                   "status": "TEMPLATE_ONLY" if template_digest else "NOT_FOUND",
                                   "sha256": template_digest,
                                   "resolved_authoring_answers_persisted": False},
            "questionnaire_answers": {"status": "NO_PROJECT_SIDE_ANSWER_STORE_FOUND"},
            "pdf_project_source_ingestion": {
                "status": "PRESENT_VERIFIED" if pdf_source_package is not None else "NOT_FOUND",
                "manifest_path": str(project_directory / "engineering/test01_pdf_project_source_ingestion_v1.json"),
                "package": pdf_source_package_payload,
            },
            "source_completion_audit": {"status": source_completion.status,
                                        "source_before_digest": source_completion.source_before_digest,
                                        "source_after_digest": source_completion.source_after_digest,
                                        "new_bindings": len(source_completion.new_bindings),
                                        "inspected_candidates": len(source_completion.inspected_candidates)}},
        "adapter_status": adapter.status,
        "adapter_missing_input_count": len(adapter.missing_inputs),
        "adapter_digest": adapter.adapter_digest,
        "project_owned_binding_digest": project_owned.binding_digest,
        "input_matrix": [item.model_dump(mode="json") for item in matrix],
        "minimum_required_input_set": minimum.model_dump(mode="json"),
        "readiness": readiness.model_dump(mode="json"),
        "diagnostics": ["READINESS_ONLY_NO_SP60_CALCULATION", "NO_UFH_SIZING_OR_ROUTING"],
        "source_set_digest": _digest(source_set),
    }
    return Test01SP60EngineeringBinding(**body, digest=_digest(body))


__all__ = [
    "BindingEvidence", "SP60InputBinding", "Test01MinimumInputQuestion",
    "Test01QuestionDependencyRule", "Test01MinimumRequiredInputSet", "Test01SP60ReadinessAssessment",
    "Test01SP60EngineeringBinding", "build_test01_sp60_engineering_binding",
]
