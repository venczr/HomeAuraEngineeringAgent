from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException

from agent.model_reader import ModelSnapshot, load_snapshot


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECTS_DIRECTORY = ROOT_DIRECTORY / "projects"

app = FastAPI(
    title="HomeAura Engineering Agent API",
    description="Локальный API для связи AI-агента с AutoCAD и MagiCAD.",
    version="0.2.0",
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


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "HomeAura Engineering Agent API",
        "version": "0.2.0",
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
    project_directory = resolve_project_directory(project_name)

    snapshot_path = (
        project_directory
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

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )

    history_path = (
        history_directory
        / f"model_snapshot_{timestamp}.json"
    )

    history_path.write_text(
        json_text,
        encoding="utf-8",
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
