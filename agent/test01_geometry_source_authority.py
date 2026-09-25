"""Read-only, revision-pinned Test_01 geometry binding. Not a general IFC matcher.

The authority decision applies only to the evidence set reviewed in
TEST01_GEOMETRY_SOURCE_AUTHORITY_BINDING_V1. Changed sources require re-audit.
Geometry is obtained exclusively through the existing production IFC importer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from agent.ifc_space_importer import analyze_ifc_spaces
from agent.rooms_api import RoomBoundary, RoomExportReport
from agent.ufh_project_adapter import ProjectFieldProvenance, ProjectRoomUfhSource


EXPECTED_HASHES = {
    "current_dwg": "5a673aaa50f8d29c21555d60d7fec740ff3ce214cd7eb65ae329dc3b701397ac",
    "companion_dwg": "5a673aaa50f8d29c21555d60d7fec740ff3ce214cd7eb65ae329dc3b701397ac",
    "current_mrd": "145bc790981253a1b42f5857ff1b9e64dd4175ff3155d4d8f76437b31a512252",
    "companion_mrd": "8651e8b8a2f9320283f0c05cbf27f54f3ba4ac01f9ae94f3d27c5d89ee282897",
    "rooms": "30ee1828e74ecbf1e1b46064c39ce30755a4692fc4cd972d1e38328affe0992e",
    "snapshot": "094c60a73df5b3d43fbab368375f26825944c3de88c15f018c5935637bcbf167",
    "ifc": "01f10257cfcd31de8b682a2ced11045a3816970b9724c9fd6ba8133325954943",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


class GeometryAuthorityDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["AUTHORITATIVE", "VALIDATED_CANDIDATE", "REJECTED", "NEEDS_FRESH_NATIVE_EXPORT"]
    reasons: tuple[str, ...]
    evidence: dict[str, Any]
    ufh_source: ProjectRoomUfhSource | None = None

    @property
    def decision_digest(self) -> str:
        return _digest(self.model_dump(mode="json"))


def assess_test01_geometry_authority(
    project_directory: Path,
    ifc_directory: Path,
) -> GeometryAuthorityDecision:
    """Evaluate the reviewed source set without file writes or UFH execution.

    Both directories are explicit: there is no machine-specific default path,
    source discovery, persistence migration, or fallback to another IFC.
    """
    project_directory, ifc_directory = project_directory.resolve(), ifc_directory.resolve()
    paths = {
        "current_dwg": project_directory / "Test_01.dwg",
        "companion_dwg": ifc_directory / "Test_01_ifc_copy.dwg",
        "current_mrd": project_directory / "HomeAura_Test_01.mrd",
        "companion_mrd": ifc_directory / "HomeAura_Test_01.mrd",
        "rooms": project_directory / "exports/rooms/rooms.json",
        "snapshot": project_directory / "exports/model_snapshot.json",
        "ifc": ifc_directory / "Test_01_rooms_ifc4.ifc",
    }
    payloads: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        try:
            payloads[name] = path.read_bytes()
            hashes[name] = hashlib.sha256(payloads[name]).hexdigest()
        except OSError:
            return GeometryAuthorityDecision(status="NEEDS_FRESH_NATIVE_EXPORT",
                reasons=(f"SOURCE_UNAVAILABLE:{name}",), evidence={"hashes": hashes})
    evidence: dict[str, Any] = {
        "source_paths": {key: str(path) for key, path in paths.items()},
        "hashes": hashes,
        "dwg_byte_identical": hashes["current_dwg"] == hashes["companion_dwg"],
        "mrd_byte_identical": hashes["current_mrd"] == hashes["companion_mrd"],
    }
    changed = tuple(f"UNREVIEWED_SOURCE_REVISION:{key}" for key in hashes
                    if hashes[key] != EXPECTED_HASHES[key])
    if changed:
        return GeometryAuthorityDecision(status="NEEDS_FRESH_NATIVE_EXPORT",
                                         reasons=changed, evidence=evidence)

    raw = json.loads(payloads["rooms"])
    report = RoomExportReport.model_validate(raw)
    room = next(item for item in report.Rooms if item.SourceHandle == "101DAA3")
    outcome = analyze_ifc_spaces(paths["ifc"], raw, rooms_path_label=str(paths["rooms"]))
    if len(outcome.matched_geometries) != 1:
        return GeometryAuthorityDecision(status="REJECTED",
            reasons=("ROOM_MATCH_NOT_UNIQUE",), evidence=evidence)
    geometry = outcome.matched_geometries[0]
    loop = geometry.OuterBoundaryLoop
    if not (geometry.geometry_status == "validated_candidate" and geometry.MatchStatus == "matched"
            and geometry.MatchedRoomCode == room.Code == "101"
            and geometry.IfcSpace.GlobalId == "3Vmsu$eoz6VAzSuuOWXaVz"
            and loop is not None and loop.IsClosed and loop.IsPlanar
            and not loop.IsSelfIntersecting and loop.Direction == "CCW"
            and loop.DistinctVertexCount == 4 and not geometry.InnerBoundaryLoops):
        return GeometryAuthorityDecision(status="REJECTED",
            reasons=("ROOM_GEOMETRY_EVIDENCE_INVALID",), evidence=evidence)

    # Comparison only. No polygon is constructed from wall extents.
    entities = {e["Handle"]: e for e in json.loads(payloads["snapshot"])["Entities"]}
    xs, ys = [p.X * 1000 for p in loop.WorldVertices], [p.Y * 1000 for p in loop.WorldVertices]
    wall_sides = (
        ("101DAAB", "Maximum", "X", min(xs)),
        ("101DABF", "Minimum", "X", max(xs)),
        ("101DAC7", "Maximum", "Y", min(ys)),
        ("101DAB7", "Minimum", "Y", max(ys)),
    )
    deltas = {handle: abs(entities[handle]["Extents"][end][axis] - value)
              for handle, end, axis, value in wall_sides}
    evidence.update({"wall_side_deltas_mm": deltas,
        "marker_inside_ifc_extents": min(xs) < room.Position.X < max(xs)
                                      and min(ys) < room.Position.Y < max(ys),
        "match_method": geometry.MatchMethod,
        "direct_ifc_cad_handle_link": False,
        "ifc_geometry_digest": _digest(geometry.model_dump(mode="json")),
        "ifc_area_m2": geometry.AreaM2,
        "net_area_m2": room.NetAreaM2,
        "area_difference_m2": geometry.NetAreaDifferenceM2})
    if max(deltas.values()) > 0.000005 or not evidence["marker_inside_ifc_extents"]:
        return GeometryAuthorityDecision(status="REJECTED",
            reasons=("GEOMETRIC_FINGERPRINT_MISMATCH",), evidence=evidence)

    import ifcopenshell
    model = ifcopenshell.open(str(paths["ifc"]))
    space = model.by_guid(geometry.IfcSpace.GlobalId)
    level = space.Decomposes[0].RelatingObject
    building = level.Decomposes[0].RelatingObject
    if not (level.is_a("IfcBuildingStorey") and building.is_a("IfcBuilding")
            and level.GlobalId == "0oQei_Jnn60QnqOIJ3NBzE"
            and building.GlobalId == "1kDE4UYl903ebi3UdgvjXG"):
        return GeometryAuthorityDecision(status="REJECTED",
            reasons=("IFC_IDENTITY_CHAIN_MISMATCH",), evidence=evidence)
    evidence["identity_chain"] = {
        "room_handle": room.SourceHandle, "ifc_space": space.GlobalId,
        "building": building.GlobalId, "level": level.GlobalId,
    }
    evidence["scope"] = "Reviewed Test_01 room 101 geometry and IFC hierarchy only; not MRD equivalence"
    evidence_digest = _digest(evidence)

    def provenance(source_path: str) -> ProjectFieldProvenance:
        return ProjectFieldProvenance(source_kind="room_extraction",
            source_file=str(paths["ifc"]), source_sha256=hashes["ifc"],
            source_path=source_path,
            transformation=f"Reviewed authority evidence SHA256={evidence_digest}; production IFC extraction; existing UFH integer-mm conversion")

    boundary = RoomBoundary(SourceHandle=space.GlobalId, SourceObjectType="IfcSpace",
        SourceLayer="IFC.Body", Vertices=[{"X": p.X, "Y": p.Y, "Z": p.Z,
                                          "Bulge": 0.0, "SegmentType": "Line"}
                                          for p in loop.WorldVertices],
        IsClosed=True, IsPlanar=True, Direction=loop.Direction,
        DrawingUnits="Meters", MetersPerDrawingUnit=1.0,
        GeometrySource="MagiCADRoomIfcSpace.authority_binding",
        ContourAreaM2=geometry.AreaM2,
        Diagnostics={"IsValid": True, "IsSupported": True, "IsSelfIntersecting": False})
    source = ProjectRoomUfhSource(project_id="Test_01", room_id=room.SourceHandle,
        building_id=building.GlobalId, level_id=level.GlobalId,
        room_export=report, selected_room=room, source_file=str(paths["rooms"]),
        source_sha256=hashes["rooms"], source_kind="room_extraction",
        authoritative_boundary=boundary,
        boundary_provenance=provenance("#31.Representation -> #33; WorldVertices (metres)"),
        identity_provenance={
            "identity.building_id": provenance("#31 -> IfcRelAggregates #57 -> #29 -> #56 -> #17.GlobalId"),
            "identity.level_id": provenance("#31 -> IfcRelAggregates #57 -> #29.GlobalId"),
        })
    # Detect source mutation during importer reads; no stale binding is returned.
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]
           for key, path in paths.items()):
        return GeometryAuthorityDecision(status="NEEDS_FRESH_NATIVE_EXPORT",
            reasons=("SOURCE_CHANGED_DURING_ASSESSMENT",), evidence=evidence)
    return GeometryAuthorityDecision(status="AUTHORITATIVE", reasons=(
        "REVIEWED_REVISION_SET", "BYTE_IDENTICAL_DWG", "TRACEABLE_ROOM_MATCH",
        "FOUR_WALL_GEOMETRIC_FINGERPRINT", "PRODUCTION_GEOMETRY_VALIDATED",
        "MRD_DIFFERENCE_RETAINED_WITHOUT_CLAIMING_DATABASE_EQUIVALENCE"),
        evidence=evidence, ufh_source=source)
