from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from agent.atomic_io import (
    write_text_atomically as _write_text_atomically,
)
from agent.domain_preview_api import (
    router as domain_preview_router,
)
from agent.ifc_space_preview_api import (
    router as ifc_space_preview_router,
)
from agent.model_reader import (
    ModelSnapshot,
    reject_non_finite_json_constant,
)
from agent.project_preview_api import (
    router as project_preview_router,
)

from agent.rooms_api import RoomExportReport
from agent.rooms_api import router as rooms_router


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECTS_DIRECTORY = ROOT_DIRECTORY / "projects"
STORAGE_ERROR_DETAIL = (
    "Не удалось выполнить операцию с локальным хранилищем."
)

app = FastAPI(
    title="HomeAura Engineering Agent API",
    description="Локальный API для связи AI-агента с AutoCAD и MagiCAD.",
    version="0.6.0",
)

app.include_router(rooms_router)
app.include_router(ifc_space_preview_router)
app.include_router(domain_preview_router)
app.include_router(project_preview_router)


@app.exception_handler(OSError)
async def handle_storage_error(
    _request: Request,
    _exception: OSError,
) -> JSONResponse:
    """Return one safe contract for endpoint filesystem failures."""
    return JSONResponse(
        status_code=500,
        content={"detail": STORAGE_ERROR_DETAIL},
    )


def resolve_project_directory(project_name: str) -> Path:
    if (
        not project_name
        or project_name in {".", ".."}
        or Path(project_name).name != project_name
    ):
        raise HTTPException(
            status_code=400,
            detail="Некорректное имя проекта.",
        )

    try:
        projects_directory = PROJECTS_DIRECTORY.resolve()
        project_directory = (
            PROJECTS_DIRECTORY / project_name
        ).resolve()
        project_directory.relative_to(projects_directory)
    except (OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Путь проекта выходит за каталог projects.",
        ) from None

    return project_directory


def create_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )


def persist_snapshot(
    project_name: str,
    snapshot: ModelSnapshot,
    snapshot_payload: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    project_directory = resolve_project_directory(project_name)

    export_directory = project_directory / "exports"
    history_directory = export_directory / "history"

    if snapshot_payload is None:
        snapshot_payload = snapshot.model_dump(mode="json")

    json_text = json.dumps(
        snapshot_payload,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    export_directory.mkdir(parents=True, exist_ok=True)
    history_directory.mkdir(parents=True, exist_ok=True)

    snapshot_path = export_directory / "model_snapshot.json"
    history_path = (
        history_directory
        / f"model_snapshot_{create_timestamp()}.json"
    )

    _write_text_atomically(history_path, json_text)
    _write_text_atomically(snapshot_path, json_text)

    return snapshot_path, history_path


def load_project_snapshot_payload(
    project_name: str,
) -> dict[str, Any]:
    snapshot_path = (
        resolve_project_directory(project_name)
        / "exports"
        / "model_snapshot.json"
    )

    if not snapshot_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Снимок модели проекта '{project_name}' не найден. "
                "Сначала выполните HA_SYNC_MODEL в AutoCAD."
            ),
        )

    try:
        payload = json.loads(
            snapshot_path.read_text(encoding="utf-8"),
            parse_constant=reject_non_finite_json_constant,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Снимок модели проекта '{project_name}' "
                "содержит недопустимые данные."
            ),
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Снимок модели проекта '{project_name}' "
                "должен быть JSON-объектом."
            ),
        )

    return payload


def load_project_snapshot(project_name: str) -> ModelSnapshot:
    payload = load_project_snapshot_payload(project_name)

    try:
        return ModelSnapshot.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Снимок модели проекта '{project_name}' "
                "не прошёл проверку."
            ),
        ) from exc


def load_project_rooms(
    project_name: str,
) -> RoomExportReport | None:
    rooms_path = (
        resolve_project_directory(project_name)
        / "exports"
        / "rooms"
        / "rooms.json"
    )

    if not rooms_path.is_file():
        return None

    try:
        return RoomExportReport.model_validate_json(
            rooms_path.read_text(encoding="utf-8")
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Данные помещений проекта '{project_name}' "
                "содержат недопустимые данные."
            ),
        ) from exc


def get_entity_point(
    value: Any,
) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None

    try:
        return {
            "X": float(value["X"]),
            "Y": float(value["Y"]),
            "Z": float(value["Z"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def get_entity_extents(
    entity: dict[str, Any],
) -> tuple[
    dict[str, float],
    dict[str, float],
] | None:
    extents = entity.get("Extents")

    if not isinstance(extents, dict):
        return None

    minimum = get_entity_point(extents.get("Minimum"))
    maximum = get_entity_point(extents.get("Maximum"))

    if minimum is None or maximum is None:
        return None

    return minimum, maximum


def find_remote_entities(
    snapshot_payload: dict[str, Any],
    axis: str,
    far_side: str,
    room_minimum: float,
    room_maximum: float,
) -> tuple[bool, int, list[dict[str, Any]]]:
    entities = snapshot_payload.get("Entities")

    if not isinstance(entities, list):
        return False, 0, []

    candidates: list[dict[str, Any]] = []
    entities_with_extents = 0

    for raw_entity in entities:
        if not isinstance(raw_entity, dict):
            continue

        entity_extents = get_entity_extents(raw_entity)

        if entity_extents is None:
            continue

        entities_with_extents += 1
        minimum, maximum = entity_extents

        if far_side == "maximum":
            coordinate = maximum[axis]
            distance = coordinate - room_maximum
        else:
            coordinate = minimum[axis]
            distance = room_minimum - coordinate

        if distance <= 50000:
            continue

        center = get_entity_point(
            raw_entity.get("Center")
        )

        if center is None:
            center = {
                "X": (minimum["X"] + maximum["X"]) / 2,
                "Y": (minimum["Y"] + maximum["Y"]) / 2,
                "Z": (minimum["Z"] + maximum["Z"]) / 2,
            }

        candidates.append(
            {
                "handle": str(
                    raw_entity.get("Handle") or ""
                ),
                "dxf_name": str(
                    raw_entity.get("DxfName") or "UNKNOWN"
                ),
                "rx_class_name": str(
                    raw_entity.get("RxClassName")
                    or "UNKNOWN"
                ),
                "dotnet_type": str(
                    raw_entity.get("DotNetType")
                    or "UNKNOWN"
                ),
                "layer": str(
                    raw_entity.get("Layer") or ""
                ),
                "extents": {
                    "Minimum": minimum,
                    "Maximum": maximum,
                },
                "center": center,
                "far_coordinate_mm":
                    round(coordinate, 3),
                "distance_from_room_markers_mm":
                    round(distance, 3),
                "distance_from_room_markers_m":
                    round(distance / 1000, 3),
            }
        )

    candidates.sort(
        key=lambda item: item[
            "distance_from_room_markers_mm"
        ],
        reverse=True,
    )

    return True, entities_with_extents, candidates[:10]


def analyze_snapshot(
    project_name: str,
    snapshot: ModelSnapshot,
    rooms_report: RoomExportReport | None = None,
    snapshot_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    room_summary: dict[str, Any] = {
        "source": "not_synced",
        "count": 0,
        "codes": [],
        "total_net_area_m2": 0.0,
        "total_heat_loss_w": 0.0,
        "total_supply_m3h": 0.0,
        "total_extract_m3h": 0.0,
    }

    def add_issue(
        severity: str,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        issues.append(
            {
                "severity": severity,
                "code": code,
                "message": message,
                "details": details or {},
            }
        )

    entity_texts: list[tuple[str, int]] = []

    for entity in snapshot.EntityTypes:
        text = " ".join(
            (
                entity.DxfName,
                entity.RxClassName,
                entity.DotNetType,
            )
        ).upper()

        entity_texts.append((text, entity.Count))

    units = snapshot.DrawingUnits.strip().lower()

    if units not in {"millimeters", "millimeter"}:
        add_issue(
            "error",
            "DWG_UNITS_INVALID",
            "Единицы DWG отличаются от миллиметров.",
            {
                "actual": snapshot.DrawingUnits,
                "expected": "Millimeters",
            },
        )
    else:
        add_issue(
            "info",
            "DWG_UNITS_OK",
            "Единицы DWG установлены в миллиметрах.",
        )

    if not snapshot.Is64BitProcess:
        add_issue(
            "error",
            "PROCESS_NOT_X64",
            "AutoCAD запущен не как 64-битный процесс.",
        )

    if snapshot.ModelSpaceEntityCount <= 0:
        add_issue(
            "error",
            "MODEL_EMPTY",
            "Пространство модели не содержит объектов.",
        )
    else:
        add_issue(
            "info",
            "MODEL_NOT_EMPTY",
            "Пространство модели содержит объекты.",
            {
                "entity_count":
                    snapshot.ModelSpaceEntityCount,
            },
        )

    wall_count = sum(
        count
        for text, count in entity_texts
        if "WALL" in text
    )

    if wall_count == 0:
        add_issue(
            "error",
            "WALLS_NOT_FOUND",
            "В снимке модели стены не обнаружены.",
        )
    elif wall_count < 4:
        add_issue(
            "warning",
            "WALL_COUNT_LOW",
            "Обнаружено менее четырёх стен.",
            {
                "wall_count": wall_count,
            },
        )
    else:
        add_issue(
            "info",
            "WALLS_FOUND",
            "Стены обнаружены.",
            {
                "wall_count": wall_count,
            },
        )

    dwg_room_count = sum(
        count
        for text, count in entity_texts
        if "ROOM" in text or "SPACE" in text
    )

    if rooms_report is None:
        add_issue(
            "warning",
            "ROOM_DATA_NOT_FOUND",
            (
                "Синхронизированные данные помещений не найдены. "
                "Выполните HA_SYNC_ROOMS в AutoCAD."
            ),
            {
                "dwg_room_object_count": dwg_room_count,
            },
        )
    elif len(rooms_report.Rooms) == 0:
        room_summary["source"] = "rooms_export"

        add_issue(
            "warning",
            "ROOM_DATA_EMPTY",
            (
                "Файл помещений загружен, но не содержит "
                "ни одного помещения."
            ),
            {
                "found_markers": rooms_report.FoundMarkers,
                "drawing": rooms_report.DrawingName,
            },
        )
    else:
        room_count = len(rooms_report.Rooms)
        total_net_area = sum(
            room.NetAreaM2 or 0.0
            for room in rooms_report.Rooms
        )
        total_heat_loss = sum(
            room.TotalHeatLossW or 0.0
            for room in rooms_report.Rooms
        )
        total_supply = sum(
            room.SupplyAirflowM3H or 0.0
            for room in rooms_report.Rooms
        )
        total_extract = sum(
            room.ExtractAirflowM3H or 0.0
            for room in rooms_report.Rooms
        )

        room_summary = {
            "source": "rooms_export",
            "count": room_count,
            "codes": [
                room.Code
                for room in rooms_report.Rooms
            ],
            "total_net_area_m2": round(total_net_area, 3),
            "total_heat_loss_w": round(total_heat_loss, 3),
            "total_supply_m3h": round(total_supply, 3),
            "total_extract_m3h": round(total_extract, 3),
        }

        add_issue(
            "info",
            "ROOM_DATA_FOUND",
            "Синхронизированные данные помещений загружены.",
            {
                "room_count": room_count,
                "room_codes": room_summary["codes"],
                "total_net_area_m2":
                    room_summary["total_net_area_m2"],
                "total_heat_loss_w":
                    room_summary["total_heat_loss_w"],
                "total_supply_m3h":
                    room_summary["total_supply_m3h"],
                "total_extract_m3h":
                    room_summary["total_extract_m3h"],
            },
        )

        if (
            rooms_report.DrawingName.strip().casefold()
            != snapshot.DrawingName.strip().casefold()
        ):
            add_issue(
                "warning",
                "ROOM_DRAWING_MISMATCH",
                (
                    "Снимок модели и данные помещений получены "
                    "из разных чертежей."
                ),
                {
                    "snapshot_drawing": snapshot.DrawingName,
                    "rooms_drawing": rooms_report.DrawingName,
                },
            )

    proxy_count = sum(
        count
        for text, count in entity_texts
        if "PROXY" in text or "UNKNOWN" in text
    )

    if proxy_count > 0:
        add_issue(
            "warning",
            "PROXY_OBJECTS_FOUND",
            "Обнаружены proxy или неизвестные объекты.",
            {
                "proxy_count": proxy_count,
            },
        )

    minimum = snapshot.Extents.Minimum
    maximum = snapshot.Extents.Maximum

    size_x = maximum.X - minimum.X
    size_y = maximum.Y - minimum.Y
    size_z = maximum.Z - minimum.Z

    if size_x <= 0 or size_y <= 0:
        add_issue(
            "error",
            "MODEL_EXTENTS_INVALID",
            "Габариты модели по X или Y некорректны.",
            {
                "size_x": size_x,
                "size_y": size_y,
                "size_z": size_z,
            },
        )
    else:
        add_issue(
            "info",
            "MODEL_EXTENTS_VALID",
            "Габариты модели рассчитаны.",
            {
                "size_x": round(size_x, 3),
                "size_y": round(size_y, 3),
                "size_z": round(size_z, 3),
            },
        )

    if max(size_x, size_y) > 100000:
        axis = "X" if size_x >= size_y else "Y"
        axis_size = size_x if axis == "X" else size_y
        axis_minimum = (
            minimum.X if axis == "X" else minimum.Y
        )
        axis_maximum = (
            maximum.X if axis == "X" else maximum.Y
        )

        extent_details: dict[str, Any] = {
            "axis": axis,
            "axis_size_mm": round(axis_size, 3),
            "axis_size_m": round(axis_size / 1000, 3),
            "axis_minimum_mm": round(axis_minimum, 3),
            "axis_maximum_mm": round(axis_maximum, 3),
            "size_x_mm": round(size_x, 3),
            "size_y_mm": round(size_y, 3),
        }

        extent_message = (
            f"Габарит модели по оси {axis} составляет "
            f"{axis_size / 1000:.3f} м. Возможно, в чертеже "
            "имеется удалённый объект или лишняя геометрия."
        )

        if rooms_report is not None and rooms_report.Rooms:
            room_axis_positions = [
                (
                    room.Position.X
                    if axis == "X"
                    else room.Position.Y
                )
                for room in rooms_report.Rooms
            ]

            room_minimum = min(room_axis_positions)
            room_maximum = max(room_axis_positions)
            gap_to_minimum = room_minimum - axis_minimum
            gap_to_maximum = axis_maximum - room_maximum

            if gap_to_maximum >= gap_to_minimum:
                far_side = "maximum"
                far_gap = gap_to_maximum
                far_coordinate = axis_maximum
            else:
                far_side = "minimum"
                far_gap = gap_to_minimum
                far_coordinate = axis_minimum

            likely_remote_geometry = far_gap > 50000

            extent_details.update(
                {
                    "room_marker_minimum_mm":
                        round(room_minimum, 3),
                    "room_marker_maximum_mm":
                        round(room_maximum, 3),
                    "far_side": far_side,
                    "far_coordinate_mm":
                        round(far_coordinate, 3),
                    "gap_from_room_markers_mm":
                        round(far_gap, 3),
                    "gap_from_room_markers_m":
                        round(far_gap / 1000, 3),
                    "likely_remote_geometry":
                        likely_remote_geometry,
                }
            )

            if likely_remote_geometry:
                extent_message = (
                    f"Габарит модели по оси {axis} составляет "
                    f"{axis_size / 1000:.3f} м. Дальняя граница "
                    f"находится на {far_gap / 1000:.3f} м от "
                    "диапазона маркеров помещений; вероятна "
                    "удалённая геометрия."
                )

                diagnostics_available = False
                entities_with_extents = 0
                remote_entities: list[
                    dict[str, Any]
                ] = []

                if snapshot_payload is not None:
                    (
                        diagnostics_available,
                        entities_with_extents,
                        remote_entities,
                    ) = find_remote_entities(
                        snapshot_payload,
                        axis,
                        far_side,
                        room_minimum,
                        room_maximum,
                    )

                extent_details.update(
                    {
                        "entity_diagnostics_available":
                            diagnostics_available,
                        "entities_with_extents":
                            entities_with_extents,
                        "remote_entity_count":
                            len(remote_entities),
                        "remote_entities":
                            remote_entities,
                    }
                )

                if remote_entities:
                    first_remote = remote_entities[0]

                    extent_details["remote_entity"] = (
                        first_remote
                    )

                    extent_message = (
                        f"Вероятная удалённая геометрия: "
                        f"Handle {first_remote['handle']}, "
                        f"тип {first_remote['dxf_name']}, "
                        f"слой {first_remote['layer'] or '<без слоя>'}. "
                        f"Объект находится примерно в "
                        f"{first_remote['distance_from_room_markers_m']:.3f} "
                        "м от маркеров помещений."
                    )
                elif diagnostics_available:
                    extent_message += (
                        " Объект, создающий дальнюю границу, "
                        "не найден среди доступных геометрических "
                        "границ; выполни REGENALL и повтори "
                        "HA_SYNC_MODEL."
                    )
                else:
                    extent_message += (
                        " Для определения Handle выполни "
                        "HA_SYNC_MODEL обновлённым плагином."
                    )

        add_issue(
            "warning",
            "MODEL_EXTENTS_LARGE",
            extent_message,
            extent_details,
        )

    if len(snapshot.Layers) == 0:
        add_issue(
            "warning",
            "LAYERS_NOT_FOUND",
            "В чертеже не обнаружены слои.",
        )
    else:
        add_issue(
            "info",
            "LAYERS_FOUND",
            "Список слоёв прочитан.",
            {
                "layer_count": len(snapshot.Layers),
            },
        )

    error_count = sum(
        1 for issue in issues
        if issue["severity"] == "error"
    )

    warning_count = sum(
        1 for issue in issues
        if issue["severity"] == "warning"
    )

    info_count = sum(
        1 for issue in issues
        if issue["severity"] == "info"
    )

    score = max(
        0,
        100 - error_count * 25 - warning_count * 8,
    )

    if error_count > 0:
        status = "failed"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "passed"

    return {
        "status": status,
        "project": project_name,
        "drawing": snapshot.DrawingName,
        "rooms": room_summary,
        "score": score,
        "errors": error_count,
        "warnings": warning_count,
        "infos": info_count,
        "issues": issues,
    }


def persist_analysis_report(
    project_name: str,
    report: dict[str, Any],
) -> tuple[Path, Path]:
    project_directory = resolve_project_directory(project_name)

    analysis_directory = (
        project_directory
        / "exports"
        / "analysis"
    )

    history_directory = (
        analysis_directory
        / "history"
    )

    report_path = analysis_directory / "analysis_report.json"

    history_path = (
        history_directory
        / f"analysis_report_{create_timestamp()}.json"
    )

    report["report_path"] = str(report_path)
    report["history_path"] = str(history_path)

    json_text = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    analysis_directory.mkdir(parents=True, exist_ok=True)
    history_directory.mkdir(parents=True, exist_ok=True)

    _write_text_atomically(history_path, json_text)
    _write_text_atomically(report_path, json_text)

    return report_path, history_path


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "HomeAura Engineering Agent API",
        "version": app.version,
    }


@app.get("/api/v1/projects")
def list_projects() -> dict[str, list[str]]:
    if not PROJECTS_DIRECTORY.exists():
        return {"projects": []}

    projects = sorted(
        directory.name
        for directory in PROJECTS_DIRECTORY.iterdir()
        if directory.is_dir()
    )

    return {"projects": projects}


@app.get("/api/v1/projects/{project_name}/snapshot")
def get_project_snapshot(project_name: str) -> dict:
    return load_project_snapshot_payload(project_name)


@app.post("/api/v1/projects/{project_name}/snapshot")
def save_project_snapshot(
    project_name: str,
    snapshot_payload: dict[str, Any],
) -> dict:
    try:
        snapshot = ModelSnapshot.model_validate(
            snapshot_payload
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Снимок модели не прошёл проверку.",
        ) from exc

    try:
        snapshot_path, history_path = persist_snapshot(
            project_name,
            snapshot,
            snapshot_payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Снимок модели содержит недопустимое "
                "числовое значение."
            ),
        ) from exc

    return {
        "status": "ok",
        "project": project_name,
        "drawing": snapshot.DrawingName,
        "entities": snapshot.ModelSpaceEntityCount,
        "entity_details": (
            len(snapshot_payload["Entities"])
            if isinstance(
                snapshot_payload.get("Entities"),
                list,
            )
            else 0
        ),
        "layers": len(snapshot.Layers),
        "entity_types": len(snapshot.EntityTypes),
        "snapshot_path": str(snapshot_path),
        "history_path": str(history_path),
    }


@app.post("/api/v1/projects/{project_name}/analyze")
def analyze_project(project_name: str) -> dict[str, Any]:
    snapshot_payload = load_project_snapshot_payload(
        project_name
    )

    try:
        snapshot = ModelSnapshot.model_validate(
            snapshot_payload
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Снимок модели проекта '{project_name}' "
                "не прошёл проверку."
            ),
        ) from exc

    rooms_report = load_project_rooms(project_name)

    report = analyze_snapshot(
        project_name,
        snapshot,
        rooms_report,
        snapshot_payload,
    )

    persist_analysis_report(
        project_name,
        report,
    )

    return report
