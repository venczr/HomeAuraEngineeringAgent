"""Build user-facing Test_01 artifacts from the original PDF plans.

The package is deliberately a geometry preview. Internal routes come from the
current validated room geometry artifacts; transit and manifold alternatives
are represented as explicit proposals without drawing invented wall crossings.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pymupdf
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points
from agent.ufh_strategy_selector import select_layout
from agent.ufh_building_routing import route_building_system, build_door_transition
from agent.ufh_common_area import build_common_corridor_area

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "Test_01"
SOURCE = PROJECT / "engineering" / "source_documents"
SUMMARY = ROOT / "dev" / "ufh_real_plan" / "two_floor_summary.json"
SCHEDULE = ROOT / "dev" / "ufh_real_plan" / "circuit_schedule.json"
OUT = PROJECT / "exports" / "ufh_generator_package"
PUBLIC = ROOT / "homeaura-editor" / "public" / "plans"


def route_preview_status(selection: dict) -> str:
    """Classify a generated route without promoting a partial hybrid layout."""
    if not selection.get("routes"):
        return "UNRESOLVED"
    if (
        selection.get("strategy") == "HYBRID_SPIRAL_MEANDER"
        or selection.get("HYBRID_VALID") is False
        or selection.get("HYBRID_CONNECTION_VALID") is False
    ):
        return "PARTIAL_HYBRID_RESIDUAL_UNROUTED"
    return "ROUTED_VALID"


def clear_unrouted_room_metrics(room: dict) -> None:
    """Drop stale route and coverage claims when no current BODY was selected."""
    room["floor_global_route_polylines_mm"] = []
    room["candidate_lengths_mm"] = []
    room["route_validation"] = []
    room["coverage"] = {}


def floor_transform(floor: str):
    if floor == "FLOOR_1_PLAN":
        return 35.276963114841126, 0.354536853315949, -0.013838128109455283
    return 35.192264300635422, 0.4970194120433007, -0.36873403255594894


def to_page(point, floor):
    scale, ox, oy = floor_transform(floor)
    return ((point[0] - ox) / scale, (point[1] - oy) / scale)


def draw_routes(page, rooms, floor, *, variant_label=None):
    for room in rooms:
        routes = room.get("floor_global_route_polylines_mm") or []
        for route in routes:
            pts = [to_page(p, floor) for p in route]
            if len(pts) < 2:
                continue
            # Existing route geometry is a single ordered centerline. Split
            # colour at its midpoint for supply/return visual orientation;
            # neither colour adds a second physical line.
            mid = max(1, len(pts) // 2)
            page.draw_polyline(pts[: mid + 1], color=(0.85, 0.08, 0.12), width=1.2, overlay=True)
            page.draw_polyline(pts[mid:], color=(0.08, 0.25, 0.85), width=1.2, overlay=True)
        if room.get("routing_status") == "SKIPPED_GEOMETRY_UNRESOLVED":
            boundary = room.get("floor_global_boundary_mm") or []
            pts = [to_page(p, floor) for p in boundary]
            if len(pts) > 2:
                page.draw_polyline(pts, color=(0.95, 0.45, 0.05), width=2.0, dashes="[6 4]", overlay=True)
    if variant_label:
        page.insert_text((18, 24), variant_label, fontsize=9, color=(0.75, 0.2, 0.05), overlay=True)
        page.insert_text((18, 36), "GEOMETRY PREVIEW — transit/manifold connection UNVERIFIED", fontsize=7, color=(0.75, 0.2, 0.05), overlay=True)


def render_pdf(source_path, target_path, rooms, floor, label=None):
    document = pymupdf.open(str(source_path))
    draw_routes(document[0], rooms, floor, variant_label=label)
    document.save(str(target_path), garbage=4, deflate=True)
    document.close()


def draw_corridor_geometry_overlay(target_path, corridor_area, door_inventory):
    """Annotate the generated copy of the first-floor PDF with source-boundary evidence."""
    document = pymupdf.open(str(target_path))
    page = document[0]
    def page_points(points):
        return [to_page(p, "FLOOR_1_PLAN") for p in points]
    recovered = corridor_area.get("recovered_source_zones_mm") or []
    for zone in recovered:
        pts = page_points(zone)
        if len(pts) > 2:
            page.draw_polyline(pts, color=(0.95, 0.55, 0.05), width=2.0, dashes="[6 4]", overlay=True)
    contact = page_points(corridor_area.get("stair_contact_zone_mm") or [])
    if len(contact) > 2:
        page.draw_polyline(contact, color=(0.85, 0.05, 0.05), width=2.5, overlay=True)
    useful = page_points(corridor_area.get("useful_area_mm") or [])
    if len(useful) > 2:
            page.draw_polyline(useful, color=(0.10, 0.55, 0.25), width=1.5, dashes="[3 3]", overlay=True)
    for region in corridor_area.get("unresolved_area_regions_mm") or []:
        pts = page_points(region)
        if len(pts) > 2:
            page.draw_polyline(pts, color=(0.45, 0.45, 0.45), width=1.5, dashes="[2 4]", overlay=True)
    for door in door_inventory:
        if door.get("opening_id") != "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE":
            continue
        pts = page_points(door.get("opening_mm") or [])
        if len(pts) == 2:
            page.draw_line(pts[0], pts[1], color=(0.65, 0.15, 0.75), width=3.0, overlay=True)
            page.insert_text((pts[0][0] + 4, pts[0][1] - 4), "Котельная: проём под лестницей / UNVERIFIED", fontsize=6, color=(0.45, 0.05, 0.55), overlay=True)
    page.insert_text((18, 48), "Коридор: 6 ступеней исключены; остальная зона под лестницей оставлена полезной. Проходы UNVERIFIED.", fontsize=7, color=(0.75, 0.25, 0.05), overlay=True)
    document.save(str(target_path) + ".tmp.pdf", garbage=4, deflate=True)
    document.close()
    Path(str(target_path) + ".tmp.pdf").replace(target_path)


def build_first_floor_routing_preview(rooms, corridor_area, door_inventory):
    """Build a fail-closed first-floor transit preview from source door candidates.

    Only the boiler under-stair candidate and the source-bound opening to room 5
    are bound here. Other room openings remain explicit unresolved items until
    the PDF room binding is confirmed; no wall crossing is invented.
    """
    floor_rooms = [r for r in rooms if r.get("floor_source_id") == "FLOOR_1_PLAN"]
    boiler = next((d for d in door_inventory if d.get("opening_id") == "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE"), None)
    kitchen_door = next((d for d in door_inventory if d.get("opening_id") == "FLOOR_1_PLAN-KITCHEN-CORRIDOR-LOWER"), None)
    opening_by_room = {
        "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM": boiler,
        # DOOR-005 is drawn on the left wall of the kitchen/living room; the
        # extractor's legacy room binding to the small bathroom is retained in
        # the inventory but is not used for this routing preview.
        "FLOOR_1_PLAN:dbda1f3916917c37:ROOM": kitchen_door,
    }
    corridor_geometry = corridor_area.get("useful_area_geometry_mm") or corridor_area.get("useful_area_mm") or []
    corridor_boundary = corridor_area.get("useful_area_mm") or []

    def transition_for(room, door):
        """Convert a source gap into a finite candidate passage area.

        The extractor's horizontal kitchen gaps span the wall thickness; their
        length is retained as source width evidence and used to form a narrow
        candidate lane.  The boiler candidate is kept at its observed 296 mm
        interval and remains unverified if either face misses its room polygon.
        """
        if not door:
            return None
        source = door.get("opening_mm") or []
        if len(source) != 2:
            return None
        rb = Polygon(room.get("floor_global_boundary_mm") or [])
        cb = Polygon(corridor_boundary)
        if not rb.is_valid or not cb.is_valid:
            return None
        p0, p1 = source
        if abs(float(p0[0]) - float(p1[0])) <= abs(float(p0[1]) - float(p1[1])):
            # Vertical source interval: preserve its full observed span and
            # place the two faces on the nearest room/corridor x bounds.
            y0, y1 = sorted((float(p0[1]), float(p1[1])))
            cx = (float(p0[0]) + float(p1[0])) / 2
            room_x = rb.bounds[0] if abs(cx - rb.bounds[0]) < abs(cx - rb.bounds[2]) else rb.bounds[2]
            corr_x = cb.bounds[2] if abs(cx - cb.bounds[2]) < abs(cx - cb.bounds[0]) else cb.bounds[0]
            room_side = [[room_x, y0], [room_x, y1]]
            corr_side = [[corr_x, y0], [corr_x, y1]]
        else:
            # Horizontal source gap across a left/right wall: its length is
            # source width evidence, so create parallel vertical faces around
            # the measured midpoint rather than treating the gap as a point.
            x0, x1 = sorted((float(p0[0]), float(p1[0])))
            y = (float(p0[1]) + float(p1[1])) / 2
            half = (x1 - x0) / 2
            centre_y = y
            room_x = rb.bounds[0] if x1 <= rb.bounds[0] + 500 else rb.bounds[2]
            corr_x = cb.bounds[2] if x0 >= cb.bounds[2] - 500 else cb.bounds[0]
            room_side = [[room_x, centre_y - half], [room_x, centre_y + half]]
            corr_side = [[corr_x, centre_y - half], [corr_x, centre_y + half]]
        return build_door_transition(
            door.get("opening_id", "UNKNOWN_OPENING"), room_side, corr_side,
            source_gap_mm=LineString(source).length,
            passage_status=door.get("passage_status", "UNVERIFIED"),
            geometry_status="SOURCE_CANDIDATE_TRANSITION",
        )

    room_by_id = {r["room_hypothesis_id"]: r for r in floor_rooms}
    kitchen_room = room_by_id.get("FLOOR_1_PLAN:dbda1f3916917c37:ROOM")
    boiler_room = room_by_id.get("FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM")
    kitchen_transition = transition_for(kitchen_room, kitchen_door) if kitchen_room else None
    boiler_transition = transition_for(boiler_room, boiler) if boiler_room else None
    circuits = []
    openings = {}
    for room in floor_rooms:
        for index, route in enumerate(room.get("floor_global_route_polylines_mm") or [], start=1):
            cid = f"{room['room_hypothesis_id']}/circuit-{index}"
            validation = (room.get("route_validation") or [])[index - 1] if len(room.get("route_validation") or []) >= index else {}
            if not validation.get("INTERNAL_PIPE_LENGTH") and not validation.get("length_mm"):
                validation = dict(validation)
                validation["INTERNAL_PIPE_LENGTH"] = round(LineString(route).length, 3)
            opening = opening_by_room.get(room["room_hypothesis_id"])
            if opening:
                transition = kitchen_transition if opening.get("opening_id", "").startswith("FLOOR_1_PLAN-KITCHEN-CORRIDOR") else boiler_transition
                openings[cid] = transition or {"segment_mm": opening.get("opening_mm") or [], "opening_id": opening.get("opening_id"), "passage_status": opening.get("passage_status")}
            circuits.append({"circuit_id": cid, "room_id": room["room_hypothesis_id"], "floor": "FLOOR_1_PLAN", "room_boundary_mm": room.get("floor_global_boundary_mm") or [], "route_mm": route, "INTERNAL_PIPE_LENGTH": validation.get("INTERNAL_PIPE_LENGTH", validation.get("length_mm", 0))})
    # Project placement assumption: collector manifold is inside boiler room
    # 4 near its inner/lower-left corner. This point is a proposal only; the
    # room/collector wall crossing remains unverified.
    preview = route_building_system(
        circuits,
        openings=openings,
        corridor_polygons={"FLOOR_1_PLAN": corridor_area.get("useful_area_geometry_mm") or corridor_area.get("useful_area_mm") or []},
        collector_point=(13100.0, 8000.0),
        collector_polygon=boiler_room.get("floor_global_boundary_mm") if boiler_room else None,
        collector_transition=boiler_transition,
    )
    preview["corridor_area"] = {"useful_area_mm2": corridor_area.get("useful_heatable_area_mm2"), "stair_contact_zone_mm": corridor_area.get("stair_contact_zone_mm"), "reconstructed_area_mm2": corridor_area.get("reconstructed_corridor_area_mm2")}
    preview["collector_scenario"] = {"id": "SINGLE_MANIFOLD_BOILER_ROOM_4", "collector_point_mm": [13100, 8000], "collector_polygon_mm": boiler_room.get("floor_global_boundary_mm") if boiler_room else [], "status": "PROJECT_ASSUMPTION_UNVERIFIED", "manifold_connected": "UNVERIFIED", "transition": boiler_transition}
    preview["door_transitions"] = {"kitchen_corridor": kitchen_transition, "boiler_corridor": boiler_transition}
    preview["opening_bindings"] = [{"room_id": rid, "opening_id": (door or {}).get("opening_id"), "status": "SOURCE_CANDIDATE_ROOM_BINDING_REVIEW" if door else "OPENING_NOT_SELECTED"} for rid, door in opening_by_room.items()]
    # Persist an explicit topology audit before any route search is treated as
    # connected.  Distances are measured against the supplied source polygons;
    # no tolerance is used to silently enlarge a wall or a door.
    connectivity = {"status": "PRELIMINARY", "nodes": [], "transitions": [], "chain": []}
    room_polygons = {rid: Polygon(r.get("floor_global_boundary_mm") or []) for rid, r in room_by_id.items()}
    corridor_geom = Polygon(corridor_geometry.get("outer_mm"), corridor_geometry.get("holes_mm", [])) if isinstance(corridor_geometry, dict) else Polygon(corridor_geometry)
    def audit_transition(label, transition, room_id):
        if not transition:
            return {"id": label, "status": "UNVERIFIED", "diagnostics": ["TRANSITION_NOT_AVAILABLE"]}
        room_poly = room_polygons.get(room_id, Polygon())
        rs = [Point(p) for p in transition.get("room_side_segment_mm", [])]
        cs = [Point(p) for p in transition.get("corridor_side_segment_mm", [])]
        room_dist = round(max((room_poly.distance(p) for p in rs), default=float("inf")), 3)
        corridor_dist = round(max((corridor_geom.distance(p) for p in cs), default=float("inf")), 3)
        room_gap_points = []
        for p in rs:
            a, b = nearest_points(p, room_poly.boundary) if not room_poly.is_empty else (p, p)
            room_gap_points.append({"transition_mm": [round(p.x, 3), round(p.y, 3)], "room_boundary_mm": [round(b.x, 3), round(b.y, 3)], "distance_mm": round(a.distance(b), 3)})
        corridor_gap_points = []
        for p in cs:
            a, b = nearest_points(p, corridor_geom.boundary) if not corridor_geom.is_empty else (p, p)
            corridor_gap_points.append({"transition_mm": [round(p.x, 3), round(p.y, 3)], "corridor_boundary_mm": [round(b.x, 3), round(b.y, 3)], "distance_mm": round(a.distance(b), 3)})
        status = "CONNECTED_CANDIDATE" if room_dist <= 1.0 and corridor_dist <= 1.0 else "DISCONNECTED_SOURCE_GEOMETRY"
        diagnostics = [] if status == "CONNECTED_CANDIDATE" else ["ROOM_SIDE_NOT_ON_ROOM_BOUNDARY" if room_dist > 1.0 else "", "CORRIDOR_SIDE_NOT_ON_CORRIDOR_BOUNDARY" if corridor_dist > 1.0 else ""]
        transition_width = round(LineString([transition["room_side_segment_mm"][0], transition["corridor_side_segment_mm"][0]]).length, 3)
        return {"id": label, "opening_id": transition.get("opening_id"), "room_id": room_id, "room_side_distance_mm": room_dist, "corridor_side_distance_mm": corridor_dist, "transition_width_mm": transition_width, "source_gap_mm": transition.get("source_gap_mm"), "room_gap_points": room_gap_points, "corridor_gap_points": corridor_gap_points, "status": status, "diagnostics": [d for d in diagnostics if d]}
    kitchen_audit = audit_transition("KITCHEN_TO_CORRIDOR", kitchen_transition, "FLOOR_1_PLAN:dbda1f3916917c37:ROOM")
    boiler_audit = audit_transition("BOILER_TO_CORRIDOR", boiler_transition, "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM")
    connectivity["transitions"] = [kitchen_audit, boiler_audit]
    connectivity["nodes"] = [{"id": "ROOM_3_KITCHEN", "polygon_status": "SOURCE_POLYGON"}, {"id": "ROOM_2_CORRIDOR", "polygon_status": "USEFUL_AREA_WITH_STAIR_CONTACT_EXCLUSION"}, {"id": "ROOM_4_BOILER", "polygon_status": "SOURCE_POLYGON"}, {"id": "COLLECTOR", "status": "PROJECT_ASSUMPTION_UNVERIFIED"}]
    connectivity["chain"] = [{"from": "ROOM_3_KITCHEN", "via": "KITCHEN_TO_CORRIDOR", "to": "ROOM_2_CORRIDOR", "status": kitchen_audit["status"]}, {"from": "ROOM_2_CORRIDOR", "via": "BOILER_TO_CORRIDOR", "to": "ROOM_4_BOILER", "status": boiler_audit["status"]}]
    connectivity["status"] = "CONNECTED_CANDIDATE" if all(item["status"] == "CONNECTED_CANDIDATE" for item in (kitchen_audit, boiler_audit)) else "DISCONNECTED_SOURCE_GEOMETRY"
    connectivity["diagnostics"] = ["BOILER_SOURCE_CANDIDATE_ROOM_FACE_GAP_REQUIRES_REVIEW"] if connectivity["status"] != "CONNECTED_CANDIDATE" else []
    preview["geometry_connectivity_status"] = connectivity["status"]
    preview["geometry_connectivity_diagnostics"] = connectivity["diagnostics"]
    (OUT / "20_FIRST_FLOOR_GEOMETRY_CONNECTIVITY.json").write_text(json.dumps(connectivity, ensure_ascii=False, indent=2), encoding="utf-8")
    corridor_selection = select_layout(corridor_area.get("useful_area_mm") or [], mode="AUTO", maximum_circuit_length_mm=90_000, spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3) if corridor_area.get("useful_area_mm") else {"routes": [], "strategy": "UNRESOLVED", "rejected_candidates": ["USEFUL_CORRIDOR_POLYGON_EMPTY"]}
    preview["corridor_heating_layout"] = {
        "strategy": corridor_selection.get("strategy", "UNRESOLVED"),
        "routes": corridor_selection.get("routes", []),
        "coverage": {k: corridor_selection.get(k) for k in ("SPIRAL_COVERAGE_AREA", "MEANDER_COVERAGE_AREA", "UNCOVERED_HEATABLE_AREA", "COVERAGE_AREA_SEMANTICS", "PIPE_BAND_COVERAGE_AREA", "PIPE_BAND_UNCOVERED_AREA", "PIPE_BAND_COVERAGE_PERCENT", "PIPE_COVERAGE_METHOD") if k in corridor_selection},
        "rejected_candidates": corridor_selection.get("rejected_candidates", corridor_selection.get("diagnostics", [])),
        "status": "GEOMETRIC_PREVIEW" if corridor_selection.get("routes") else "UNRESOLVED_GEOMETRY",
        "search_basis": "SOURCE_USEFUL_CORRIDOR_POLYGON",
        "tested_candidate_summary": [
            {"orientation": "HORIZONTAL_AND_VERTICAL", "status": "REJECTED_BY_EXISTING_GENERATOR_GATES", "reasons": corridor_selection.get("rejected_candidates", [])},
            {"orientation": "COMPLEX_POLYGON", "status": "REQUIRES_ZONE_DECOMPOSITION", "reason": "NO_ROUTE_ACCEPTED_WITHOUT_INVENTING_A_RECTANGULAR_CORRIDOR"},
        ],
    }
    return preview


def write_routing_preview_svg(path, preview):
    rows = preview.get("circuits", [])
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="8500 5000 6500 12000">', '<rect x="8500" y="5000" width="6500" height="12000" fill="white" stroke="#888"/>', '<text x="8600" y="5200" font-size="120">FLOOR 1 TRANSIT PREVIEW — UNVERIFIED</text>']
    for row in rows:
        for role, color in (("SUPPLY", "#d92d20"), ("RETURN", "#1570ef")):
            item = (row.get("exits") or {}).get(role)
            pts = (item or {}).get("path_mm") or []
            if len(pts) >= 2:
                out.append(f'<polyline points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="none" stroke="{color}" stroke-width="18"/>')
        out.append(f'<text x="8600" y="{5300 + 180*len(out)}" font-size="70">{row.get("circuit_id")} / {row.get("status")}</text>')
    for name, transition in (preview.get("door_transitions") or {}).items():
        pts = (transition or {}).get("transition_polygon_mm") or []
        if len(pts) >= 3:
            out.append(f'<polygon points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="#9333ea" fill-opacity="0.18" stroke="#9333ea" stroke-width="14" stroke-dasharray="28 18"/>')
            out.append(f'<text x="{pts[0][0]}" y="{pts[0][1]}" font-size="65" fill="#7e22ce">{name} / SOURCE CANDIDATE</text>')
    collector = (preview.get("collector_scenario") or {}).get("collector_polygon_mm") or []
    if len(collector) >= 3:
        out.append(f'<polygon points="{" ".join(f"{p[0]},{p[1]}" for p in collector)}" fill="#f59e0b" fill-opacity="0.15" stroke="#f59e0b" stroke-width="14" stroke-dasharray="24 16"/>')
        out.append('<text x="12900" y="7900" font-size="70" fill="#b45309">PROJECT COLLECTOR / UNVERIFIED</text>')
    out.append('</svg>')
    path.write_text("\n".join(out), encoding="utf-8")


def draw_transit_routes_overlay(target_path, preview):
    """Draw the same preliminary transit model over the copied source PDF."""
    document = pymupdf.open(str(target_path))
    page = document[0]
    for row in preview.get("circuits", []):
        for role, color in (("SUPPLY", (0.85, 0.08, 0.12)), ("RETURN", (0.08, 0.25, 0.85))):
            pts = ((row.get("exits") or {}).get(role) or {}).get("path_mm") or []
            if len(pts) >= 2:
                page.draw_polyline([to_page(p, "FLOOR_1_PLAN") for p in pts], color=color, width=1.8, overlay=True)
    for transition in (preview.get("door_transitions") or {}).values():
        pts = (transition or {}).get("transition_polygon_mm") or []
        if len(pts) >= 3:
            page.draw_polyline([to_page(p, "FLOOR_1_PLAN") for p in pts], color=(0.58, 0.20, 0.75), width=2.4, dashes="[5 3]", overlay=True)
    collector = (preview.get("collector_scenario") or {}).get("collector_polygon_mm") or []
    if len(collector) >= 3:
        page.draw_polyline([to_page(p, "FLOOR_1_PLAN") for p in collector], color=(0.95, 0.55, 0.05), width=2.4, dashes="[5 3]", overlay=True)
    page.insert_text((18, 60), "TRANSIT PREVIEW: red supply / blue return; purple doors; orange collector — authority UNVERIFIED", fontsize=6.5, color=(0.55, 0.15, 0.05), overlay=True)
    temporary = str(target_path) + ".transit.tmp.pdf"
    document.save(temporary, garbage=4, deflate=True)
    document.close()
    Path(temporary).replace(target_path)


def write_corridor_geometry_svg(path, corridor_area, door_inventory):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="9000 5800 5000 11500">', '<rect x="9000" y="5800" width="5000" height="11500" fill="white" stroke="#777"/>', '<text x="9100" y="6000" font-size="120">ROOM 2 CORRIDOR GEOMETRY — SOURCE PDF PREVIEW</text>']
    def poly(points, stroke, fill="none", dash=None):
        if len(points) < 3: return
        attrs = f'fill="{fill}" fill-opacity="0.15" stroke="{stroke}" stroke-width="24"'
        if dash: attrs += f' stroke-dasharray="{dash}"'
        out.append(f'<polygon points="{" ".join(f"{p[0]},{p[1]}" for p in points)}" {attrs}/>')
    poly(corridor_area.get("source_boundary_mm") or [], "#16a34a")
    poly(corridor_area.get("useful_area_mm") or [], "#22c55e", "#22c55e")
    poly(corridor_area.get("stair_contact_zone_mm") or [], "#dc2626", "#dc2626")
    for region in corridor_area.get("unresolved_area_regions_mm") or []: poly(region, "#6b7280", "#9ca3af", "20 20")
    for door in door_inventory:
        if door.get("opening_id") == "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE":
            p = door.get("opening_mm") or []
            if len(p)==2: out.append(f'<line x1="{p[0][0]}" y1="{p[0][1]}" x2="{p[1][0]}" y2="{p[1][1]}" stroke="#9333ea" stroke-width="40"/><text x="{p[0][0]+80}" y="{p[0][1]-80}" font-size="80">BOILER DOOR CANDIDATE 296 mm / FULL WIDTH UNVERIFIED</text>')
    out += ['<text x="9100" y="16500" font-size="80" fill="#dc2626">RED: six stair treads excluded</text>', '<text x="9100" y="16650" font-size="80" fill="#22c55e">GREEN: useful floor area</text>', '<text x="9100" y="16800" font-size="80" fill="#6b7280">GRAY: unresolved source-area gap</text>', '<text x="9100" y="16950" font-size="80" fill="#9333ea">PURPLE: boiler-door source candidate</text>', '</svg>']
    path.write_text("\n".join(out), encoding="utf-8")


def main():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    rooms = summary["rooms"]
    # Re-select the emitted geometry from the real source boundaries.  The
    # legacy summary is retained for provenance, but it must not force every
    # room back to its old dense meander route.
    effective = {}
    for room in rooms:
        boundary = room.get("floor_global_boundary_mm") or []
        if not boundary:
            clear_unrouted_room_metrics(room)
            room["routing_status"] = "SKIPPED_GEOMETRY_UNRESOLVED"
            continue
        selection = select_layout(boundary, mode="AUTO", maximum_circuit_length_mm=90_000, spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3)
        if selection["routes"]:
            if room.get("geometry_status") != "GEOMETRY_UNRESOLVED":
                room["routing_status"] = route_preview_status(selection)
            room["floor_global_route_polylines_mm"] = [route["route_mm"] for route in selection["routes"]]
            room["candidate_lengths_mm"] = [round(route["length_mm"]) for route in selection["routes"]]
            room["routing_strategy"] = selection["strategy"]
            room["selected_strategy"] = selection["strategy"]
            room["strategy_selection_reason"] = selection.get("strategy_reason", "")
            room["strategy_diagnostics"] = selection.get("rejected_candidates", [])
            room["route_validation"] = [
                {key: route.get(key) for key in ("route_id", "length_mm", "INTERNAL_PIPE_LENGTH", "IN_ROOM_CONNECTION_LENGTH", "BUILDING_TRANSIT_LENGTH", "TOTAL_CIRCUIT_LENGTH", "LENGTH_RESERVE", "GEOMETRY_VALID", "TOPOLOGY_VALID", "BEND_VALID", "PIPE_LENGTH_VALID", "ENDPOINT_ACCESS_VALID", "MANIFOLD_CONNECTED", "rounded_geometry", "endpoint_access")}
                for route in selection["routes"]
            ]
            room["coverage"] = {key: selection.get(key) for key in ("SPIRAL_COVERAGE_AREA", "MEANDER_COVERAGE_AREA", "UNCOVERED_HEATABLE_AREA", "HYBRID_CONNECTION_VALID", "HYBRID_VALID", "COVERAGE_AREA_SEMANTICS", "PIPE_BAND_COVERAGE_AREA", "PIPE_BAND_UNCOVERED_AREA", "PIPE_BAND_COVERAGE_PERCENT", "PIPE_COVERAGE_METHOD") if key in selection}
        else:
            # Do not retain a legacy dense sweep when the current selector
            # cannot prove a physically valid candidate.  Preserve the room
            # boundary and diagnostics, but fail closed for route geometry.
            clear_unrouted_room_metrics(room)
            room["routing_strategy"] = selection.get("strategy", "UNRESOLVED")
            room["selected_strategy"] = selection.get("strategy", "UNRESOLVED")
            room["strategy_selection_reason"] = selection.get("strategy_reason", "all requested strategies failed independent gates")
            room["strategy_diagnostics"] = selection.get("rejected_candidates", selection.get("diagnostics", []))
            room["routing_status"] = "SKIPPED_GEOMETRY_UNRESOLVED" if room.get("geometry_status") == "GEOMETRY_UNRESOLVED" else "UNRESOLVED_STRATEGY"
        effective[room["room_hypothesis_id"]] = selection
    by_floor = {"FLOOR_1_PLAN": [r for r in rooms if r["floor_source_id"] == "FLOOR_1_PLAN"], "ATTIC_PLAN": [r for r in rooms if r["floor_source_id"] == "ATTIC_PLAN"]}
    for floor, filename, artifact in (("FLOOR_1_PLAN", "Test_01_floor_1_plan.pdf", "01_FIRST_FLOOR_LAYOUT.pdf"), ("ATTIC_PLAN", "Test_01_attic_plan.pdf", "02_MANSARD_LAYOUT.pdf")):
        render_pdf(SOURCE / filename, OUT / artifact, by_floor[floor], floor)
        document = pymupdf.open(str(SOURCE / filename)); pix = document[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False); pix.save(str(PUBLIC / filename.replace(".pdf", ".png"))); document.close()
    render_pdf(SOURCE / "Test_01_floor_1_plan.pdf", OUT / "03_SINGLE_MANIFOLD_OPTION.pdf", by_floor["FLOOR_1_PLAN"], "FLOOR_1_PLAN", "OPTION A — single manifold in boiler room; transit UNVERIFIED")
    render_pdf(SOURCE / "Test_01_attic_plan.pdf", OUT / "03_SINGLE_MANIFOLD_OPTION_attic.pdf", by_floor["ATTIC_PLAN"], "ATTIC_PLAN", "OPTION A — attic circuits to first-floor manifold; riser/transit UNVERIFIED")
    render_pdf(SOURCE / "Test_01_floor_1_plan.pdf", OUT / "04_TWO_MANIFOLDS_OPTION.pdf", by_floor["FLOOR_1_PLAN"], "FLOOR_1_PLAN", "OPTION B — first-floor manifold; upper manifold proposal separate")
    render_pdf(SOURCE / "Test_01_attic_plan.pdf", OUT / "04_TWO_MANIFOLDS_OPTION_attic.pdf", by_floor["ATTIC_PLAN"], "ATTIC_PLAN", "OPTION B — attic manifold proposal; exact position UNVERIFIED")
    # UI-friendly, page-coordinate project data.
    ui_rooms = []
    door_inventory = []
    door_inventory_path = ROOT / "dev" / "ufh_real_plan" / "door_openings_from_pdf.json"
    if door_inventory_path.exists():
        door_inventory = json.loads(door_inventory_path.read_text(encoding="utf-8")).get("openings", [])
    for room in rooms:
        page_routes = [[list(to_page(p, room["floor_source_id"])) for p in route] for route in room.get("floor_global_route_polylines_mm", [])]
        page_boundary = [list(to_page(p, room["floor_source_id"])) for p in room.get("floor_global_boundary_mm", [])]
        room_note = "SOURCE_PLAN_OPENING_UNBOUND: проём под лестницей, ближе к наружной стене; требуется привязка отрезка" if room["room_hypothesis_id"].startswith("FLOOR_1_PLAN:2c35c0ccf04544b4") else ""
        ui_rooms.append({"id": room["room_hypothesis_id"], "floor": room["floor_source_id"], "label": room["label"], "status": room["routing_status"], "geometry_status": room["geometry_status"], "routes": page_routes, "route_ids": [item.get("route_id") for item in room.get("route_validation", [])], "strategy": room.get("routing_strategy", "UNRESOLVED"), "strategy_reason": room.get("strategy_selection_reason", ""), "route_validation": room.get("route_validation", []), "coverage": room.get("coverage", {}), "boundary": page_boundary, "global_boundary_mm": room.get("floor_global_boundary_mm") or [], "lengths_mm": list(room.get("candidate_lengths_mm") or []), "door_note": room_note, "diagnostics": list(room.get("geometry_diagnostics") or []) + list(room.get("strategy_diagnostics") or [])})
    ui = {"project_id": "Test_01", "source_plans": {"FLOOR_1_PLAN": "/plans/Test_01_floor_1_plan.png", "ATTIC_PLAN": "/plans/Test_01_attic_plan.png"}, "page_size": [595, 842], "units": "mm_global_routes_with_page_overlay", "transforms": {"FLOOR_1_PLAN": {"scale_mm_per_drawing_unit": 35.276963114841126, "origin_mm": [0.354536853315949, -0.013838128109455283]}, "ATTIC_PLAN": {"scale_mm_per_drawing_unit": 35.192264300635422, "origin_mm": [0.4970194120433007, -0.36873403255594894]}}, "defaults": {"spacing_mm": 200, "wall_offset_mm": 100, "pipe": "16x2 mm", "bend_radius_mm": 80, "maximum_circuit_length_mm": 90000}, "rooms": ui_rooms, "door_openings": door_inventory, "door_authority": "SOURCE_PDF_CANDIDATES_WITH_ROOM_BINDING_REVIEW_REQUIRED", "common_areas": [{"id": "FLOOR_1_CORRIDOR_ROOM_2", "room_id": "FLOOR_1_PLAN:23e1c19b1e8cd7bd:ROOM", "stair_contact_policy": "SIX_STAIR_TREADS_EXCLUDED", "remaining_area_policy": "USEFUL_HEATABLE_AREA", "transit_status": "UNVERIFIED"}], "manifold_options": [{"id": "SINGLE_MANIFOLD", "label": "Один в котельной", "status": "UNVERIFIED"}, {"id": "TWO_MANIFOLDS", "label": "По коллектору на этаж", "status": "UNVERIFIED"}], "authority": "GEOMETRY_ONLY_PREVIEW_NOT_FOR_CONSTRUCTION"}
    (PUBLIC / "test01-project.json").write_text(json.dumps(ui, ensure_ascii=False, indent=2), encoding="utf-8")
    source_data = {"project_id": "Test_01", "source_pdfs": [str(SOURCE / "Test_01_floor_1_plan.pdf"), str(SOURCE / "Test_01_attic_plan.pdf")], "parameters": ui["defaults"], "rooms": ui_rooms, "provenance": "two_floor_summary.json + original PDFs"}
    (OUT / "08_PROJECT_SOURCE_DATA.json").write_text(json.dumps(source_data, ensure_ascii=False, indent=2), encoding="utf-8")
    transit_circuits = []
    for room in rooms:
        for index, route in enumerate(room.get("floor_global_route_polylines_mm", []), start=1):
            validation = (room.get("route_validation") or [])[index - 1] if len(room.get("route_validation") or []) >= index else {}
            transit_circuits.append({"circuit_id": f"{room['room_hypothesis_id']}/circuit-{index}", "room_id": room["room_hypothesis_id"], "floor": room["floor_source_id"], "room_boundary_mm": room.get("floor_global_boundary_mm") or [], "route_mm": route, "INTERNAL_PIPE_LENGTH": validation.get("INTERNAL_PIPE_LENGTH", validation.get("length_mm", 0))})
    transit_preview = route_building_system(transit_circuits)
    transit_preview["source"] = "current_room_routes; explicit door/corridor geometry required"
    transit_preview["options"] = {"SINGLE_MANIFOLD": {"status": "UNVERIFIED", "collector_location": "BOILER_ROOM_SOURCE_POSITION_UNVERIFIED"}, "TWO_MANIFOLDS": {"status": "UNVERIFIED", "collector_location": "EACH_FLOOR_POSITION_UNVERIFIED"}}
    (OUT / "15_BUILDING_TRANSIT_PREVIEW.json").write_text(json.dumps(transit_preview, ensure_ascii=False, indent=2), encoding="utf-8")
    corridor_room = next((r for r in rooms if r["room_hypothesis_id"].startswith("FLOOR_1_PLAN:23e1c19b1e8cd7bd")), None)
    if corridor_room:
        # The PDF vector stair flight is an observed part of room 2.  The
        # owner clarification is now six floor-contact treads; the remainder
        # of the drawn under-stair footprint stays useful floor.  The contact
        # polygon is deliberately kept separate from the recovered stair
        # footprint so the editor can show both areas and their authority.
        stair_footprint = [[11059, 6509], [12612, 6509], [12612, 10777], [11324, 10759], [11324, 8872], [11059, 8855]]
        stair_contact = [[11976, 8932], [12612, 8932], [12612, 10777], [11976, 10759]]
        corridor_area = build_common_corridor_area(
            corridor_room.get("floor_global_boundary_mm") or [],
            stair_contact_zone_mm=stair_contact,
            additional_useful_zones_mm=[stair_footprint],
            stair_contact_label="SIX_STAIR_TREADS_CONTACT_FLOOR_USER_CLARIFIED",
        )
        corridor_area["declared_architectural_area_mm2"] = 30_700_000
        corridor_area["observed_source_boundary_area_mm2"] = corridor_area.get("source_boundary_area_mm2", 0.0)
        corridor_area["declared_area_gap_mm2"] = round(float(corridor_area["declared_architectural_area_mm2"] - corridor_area.get("reconstructed_corridor_area_mm2", corridor_area["useful_heatable_area_mm2"])), 3)
        corridor_area["area_diagnostics"] = [
            "ARCHITECTURAL_LABEL_30_7_M2_RETAINED",
            "OBSERVED_ROOM_BOUNDARY_19_2_M2_RECONSTRUCTED_FROM_SOURCE_VECTOR",
            "STAIR_FOOTPRINT_RECOVERED_FROM_SOURCE_VECTOR_WITH_USER_SIX_TREAD_CLARIFICATION",
            "DECLARED_AREA_REMAINDER_REQUIRES_SOURCE_BOUNDARY_REVIEW",
        ]
        source_poly = Polygon(corridor_room.get("floor_global_boundary_mm") or [])
        envelope = box(*source_poly.bounds)
        unresolved = envelope.difference(Polygon(corridor_area.get("reconstructed_corridor_boundary_mm") or []))
        corridor_area["unresolved_area_regions_mm"] = [
            [[int(round(x)), int(round(y))] for x, y in geom.exterior.coords]
            for geom in getattr(unresolved, "geoms", [unresolved])
            if getattr(geom, "geom_type", "") == "Polygon" and geom.area > 1000
        ]
        corridor_area["unresolved_area_analysis"] = [
            {"region_index": index + 1, "area_mm2": round(float(Polygon(region).area), 3), "reason": (
                "ADJACENT_ROOM_OR_STAIR_SOURCE_FACE_NOT_BOUND_TO_ROOM_2" if min(p[0] for p in region) < 11000 and min(p[1] for p in region) < 9000 else
                "WALL_OR_DOOR_RECESS_SOURCE_GAP" if Polygon(region).area < 100000 else
                "SOURCE_BOUNDARY_RECONSTRUCTION_REQUIRED"
            ), "heating_authorized": False}
            for index, region in enumerate(corridor_area["unresolved_area_regions_mm"])
        ]
        corridor_area["unresolved_area_regions_status"] = "UNVERIFIED_ENVELOPE_DIFFERENCE_NOT_AUTHORIZED_FOR_HEATING"
        corridor_area["room_id"] = corridor_room["room_hypothesis_id"]
        corridor_area["floor"] = corridor_room["floor_source_id"]
        (OUT / "18_COMMON_CORRIDOR_AREA.json").write_text(json.dumps(corridor_area, ensure_ascii=False, indent=2), encoding="utf-8")
        draw_corridor_geometry_overlay(OUT / "01_FIRST_FLOOR_LAYOUT.pdf", corridor_area, door_inventory)
        write_corridor_geometry_svg(OUT / "18_COMMON_CORRIDOR_AREA.svg", corridor_area, door_inventory)
        routing_preview = build_first_floor_routing_preview(rooms, corridor_area, door_inventory)
        (OUT / "19_FIRST_FLOOR_TRANSIT_ROUTING_PREVIEW.json").write_text(json.dumps(routing_preview, ensure_ascii=False, indent=2), encoding="utf-8")
        write_routing_preview_svg(OUT / "19_FIRST_FLOOR_TRANSIT_ROUTING_PREVIEW.svg", routing_preview)
        draw_transit_routes_overlay(OUT / "01_FIRST_FLOOR_LAYOUT.pdf", routing_preview)
        ui["common_areas"][0].update({
            "geometry_artifact": "18_COMMON_CORRIDOR_AREA.json",
            "transit_preview_artifact": "19_FIRST_FLOOR_TRANSIT_ROUTING_PREVIEW.json",
            "stair_contact_zone_mm": corridor_area.get("stair_contact_zone_mm"),
            "useful_heatable_area_mm2": corridor_area.get("useful_heatable_area_mm2"),
            "reconstructed_corridor_area_mm2": corridor_area.get("reconstructed_corridor_area_mm2"),
            "declared_area_gap_mm2": corridor_area.get("declared_area_gap_mm2"),
            "stair_contact_geometry_status": corridor_area.get("stair_contact_geometry_status"),
            "connectivity_artifact": "20_FIRST_FLOOR_GEOMETRY_CONNECTIVITY.json",
            "connectivity_status": routing_preview.get("geometry_connectivity_status"),
            "door_transition_model": routing_preview.get("door_transitions"),
        })
        (PUBLIC / "test01-project.json").write_text(json.dumps(ui, ensure_ascii=False, indent=2), encoding="utf-8")
    door_inventory = ROOT / "dev" / "ufh_real_plan" / "door_openings_from_pdf.json"
    room12_transit = ROOT / "dev" / "ufh_real_plan" / "room12_door_to_corridor.json"
    if door_inventory.exists(): shutil.copy2(door_inventory, OUT / "16_DOOR_OPENINGS_FROM_PDF.json")
    if room12_transit.exists(): shutil.copy2(room12_transit, OUT / "17_ROOM12_DOOR_TRANSIT_PREVIEW.json")
    fields = ["CIRCUIT_ID", "ROOM", "FLOOR", "STRATEGY", "COVERAGE_LENGTH", "TRANSIT_LENGTH", "VERTICAL_LENGTH", "TOTAL_LENGTH", "POLICY_LIMIT", "VALIDATION_STATUS", "AUTHORITY_STATUS"]
    schedule_rows = []
    for room in rooms:
        selection = effective.get(room["room_hypothesis_id"], {})
        for index, route in enumerate(selection.get("routes", []), start=1):
            schedule_rows.append({
                "CIRCUIT_ID": f"{room['room_hypothesis_id']}/circuit-{index}",
                "ROOM": room["label"],
                "FLOOR": room["floor_source_id"],
                "STRATEGY": selection.get("strategy", "UNRESOLVED"),
                "COVERAGE_LENGTH": round(float(route.get("INTERNAL_PIPE_LENGTH", route.get("length_mm", 0))) / 1000, 3),
                "TRANSIT_LENGTH": "UNVERIFIED" if route.get("BUILDING_TRANSIT_LENGTH") is None else round(float(route["BUILDING_TRANSIT_LENGTH"]) / 1000, 3),
                "VERTICAL_LENGTH": "UNVERIFIED",
                "TOTAL_LENGTH": "UNVERIFIED" if route.get("TOTAL_CIRCUIT_LENGTH") is None else round(float(route["TOTAL_CIRCUIT_LENGTH"]) / 1000, 3),
                "POLICY_LIMIT": 90.0,
                "VALIDATION_STATUS": "GEOMETRY_VALID" if route.get("GEOMETRY_VALID") else "UNVERIFIED",
                "AUTHORITY_STATUS": "MANIFOLD_CONNECTED=UNVERIFIED",
            })
    with (OUT / "05_CIRCUIT_SCHEDULE.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows({k: row.get(k, "") for k in fields} for row in schedule_rows)
    validation = {"project_id": "Test_01", "authority": "GEOMETRY_ONLY_PREVIEW_NOT_FOR_CONSTRUCTION", "geometry_valid_routes": sum(bool(route.get("GEOMETRY_VALID")) for selection in effective.values() for route in selection.get("routes", [])), "independent_routes": len(schedule_rows), "rooms_total": len(rooms), "statuses": {"GEOMETRY_VALID": "VALID for measured route candidates; UNVERIFIED for unresolved rooms", "TOPOLOGY_VALID": "VALID for measured route candidates", "BEND_VALID": "VALID for measured route candidates", "CIRCUIT_SPLIT_VALID": "VALID for accepted independent spiral zones; remaining candidates retain rejection diagnostics", "PIPE_LENGTH_VALID": "VALID for internal route length only", "ENDPOINT_ACCESS_VALID": "VALID to room boundary only", "MANIFOLD_CONNECTED": "UNVERIFIED", "HYDRAULIC_VALID": "UNVERIFIED", "VISUALIZATION_VALID": "VALID against generated overlay geometry"}, "rooms": [{"id": r["room_hypothesis_id"], "label": r["label"], "route_status": r["routing_status"], "strategy": r.get("routing_strategy", "UNRESOLVED"), "lengths_mm": r.get("candidate_lengths_mm", []), "diagnostics": r.get("geometry_diagnostics", []) + r.get("strategy_diagnostics", [])} for r in rooms]}
    (OUT / "07_GENERATION_VALIDATION.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "06_UNRESOLVED_ENGINEERING_ITEMS.md").write_text("""# Нерешённые инженерные вопросы\n\n- Дверные проёмы извлечены из PDF, но разрешённые пути через стены и коридоры не подтверждены.\n- `MANIFOLD_CONNECTED` остаётся `UNVERIFIED` для всех контуров.\n- Десять длинных маршрутов требуют независимого зонирования с подтверждёнными конечными точками; произвольное разрезание не используется.\n- Помещение 9 и лестничная зона помещения 2 имеют неподтверждённую геометрию.\n- Гидравлика, расход, балансировка, теплоизоляция транзита и характеристики конкретной трубы не подтверждены.\n- Варианты одного и двух коллекторов являются проектными предложениями.\n""", encoding="utf-8")
    (OUT / "09_USER_GUIDE.md").write_text("""# HomeAura Test_01\n\nЗапустите `homeaura-editor\\Start-HomeAuraEditor.ps1`. В верхней панели выберите `Дом Test_01`, затем этаж и помещение. Кнопка «Рассчитать выбранное помещение» применяет текущие параметры шага и лимита длины к сохранённой геометрии. Красный цвет обозначает подачу, синий — обратку. Статусы подключения к коллекторам остаются `UNVERIFIED`, пока не подтверждены реальные транзитные пути.\n\nЭкспорт PDF и CSV находится в каталоге этого пакета. Результат является geometry-only preview и не заменяет монтажную документацию.\n""", encoding="utf-8")
    (OUT / "03_SINGLE_MANIFOLD_OPTION.md").write_text("Вариант А: один коллектор в котельной. Внутренние маршруты показаны на PDF; межкомнатный и межэтажный транзит не подтверждён.\n", encoding="utf-8")
    (OUT / "04_TWO_MANIFOLDS_OPTION.md").write_text("Вариант Б: отдельный коллектор на каждом этаже. Положение верхнего коллектора и общие магистрали остаются проектным предложением.\n", encoding="utf-8")
    print(json.dumps({"rooms": len(rooms), "routed": sum(r["routing_status"] == "ROUTED_VALID" for r in rooms), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

