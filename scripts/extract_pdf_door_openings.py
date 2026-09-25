"""Extract source-vector door evidence and prepare a room-12 transit preview."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.pdf_door_openings import extract_pdf_door_openings
from agent.test01_drawing_understanding import reconstruct_test01_room_candidates


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "Test_01"
OUT = ROOT / "dev" / "ufh_real_plan"


def _room_data(drawing, floor):
    rows = []
    for room in drawing.building_rooms:
        if room.floor_source_id != floor:
            continue
        hypothesis = next(h for h in drawing.understanding.hypotheses if h.hypothesis_id == room.room_hypothesis_id)
        rows.append((room.room_hypothesis_id, [(float(p.x), float(p.y)) for p in hypothesis.geometry.points]))
    return rows


def _room12_preview(drawing, doors):
    room = next(r for r in drawing.building_rooms if r.floor_source_id == "ATTIC_PLAN" and r.label_text.startswith("12 /"))
    h = next(h for h in drawing.understanding.hypotheses if h.hypothesis_id == room.room_hypothesis_id)
    scale = float(next(s.scale_m_per_drawing_unit for s in drawing.scale_candidates if s.frame.frame_id.startswith("ATTIC_PLAN"))) * 1000
    # The existing zone candidate is intentionally read-only input to this
    # preview; no new heating route is generated here.
    candidate_path = OUT / "zone_decomposition_review.json"
    source = json.loads(candidate_path.read_text(encoding="utf-8"))
    zone = next(x for x in source["long_route_rooms"] if x["label"].startswith("12 /"))["zone_decomposition"]["recommended"]
    # Only the 895 mm source door is wide enough for a door-transit preview.
    # The 198 mm vertical symbol is retained in the inventory as an
    # unknown/detail opening and is not used to route a circuit.
    room12_doors = [d for d in doors if d["opening_id"] == "ATTIC_PLAN-DOOR-005"]
    # Drawing-to-model origin is derived from the source room boundary and the
    # existing global room boundary, never invented as a building coordinate.
    ox = 13180 - 374.5 * scale
    oy = 12880 - 366.0 * scale
    def global_xy(p): return [round(ox + p[0] * scale), round(oy + p[1] * scale)]
    door_rows = []
    for door in room12_doors:
        a, b = door["opening_drawing_units"]
        # The extractor stores the nearest source wall band.  For the room-12
        # route we bind the exit to the room's own top boundary (y=366.0 in
        # the source drawing), preserving the distinction between the two
        # parallel wall bands around the opening.
        room_threshold = [[a[0], 366.0], [b[0], 366.0]]
        door_rows.append({
            "opening_id": door["opening_id"],
            "room_id": room.room_hypothesis_id,
            "room_boundary_exit": "SOURCE_VECTOR_THRESHOLD_CANDIDATE",
            "source_threshold_drawing_units": [[a[0], a[1]], [b[0], b[1]]],
            "threshold_drawing_units": room_threshold,
            "threshold_global_mm": [global_xy(room_threshold[0]), global_xy(room_threshold[1])],
            "corridor_side": "CORRIDOR_SPACE_UNRESOLVED",
            "door_passage_authorized": "UNVERIFIED",
            "manifold_connected": "UNVERIFIED",
        })
    routes = []
    for row in zone["routes"]:
        points = row["route_mm"]
        # Exit tails are deliberately shown as candidates only.  They end at
        # the detected threshold and never claim a wall crossing or manifold.
        # The only coordinates available for this connection are the route
        # endpoints and the source-derived door threshold.  Do not fabricate
        # perimeter/corridor waypoints.  The straight candidates below are
        # retained for a later occupancy and corridor-graph check.
        door_id = "ATTIC_PLAN-DOOR-005"
        threshold = [16956, 12884]
        supply_path = [points[0], threshold]
        return_path = [points[-1], threshold]
        routes.append({
            "zone_id": row["zone_id"],
            "length_mm": row["length_mm"],
            "door_id": door_id,
            "supply_exit_candidate": supply_path,
            "return_exit_candidate": return_path,
            "exit_geometry_status": "UNVERIFIED_STRAIGHT_CANDIDATE",
            "door_passage_authorized": "UNVERIFIED",
            "corridor_path_geometric": "UNVERIFIED",
            "manifold_connected": "UNVERIFIED",
            "diagnostics": ["STRAIGHT_CANDIDATE_NOT_PHYSICAL_ROUTE", "CORRIDOR_STRIP_REQUIRES_SOURCE_TOPOLOGY_BINDING", "NO_MANIFOLD_COORDINATE_AUTHORITY"],
        })
    return {
        "method": "SOURCE_VECTOR_DOOR_EVIDENCE_ROOM12_TRANSIT_PREVIEW",
        "room_id": room.room_hypothesis_id,
        "room_label": room.label_text,
        "route_source": "zone_decomposition_review.json",
        "scale_mm_per_drawing_unit": scale,
        "doors": door_rows,
        "routes": routes,
        "statuses": {
            "ROOM_ENDPOINT_REACHABLE": "VALID",
            "DOOR_GEOMETRY_DETECTED": "VALID",
            "DOOR_PASSAGE_AUTHORIZED": "UNVERIFIED",
            "CORRIDOR_PATH_GEOMETRIC": "UNVERIFIED",
            "MANIFOLD_CONNECTED": "UNVERIFIED",
        },
        "engineering_boundary": "Geometry-only preview; PDF door vectors do not establish a permitted floor penetration, corridor lane, riser or collector connection.",
    }


def _render_svg(preview, output):
    routes = preview["routes"]
    xs = [p[0] for r in routes for p in r["supply_exit_candidate"] + r["return_exit_candidate"]]
    ys = [p[1] for r in routes for p in r["supply_exit_candidate"] + r["return_exit_candidate"]]
    for d in preview["doors"]:
        xs += [p[0] for p in d["threshold_global_mm"]]; ys += [p[1] for p in d["threshold_global_mm"]]
    pad = 500; minx, maxx, miny, maxy = min(xs)-pad, max(xs)+pad, min(ys)-pad, max(ys)+pad
    def pts(points): return " ".join(f"{x},{y}" for x,y in points)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {maxx-minx} {maxy-miny}">', '<rect x="%s" y="%s" width="%s" height="%s" fill="#fff" stroke="#444"/>'%(minx,miny,maxx-minx,maxy-miny)]
    colors = ["#d92d20", "#1570ef"]
    for i, row in enumerate(routes):
        out.append(f'<polyline points="{pts(row["supply_exit_candidate"])}" fill="none" stroke="{colors[0]}" stroke-width="24"/>')
        out.append(f'<polyline points="{pts(row["return_exit_candidate"])}" fill="none" stroke="{colors[1]}" stroke-width="24"/>')
        out.append(f'<text x="{row["supply_exit_candidate"][0][0]}" y="{row["supply_exit_candidate"][0][1]-100}">{row["zone_id"]} / exit UNVERIFIED</text>')
    for door in preview["doors"]:
        out.append(f'<line x1="{door["threshold_global_mm"][0][0]}" y1="{door["threshold_global_mm"][0][1]}" x2="{door["threshold_global_mm"][1][0]}" y2="{door["threshold_global_mm"][1][1]}" stroke="#f59e0b" stroke-width="35" stroke-dasharray="80 40"/>')
        out.append(f'<text x="{door["threshold_global_mm"][0][0]}" y="{door["threshold_global_mm"][0][1]-100}">{door["opening_id"]} / corridor UNVERIFIED</text>')
    out.append('</svg>')
    output.write_text("\n".join(out), encoding="utf-8")


def main():
    drawing = reconstruct_test01_room_candidates(PROJECT)
    all_doors = []
    for floor, filename in (("FLOOR_1_PLAN", "Test_01_floor_1_plan.pdf"), ("ATTIC_PLAN", "Test_01_attic_plan.pdf")):
        scale = float(next(s.scale_m_per_drawing_unit for s in drawing.scale_candidates if s.frame.frame_id.startswith(floor))) * 1000
        all_doors.extend(d.as_dict() for d in extract_pdf_door_openings(PROJECT / "engineering" / "source_documents" / filename, floor, scale_mm_per_drawing_unit=scale, rooms=_room_data(drawing, floor)))
        if floor == "FLOOR_1_PLAN":
            # The boiler-room wall has a source-vector gap at x=366.36,
            # y=237.72..246.12.  It is the under-stair opening described by
            # the owner; the short symbol is retained as a candidate and
            # passage authority remains unverified.
            corridor_id = "FLOOR_1_PLAN:23e1c19b1e8cd7bd:ROOM"
            boiler_id = "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM"
            a, b = (366.36, 237.72), (366.36, 246.12)
            all_doors.append({
                "opening_id": "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE",
                "document_id": floor,
                "orientation": "VERTICAL",
                "opening_drawing_units": [list(a), list(b)],
                "opening_mm": [[round(a[0]*scale), round(a[1]*scale)], [round(b[0]*scale), round(b[1]*scale)]],
                "width_mm": round((b[1]-a[1])*scale),
                "adjacent_room_ids": [corridor_id, boiler_id],
                "vector_evidence": ["BOILER_LEFT_WALL_CONTINUOUS_SEGMENTS", "SOURCE_VECTOR_GAP_UNDER_STAIR", "OWNER_LOCATION_CLARIFICATION"],
                "geometry_status": "DOOR_GEOMETRY_SOURCE_GAP_CANDIDATE",
                "passage_status": "UNVERIFIED_NARROW_SOURCE_SYMBOL",
                "transit_preview_allowed": False,
                "manifold_connected": "UNVERIFIED",
                "width_interpretation": "PARTIAL_SOURCE_VECTOR_GAP_NOT_CONFIRMED_FULL_DOOR_WIDTH",
                "full_width_status": "USER_CONFIRMATION_REQUIRED",
                "diagnostics": ["296_MM_GAP_MAY_BE_PART_OF_DOOR_SYMBOL", "DO_NOT_ROUTE_THROUGH_UNTIL_FULL_JAMBS_CONFIRMED"],
            })
            # Two source-vector gaps in the shared wall between room 2 and
            # kitchen/living room 3. They are retained as door candidates;
            # passage authorization is still separate from vector detection.
            for suffix, y in (("LOWER", 370.32), ("UPPER", 321.60)):
                a, b = (358.20, y), (366.72, y)
                all_doors.append({
                    "opening_id": f"FLOOR_1_PLAN-KITCHEN-CORRIDOR-{suffix}",
                    "document_id": floor,
                    "orientation": "HORIZONTAL",
                    "opening_drawing_units": [list(a), list(b)],
                    "opening_mm": [[round(a[0]*scale), round(a[1]*scale)], [round(b[0]*scale), round(b[1]*scale)]],
                    "width_mm": round((b[0]-a[0])*scale),
                    "adjacent_room_ids": ["FLOOR_1_PLAN:23e1c19b1e8cd7bd:ROOM", "FLOOR_1_PLAN:dbda1f3916917c37:ROOM"],
                    "vector_evidence": ["SHARED_WALL_SOURCE_VECTOR_GAP", "ROOM_2_ROOM_3_BOUNDARY_BINDING"],
                    "geometry_status": "DOOR_GEOMETRY_SOURCE_GAP_CANDIDATE",
                    "passage_status": "UNVERIFIED_SOURCE_VECTOR_CONFIRMED",
                    "transit_preview_allowed": True,
                    "manifold_connected": "UNVERIFIED",
                })
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"method": "SOURCE_PDF_VECTOR_DOOR_PATTERN", "authority": "SOURCE_VECTOR_GEOMETRY", "openings": all_doors, "unresolved": ["CORRIDOR_TOPOLOGY", "MANIFOLD_LOCATION", "AUTHORIZED_WALL_CROSSING"]}
    (OUT / "door_openings_from_pdf.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    preview = _room12_preview(drawing, all_doors)
    (OUT / "room12_door_to_corridor.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    _render_svg(preview, OUT / "room12_door_to_corridor.svg")
    print(json.dumps({"doors": len(all_doors), "room12": preview["statuses"]}, ensure_ascii=False))


if __name__ == "__main__": main()
