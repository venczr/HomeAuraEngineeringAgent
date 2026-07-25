from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from agent.model_reader import ModelSnapshot, load_snapshot


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECTS_DIRECTORY = ROOT_DIRECTORY / "projects"

app = FastAPI(
    title="HomeAura Engineering Agent API",
    description="Локальный API для связи AI-агента с AutoCAD и MagiCAD.",
    version="0.3.0",
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

    return PROJECTS_DIRECTORY / project_name


def create_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )


def persist_snapshot(
    project_name: str,
    snapshot: ModelSnapshot,
) -> tuple[Path, Path]:
    project_directory = resolve_project_directory(project_name)

    export_directory = project_directory / "exports"
    history_directory = export_directory / "history"

    export_directory.mkdir(parents=True, exist_ok=True)
    history_directory.mkdir(parents=True, exist_ok=True)

    json_text = snapshot.model_dump_json(indent=2)

    snapshot_path = export_directory / "model_snapshot.json"
    snapshot_path.write_text(
        json_text,
        encoding="utf-8",
    )

    history_path = (
        history_directory
        / f"model_snapshot_{create_timestamp()}.json"
    )

    history_path.write_text(
        json_text,
        encoding="utf-8",
    )

    return snapshot_path, history_path


def analyze_snapshot(
    project_name: str,
    snapshot: ModelSnapshot,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

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

    room_count = sum(
        count
        for text, count in entity_texts
        if "ROOM" in text or "SPACE" in text
    )

    if room_count == 0:
        add_issue(
            "warning",
            "ROOM_DATA_NOT_FOUND",
            (
                "Помещения не обнаружены в DWG-снимке. "
                "Расчётные данные MagiCAD Room находятся "
                "в проекте MRD и будут подключены отдельным "
                "адаптером."
            ),
        )
    else:
        add_issue(
            "info",
            "ROOM_DATA_FOUND",
            "В DWG обнаружены объекты помещений.",
            {
                "room_count": room_count,
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
        add_issue(
            "warning",
            "MODEL_EXTENTS_LARGE",
            (
                "Габарит модели превышает 100 метров. "
                "Возможно, в чертеже имеется удалённый "
                "объект или лишняя геометрия."
            ),
            {
                "size_x": round(size_x, 3),
                "size_y": round(size_y, 3),
            },
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

    analysis_directory.mkdir(parents=True, exist_ok=True)
    history_directory.mkdir(parents=True, exist_ok=True)

    import json

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
    )

    report_path.write_text(
        json_text,
        encoding="utf-8",
    )

    history_path.write_text(
        json_text,
        encoding="utf-8",
    )

    return report_path, history_path


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "HomeAura Engineering Agent API",
        "version": "0.3.0",
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
    snapshot_path = (
        resolve_project_directory(project_name)
        / "exports"
        / "model_snapshot.json"
    )

    try:
        snapshot = load_snapshot(snapshot_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return snapshot.model_dump(mode="json")


@app.post("/api/v1/projects/{project_name}/snapshot")
def save_project_snapshot(
    project_name: str,
    snapshot: ModelSnapshot,
) -> dict:
    snapshot_path, history_path = persist_snapshot(
        project_name,
        snapshot,
    )

    return {
        "status": "ok",
        "project": project_name,
        "drawing": snapshot.DrawingName,
        "entities": snapshot.ModelSpaceEntityCount,
        "layers": len(snapshot.Layers),
        "entity_types": len(snapshot.EntityTypes),
        "snapshot_path": str(snapshot_path),
        "history_path": str(history_path),
    }


@app.post("/api/v1/projects/{project_name}/analyze")
def analyze_project(
    project_name: str,
    snapshot: ModelSnapshot,
) -> dict[str, Any]:
    persist_snapshot(
        project_name,
        snapshot,
    )

    report = analyze_snapshot(
        project_name,
        snapshot,
    )

    persist_analysis_report(
        project_name,
        report,
    )

    return report
