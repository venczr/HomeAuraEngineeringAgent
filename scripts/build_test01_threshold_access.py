"""Build the geometry-only door-threshold access review for Test_01.

Inputs
------
* ``dev/ufh_real_plan/two_floor_summary.json`` - room boundaries and the
  validated coverage centrelines.
* ``dev/ufh_real_plan/door_openings_from_pdf.json`` - source-vector door
  thresholds already extracted from the plan PDFs.
* ``dev/ufh_real_plan/door_symbol_inventory_audit.json`` - per-room audit of
  the source vectors when no full door symbol is present.

Output
------
* ``dev/ufh_real_plan/room_threshold_access.json`` and ``.svg``.

The script changes no routing, no manifold status and no authority flag.  It
only records, per room, whether two independent in-room pipe paths can reach
the detected threshold.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shapely.geometry import LineString, Polygon

from agent.ufh_threshold_access import check_threshold_access


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dev" / "ufh_real_plan"

STATUS_ORDER = (
    "TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID",
    "TWO_PATHS_BELOW_SEPARATION",
    "SINGLE_PATH_ONLY",
    "THRESHOLD_UNREACHABLE",
    "ENDPOINT_A_UNREACHABLE",
    "NO_BOUND_DOOR_SYMBOL",
    "NO_COVERAGE_ROUTE",
    "GEOMETRY_INVALID",
)

# A door symbol is bound to a room only when the drawn opening comes within
# this distance of the room's own modelled boundary.  The extractor can store
# the opposite wall band of a shared opening; projecting onto the room's own
# boundary recovers the threshold that actually belongs to that room.
THRESHOLD_BINDING_TOLERANCE_MM = 300.0


def _room_threshold(
    boundary_mm: list[list[float]],
    door_mm: list[list[float]],
) -> tuple[list[list[float]] | None, float]:
    """Return the room's own threshold segment and the measured band offset."""
    room = Polygon([tuple(p) for p in boundary_mm])
    door = LineString([tuple(p) for p in door_mm])
    offset = float(door.distance(room.boundary))
    if offset > THRESHOLD_BINDING_TOLERANCE_MM:
        return None, offset
    portion = room.boundary.intersection(door.buffer(THRESHOLD_BINDING_TOLERANCE_MM))
    if portion.is_empty:
        return None, offset
    if portion.geom_type == "MultiLineString":
        portion = max(portion.geoms, key=lambda geom: geom.length)
    if portion.geom_type != "LineString" or portion.length <= 0:
        return None, offset
    coords = list(portion.coords)
    return [[coords[0][0], coords[0][1]], [coords[-1][0], coords[-1][1]]], offset


def _load(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main() -> None:
    summary = _load("two_floor_summary.json")
    doors = _load("door_openings_from_pdf.json")["openings"]
    audit = _load("door_symbol_inventory_audit.json")

    audit_by_room: dict[str, dict] = {}
    for document in audit["documents"]:
        for row in document["rooms"]:
            audit_by_room[row["room_hypothesis_id"]] = row

    thresholds_by_room: dict[str, list[dict]] = {}
    for door in doors:
        for room_id in door.get("adjacent_room_ids", []):
            thresholds_by_room.setdefault(room_id, []).append(door)

    rooms: list[dict] = []
    for record in summary["rooms"]:
        room_id = record["room_hypothesis_id"]
        boundary = record.get("floor_global_boundary_mm") or []
        routes = record.get("physical_coverage_routes_mm") or []
        entry: dict[str, object] = {
            "room_id": room_id,
            "label": record.get("label"),
            "floor": record.get("floor_source_id"),
            "geometry_status": record.get("geometry_status"),
            "bound_threshold_count": len(thresholds_by_room.get(room_id, [])),
        }
        if not routes:
            entry.update({
                "status": "NO_COVERAGE_ROUTE",
                "diagnostics": ["ROOM_HAS_NO_VALIDATED_COVERAGE_ROUTE"],
                "door_passage_authorized": "UNVERIFIED",
                "manifold_connected": "UNVERIFIED",
            })
            rooms.append(entry)
            continue
        route = max(
            routes,
            key=lambda pts: sum(
                ((pts[i][0] - pts[i - 1][0]) ** 2 + (pts[i][1] - pts[i - 1][1]) ** 2) ** 0.5
                for i in range(1, len(pts))
            ),
        )
        entry["coverage_endpoints_mm"] = [route[0], route[-1]]
        bound = thresholds_by_room.get(room_id, [])
        projected: list[tuple[dict, list[list[float]], float]] = []
        for door in bound:
            threshold, offset = _room_threshold(boundary, door["opening_mm"])
            if threshold is not None:
                projected.append((door, threshold, offset))
        if not projected:
            room_audit = audit_by_room.get(room_id, {})
            entry.update({
                "status": "NO_BOUND_DOOR_SYMBOL",
                "diagnostics": [
                    "SOURCE_VECTOR_DOOR_SYMBOL_NOT_BOUND_TO_THIS_ROOM",
                    room_audit.get("inventory_status", "NO_INVENTORY_ROW"),
                ],
                "source_wall_gap_candidate_count": room_audit.get("wall_gap_candidate_count", 0),
                "door_symbol_inventory_status": room_audit.get("inventory_status"),
                "rejected_door_bindings": [
                    {
                        "opening_id": door["opening_id"],
                        "measured_band_offset_mm": round(
                            float(LineString([tuple(p) for p in door["opening_mm"]]).distance(
                                Polygon([tuple(p) for p in boundary]).boundary)), 3),
                    }
                    for door in bound
                ],
                "door_passage_authorized": "UNVERIFIED",
                "manifold_connected": "UNVERIFIED",
            })
            rooms.append(entry)
            continue

        # A room can carry several source-detected openings.  Evaluate every
        # one of them and keep the best geometric result: the room passes only
        # when at least one of its own thresholds admits two independent paths.
        evaluations = []
        for door, threshold, offset in projected:
            evaluated = check_threshold_access(boundary, threshold, [route[0], route[-1]])
            evaluations.append((door, threshold, offset, evaluated))
        rank = {
            "TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID": 0,
            "SINGLE_PATH_ONLY": 1,
            "TWO_PATHS_BELOW_SEPARATION": 2,
            "THRESHOLD_UNREACHABLE": 3,
            "ENDPOINT_A_UNREACHABLE": 4,
        }
        evaluations.sort(key=lambda item: (
            rank.get(item[3].status, 9),
            -int(item[0].get("width_mm") or 0),
            0 if item[0].get("transit_preview_allowed") else 1,
        ))
        chosen, chosen_threshold, chosen_offset, result = evaluations[0]
        entry["threshold"] = {
            "opening_id": chosen["opening_id"],
            "opening_mm": chosen["opening_mm"],
            "room_threshold_mm": chosen_threshold,
            "measured_band_offset_mm": round(chosen_offset, 3),
            "width_mm": chosen["width_mm"],
            "passage_status": chosen.get("passage_status"),
            "transit_preview_allowed": chosen.get("transit_preview_allowed"),
            "all_bound_threshold_ids": [d["opening_id"] for d in bound],
            "projected_threshold_ids": [d["opening_id"] for d, _t, _o in projected],
        }
        entry["threshold_evaluations"] = [
            {
                "opening_id": door["opening_id"],
                "width_mm": door["width_mm"],
                "transit_preview_allowed": door.get("transit_preview_allowed"),
                "measured_band_offset_mm": round(offset, 3),
                "status": evaluated.status,
                "minimum_pair_separation_mm": (
                    None if evaluated.minimum_pair_separation_mm is None
                    else round(evaluated.minimum_pair_separation_mm, 3)
                ),
            }
            for door, _threshold, offset, evaluated in evaluations
        ]
        entry.update(result.as_dict())
        rooms.append(entry)

    rooms.sort(key=lambda row: (
        STATUS_ORDER.index(row["status"]) if row["status"] in STATUS_ORDER else len(STATUS_ORDER),
        str(row["label"]),
    ))
    total = len(rooms)
    valid = sum(row["status"] == "TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID" for row in rooms)
    payload = {
        "method": "GEOMETRY_ONLY_TWO_INDEPENDENT_IN_ROOM_PATHS_TO_DETECTED_THRESHOLD",
        "policy": {
            "wall_offset_mm": 100.0,
            "pipe_outer_diameter_mm": 16.0,
            "minimum_free_clearance_mm": 16.0,
            "grid_step_mm": 100.0,
        },
        "rooms_total": total,
        "two_independent_paths_geometric_valid": valid,
        "status_counts": {
            status: sum(row["status"] == status for row in rooms) for status in STATUS_ORDER
            if any(row["status"] == status for row in rooms)
        },
        "rooms": rooms,
        "statuses": {
            "ENDPOINT_TO_THRESHOLD_PATH_GEOMETRIC": f"{valid}/{total}",
            "DOOR_PASSAGE_AUTHORIZED": "UNVERIFIED",
            "CORRIDOR_PATH_GEOMETRIC": "UNVERIFIED",
            "MANIFOLD_CONNECTED": "UNVERIFIED",
        },
        "engineering_boundary": (
            "In-room geometric reachability only. It does not authorize a wall "
            "penetration, a corridor lane, a riser crossing or a manifold connection."
        ),
    }
    (OUT / "room_threshold_access.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _render_svg(payload, OUT / "room_threshold_access.svg")
    print(json.dumps({
        "rooms_total": total,
        "two_independent_paths_geometric_valid": valid,
        "status_counts": payload["status_counts"],
    }, ensure_ascii=False, indent=2))


def _render_svg(payload: dict, output: Path) -> None:
    summary = json.loads((OUT / "two_floor_summary.json").read_text(encoding="utf-8"))
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24000 20000">',
             '<rect x="0" y="0" width="24000" height="20000" fill="#ffffff"/>',
             '<text x="200" y="260" font-size="260">THRESHOLD ACCESS REVIEW - geometry only</text>',
             '<text x="200" y="480" font-size="170">red = supply path, blue = return path, amber = detected threshold</text>']
    for record in summary["rooms"]:
        row = next((r for r in payload["rooms"] if r["room_id"] == record["room_hypothesis_id"]), None)
        boundary = record.get("floor_global_boundary_mm") or []
        if boundary:
            points = " ".join(f"{x},{y}" for x, y in boundary)
            parts.append(f'<polygon data-layer="room-boundary" data-room-id="{record["room_hypothesis_id"]}" '
                         f'points="{points}" fill="none" stroke="#94a3b8" stroke-width="20"/>')
        if not row:
            continue
        for key, colour, role in (("path_supply_mm", "#d92d20", "supply"),
                                  ("path_return_mm", "#1570ef", "return")):
            path = row.get(key) or []
            if len(path) >= 2:
                points = " ".join(f"{x},{y}" for x, y in path)
                parts.append(f'<polyline data-layer="threshold-access" data-flow-role="{role}" '
                             f'data-room-id="{row["room_id"]}" points="{points}" fill="none" '
                             f'stroke="{colour}" stroke-width="26"/>')
        threshold = (row.get("threshold") or {}).get("opening_mm")
        if threshold:
            (x1, y1), (x2, y2) = threshold
            parts.append(f'<line data-layer="threshold" data-room-id="{row["room_id"]}" '
                         f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#f59e0b" '
                         f'stroke-width="48" stroke-dasharray="120 60"/>')
    parts.append("</svg>")
    output.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
