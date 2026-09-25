"""Read-only questionnaire; decisions are not resolved engineering properties."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent.ufh_project_engineering_profile_authoring import (
    Test01UfhEngineeringAuthoringTemplate, load_ufh_project_engineering_authoring_template,
)
from agent.ufh_project_adapter import (
    ProjectOwnedEngineeringValues,
    ProjectUfhAdapterResult,
    collect_project_owned_ufh_values,
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


class Decision(Model):
    question_id: str
    value: Any
    source_reference: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    source_type: Literal["user_project_decision", "authoritative_project"] = "user_project_decision"
    transformation: str = "questionnaire answer; unresolved properties require resolver"


class ProjectContext(Model):
    source_reference: str
    coordinate_system: str
    known_decisions: dict[str, Decision] = Field(default_factory=dict)
    project_owned_values: ProjectOwnedEngineeringValues | None = None


class QuestionnaireState(Model):
    authoring: Test01UfhEngineeringAuthoringTemplate
    decisions: dict[str, Decision] = Field(default_factory=dict)


class Question(Model):
    question_id: str
    group: str
    prompt: str
    answer_type: Literal["choice", "text", "structured", "location", "point", "quantity"]
    allowed_options: list[str] = Field(default_factory=list)
    required: bool = True
    why_required: str
    targets: list[str]
    dependency_conditions: dict[str, list[str]] = Field(default_factory=dict)
    unit: str | None = None


class QuestionnaireResult(Model):
    questions: list[Question]
    resolver_requirements: list[str]
    digest: str

    def pages(self, page_size: int = 8) -> list[list[Question]]:
        """Presentation batching only; never silently omit unresolved questions."""
        if type(page_size) is not int or not 1 <= page_size <= 10:
            raise ValueError("PAGE_SIZE_MUST_BE_1_TO_10")
        return [self.questions[i:i + page_size] for i in range(0, len(self.questions), page_size)]


def project_context_from_adapter_result(
    adapter_result: ProjectUfhAdapterResult,
    coordinate_system: str,
    known_decisions: dict[str, Decision] | None = None,
) -> ProjectContext:
    """Create questionnaire context and bindings directly from adapter output."""
    return ProjectContext(
        source_reference=adapter_result.source_file,
        coordinate_system=coordinate_system,
        known_decisions=known_decisions or {},
        project_owned_values=collect_project_owned_ufh_values(adapter_result),
    )


def _q(key, prompt, options, targets, *, parent=None, when=None, kind="choice", unit=None):
    return Question(question_id=key, group=key.split(".")[0], prompt=prompt,
                    answer_type=kind, allowed_options=options.split() if options else [],
                    targets=targets.split(), unit=unit,
                    why_required="Нужен подтверждённый источник для: " + targets,
                    dependency_conditions={parent: when.split()} if parent else {})


QUESTIONS = [
    _q("climate", "В каком населённом пункте и регионе расположен объект?", "", "design_conditions.outdoor_design_temperature_c", kind="location"),
    _q("indoor_rh", "Какова расчётная относительная влажность внутреннего воздуха для помещения?", "", "project_context.indoor_design_relative_humidity_percent", kind="quantity", unit="%"),
    _q("moisture_zone", "Укажите зону влажности района строительства по Приложению А СП 50.13330.2024 и ссылку на утверждённый источник (не выбирайте А/Б).", "", "project_context.construction_moisture_zone", kind="structured"),
    _q("below", "Что находится под помещением?", "HEATED_ROOM UNHEATED_BASEMENT GROUND OUTDOOR VENTILATED_VOID OTHER", "design_conditions.floor_boundary_temperature_c"),
    _q("below.source", "Укажите проектный источник конструкции пола по грунту.", "", "building_physics.floor_u_value_w_m2k", parent="below", when="GROUND", kind="text"),
    _q("below.details", "Укажите условия и проектный источник для пространства снизу.", "", "design_conditions.floor_boundary_temperature_c", parent="below", when="OTHER UNHEATED_BASEMENT", kind="text"),
    _q("above", "Что находится над помещением?", "HEATED_ROOM UNHEATED_ATTIC ROOF_OUTDOOR VENTILATED_VOID OTHER", "design_conditions.ceiling_boundary_temperature_c"),
    _q("above.details", "Укажите условия и проектный источник для пространства сверху.", "", "design_conditions.ceiling_boundary_temperature_c", parent="above", when="OTHER UNHEATED_ATTIC", kind="text"),
    _q("envelope", "Какой источник или способ описания конструкции использовать?", "PROJECT_ASSEMBLY CATALOG_SYSTEM LAYERED_CUSTOM_ASSEMBLY EXPLICIT_U_VALUE_WITH_PROVENANCE UNKNOWN PROJECT_CONSTRUCTION LAYERS APPROVED_BASELINE", "envelope_constructions.selected"),
    _q("envelope.source", "Передайте структурированные данные конструкции и их источники (для слоёв — упорядоченный список).", "", "envelope_constructions.selected", parent="envelope", when="PROJECT_ASSEMBLY CATALOG_SYSTEM LAYERED_CUSTOM_ASSEMBLY EXPLICIT_U_VALUE_WITH_PROVENANCE PROJECT_CONSTRUCTION LAYERS APPROVED_BASELINE", kind="structured"),
    _q("finish", "Какое покрытие пола планируется?", "TILE_STONE LAMINATE PARQUET VINYL CARPET CUSTOM", "floor_system_product.r_o_m2k_w"),
    _q("finish.source", "Укажите документ на покрытие или состав конструкции.", "", "floor_system_product.r_o_m2k_w", parent="finish", when="CUSTOM", kind="text"),
    _q("exclusions", "Есть ли зоны, где трубу прокладывать нельзя?", "NO YES UNKNOWN", "explicit_confirmations.exclusion_zones"),
    _q("collector", "Выберите положение коллектора на плане.", "", "ufh_design_settings.collector_point_x_mm ufh_design_settings.collector_point_y_mm", kind="point", unit="mm"),
    _q("system", "Как выбрать систему тёплого пола и трубу?", "CATALOG AUTO CUSTOM", "pipe_product floor_system_product manifold_product control_model.control_characteristic"),
    _q("system.source", "Укажите идентификатор комплекта каталога или документ спецификации.", "", "pipe_product floor_system_product manifold_product control_model.control_characteristic", parent="system", when="CATALOG CUSTOM", kind="text"),
    _q("layout", "Какой режим проектирования выбрать?", "AUTO COMFORT LOW_TEMPERATURE CUSTOM", "ufh_design_settings.spacing_mm ufh_design_settings.wall_offset_mm ufh_design_settings.design_margin_percent ufh_design_settings.area_basis"),
    _q("layout.spacing", "Укажите шаг укладки.", "", "ufh_design_settings.spacing_mm", parent="layout", when="CUSTOM", kind="quantity", unit="mm"),
    _q("layout.offset", "Укажите отступ от стен.", "", "ufh_design_settings.wall_offset_mm", parent="layout", when="CUSTOM", kind="quantity", unit="mm"),
    _q("fluid", "Какой теплоноситель предусмотрен?", "WATER ANTIFREEZE PROJECT_SYSTEM", "fluid_definition"),
    _q("fluid.temperature", "Укажите температуру, при которой следует определить свойства воды.", "", "fluid_definition", parent="fluid", when="WATER", kind="quantity", unit="degC"),
    _q("fluid.source", "Укажите продукт, концентрацию и температурный режим либо ссылку на систему проекта.", "", "fluid_definition", parent="fluid", when="ANTIFREEZE PROJECT_SYSTEM", kind="text"),
    _q("thermal", "Что известно о температурном режиме?", "AUTO_DESIGN KNOWN_SUPPLY_TEMPERATURE KNOWN_DELTA_T", "ufh_design_settings.mode"),
    _q("thermal.supply", "Укажите известную температуру подачи.", "", "design_conditions.theta_supply_c", parent="thermal", when="KNOWN_SUPPLY_TEMPERATURE", kind="quantity", unit="degC"),
    _q("thermal.delta", "Укажите известный перепад температур.", "", "design_conditions.sigma_k", parent="thermal", when="KNOWN_DELTA_T", kind="quantity", unit="K"),
    _q("surface", "Каково назначение обогреваемой зоны?", "RESIDENTIAL BATHROOM PERIPHERAL CUSTOM", "control_model.surface_limit_w_m2"),
    _q("surface.source", "Укажите документ с ограничением поверхности.", "", "control_model.surface_limit_w_m2", parent="surface", when="CUSTOM", kind="text"),
    _q("openings", "Есть ли проёмы, которые ещё не описаны в проекте?", "NO YES UNKNOWN", "explicit_confirmations.openings"),
]


def _resolved(payload, path):
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    if "status" in value:
        return value["status"] != "UNSET" and value.get("provenance") is not None
    return bool(value) and all(_resolved({"v": item}, "v") for item in value.values())


def build_ufh_pre_generation_questions(project_context: ProjectContext,
                                       authoring_state: QuestionnaireState) -> QuestionnaireResult:
    decisions = {**authoring_state.decisions, **project_context.known_decisions}
    payload = authoring_state.authoring.model_dump(mode="json")
    dependency_values = {key: item.value for key, item in decisions.items()}
    mode = payload["ufh_design_settings"].get("mode", {})
    if "thermal" not in dependency_values and _resolved(payload, "ufh_design_settings.mode"):
        dependency_values["thermal"] = {"solve_supply": "KNOWN_DELTA_T", "solve_return": "KNOWN_SUPPLY_TEMPERATURE"}.get(mode.get("value"))
    questions, requirements = [], []
    project_owned_paths = {
        item.canonical_field_path
        for item in (project_context.project_owned_values.values
                     if project_context.project_owned_values is not None else [])
    }
    project_owned_question_targets = {
        "building_physics.air_changes_per_hour"
        for path in project_owned_paths
        if path == "sizing.room.insulation.air_changes_per_hour"
    }
    envelope_source = decisions.get("envelope.source")
    operating_scope = None
    if envelope_source is not None and isinstance(envelope_source.value, dict):
        operating_scope = envelope_source.value.get("construction_scope")
        assemblies = envelope_source.value.get("assemblies", [])
        kinds = {item.get("boundary_kind") for item in assemblies if isinstance(item, dict)}
        if kinds and kinds <= {"EXTERIOR_WALL", "WINDOW", "EXTERIOR_DOOR"}:
            operating_scope = "EXTERIOR_ENVELOPE"
        elif kinds and kinds == {"INTERIOR_WALL_DIFFERENT_ZONE"}:
            operating_scope = "INTERIOR"
    for q in QUESTIONS:
        if q.question_id in {"indoor_rh", "moisture_zone"}:
            if operating_scope != "EXTERIOR_ENVELOPE":
                continue
            if _resolved(payload, "envelope_constructions.operating_condition"):
                continue
        if not all(parent in dependency_values and dependency_values[parent] in options
                   for parent, options in q.dependency_conditions.items()):
            continue
        if all(_resolved(payload, path) for path in q.targets):
            continue
        if any(target in project_owned_question_targets for target in q.targets):
            continue
        if q.question_id in decisions:
            decision = decisions[q.question_id]
            workflow = "GEOMETRY_SELECTION_REQUIRED" if q.question_id in {"exclusions", "openings"} and decision.value == "YES" else "RESOLUTION_REQUIRED"
            requirements.append(workflow + ":" + q.question_id)
        else:
            questions.append(q)
    body = {"questions": [q.model_dump(mode="json") for q in questions],
            "resolver_requirements": requirements, "context": project_context.model_dump(mode="json"),
            "state": authoring_state.model_dump(mode="json")}
    return QuestionnaireResult(questions=questions, resolver_requirements=requirements, digest=digest(body))


def apply_ufh_questionnaire_answers(project_context: ProjectContext, state: QuestionnaireState,
                                    answers: list[Decision]) -> QuestionnaireState:
    """Atomic ordered application. Callers supply stable revision metadata, never wall-clock defaults."""
    result = state.model_copy(deep=True)
    payload = result.authoring.model_dump(mode="json")
    for answer in answers:
        available = {q.question_id: q for q in build_ufh_pre_generation_questions(project_context, result).questions}
        if answer.question_id not in available:
            raise ValueError("QUESTION_NOT_ACTIVE:" + answer.question_id)
        if answer.source_type != "user_project_decision":
            raise ValueError("USER_ANSWER_SOURCE_REQUIRED")
        q, value = available[answer.question_id], answer.value
        if q.answer_type == "choice" and value not in q.allowed_options:
            raise ValueError("INVALID_OPTION")
        if q.answer_type == "text" and (not isinstance(value, str) or not value.strip()):
            raise ValueError("NONEMPTY_REFERENCE_REQUIRED")
        if q.answer_type == "structured" and not isinstance(value, dict):
            raise ValueError("STRUCTURED_OBJECT_REQUIRED")
        if q.answer_type == "location" and (not isinstance(value, dict) or set(value) != {"settlement", "region"} or not all(isinstance(v, str) and v.strip() for v in value.values())):
            raise ValueError("SETTLEMENT_AND_REGION_REQUIRED")
        if q.answer_type in {"quantity", "point"}:
            keys = {"value", "unit"} if q.answer_type == "quantity" else {"x_mm", "y_mm", "unit", "coordinate_system"}
            if not isinstance(value, dict) or set(value) != keys or value["unit"] != q.unit:
                raise ValueError("INVALID_QUANTITY_OR_UNIT")
            numbers = [value["value"]] if q.answer_type == "quantity" else [value["x_mm"], value["y_mm"]]
            import math
            if any(type(n) not in (int, float) or not math.isfinite(n) for n in numbers):
                raise ValueError("FINITE_NUMBER_REQUIRED")
            if q.unit in {"mm", "K"} and q.answer_type == "quantity" and numbers[0] <= 0:
                raise ValueError("POSITIVE_VALUE_REQUIRED")
            if q.question_id == "indoor_rh" and not 0 <= numbers[0] <= 100:
                raise ValueError("RELATIVE_HUMIDITY_OUT_OF_RANGE")
            if q.answer_type == "point" and (value["coordinate_system"] != project_context.coordinate_system or any(type(n) is not int for n in numbers)):
                raise ValueError("AUTHORITATIVE_INTEGER_MM_FRAME_REQUIRED")
        if q.question_id == "moisture_zone":
            from agent.ufh_envelope_operating_condition_resolver import ConstructionMoistureZoneInput
            try:
                ConstructionMoistureZoneInput.model_validate(value)
            except Exception as error:
                raise ValueError("INVALID_CONSTRUCTION_MOISTURE_ZONE_INPUT") from error

        def assign(path, raw, unit, status="EXPLICIT_VALUE"):
            group, key = path.split(".")
            payload[group][key] = {"status": status, "value": raw, "unit": unit,
                "provenance": {"source_type": "project_decision", "source_reference": answer.source_reference,
                "source_field": answer.question_id, "author_or_confirmation": answer.revision,
                "transformation": f"questionnaire:{answer.question_id}; frame={project_context.coordinate_system}", "units": unit}}

        if q.question_id in {"exclusions", "openings"} and value == "NO":
            assign(q.targets[0], [], "none", "EXPLICIT_EMPTY")
        elif q.question_id == "collector":
            for path, key in zip(q.targets, ("x_mm", "y_mm")):
                assign(path, value[key], "mm")
        elif q.question_id in {"layout.spacing", "layout.offset", "thermal.supply", "thermal.delta"}:
            assign(q.targets[0], value["value"], value["unit"])
        elif q.question_id == "thermal" and value != "AUTO_DESIGN":
            assign("ufh_design_settings.mode", "solve_return" if value == "KNOWN_SUPPLY_TEMPERATURE" else "solve_supply", "none")
            payload["design_conditions"]["sigma_k" if value == "KNOWN_SUPPLY_TEMPERATURE" else "theta_supply_c"] = {"status": "UNSET"}
        result.decisions[answer.question_id] = answer
        result.authoring = Test01UfhEngineeringAuthoringTemplate.model_validate(payload)
    return result


def load_questionnaire_authoring(
    state: QuestionnaireState,
    project_context: ProjectContext | None = None,
):
    """Only the existing authoring loader may build a profile; never calls downstream UFH."""
    return load_ufh_project_engineering_authoring_template(
        state.authoring.model_dump(mode="json"),
        project_owned_values=(project_context.project_owned_values
                              if project_context is not None else None),
    )
