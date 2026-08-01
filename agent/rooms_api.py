from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from agent.atomic_io import (
    write_text_atomically as _write_text_atomically,
)
from agent.ifc_space_models import (
    IfcSpaceGeometry as IfcSpaceGeometryModel,
    IfcSpaceImportSummary,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECTS_DIRECTORY = ROOT_DIRECTORY / "projects"

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["rooms"],
)


class RoomPoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    X: float
    Y: float
    Z: float


class RoomBoundaryVertex(BaseModel):
    model_config = ConfigDict(extra="ignore")

    X: float
    Y: float
    Z: float
    Bulge: float = 0.0
    SegmentType: str = "Line"


class RoomBoundaryDiagnostics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    IsSupported: bool = False
    IsValid: bool = False
    DuplicateVerticesRemoved: int = 0
    IsSelfIntersecting: bool = False
    MinimumVertexCount: int = 3
    VertexToleranceDrawingUnits: float = 0.0
    ArcChordToleranceDrawingUnits: float = 0.0
    ContainingMarkerHandles: list[str] = Field(
        default_factory=list
    )
    Messages: list[str] = Field(default_factory=list)


class RoomBoundary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    SourceHandle: str
    SourceObjectType: str
    SourceLayer: str
    Vertices: list[RoomBoundaryVertex] = Field(
        default_factory=list
    )
    IsClosed: bool
    ContourAreaDrawingUnits2: float | None = None
    ContourAreaM2: float | None = None
    PerimeterDrawingUnits: float | None = None
    PerimeterM: float | None = None
    OriginalDirection: str | None = None
    Direction: str | None = None
    DrawingUnits: str
    MetersPerDrawingUnit: float | None = None
    GeometrySource: str
    Diagnostics: RoomBoundaryDiagnostics = Field(
        default_factory=RoomBoundaryDiagnostics
    )
    SourceVertices: list[RoomBoundaryVertex] = Field(
        default_factory=list
    )
    OriginalClosedFlag: bool = False
    LogicalClosureMethod: str | None = None
    ZDeviationDrawingUnits: float | None = None
    ZDeviationM: float | None = None
    IsPlanar: bool = False
    Polyline3dType: str | None = None
    HasMagiCadData: bool = False


class RoomBoundaryCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    SourceHandle: str
    SourceObjectType: str
    SourceLayer: str
    GeometrySource: str
    HasMagiCadData: bool = False
    PriorityTier: int
    PriorityReason: str
    BoundaryAreaM2: float | None = None
    AreaDifferenceM2: float | None = None
    AreaDifferencePercent: float | None = None
    AreaMatchStatus: str
    GeometryStatus: str
    IsSelected: bool = False


class MagiCadRoom(BaseModel):
    model_config = ConfigDict(extra="ignore")

    SourceHandle: str
    SourceLayer: str
    Position: RoomPoint

    Code: str
    Name: str

    HeatingTemperatureC: float | None = None
    SupplyAirTemperatureC: float | None = None
    OutdoorTemperatureC: float | None = None

    RoomHeightMm: float | None = None

    NetAreaM2: float | None = None
    GrossAreaM2: float | None = None
    NetVolumeM3: float | None = None
    GrossVolumeM3: float | None = None

    SupplyAirflowLs: float | None = None
    ExtractAirflowLs: float | None = None

    SupplyAirflowM3H: float | None = None
    ExtractAirflowM3H: float | None = None

    SupplyAirflowLsM2: float | None = None
    SupplyAirflowM3HM2: float | None = None

    AirExchangeRate: float | None = None
    ExtractPercentOfSupply: float | None = None
    LeakageFactor: float | None = None

    TotalHeatLossW: float | None = None
    HeatLossWM2: float | None = None
    StructuralHeatLossW: float | None = None

    SupplyAirHeatLossW: float | None = None
    ExtractTransferHeatLossW: float | None = None
    LeakageHeatLossW: float | None = None

    Warnings: list[str] = Field(default_factory=list)

    MagiCadNetAreaM2: float | None = None
    Boundary: RoomBoundary | None = None
    BoundaryAreaDifferenceM2: float | None = None
    BoundaryAreaDifferencePercent: float | None = None
    BoundaryAreaM2: float | None = None
    geometry_status: str | None = None
    area_match_status: str | None = None
    boundary_selection_status: str | None = None
    boundary_selection_warning: str | None = None
    boundary_candidates: list[
        RoomBoundaryCandidate
    ] = Field(default_factory=list)
    IfcSpaceGeometry: IfcSpaceGeometryModel | None = None

    @model_validator(mode="after")
    def preserve_magi_cad_area(self) -> "MagiCadRoom":
        if self.MagiCadNetAreaM2 is None:
            self.MagiCadNetAreaM2 = self.NetAreaM2
        return self


class RoomExportReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    FormatVersion: str
    ParserVersion: str
    GeneratedAtUtc: str
    DrawingName: str
    DrawingFullPath: str
    FoundMarkers: int

    Rooms: list[MagiCadRoom] = Field(
        default_factory=list
    )

    Warnings: list[str] = Field(
        default_factory=list
    )

    FoundBoundaryCandidates: int = 0
    ValidBoundaryCandidates: int = 0
    BoundaryDiagnostics: list[str] = Field(
        default_factory=list
    )
    IfcSpaceImport: IfcSpaceImportSummary | None = None


def resolve_project_directory(
    project_name: str,
) -> Path:
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


@router.post("/{project_name}/rooms")
def save_rooms(
    project_name: str,
    report: RoomExportReport,
) -> dict:
    project_directory = resolve_project_directory(
        project_name
    )

    rooms_directory = (
        project_directory
        / "exports"
        / "rooms"
    )

    history_directory = (
        rooms_directory
        / "history"
    )

    rooms_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    history_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_text = report.model_dump_json(indent=2)

    rooms_path = rooms_directory / "rooms.json"

    history_path = (
        history_directory
        / f"rooms_{create_timestamp()}.json"
    )

    # Commit immutable history first. If it fails, the current snapshot remains
    # untouched. Each same-directory replace is atomic for readers.
    _write_text_atomically(history_path, json_text)
    _write_text_atomically(rooms_path, json_text)

    total_area = sum(
        room.NetAreaM2 or 0
        for room in report.Rooms
    )

    total_heat_loss = sum(
        room.TotalHeatLossW or 0
        for room in report.Rooms
    )

    total_supply = sum(
        room.SupplyAirflowM3H or 0
        for room in report.Rooms
    )

    total_extract = sum(
        room.ExtractAirflowM3H or 0
        for room in report.Rooms
    )

    return {
        "status": "ok",
        "project": project_name,
        "drawing": report.DrawingName,
        "found_markers": report.FoundMarkers,
        "exported_rooms": len(report.Rooms),
        "total_net_area_m2": total_area,
        "total_heat_loss_w": total_heat_loss,
        "total_supply_m3h": total_supply,
        "total_extract_m3h": total_extract,
        "rooms_path": str(rooms_path),
        "history_path": str(history_path),
    }


@router.get("/{project_name}/rooms")
def get_rooms(project_name: str) -> dict:
    rooms_path = (
        resolve_project_directory(project_name)
        / "exports"
        / "rooms"
        / "rooms.json"
    )

    if not rooms_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Файл не найден: {rooms_path}",
        )

    return RoomExportReport.model_validate_json(
        rooms_path.read_text(encoding="utf-8")
    ).model_dump(mode="json")
