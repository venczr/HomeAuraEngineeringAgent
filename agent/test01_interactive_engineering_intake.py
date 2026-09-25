"""Persistent, provenance-bearing Test_01 engineering intake.

This application layer reuses the existing Test_01 source binding and UFH
pre-generation session. It never runs SP60 heat-loss, UFH sizing, or routing.
Answers are stored in a separate project-side JSON artifact; project source
exports remain read-only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, JsonValue, field_validator

from agent.atomic_io import write_text_atomically
from agent.project_models import StrictProjectModel
from agent.test01_sp60_engineering_binding import (
    Test01SP60EngineeringBinding,
    build_test01_sp60_engineering_binding,
)
from agent.ufh_pre_generation_questionnaire import Decision, digest
from agent.ufh_project_pre_generation import (
    UFHPreGenerationSession,
    apply_ufh_questionnaire_answer,
    create_test01_ufh_pre_generation_session,
    profile_readiness,
    replace_ufh_questionnaire_answer,
)


SCHEMA_VERSION = "1.0"
ANSWER_AUTHORITY = "PROJECT_APPROVED_USER_INPUT"
AnswerStatus = Literal["VALID", "STALE", "CONFLICT"]
DashboardStatus = Literal["READY", "PARTIAL", "BLOCKED", "NOT_APPLICABLE"]
IntakeStatus = Literal["INCOMPLETE", "READY_FOR_FIRST_SP60_CALCULATION", "INVALID", "STALE"]


def _canonical(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


class IntakeModel(StrictProjectModel):
    pass


class EngineeringQuestionAnswer(IntakeModel):
    question_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str | None = Field(default=None, max_length=128)
    answer_type: Literal["choice", "text", "structured", "location"]
    normalized_value: JsonValue
    original_user_value: JsonValue
    unit: str | None = Field(default=None, max_length=64)
    authority_class: Literal["PROJECT_APPROVED_USER_INPUT"]
    source_type: Literal["user_project_decision"]
    answered_at: datetime
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_reference: str = Field(min_length=1, max_length=1024)
    source_field: str = Field(min_length=1, max_length=256)
    transformation: str = Field(min_length=1, max_length=512)
    validation_status: AnswerStatus = "VALID"

    @field_validator("answered_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ANSWERED_AT_TIMEZONE_REQUIRED")
        return value


class StaleResolverRecord(IntakeModel):
    resolver_type: str
    result_status_before_invalidation: str
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    invalidated_by_question_id: str
    reason: Literal["PARENT_ANSWER_CHANGED_OR_CLEARED"] = "PARENT_ANSWER_CHANGED_OR_CLEARED"


class EngineeringIntakeAnswerArtifact(IntakeModel):
    schema_version: Literal["1.0"]
    project_id: str
    room_id: str
    source_binding_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    answers: dict[str, EngineeringQuestionAnswer] = Field(default_factory=dict)
    stale_answers: list[EngineeringQuestionAnswer] = Field(default_factory=list)
    conflicts: list[SourceUserInputConflict] = Field(default_factory=list)
    stale_resolver_results: list[StaleResolverRecord] = Field(default_factory=list)
    artifact_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class IntakeQuestion(IntakeModel):
    question_id: str
    group: str
    prompt: str
    answer_type: Literal["choice", "structured", "location"]
    allowed_options: list[str] = Field(default_factory=list)
    required: bool = True
    why_required: str
    dependency_question_ids: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    unit: str | None = None
    ui_context: dict[str, Any] = Field(default_factory=dict)


class ReadinessCard(IntakeModel):
    status: DashboardStatus
    reason: str


class EngineeringIntakeSession(IntakeModel):
    project_id: str
    room_id: str
    schema_version: Literal["1.0"]
    source_binding: Test01SP60EngineeringBinding
    pre_generation_session: UFHPreGenerationSession
    answers: dict[str, EngineeringQuestionAnswer] = Field(default_factory=dict)
    stale_answers: list[EngineeringQuestionAnswer] = Field(default_factory=list)
    conflicts: list[SourceUserInputConflict] = Field(default_factory=list)
    stale_resolver_results: list[StaleResolverRecord] = Field(default_factory=list)
    current_questions: list[IntakeQuestion]
    dashboard: dict[str, ReadinessCard]
    opening_inventory_status: Literal["UNRESOLVED", "COMPLETE_EMPTY", "INPUT_REQUIRED"]
    engineering_profile_status: Literal["READY", "INCOMPLETE", "INVALID"]
    engineering_profile_missing_paths: list[str] = Field(default_factory=list)
    resolver_diagnostics: list[str] = Field(default_factory=list)
    unresolved_source_groups: list[str]
    status: IntakeStatus
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    session_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    diagnostics: list[str] = Field(default_factory=list)


class EngineeringAnswerSubmission(IntakeModel):
    question_id: str
    value: JsonValue
    original_user_value: JsonValue | None = None
    source_reference: str = "user-confirmed project decision"
    answered_at: datetime | None = None


class SourceUserInputConflict(IntakeModel):
    code: Literal["PROJECT_SOURCE_USER_INPUT_CONFLICT"] = "PROJECT_SOURCE_USER_INPUT_CONFLICT"
    project_id: str
    room_id: str | None = None
    field_path: str
    authoritative_project_value: JsonValue
    user_value: JsonValue
    project_source_reference: str
    user_source_reference: str
    resolution_required: Literal[True] = True


def answer_store_path(project_directory: Path) -> Path:
    """Dedicated profile/intake sidecar, never in DWG/MRD/rooms/IFC exports."""
    root = project_directory.resolve()
    return root / "engineering" / "ufh_engineering_intake_v1.json"


def _answer_dependency(question_id: str, binding: Test01SP60EngineeringBinding,
                       answers: dict[str, EngineeringQuestionAnswer],
                       answer_value: Any = None,
                       source_reference: str | None = None) -> str:
    dependencies = {
        "room.qmts_process": ["room.use"],
        "boundary.below.details": ["boundary.below"],
        "boundary.above.details": ["boundary.above"],
        "openings.details": ["openings.inventory"],
        "openings.source_reference": ["openings.inventory"],
        "wall.boundary_details": ["wall.boundaries"],
        "construction.details": ["construction.mode"],
        "ventilation.design_basis": ["ventilation.mode"],
        "infiltration.details": ["infiltration.source"],
        "infiltration.pressure_model": ["infiltration.source", "infiltration.details"],
        "thermal_bridges.details": ["thermal_bridges.mode"],
        "room.qmts.details": ["room.use", "room.qmts_process"],
    }.get(question_id, [])
    dependencies: dict[str, Any] = {}
    if question_id in {"wall.boundaries", "wall.boundary_details", "openings.inventory", "openings.details"}:
        dependencies["geometry"] = {
            "snapshot": binding.source_inventory.get("snapshot_sha256"),
            "ifc": binding.source_inventory.get("ifc_binding", {}).get("sha256"),
        }
    elif question_id == "ventilation.design_basis":
        dependencies["rooms_export"] = binding.source_inventory.get("rooms_export", {}).get("sha256")
    elif question_id in {"construction.details", "infiltration.details", "thermal_bridges.details"}:
        dependencies["project_sources"] = binding.source_set_digest
    elif question_id == "climate":
        from agent.ufh_climate_resolver import load_climate_dataset
        dependencies["climate_dataset"] = load_climate_dataset().dataset_digest
    return digest({
        "project": binding.project_id,
        "room": binding.room_id,
        "source_dependencies": dependencies,
        "question": question_id,
        "answer": answer_value,
        "answer_source_reference": source_reference,
        "parents": {key: {"value": answers[key].normalized_value,
                           "dependency_digest": answers[key].dependency_digest}
                    for key in dependencies if key in answers},
    })


def _wall_candidates(binding: Test01SP60EngineeringBinding,
                     project_directory: Path,
                     ifc_directory: Path) -> list[dict[str, Any]]:
    inventory = next(item for item in binding.input_matrix
                     if item.input_id == "THERMAL_BOUNDARY_INVENTORY")
    raw = (inventory.value or {}).get("dwg_exterior_wall_candidates", [])
    by_handle = {item.get("handle"): item for item in raw}
    from agent.test01_geometry_source_authority import assess_test01_geometry_authority
    decision = assess_test01_geometry_authority(project_directory, ifc_directory)
    if decision.status != "AUTHORITATIVE" or decision.ufh_source is None:
        raise ValueError("BOUNDARY_CANDIDATE_GEOMETRY_AUTHORITY_REQUIRED")
    boundary = decision.ufh_source.authoritative_boundary
    if boundary is None:
        raise ValueError("BOUNDARY_CANDIDATE_GEOMETRY_REQUIRED")
    vertices = boundary.Vertices
    # IFC points are metres in the accepted source frame. UI endpoints are mm
    # in that same room boundary frame, with an explicit frame label.
    points = [(int(round(point.X * 1000)), int(round(point.Y * 1000))) for point in vertices]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    side_indices = {
        "X_MIN": ("x", min(xs)), "X_MAX": ("x", max(xs)),
        "Y_MIN": ("y", min(ys)), "Y_MAX": ("y", max(ys)),
    }
    # Side association is the reviewed geometric-fingerprint mapping in the
    # existing authority decision. IDs are human labels; evidence handles are
    # carried only as technical provenance, not shown as the prompt itself.
    side_map = [
        ("boundary-A", "X_MIN", "101DAAB"),
        ("boundary-B", "X_MAX", "101DABF"),
        ("boundary-C", "Y_MIN", "101DAC7"),
        ("boundary-D", "Y_MAX", "101DAB7"),
    ]
    candidates = []
    for boundary_id, position, handle in side_map:
        axis, coordinate = side_indices[position]
        endpoints = []
        for index, start in enumerate(points):
            end = points[(index + 1) % len(points)]
            aligned = start[0] == end[0] == coordinate if axis == "x" else start[1] == end[1] == coordinate
            if aligned:
                endpoints = [start, end]
                break
        length_mm = None
        if endpoints:
            delta = endpoints[1][0] - endpoints[0][0] if axis == "y" else endpoints[1][1] - endpoints[0][1]
            length_mm = abs(delta)
        candidates.append({
            "boundary_id": boundary_id,
            "room_relative_position": position,
            "endpoints_mm": endpoints,
            "length_mm": length_mm,
            "coordinate_system": "authoritative IfcSpace room-boundary plane; millimetres; X_MIN/X_MAX/Y_MIN/Y_MAX",
            "candidate_object_id": by_handle.get(handle, {}).get("handle", handle),
            "candidate_source": "Test_01 DWG model_snapshot.json / MAGIEXTERIORWALLS; geometric candidate only",
            "candidate_source_digest": binding.source_inventory.get("snapshot_sha256"),
            "geometry_source": binding.source_inventory["ifc_binding"]["path"],
            "geometry_source_digest": binding.source_inventory["ifc_binding"]["sha256"],
        })
    return candidates


def _airflow_observations(binding: Test01SP60EngineeringBinding) -> dict[str, Any]:
    """Read-only display values, hash-checked against the source binding."""
    source = binding.source_inventory["rooms_export"]
    path = Path(source["path"])
    raw = path.read_bytes()
    import hashlib
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError("ROOM_EXPORT_CHANGED_SINCE_BINDING")
    from agent.rooms_api import RoomExportReport
    report = RoomExportReport.model_validate_json(raw)
    room = next((item for item in report.Rooms if item.SourceHandle == binding.room_id), None)
    if room is None:
        raise ValueError("BOUND_ROOM_MISSING_FROM_EXPORT")
    fields = ("SupplyAirflowM3H", "ExtractAirflowM3H", "AirExchangeRate")
    return {field: {"value": getattr(room, field), "source_reference": source["path"],
                    "source_field": f"$.Rooms[SourceHandle={binding.room_id}].{field}",
                    "source_sha256": source["sha256"], "authority": "PROJECT_OBSERVATION_ONLY"}
            for field in fields if getattr(room, field) is not None}


def _q(question_id: str, group: str, prompt: str, kind: str,
       options: list[str] | None = None, *, why: str, targets: list[str] | None = None,
       parents: list[str] | None = None, context: dict[str, Any] | None = None) -> IntakeQuestion:
    return IntakeQuestion(question_id=question_id, group=group, prompt=prompt,
                          answer_type=kind, allowed_options=options or [], why_required=why,
                          targets=targets or [], dependency_question_ids=parents or [],
                          ui_context=context or {})


def _questions(binding: Test01SP60EngineeringBinding,
               answers: dict[str, EngineeringQuestionAnswer],
               project_directory: Path,
               ifc_directory: Path,
               pre_session: UFHPreGenerationSession) -> list[IntakeQuestion]:
    questions: list[IntakeQuestion] = []
    def add(item: IntakeQuestion, *, force: bool = False):
        if force or item.question_id not in answers:
            questions.append(item)

    climate_ok = any(
        execution.resolver_result.status == "RESOLVED"
        and any(value.target_authoring_field == "design_conditions.outdoor_design_temperature_c"
                for value in execution.resolver_result.values)
        for execution in pre_session.resolver_executions
    )
    pdf_package = binding.source_inventory.get("pdf_project_source_ingestion", {}).get("package") or {}
    pdf_location = next((item for item in pdf_package.get("observations", [])
                         if item.get("observation_id") == "PROJECT_SITE_LOCATION_TEXT"), None)
    location_context = ({
        "project_document_observation": pdf_location,
        "location_source_status": "OBSERVED_NOT_BOUND",
        "requires_normative_locality_resolution": True,
    } if pdf_location else {})
    climate_prompt = (
        "В плане проекта указан адрес: " + str(pdf_location.get("value"))
        + ". Подтвердите населённый пункт для нормативной климатической привязки."
        if pdf_location else "Где расположен проект?"
    )
    climate_why = (
        "Адрес обнаружен в титульном блоке планов, но нормативная климатическая запись для точного населённого пункта ещё не разрешена; температуру вручную вводить нельзя."
        if pdf_location else "Нужна нормативная климатическая запись; температура вручную не вводится."
    )
    add(_q("climate", "CLIMATE", climate_prompt, "location",
           why=climate_why,
           targets=["CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE", "DESIGN_WIND_SOURCE"],
           context=location_context),
        force=("climate" in answers and not climate_ok))
    add(_q("room.use", "ROOM_USE", "Для чего используется помещение 101?", "choice",
           ["LIVING_ROOM", "BEDROOM", "KITCHEN", "BATHROOM", "CORRIDOR", "OFFICE",
            "UTILITY_TECHNICAL", "OTHER_CUSTOM"],
           why="Назначение сначала фиксируется как решение проекта; нормативные последствия отдельно разрешаются.",
           targets=["ROOM_USE", "QMTS_APPLICABILITY"]))
    if "room.use" in answers and "room.qmts_process" not in answers:
        add(_q("room.qmts_process", "QMTS", "Регулярно ли в помещение вносят материалы, оборудование или транспорт, которые требуется нагревать?", "choice",
               ["YES", "NO", "UNKNOWN"], why="Нужно для классификации применимости Q_mts; ответ сам не назначает Q_mts.",
               targets=["QMTS_APPLICABILITY"], parents=["room.use"]))
    if "room.qmts_process" in answers and answers["room.qmts_process"].normalized_value == "YES" and "room.qmts.details" not in answers:
        add(_q("room.qmts.details", "QMTS", "Укажите проектный процесс и источник технологических данных для нагреваемого материала/оборудования.", "structured",
               why="Применимый Q_mts требует специализированного нормативного метода и входных данных.", targets=["QMTS_METHOD_AND_PROCESS_INPUTS"], parents=["room.use", "room.qmts_process"]))

    add(_q("below", "BOUNDARIES", "Что находится непосредственно под Room 101?", "choice",
           ["HEATED_ROOM", "UNHEATED_BASEMENT", "GROUND", "OUTDOOR", "VENTILATED_VOID", "OTHER"],
           why="Задаёт только семантику; numeric temperature не предполагается.", targets=["BELOW_BOUNDARY_SEMANTICS"]))
    add(_q("above", "BOUNDARIES", "Что находится непосредственно над Room 101?", "choice",
           ["HEATED_ROOM", "UNHEATED_BASEMENT", "GROUND", "OUTDOOR", "VENTILATED_VOID", "OTHER"],
           why="Задаёт только семантику; numeric temperature не предполагается.", targets=["ABOVE_BOUNDARY_SEMANTICS"]))

    wall_ids = ["boundary-A", "boundary-B", "boundary-C", "boundary-D"]
    if "wall.boundaries" not in answers:
        add(_q("wall.boundaries", "WALL_BOUNDARIES", "Что находится по другую сторону каждой из четырёх геометрических сторон?", "structured",
               why="Четыре DWG candidates требуют ручной семантической классификации; геометрия не доказывает exterior status.",
               targets=["THERMAL_BOUNDARY_SEMANTICS"], context={"candidates": _wall_candidates(binding, project_directory, ifc_directory),
               "allowed_values": ["OUTDOOR", "HEATED_ROOM", "UNHEATED_SPACE", "OTHER_BUILDING_ZONE", "UNKNOWN"],
               "required_boundary_ids": wall_ids}))
    elif "wall.boundaries" in answers and "UNKNOWN" in answers["wall.boundaries"].normalized_value.values() and "wall.boundary_details" not in answers:
        add(_q("wall.boundary_details", "WALL_BOUNDARIES", "Уточните проектный источник для сторон, отмеченных как UNKNOWN.", "structured",
               why="Неизвестные стороны остаются неразрешёнными до подтверждения.", targets=["THERMAL_BOUNDARY_SEMANTICS"], parents=["wall.boundaries"]))

    add(_q("openings.inventory", "OPENINGS", "Есть ли окна или двери на границах этого помещения?", "choice",
           ["NONE", "DEFINE_MANUALLY", "IMPORT_PROJECT_SOURCE", "UNKNOWN"],
           why="Отсутствие opening inventory нельзя трактовать как отсутствие проёмов.", targets=["OPENING_INVENTORY"]))
    if "openings.inventory" in answers and answers["openings.inventory"].normalized_value == "DEFINE_MANUALLY" and "openings.details" not in answers:
        add(_q("openings.details", "OPENINGS", "Для каждого проёма укажите родительскую сторону, тип, ширину, высоту и источник конструкции.", "structured",
               why="Нужно для net boundary area; исходники не содержат подтверждённой инвентаризации.", targets=["OPENING_GEOMETRY_PARENT_LINKAGE_AREAS"], parents=["openings.inventory"],
               context={"candidates": _wall_candidates(binding, project_directory, ifc_directory)}))
    if "openings.inventory" in answers and answers["openings.inventory"].normalized_value == "IMPORT_PROJECT_SOURCE" and "openings.source_reference" not in answers:
        add(_q("openings.source_reference", "OPENINGS", "Укажите точный источник проекта, revision и поле/лист, из которого должна быть импортирована инвентаризация проёмов.", "structured",
               why="Выбор import mode сам не доказывает наличие/отсутствие проёмов.", targets=["OPENING_INVENTORY"], parents=["openings.inventory"]))

    add(_q("construction.mode", "CONSTRUCTIONS", "Как определить ограждающие конструкции помещения?", "choice",
           ["ENTER_LAYERS_MANUALLY", "KNOWN_CATALOG_CONSTRUCTION", "IMPORT_PROJECT_DOCUMENTATION", "DIRECT_APPROVED_U_VALUE", "UNKNOWN"],
           why="Сначала выбирается источник/метод; слои и свойства запрашиваются только по ветке.", targets=["CONSTRUCTION_ASSEMBLIES", "U_VALUES"]))
    if "construction.mode" in answers and answers["construction.mode"].normalized_value in {
        "ENTER_LAYERS_MANUALLY", "DIRECT_APPROVED_U_VALUE", "KNOWN_CATALOG_CONSTRUCTION",
        "IMPORT_PROJECT_DOCUMENTATION",
    } and "construction.details" not in answers:
        prompt = ("Передайте для каждой конструкции порядок слоёв: material/product ID, thickness, density discriminator if required, source reference. Не вводите λ вручную без разрешённого источника."
                  if answers["construction.mode"].normalized_value == "ENTER_LAYERS_MANUALLY"
                  else "Для прямого U-value передайте значение, единицы и проектное подтверждение." if answers["construction.mode"].normalized_value == "DIRECT_APPROVED_U_VALUE"
                  else "Укажите точный идентификатор каталожной конструкции или документа проекта, revision и поля/страницы; сам выбор источника не подтверждает найденные слои/U.")
        add(_q("construction.details", "CONSTRUCTIONS", prompt, "structured",
               why="Структура будет проверена существующим construction/material resolver; сырой ответ сам по себе не считается resolved U.",
               targets=["CONSTRUCTION_ASSEMBLIES", "U_VALUES"], parents=["construction.mode"]))

    add(_q("ventilation.mode", "VENTILATION", "Как запроектирована вентиляция этого помещения?", "choice",
           ["NATURAL", "MECHANICAL_SUPPLY", "MECHANICAL_EXTRACT", "BALANCED_SUPPLY_EXTRACT", "DESIGN_PRESSURIZATION", "UNKNOWN_CUSTOM"],
           why="Режим выбирает семантику последующих airflow и pressure questions.", targets=["VENTILATION_PRESSURE_MODE", "DESIGN_VENTILATION_AIRFLOW"]))
    if "ventilation.mode" in answers and answers["ventilation.mode"].normalized_value != "UNKNOWN_CUSTOM" and "ventilation.design_basis" not in answers:
        add(_q("ventilation.design_basis", "VENTILATION", "Предоставьте утверждённую базу расчётного расхода наружного воздуха и подтвердите, относятся ли обнаруженные в проекте расходы к зимнему расчётному режиму.", "structured",
               why="Наблюдаемые Supply/Extract/ACH остаются audit-only без явного design semantics.",
               targets=["DESIGN_VENTILATION_AIRFLOW", "VENTILATION_AIRFLOW_SEMANTICS"], parents=["ventilation.mode"],
               context={"project_observations": _airflow_observations(binding), "never_auto_promote": True}))

    add(_q("infiltration.source", "INFILTRATION", "Как предоставить данные воздухопроницаемости ограждений?", "choice",
           ["PRODUCT_OR_TEST_DATA", "PROJECT_SPECIFICATION", "NORMATIVE_CONSTRUCTION_DATA", "NOT_AVAILABLE", "UNKNOWN"],
           why="Сначала выбирается источник; Ru и pressure inputs не запрашиваются вслепую.", targets=["INFILTRATION_ELEMENT_INVENTORY", "RU_VALUES", "PRESSURE_MODEL"]))
    if "infiltration.source" in answers and answers["infiltration.source"].normalized_value in {"PRODUCT_OR_TEST_DATA", "PROJECT_SPECIFICATION", "NORMATIVE_CONSTRUCTION_DATA"} and "infiltration.details" not in answers:
        add(_q("infiltration.details", "INFILTRATION", "Передайте источник испытаний/спецификации для air-permeable elements; дополнительные elevation, building-height, wind и pressure данные запрашиваются только по валидированной модели.", "structured",
               why="Нет promotion ACH или скрытых аэродинамических коэффициентов.", targets=["INFILTRATION_ELEMENT_INVENTORY", "RU_VALUES"], parents=["infiltration.source"]))
    elif "infiltration.details" in answers:
        details = answers["infiltration.details"].normalized_value
        if (not isinstance(details, dict) or not details.get("building_height_m")
                or not details.get("element_elevations_m")) and "infiltration.pressure_model" not in answers:
            add(_q("infiltration.pressure_model", "INFILTRATION", "Если расчёт инфильтрации применим: укажите из проектного источника общую высоту здания и высотные отметки центров проницаемых элементов; RoomHeight не заменяет высоту здания.", "structured",
                   why="A.9 требует геометрию здания и элемента, если её не извлекает источник.", targets=["BUILDING_HEIGHT", "ELEMENT_ELEVATIONS"], parents=["infiltration.details"]))

    add(_q("thermal_bridges.mode", "THERMAL_BRIDGES", "Как учитывать линейные и точечные тепловые мосты?", "choice",
           ["PROJECT_CALCULATION", "CATALOG_OR_NORMATIVE_JUNCTION_DATA", "NOT_YET_AVAILABLE", "DETAILED_CALCULATION_LATER"],
           why="Тепловые мосты нельзя молча приравнивать к нулю.", targets=["THERMAL_BRIDGES"]))
    if "thermal_bridges.mode" in answers and answers["thermal_bridges.mode"].normalized_value in {"PROJECT_CALCULATION", "CATALOG_OR_NORMATIVE_JUNCTION_DATA"} and "thermal_bridges.details" not in answers:
        add(_q("thermal_bridges.details", "THERMAL_BRIDGES", "Передайте утверждённый расчёт ψ/χ или идентификатор применимого узла с источником.", "structured",
               why="Необходима traceable bridge contribution.", targets=["THERMAL_BRIDGE_PSI_CHI_DETAILS"], parents=["thermal_bridges.mode"]))
    return questions


def _dashboard(binding: Test01SP60EngineeringBinding,
               pre_session: UFHPreGenerationSession,
               answers: dict[str, EngineeringQuestionAnswer]) -> tuple[dict[str, ReadinessCard], list[str], IntakeStatus]:
    matrix = {item.input_id: item for item in binding.input_matrix}
    pre_answers = pre_session.questionnaire_state.decisions
    climate_resolved = any(
        execution.resolver_result.status == "RESOLVED"
        and execution.resolver_result.values
        and execution.resolver_result.values[0].target_authoring_field == "design_conditions.outdoor_design_temperature_c"
        for execution in pre_session.resolver_executions
    )
    boundary_decisions = all(name in pre_answers for name in ("below", "above"))
    resolved_overrides: set[str] = set()
    if climate_resolved:
        resolved_overrides.update({"CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE"})
    if boundary_decisions and "wall.boundaries" in answers:
        wall_values = answers["wall.boundaries"].normalized_value.values()
        if all(value != "UNKNOWN" for value in wall_values):
            resolved_overrides.update({"THERMAL_BOUNDARY_INVENTORY", "BOUNDARY_SEMANTICS"})
    if ("openings.inventory" in answers
            and (answers["openings.inventory"].normalized_value == "NONE"
                 or "openings.details" in answers)):
        resolved_overrides.add("OPENING_INVENTORY")
    ventilation = answers.get("ventilation.design_basis")
    if ventilation is not None and ventilation.validation_status == "VALID" and ventilation.normalized_value.get("mode") in {
        "PROJECT_DESIGN_AIRFLOW", "CONFIRMED_OBSERVATION", "DESIGN_ACH"
    }:
        resolved_overrides.update({"DESIGN_VENTILATION_AIRFLOW", "VENTILATION_AIRFLOW_SEMANTICS"})

    def complete(field_id: str) -> bool:
        if field_id in resolved_overrides:
            return True
        item = matrix.get(field_id)
        return item is not None and item.status in {"RESOLVED", "DERIVED", "NOT_APPLICABLE"}

    def group_card(fields: set[str], reason: str, *, partial_if_answer: bool = False,
                   answer_ids: set[str] | None = None) -> ReadinessCard:
        satisfied = sum(complete(field) for field in fields)
        if satisfied == len(fields):
            return ReadinessCard(status="READY", reason=reason)
        has_answer = bool(answer_ids and set(answers).intersection(answer_ids))
        status = "PARTIAL" if satisfied or (partial_if_answer and has_answer) else "BLOCKED"
        missing = ", ".join(sorted(field for field in fields if not complete(field)))
        return ReadinessCard(status=status, reason=f"Нужны подтверждённые входы: {missing}.")

    qtr_fields = {
        "ROOM_BOUNDARY_GEOMETRY", "ROOM_AREA", "ROOM_HEIGHT", "INDOOR_DESIGN_TEMPERATURE",
        "CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE", "THERMAL_BOUNDARY_INVENTORY",
        "BOUNDARY_SEMANTICS", "BOUNDARY_AREAS", "OPENING_INVENTORY",
        "CONSTRUCTION_ASSEMBLIES", "U_VALUES", "THERMAL_BRIDGES",
    }
    qvent_fields = {"INDOOR_DESIGN_TEMPERATURE", "CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE",
                    "DESIGN_VENTILATION_AIRFLOW", "VENTILATION_AIRFLOW_SEMANTICS"}
    qinf_fields = {"INDOOR_DESIGN_TEMPERATURE", "CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE",
                   "INFILTRATION_ELEMENT_INVENTORY", "RU_VALUES", "ELEMENT_ELEVATIONS",
                   "BUILDING_HEIGHT", "DESIGN_WIND", "KZ", "AERODYNAMIC_MODEL", "PRESSURE_MODE"}
    geometry_ready = complete("ROOM_BOUNDARY_GEOMETRY")
    qtr = group_card(qtr_fields, "Все исходные данные передачи тепла привязаны; расчёт ещё не выполнялся.",
                     partial_if_answer=True,
                     answer_ids={"below", "above", "wall.boundaries", "openings.inventory", "construction.mode"})
    qvent = group_card(qvent_fields, "Входы требуемого вентиляционного расхода и температур привязаны; Q_vent ещё не вычислялся.",
                       partial_if_answer=True, answer_ids={"ventilation.mode", "ventilation.design_basis"})
    qinf = group_card(qinf_fields, "Входы A.8–A.10 привязаны; Q_inf ещё не вычислялся.",
                      partial_if_answer=True, answer_ids={"infiltration.source", "infiltration.details"})
    openings_answer = answers.get("openings.inventory")
    openings_explicitly_empty = (
        openings_answer is not None
        and openings_answer.validation_status == "VALID"
        and openings_answer.normalized_value == "NONE"
    )
    qmts_ready = complete("QMTS_APPLICABILITY")
    qmts = ReadinessCard(status="READY" if qmts_ready else
                         "PARTIAL" if "room.qmts_process" in answers else "BLOCKED",
                         reason=("Q_mts applicability has a sourced project/SP60 determination."
                                 if qmts_ready else "Room/process claims need a source-backed SP60 applicability determination; no blanket zero."))
    all_inputs_ready = all(card.status in {"READY", "NOT_APPLICABLE"}
                           for card in (qtr, qvent, qinf, qmts))
    cards = {
        "GEOMETRY": ReadinessCard(status="READY" if geometry_ready else "BLOCKED",
                                  reason="Авторитетная замкнутая геометрия комнаты подтверждена." if geometry_ready else "Геометрическая authority не подтверждена."),
        "CLIMATE": ReadinessCard(status="READY" if climate_resolved else "BLOCKED",
                                 reason="SP131 locality resolved through the existing normative resolver." if climate_resolved else "Нужно явно ответить на locality; климат не выводится из окружения/файлов."),
        "BOUNDARIES": group_card({"THERMAL_BOUNDARY_INVENTORY", "BOUNDARY_SEMANTICS", "BOUNDARY_AREAS"},
                                 "Thermal boundary semantics and areas are source-bound.", partial_if_answer=True,
                                 answer_ids={"below", "above", "wall.boundaries"}),
        "OPENINGS": ReadinessCard(status=("READY" if (openings_explicitly_empty or "openings.details" in answers)
                                  and complete("OPENING_INVENTORY") and complete("BOUNDARY_AREAS")
                                  else "PARTIAL" if "openings.inventory" in answers else "BLOCKED"),
                                  reason="Инвентаризация openings перечислена/явно подтверждено отсутствие; net-area binding остаётся отдельной проверкой."),
        "CONSTRUCTIONS": group_card({"CONSTRUCTION_ASSEMBLIES", "U_VALUES"},
                                     "Construction assemblies and U-values are bound.", partial_if_answer=True,
                                     answer_ids={"construction.mode", "construction.details"}),
        "VENTILATION": qvent,
        "INFILTRATION": qinf,
        "QMTS": qmts,
        "TRANSMISSION": qtr,
        "SP60_ROOM_LOAD": ReadinessCard(status="READY" if all_inputs_ready else "BLOCKED",
                                        reason="All required SP60 input groups are ready; calculation was not executed." if all_inputs_ready else "At least one A.1 input group is incomplete."),
        "UFH_HANDOFF": ReadinessCard(status="BLOCKED", reason="No room_design_heating_load_w has been calculated or handed to UFH."),
    }
    conflict_groups = {
        "CLIMATE": {"climate"}, "ROOM_USE": {"room.use", "room.qmts_process", "room.qmts.details"},
        "BOUNDARIES": {"below", "above", "wall.boundaries", "wall.boundary_details"},
        "OPENINGS": {"openings.inventory", "openings.details", "openings.source_reference"},
        "CONSTRUCTIONS": {"construction.mode", "construction.details"},
        "VENTILATION": {"ventilation.mode", "ventilation.design_basis"},
        "INFILTRATION": {"infiltration.source", "infiltration.details", "infiltration.pressure_model"},
        "THERMAL_BRIDGES": {"thermal_bridges.mode", "thermal_bridges.details"},
    }
    for group, question_ids in conflict_groups.items():
        if any(answer.validation_status == "CONFLICT" and answer.question_id in question_ids
               for answer in answers.values()):
            previous = cards.get(group)
            if previous is not None:
                cards[group] = ReadinessCard(
                    status="BLOCKED",
                    reason="Project/user source conflict is preserved; explicit reconciliation is required before binding.",
                )
    ready_groups = ("GEOMETRY", "CLIMATE", "BOUNDARIES", "OPENINGS", "CONSTRUCTIONS",
                    "VENTILATION", "INFILTRATION", "QMTS", "TRANSMISSION")
    all_inputs_ready = all(cards[group].status in {"READY", "NOT_APPLICABLE"}
                           for group in ready_groups)
    cards["SP60_ROOM_LOAD"] = ReadinessCard(
        status="READY" if all_inputs_ready else "BLOCKED",
        reason=("All required SP60 input groups are ready; calculation was not executed."
                if all_inputs_ready else "At least one required A.1 input group is incomplete."),
    )
    cards["UFH_HANDOFF"] = ReadinessCard(
        status="BLOCKED",
        reason="No room_design_heating_load_w has been calculated or handed to UFH.",
    )
    unresolved_set = {item.input_id for item in binding.input_matrix
                      if item.status in {"UNRESOLVED", "BLOCKED_BY_PARENT_DEPENDENCY"}}
    if climate_resolved:
        unresolved_set.difference_update({"CLIMATE_LOCALITY", "OUTDOOR_DESIGN_TEMPERATURE"})
    if (boundary_decisions and "wall.boundaries" in answers
            and "UNKNOWN" not in answers["wall.boundaries"].normalized_value.values()):
        unresolved_set.discard("BOUNDARY_SEMANTICS")
    if ("openings.inventory" in answers
            and (answers["openings.inventory"].normalized_value == "NONE"
                 or "openings.details" in answers)):
        unresolved_set.discard("OPENING_INVENTORY")
    unresolved = sorted(unresolved_set)
    ready = all_inputs_ready
    status: IntakeStatus = "READY_FOR_FIRST_SP60_CALCULATION" if ready else "INCOMPLETE"
    return cards, unresolved, status


def _rebuild(session: EngineeringIntakeSession) -> EngineeringIntakeSession:
    source_inventory = session.source_binding.source_inventory
    project_directory = Path(source_inventory["rooms_export"]["path"]).parent.parent.parent
    ifc_directory = Path(source_inventory["ifc_binding"]["path"]).parent
    session.current_questions = _questions(session.source_binding, session.answers,
                                           project_directory, ifc_directory,
                                           session.pre_generation_session)
    opening_answer = session.answers.get("openings.inventory")
    session.opening_inventory_status = (
        "COMPLETE_EMPTY" if opening_answer is not None and opening_answer.validation_status == "VALID"
        and opening_answer.normalized_value == "NONE"
        else "INPUT_REQUIRED" if opening_answer is not None
        and opening_answer.normalized_value in {"DEFINE_MANUALLY", "IMPORT_PROJECT_SOURCE"}
        else "UNRESOLVED"
    )
    session.dashboard, session.unresolved_source_groups, session.status = _dashboard(
        session.source_binding, session.pre_generation_session, session.answers)
    profile = profile_readiness(session.pre_generation_session)
    session.engineering_profile_status = profile.status
    session.engineering_profile_missing_paths = sorted(profile.missing_authoring_paths)
    session.resolver_diagnostics = sorted({
        f"{execution.resolver_request.resolver_type}:{execution.resolver_result.status}:{diagnostic}"
        for execution in session.pre_generation_session.resolver_executions
        for diagnostic in execution.resolver_result.diagnostics
    })
    session.dependency_digest = digest({
        "project": session.project_id,
        "room": session.room_id,
        "source_set": session.source_binding.source_set_digest,
        "answers": {key: answer.normalized_value for key, answer in sorted(session.answers.items())},
        "resolver_bindings": [binding.model_dump(mode="json") for binding in session.pre_generation_session.bindings],
    })
    session.session_digest = digest({
        "project": session.project_id,
        "room": session.room_id,
        "schema_version": session.schema_version,
        "source_set": session.source_binding.source_set_digest,
        "dependency_digest": session.dependency_digest,
        "answer_provenance": {
            key: {"dependency_digest": answer.dependency_digest,
                  "source_reference": answer.source_reference,
                  "source_field": answer.source_field,
                  "authority_class": answer.authority_class,
                  "validation_status": answer.validation_status}
            for key, answer in sorted(session.answers.items())
        },
        "conflicts": [item.model_dump(mode="json") for item in session.conflicts],
        "stale_answers": [
            {**answer.model_dump(mode="json"), "answered_at": None}
            for answer in session.stale_answers
        ],
        "stale_resolver_results": [item.model_dump(mode="json") for item in session.stale_resolver_results],
        "questions": [question.model_dump(mode="json") for question in session.current_questions],
        "dashboard": {key: value.model_dump(mode="json") for key, value in session.dashboard.items()},
    })
    return session


def create_test01_engineering_intake_session(
    project_directory: Path,
    ifc_directory: Path,
    *,
    normative_profile: str = "RU_CURRENT",
    answer_artifact: EngineeringIntakeAnswerArtifact | None = None,
) -> EngineeringIntakeSession:
    binding = build_test01_sp60_engineering_binding(project_directory, ifc_directory)
    if binding.authority_status != "AUTHORITATIVE":
        raise ValueError("TEST01_SOURCE_BINDING_" + binding.authority_status)
    pre = create_test01_ufh_pre_generation_session(project_directory, ifc_directory,
                                                   normative_profile=normative_profile)
    if answer_artifact is not None:
        if (answer_artifact.project_id, answer_artifact.room_id) != (binding.project_id, binding.room_id):
            raise ValueError("INTAKE_ARTIFACT_IDENTITY_MISMATCH")
        retained: dict[str, EngineeringQuestionAnswer] = {}
        stale = list(answer_artifact.stale_answers)
        for key, item in answer_artifact.answers.items():
            expected = _answer_dependency(key, binding, answer_artifact.answers,
                                           item.normalized_value, item.source_reference)
            if expected == item.dependency_digest:
                retained[key] = item
            else:
                stale.append(item.model_copy(update={"validation_status": "STALE"}))
        answer_artifact = answer_artifact.model_copy(update={"answers": retained, "stale_answers": stale,
                                                            "source_binding_digest": binding.source_set_digest})
        decisions = answer_artifact.answers
        for intake_id, question_id in (("climate", "climate"), ("below", "below"), ("above", "above"),
                                       ("construction.mode", "envelope"), ("construction.details", "envelope.source")):
            if intake_id not in decisions:
                continue
            answer = decisions[intake_id]
            normalized = answer.normalized_value
            if intake_id == "construction.mode":
                normalized = {
                    "ENTER_LAYERS_MANUALLY": "LAYERED_CUSTOM_ASSEMBLY",
                    "KNOWN_CATALOG_CONSTRUCTION": "CATALOG_SYSTEM",
                    "IMPORT_PROJECT_DOCUMENTATION": "PROJECT_ASSEMBLY",
                    "DIRECT_APPROVED_U_VALUE": "EXPLICIT_U_VALUE_WITH_PROVENANCE",
                    "UNKNOWN": "UNKNOWN",
                }[normalized]
            submission = Decision(
                question_id=question_id,
                value=normalized,
                source_reference=answer.source_reference,
                revision=answer.dependency_digest,
                source_type="user_project_decision",
            )
            pre = apply_ufh_questionnaire_answer(pre, submission)
    base = EngineeringIntakeSession(
        project_id=binding.project_id, room_id=binding.room_id, schema_version=SCHEMA_VERSION,
        source_binding=binding, pre_generation_session=pre,
        answers=(answer_artifact.answers if answer_artifact else {}),
        stale_answers=(answer_artifact.stale_answers if answer_artifact else []),
        conflicts=(answer_artifact.conflicts if answer_artifact else []),
        stale_resolver_results=(answer_artifact.stale_resolver_results if answer_artifact else []),
        current_questions=[], dashboard={}, opening_inventory_status="UNRESOLVED",
        engineering_profile_status="INCOMPLETE", engineering_profile_missing_paths=[],
        resolver_diagnostics=[],
        unresolved_source_groups=[], status="INCOMPLETE",
        dependency_digest="0" * 64, session_digest="0" * 64,
    )
    return _rebuild(base)


def _validate_submission(question: IntakeQuestion, value: Any) -> Any:
    if question.answer_type == "choice":
        if not isinstance(value, str) or value not in question.allowed_options:
            raise ValueError("INVALID_OPTION:" + question.question_id)
        return value
    if question.answer_type == "location":
        if (not isinstance(value, dict) or set(value) != {"settlement", "region"}
                or not all(isinstance(item, str) and item.strip() for item in value.values())):
            raise ValueError("SETTLEMENT_AND_REGION_REQUIRED")
        return {"settlement": " ".join(value["settlement"].split()),
                "region": " ".join(value["region"].split())}
    if question.question_id == "wall.boundaries":
        required = {"boundary-A", "boundary-B", "boundary-C", "boundary-D"}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("ALL_FOUR_STABLE_BOUNDARY_IDS_REQUIRED")
        allowed = set(question.ui_context["allowed_values"])
        if any(not isinstance(item, str) or item not in allowed for item in value.values()):
            raise ValueError("INVALID_BOUNDARY_SEMANTIC")
        return {key: value[key] for key in sorted(value)}
    if question.answer_type == "structured":
        if not isinstance(value, dict):
            raise ValueError("STRUCTURED_OBJECT_REQUIRED")
        def inspect_authority(node: Any):
            if isinstance(node, dict):
                claimed_authority = node.get("authority_class")
                if claimed_authority is not None and claimed_authority not in {
                    "PROJECT_APPROVED_USER_INPUT", "USER_CONFIRMED_PROJECT_DECISION"
                }:
                    raise ValueError("USER_CANNOT_ASSERT_EXTERNAL_OR_NORMATIVE_AUTHORITY")
                claimed_source_type = node.get("source_type")
                if claimed_source_type is not None and claimed_source_type not in {
                    "project_decision", "user_project_decision"
                }:
                    raise ValueError("USER_CANNOT_FORGE_SOURCE_TYPE")
                for child in node.values():
                    inspect_authority(child)
            elif isinstance(node, list):
                for child in node:
                    inspect_authority(child)
        inspect_authority(value)
        if question.question_id == "openings.details":
            rows = value.get("openings")
            if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
                raise ValueError("OPENING_ROWS_REQUIRED")
            ids = [row.get("opening_id") for row in rows if isinstance(row, dict)]
            if len(ids) != len(rows) or len(ids) != len(set(ids)):
                raise ValueError("OPENING_IDS_MUST_BE_UNIQUE")
            parent_ids = {item["boundary_id"] for item in question.ui_context.get("candidates", [])}
            for row in rows:
                if row.get("parent_boundary_id") not in parent_ids:
                    raise ValueError("OPENING_PARENT_BOUNDARY_REQUIRED")
                if row.get("type") not in {"WINDOW", "DOOR", "OTHER_OPENING"}:
                    raise ValueError("OPENING_TYPE_REQUIRED")
                for key in ("width_mm", "height_mm"):
                    try:
                        number = float(row[key])
                    except (KeyError, TypeError, ValueError) as error:
                        raise ValueError("OPENING_DIMENSIONS_REQUIRED") from error
                    if not number > 0:
                        raise ValueError("OPENING_DIMENSIONS_MUST_BE_POSITIVE")
                if not row.get("construction_source"):
                    raise ValueError("OPENING_CONSTRUCTION_SOURCE_REQUIRED")
        if question.question_id == "ventilation.design_basis":
            if value.get("mode") not in {"PROJECT_DESIGN_AIRFLOW", "CONFIRMED_OBSERVATION", "DESIGN_ACH", "PER_PERSON", "SP60_7_4_1"}:
                raise ValueError("VENTILATION_SOURCE_MODE_REQUIRED")
            if not value.get("source_reference") or not value.get("source_field"):
                raise ValueError("VENTILATION_SOURCE_PROVENANCE_REQUIRED")
            if value.get("mode") == "CONFIRMED_OBSERVATION":
                if (not value.get("observation_field") or value.get("confirmed_cold_period_design") is not True
                        or value.get("units") is None):
                    raise ValueError("OBSERVATION_REQUIRES_EXPLICIT_DESIGN_CONFIRMATION")
                expected_units = "1/h" if value.get("observation_field") == "AirExchangeRate" else "m3/h"
                if value.get("units") != expected_units:
                    raise ValueError("OBSERVATION_UNITS_MISMATCH")
            elif value.get("mode") in {"PROJECT_DESIGN_AIRFLOW", "DESIGN_ACH"}:
                expected = "m3/h" if value["mode"] == "PROJECT_DESIGN_AIRFLOW" else "1/h"
                number = value.get("value")
                if (type(number) not in {int, float} or not __import__("math").isfinite(number)
                        or value.get("units") != expected or number <= 0):
                    raise ValueError("VENTILATION_VALUE_AND_CANONICAL_UNITS_REQUIRED")
                if value["mode"] == "DESIGN_ACH" and value.get("confirmed_winter_design_rate") is not True:
                    raise ValueError("ACH_DESIGN_SEMANTICS_CONFIRMATION_REQUIRED")
        return value
    raise ValueError("UNSUPPORTED_ANSWER_TYPE")


def _stale_descendants(question_id: str, answers: dict[str, EngineeringQuestionAnswer]) -> tuple[dict[str, EngineeringQuestionAnswer], list[EngineeringQuestionAnswer]]:
    children = {
        "room.use": {"room.qmts_process", "room.qmts.details"},
        "room.qmts_process": {"room.qmts.details"},
        "construction.mode": {"construction.details"},
        "ventilation.mode": {"ventilation.design_basis"},
        "infiltration.source": {"infiltration.details"},
        "infiltration.details": {"infiltration.pressure_model"},
        "thermal_bridges.mode": {"thermal_bridges.details"},
        "openings.inventory": {"openings.details", "openings.source_reference"},
        "wall.boundaries": {"wall.boundary_details"},
        "boundary.below": {"boundary.below.details"},
        "boundary.above": {"boundary.above.details"},
    }
    invalid = set(children.get(question_id, set()))
    pending = list(invalid)
    while pending:
        parent = pending.pop()
        for child in children.get(parent, set()) - invalid:
            invalid.add(child)
            pending.append(child)
    updated = dict(answers)
    stale: list[EngineeringQuestionAnswer] = []
    for key in invalid:
        item = updated.pop(key, None)
        if item is not None:
            stale.append(item.model_copy(update={"validation_status": "STALE"}))
    return updated, stale


def detect_source_user_input_conflict(
    *, project_id: str, room_id: str | None, field_path: str,
    project_value: Any, user_value: Any, project_source_reference: str,
    user_source_reference: str,
) -> SourceUserInputConflict | None:
    """Preserve both claims when explicit user and project values disagree."""
    if _canonical(project_value) == _canonical(user_value):
        return None
    return SourceUserInputConflict(
        project_id=project_id, room_id=room_id, field_path=field_path,
        authoritative_project_value=_canonical(project_value),
        user_value=_canonical(user_value),
        project_source_reference=project_source_reference,
        user_source_reference=user_source_reference,
    )


def _stale_resolver_records(session: EngineeringIntakeSession,
                            question_id: str) -> list[StaleResolverRecord]:
    affected: set[str] = set()
    if question_id == "climate":
        affected.add("CLIMATE_RESOLVER")
        for side, answer_id in (("BELOW", "below"), ("ABOVE", "above")):
            prior = session.pre_generation_session.questionnaire_state.decisions.get(answer_id)
            if prior is not None and prior.value in {"OUTDOOR", "ROOF_OUTDOOR"}:
                affected.add("BOUNDARY_CONDITION_RESOLVER")
    elif question_id in {"below", "above"}:
        affected.add("BOUNDARY_CONDITION_RESOLVER")
    elif question_id in {"construction.mode", "construction.details"}:
        affected.add("BUILDING_CONSTRUCTION_RESOLVER")
    records = []
    for execution in session.pre_generation_session.resolver_executions:
        if execution.resolver_request.resolver_type not in affected:
            continue
        if question_id not in execution.resolver_request.source_question_ids and not (
            question_id == "climate" and execution.resolver_request.resolver_type == "BOUNDARY_CONDITION_RESOLVER"
        ):
            continue
        records.append(StaleResolverRecord(
            resolver_type=execution.resolver_request.resolver_type,
            result_status_before_invalidation=execution.resolver_result.status,
            dependency_digest=execution.resolver_result.dependency_digest,
            result_digest=digest(execution.resolver_result.model_dump(mode="json")),
            invalidated_by_question_id=question_id,
        ))
    return records


def apply_engineering_intake_answer(
    session: EngineeringIntakeSession,
    submission: EngineeringAnswerSubmission,
) -> EngineeringIntakeSession:
    question = next((item for item in session.current_questions
                     if item.question_id == submission.question_id), None)
    if question is None:
        raise ValueError("QUESTION_NOT_ACTIVE:" + submission.question_id)
    value = _validate_submission(question, submission.value)
    existing = session.answers.get(submission.question_id)
    if existing is not None and existing.normalized_value == value:
        return session.model_copy(deep=True)

    updated = session.model_copy(deep=True)
    if existing is not None:
        updated.stale_resolver_results.extend(_stale_resolver_records(session, question.question_id))
        updated.answers, newly_stale = _stale_descendants(submission.question_id, updated.answers)
        updated.stale_answers.extend(newly_stale)
    now = submission.answered_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("ANSWERED_AT_TIMEZONE_REQUIRED")
    source_ref = submission.source_reference.strip()
    if not source_ref:
        raise ValueError("ANSWER_SOURCE_REFERENCE_REQUIRED")
    if question.question_id == "ventilation.design_basis" and value.get("mode") == "CONFIRMED_OBSERVATION":
        observations = question.ui_context["project_observations"]
        field = value["observation_field"]
        if field not in observations:
            raise ValueError("CONFIRMED_OBSERVATION_NOT_IN_PROJECT_SOURCE")
        observation = observations[field]
        if value.get("value") != observation["value"]:
            raise ValueError("CONFIRMED_OBSERVATION_VALUE_MISMATCH")
        source_ref = f"{observation['source_reference']}#{observation['source_field']}[{observation['source_sha256']}]; user confirmation: {source_ref}"
    answer = EngineeringQuestionAnswer(
        question_id=question.question_id, project_id=session.project_id, room_id=session.room_id,
        answer_type=question.answer_type, normalized_value=value,
        original_user_value=(submission.original_user_value if submission.original_user_value is not None else submission.value),
        unit=(question.unit or (value.get("units") if isinstance(value, dict) and isinstance(value.get("units"), str) else None)),
        authority_class=ANSWER_AUTHORITY, source_type="user_project_decision",
        answered_at=now, dependency_digest=_answer_dependency(
            question.question_id, session.source_binding, updated.answers, value, source_ref),
        source_reference=source_ref, source_field=question.question_id,
        transformation="validated interactive engineering intake answer; semantic/user claim only; physical resolution remains with registered resolver",
    )
    updated.answers[question.question_id] = answer

    # Preserve conflicting project/user claims; never silently replace the
    # authoritative project-owned value.
    if isinstance(value, dict) and isinstance(value.get("field_path"), str) and "value" in value:
        project_values = (updated.pre_generation_session.project_context.project_owned_values.values
                          if updated.pre_generation_session.project_context.project_owned_values else [])
        project_claim = next((item for item in project_values
                              if item.canonical_field_path == value["field_path"]), None)
        if project_claim is not None:
            conflict = detect_source_user_input_conflict(
                project_id=session.project_id, room_id=session.room_id,
                field_path=project_claim.canonical_field_path,
                project_value=project_claim.value, user_value=value["value"],
                project_source_reference=project_claim.source_reference,
                user_source_reference=source_ref,
            )
            if conflict is not None:
                updated.conflicts.append(conflict)
                updated.answers[question.question_id] = answer.model_copy(update={"validation_status": "CONFLICT"})
                return _rebuild(updated)

    # Only existing supported question IDs are handed to the existing session.
    # EngineeringIntake-specific decisions remain typed intake claims until a
    # suitable existing resolver/profile field is available.
    existing_id = {"construction.mode": "envelope", "construction.details": "envelope.source"}.get(question.question_id, question.question_id)
    if existing_id in {"climate", "below", "above", "envelope", "envelope.source"}:
        normalized = value
        if question.question_id == "construction.mode":
            normalized = {
                "ENTER_LAYERS_MANUALLY": "LAYERED_CUSTOM_ASSEMBLY",
                "KNOWN_CATALOG_CONSTRUCTION": "CATALOG_SYSTEM",
                "IMPORT_PROJECT_DOCUMENTATION": "PROJECT_ASSEMBLY",
                "DIRECT_APPROVED_U_VALUE": "EXPLICIT_U_VALUE_WITH_PROVENANCE",
                "UNKNOWN": "UNKNOWN",
            }[value]
        decision = Decision(
            question_id=existing_id, value=normalized, source_reference=source_ref,
            revision=answer.dependency_digest, source_type="user_project_decision",
        )
        if existing_id in updated.pre_generation_session.questionnaire_state.decisions:
            updated.pre_generation_session = replace_ufh_questionnaire_answer(
                updated.pre_generation_session, decision)
        else:
            updated.pre_generation_session = apply_ufh_questionnaire_answer(
                updated.pre_generation_session, decision)
    return _rebuild(updated)


def clear_engineering_intake_answer(
    session: EngineeringIntakeSession, question_id: str,
) -> EngineeringIntakeSession:
    if question_id not in session.answers:
        raise ValueError("ANSWER_NOT_FOUND:" + question_id)
    updated = session.model_copy(deep=True)
    current = updated.answers.pop(question_id)
    updated.stale_answers.append(current.model_copy(update={"validation_status": "STALE"}))
    updated.stale_resolver_results.extend(_stale_resolver_records(session, question_id))
    updated.answers, children = _stale_descendants(question_id, updated.answers)
    updated.stale_answers.extend(children)
    existing_id = {"construction.mode": "envelope", "construction.details": "envelope.source"}.get(question_id, question_id)
    if existing_id in updated.pre_generation_session.questionnaire_state.decisions:
        # Recreate from the remaining persisted answers to ensure resolver
        # outputs whose parent was cleared cannot survive the clear operation.
        reconstructed = create_test01_ufh_pre_generation_session(
            Path(updated.source_binding.source_inventory["rooms_export"]["path"]).parent.parent.parent,
            Path(updated.source_binding.source_inventory["ifc_binding"]["path"]).parent,
            normative_profile=updated.pre_generation_session.normative_profile,
        )
        for intake_id, key in (("climate", "climate"), ("below", "below"), ("above", "above"),
                               ("construction.mode", "envelope"), ("construction.details", "envelope.source")):
            item = updated.answers.get(intake_id)
            if item is not None:
                value = item.normalized_value
                if intake_id == "construction.mode":
                    value = {
                        "ENTER_LAYERS_MANUALLY": "LAYERED_CUSTOM_ASSEMBLY",
                        "KNOWN_CATALOG_CONSTRUCTION": "CATALOG_SYSTEM",
                        "IMPORT_PROJECT_DOCUMENTATION": "PROJECT_ASSEMBLY",
                        "DIRECT_APPROVED_U_VALUE": "EXPLICIT_U_VALUE_WITH_PROVENANCE",
                        "UNKNOWN": "UNKNOWN",
                    }[value]
                reconstructed = apply_ufh_questionnaire_answer(reconstructed, Decision(
                    question_id=key, value=value, source_reference=item.source_reference,
                    revision=item.dependency_digest, source_type="user_project_decision"))
        updated.pre_generation_session = reconstructed
    return _rebuild(updated)


def replace_engineering_intake_answer(session: EngineeringIntakeSession,
                                      submission: EngineeringAnswerSubmission) -> EngineeringIntakeSession:
    if submission.question_id not in session.answers:
        raise ValueError("ANSWER_HAS_NO_PRIOR_VALUE:" + submission.question_id)
    staged = session.model_copy(deep=True)
    current = staged.answers.pop(submission.question_id)
    staged.stale_answers.append(current.model_copy(update={"validation_status": "STALE"}))
    staged.stale_resolver_results.extend(_stale_resolver_records(session, submission.question_id))
    staged.answers, descendants = _stale_descendants(submission.question_id, staged.answers)
    staged.stale_answers.extend(descendants)
    staged = _rebuild(staged)
    return apply_engineering_intake_answer(staged, submission)


def artifact_from_session(session: EngineeringIntakeSession) -> EngineeringIntakeAnswerArtifact:
    body = {
        "schema_version": SCHEMA_VERSION,
        "project_id": session.project_id,
        "room_id": session.room_id,
        "source_binding_digest": session.source_binding.source_set_digest,
        "answers": {key: value for key, value in sorted(session.answers.items())},
        "stale_answers": list(session.stale_answers),
        "conflicts": list(session.conflicts),
        "stale_resolver_results": list(session.stale_resolver_results),
    }
    return EngineeringIntakeAnswerArtifact(**body, artifact_digest=digest(_canonical(body)))


def persist_engineering_intake_session(session: EngineeringIntakeSession,
                                       project_directory: Path,
                                       *, expected_artifact_digest: str | None = None) -> EngineeringIntakeAnswerArtifact:
    """Atomically save answer/profile sidecar with optimistic concurrency."""
    path = answer_store_path(project_directory)
    current_digest = None
    if path.exists():
        current = EngineeringIntakeAnswerArtifact.model_validate_json(path.read_text(encoding="utf-8"))
        current_digest = current.artifact_digest
    if current_digest != expected_artifact_digest:
        raise ValueError("INTAKE_ARTIFACT_REVISION_CONFLICT")
    artifact = artifact_from_session(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact.model_dump(mode="json"), sort_keys=True,
                      ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    write_text_atomically(path, text)
    return artifact


def load_engineering_intake_artifact(project_directory: Path,
                                     binding: Test01SP60EngineeringBinding) -> EngineeringIntakeAnswerArtifact | None:
    path = answer_store_path(project_directory)
    if not path.exists():
        return None
    artifact = EngineeringIntakeAnswerArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    if (artifact.project_id, artifact.room_id) != (binding.project_id, binding.room_id):
        raise ValueError("INTAKE_ARTIFACT_IDENTITY_MISMATCH")
    body = artifact.model_dump(mode="json", exclude={"artifact_digest"})
    if digest(body) != artifact.artifact_digest:
        raise ValueError("INTAKE_ARTIFACT_DIGEST_INVALID")
    return artifact


def answer_and_persist_engineering_intake(
    session: EngineeringIntakeSession,
    submission: EngineeringAnswerSubmission,
    project_directory: Path,
    *,
    expected_artifact_digest: str | None,
) -> tuple[EngineeringIntakeSession, EngineeringIntakeAnswerArtifact]:
    """Validate/re-resolve first; persist only the complete new session state."""
    updated = apply_engineering_intake_answer(session, submission)
    artifact = persist_engineering_intake_session(
        updated, project_directory, expected_artifact_digest=expected_artifact_digest)
    return updated, artifact


def create_persistent_test01_intake_session(project_directory: Path,
                                            ifc_directory: Path,
                                            *, normative_profile: str = "RU_CURRENT") -> EngineeringIntakeSession:
    binding = build_test01_sp60_engineering_binding(project_directory, ifc_directory)
    artifact = load_engineering_intake_artifact(project_directory, binding)
    return create_test01_engineering_intake_session(
        project_directory, ifc_directory, normative_profile=normative_profile,
        answer_artifact=artifact,
    )


__all__ = [
    "ANSWER_AUTHORITY", "EngineeringAnswerSubmission", "EngineeringIntakeAnswerArtifact",
    "EngineeringIntakeSession", "EngineeringQuestionAnswer", "IntakeQuestion",
    "ReadinessCard", "SourceUserInputConflict", "answer_store_path",
    "apply_engineering_intake_answer", "artifact_from_session",
    "clear_engineering_intake_answer", "create_persistent_test01_intake_session",
    "create_test01_engineering_intake_session", "load_engineering_intake_artifact",
    "persist_engineering_intake_session", "replace_engineering_intake_answer",
    "detect_source_user_input_conflict",
    "answer_and_persist_engineering_intake",
]
