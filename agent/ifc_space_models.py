from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _FiniteModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        allow_inf_nan=False,
    )


class IfcPoint3D(_FiniteModel):

    X: float
    Y: float
    Z: float


class IfcFileInfo(_FiniteModel):

    Path: str
    Sha256: str
    Schema: str


class IfcSpaceInfo(_FiniteModel):

    StepId: int
    GlobalId: str
    Name: str | None = None
    LongName: str | None = None
    ObjectType: str | None = None
    PredefinedType: str | None = None
    StoreyName: str | None = None
    StoreyElevationModelUnits: float | None = None
    StoreyElevationM: float | None = None


class IfcUnitInfo(_FiniteModel):

    LengthUnit: str
    MetersPerLengthUnit: float
    AreaUnit: str | None = None


class IfcRepresentationInfo(_FiniteModel):

    Identifier: str | None = None
    Type: str | None = None
    SolidType: str | None = None
    ProfileType: str | None = None
    CurveType: str | None = None
    ExtrusionDirection: IfcPoint3D | None = None
    TriangulatedVertexCount: int | None = None
    TriangulatedTriangleCount: int | None = None
    TriangulatedAreaM2: float | None = None
    AnalyticAreaDifferenceM2: float | None = None


class IfcBoundaryLoop(_FiniteModel):

    SourceVertices: list[IfcPoint3D] = Field(default_factory=list)
    LocalVertices: list[IfcPoint3D] = Field(default_factory=list)
    WorldVertices: list[IfcPoint3D] = Field(default_factory=list)
    IsClosed: bool = False
    ClosureMethod: str | None = None
    SourceHadRepeatedEndpoint: bool = False
    DuplicateVerticesRemoved: int = 0
    DistinctVertexCount: int = 0
    OriginalDirection: str | None = None
    Direction: str | None = None
    IsSelfIntersecting: bool = False
    IsPlanar: bool = False
    ZDeviationM: float | None = None
    AreaM2: float | None = None
    PerimeterM: float | None = None


class IfcSpaceGeometry(_FiniteModel):

    source: str = "MagiCADRoomIfcSpace"
    geometry_status: str
    IfcFile: IfcFileInfo
    IfcSpace: IfcSpaceInfo
    Units: IfcUnitInfo
    Representation: IfcRepresentationInfo
    LocalToWorldMatrix: list[list[float]]
    MatrixLengthUnit: str
    OuterBoundaryLoop: IfcBoundaryLoop | None = None
    InnerBoundaryLoops: list[IfcBoundaryLoop] = Field(
        default_factory=list
    )
    AreaM2: float | None = None
    PerimeterM: float | None = None
    HeightM: float | None = None
    MatchStatus: str
    MatchMethod: str | None = None
    MatchedRoomCode: str | None = None
    NetAreaDifferenceM2: float | None = None
    NetAreaDifferencePercent: float | None = None
    BoundaryAreaDifferenceM2: float | None = None
    BoundaryAreaDifferencePercent: float | None = None
    Warnings: list[str] = Field(default_factory=list)
    Diagnostics: list[str] = Field(default_factory=list)


class IfcSpaceImportResult(_FiniteModel):

    GlobalId: str | None = None
    Name: str | None = None
    LongName: str | None = None
    Status: str
    MatchMethod: str | None = None
    MatchedRoomCode: str | None = None
    GeometryStatus: str
    Diagnostics: list[str] = Field(default_factory=list)


class IfcSpaceImportSummary(_FiniteModel):

    source: str = "MagiCADRoomIfcSpace"
    Mode: str
    InputIfcPath: str
    InputRoomsPath: str
    OutputPath: str | None = None
    IfcFileSha256: str
    IfcSchema: str
    FoundIfcSpaces: int
    MatchedIfcSpaces: int
    AmbiguousIfcSpaces: int
    UnmatchedIfcSpaces: int
    UnsupportedIfcSpaces: int
    Results: list[IfcSpaceImportResult] = Field(
        default_factory=list
    )
    Diagnostics: list[str] = Field(default_factory=list)
