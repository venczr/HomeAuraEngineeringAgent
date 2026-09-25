"""Build the user-selected boiler opening and kitchen circuit previews.

This is an incremental Test_01 artifact builder.  It keeps the source PDF and
the old 296 mm source candidate in history, while routing through a separate
800 mm project opening selected on the boiler/corridor wall.
"""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from agent.ufh_bend_geometry import build_rounded_centerline
from agent.ufh_building_routing import _orthogonal_search, build_door_transition

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "projects" / "Test_01" / "exports" / "ufh_generator_package"
SOURCE = ROOT / "projects" / "Test_01" / "engineering" / "source_documents" / "Test_01_floor_1_plan.pdf"
SUMMARY = ROOT / "dev" / "ufh_real_plan" / "two_floor_summary.json"
SOURCE_DATA = PACKAGE / "08_PROJECT_SOURCE_DATA.json"
AUTO_KITCHEN_ZONES = PACKAGE / "11_KITCHEN_AUTO_ZONE_RESULT.json"

SCALE, OX, OY = 35.276963114841126, 0.354536853315949, -0.013838128109455283


def to_page(point: tuple[float, float]) -> tuple[float, float]:
    return ((point[0] - OX) / SCALE, (point[1] - OY) / SCALE)


def project_boiler_opening() -> dict[str, object]:
    # The wall faces are the existing source-derived room and corridor faces.
    # The 335 mm separation is retained; only the user-selected 800 mm interval
    # along that wall is proposed for a passage.  It sits above the six stair
    # contact zone (y=8932..10777) and remains inside both source polygons.
    opening = build_door_transition(
        "FLOOR_1_PLAN-BOILER-CORRIDOR-USER-PROPOSED-800MM",
        [[12947, 7400], [12947, 8200]],
        [[12612, 7400], [12612, 8200]],
        wall_thickness_mm=335,
        source_gap_mm=335,
        passage_status="UNVERIFIED_CONSTRUCTION_PROPOSAL",
        geometry_status="USER_SELECTED_PROPOSED_OPENING",
    )
    opening.update(
        {
            "document_id": "FLOOR_1_PLAN",
            "room_id": "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM",
            "corridor_id": "FLOOR_1_PLAN:23e1c19b1e8cd7bd:ROOM",
            "width_mm": 800.0,
            "width_basis": "USER_SELECTED_PROJECT_PARAMETER",
            "position_basis": "USER_SELECTED_ON_EXISTING_BOILER_CORRIDOR_WALL_UNDER_STAIR",
            "source_geometry_unchanged": True,
            "stair_contact_overlap": False,
            "construction_status": "REQUIRES_SEPARATE_CONSTRUCTION_CONFIRMATION",
            "active_for_preliminary_routing": True,
            "replaces_active_candidate": "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE",
        }
    )
    return opening


def load_auto_kitchen_routes() -> tuple[dict[str, object], list[dict[str, object]]]:
    """Load the current AUTO layout, not the superseded two-spiral snapshot.

    The former project-opening preview read the first two entries from
    ``08_PROJECT_SOURCE_DATA.json``.  Those entries are an earlier 80/87 m
    layout, whereas the AUTO generator already selected three independent
    63.088 m zones for this kitchen.  Routing the stale source made the
    building preview contradict the automatic-layout result and guaranteed a
    90 m limit violation before transit was even fully validated.

    AUTO routes are already expressed in the floor-global coordinate system.
    They must therefore be used as-is: reflecting them again would turn a
    verified zone into a different, unvalidated layout.
    """
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    auto = json.loads(AUTO_KITCHEN_ZONES.read_text(encoding="utf-8"))
    kitchen_summary = next(r for r in summary["rooms"] if "dbda1f3916917c37" in r.get("room_hypothesis_id", ""))
    if auto.get("room_id") != kitchen_summary["room_hypothesis_id"]:
        raise ValueError("AUTO_KITCHEN_ROUTE_ROOM_MISMATCH")
    routes: list[dict[str, object]] = []
    for index, zone in enumerate(auto.get("routes", []), start=1):
        global_points = [[round(float(x), 3), round(float(y), 3)] for x, y in zone["route_mm"]]
        if len(global_points) < 2 or float(zone.get("internal_length_mm", 0)) <= 0:
            raise ValueError(f"AUTO_KITCHEN_ROUTE_INVALID:{zone.get('route_id', index)}")
        routes.append(
            {
                "circuit_id": f"FLOOR_1_PLAN:dbda1f3916917c37:ROOM/{zone['route_id']}-project-opening",
                "room_id": kitchen_summary["room_hypothesis_id"],
                "floor": "FLOOR_1_PLAN",
                "room_boundary_mm": kitchen_summary["floor_global_boundary_mm"],
                "route_mm": global_points,
                "INTERNAL_PIPE_LENGTH": float(zone["internal_length_mm"]),
                "spiral_route_id": str(zone["route_id"]),
                "internal_geometry_source": "11_KITCHEN_AUTO_ZONE_RESULT.routes",
                "internal_bend_radius_mm": 80.0,
                "door_oriented_strategy": "AUTO_ZONE_LAYOUT_DOOR_TRANSIT_PENDING",
            }
        )
    if not routes:
        raise ValueError("AUTO_KITCHEN_LAYOUT_HAS_NO_ROUTES")
    return kitchen_summary, routes


def _pick_orthogonal(start, end, allowed, occupied=()):
    """Pick a short orthogonal leg and validate its centreline clearance."""
    candidates = [
        [tuple(start), (float(end[0]), float(start[1])), tuple(end)],
        [tuple(start), (float(start[0]), float(end[1])), tuple(end)],
        [tuple(start), tuple(end)],
    ]
    for points in candidates:
        line = LineString(points)
        if not allowed.covers(line):
            continue
        if any(line.distance(LineString(other)) < 16.0 for other in occupied):
            continue
        return points
    return None


def _project_route(circuit, kitchen_opening, boiler_opening, corridor_geom, boiler_geom, stair_geom, occupied, circuit_index):
    """Build one pair through explicit transitions, reserving only valid pairs."""
    route = circuit["route_mm"]
    room = Polygon(circuit["room_boundary_mm"])
    kitchen_room = [tuple(p) for p in kitchen_opening["room_side_segment_mm"]]
    kitchen_corridor = [tuple(p) for p in kitchen_opening["corridor_side_segment_mm"]]
    boiler_room = [tuple(p) for p in boiler_opening["room_side_segment_mm"]]
    boiler_corridor = [tuple(p) for p in boiler_opening["corridor_side_segment_mm"]]
    collector_terms = [(13150.0, 8000.0), (13300.0, 8200.0)]
    # Keep lane order monotonic between the kitchen threshold and boiler
    # threshold; reversing the two lanes would force a crossing in the
    # corridor's orthogonal dog-legs.
    lane_groups = [[11400.0, 11200.0], [11600.0, 11800.0]]
    lanes = lane_groups[min(circuit_index, len(lane_groups) - 1)]
    door_y_groups = [[13025.0, 13100.0], [12945.0, 13180.0]]
    door_ys = door_y_groups[min(circuit_index, len(door_y_groups) - 1)]
    pairs = []
    for role_index, endpoint_index in enumerate((0, 1)):
        endpoint = tuple(route[0] if role_index == 0 else route[-1])
        kitchen_target = (kitchen_room[0][0], door_ys[endpoint_index])
        leg_occupied = list(occupied)
        if role_index == 1 and pairs and pairs[0] is not None:
            leg_occupied.append(pairs[0]["path_mm"])
        room_path = _pick_orthogonal(endpoint, kitchen_target, room, leg_occupied)
        if room_path is None and leg_occupied:
            room_path = _orthogonal_search(endpoint, kitchen_target, room, leg_occupied, clearance_mm=16.0)
        if room_path is None:
            pairs.append(None); continue
        corridor_target = (kitchen_corridor[0][0], door_ys[endpoint_index])
        # The return uses the lower edge of the proposed 800 mm passage so its
        # corridor dog-leg passes below the supply lane instead of crossing it.
        boiler_y_groups = [[7800.0, 7400.0], [7600.0, 8200.0]]
        boiler_y = boiler_y_groups[min(circuit_index, len(boiler_y_groups) - 1)][role_index]
        boiler_corridor_target = (boiler_corridor[0][0], boiler_y)
        lane = lanes[role_index]
        corridor_path = [tuple(corridor_target), (lane, float(corridor_target[1])), (lane, boiler_y), boiler_corridor_target]
        corridor_line = LineString(corridor_path)
        if not corridor_geom.covers(corridor_line) or corridor_line.intersects(stair_geom):
            pairs.append(None); continue
        if any(corridor_line.distance(LineString(other)) < 16.0 for other in leg_occupied):
            pairs.append(None); continue
        boiler_corridor_point = tuple(boiler_corridor_target)
        boiler_room_point = (boiler_room[0][0], boiler_y)
        bridge = LineString([boiler_corridor_point, boiler_room_point])
        transition_geom = Polygon(boiler_opening["transition_polygon_mm"])
        if not transition_geom.buffer(16).covers(bridge):
            pairs.append(None); continue
        collector = collector_terms[role_index]
        boiler_path = _pick_orthogonal(boiler_room_point, collector, boiler_geom, leg_occupied)
        if boiler_path is None:
            pairs.append(None); continue
        full = room_path[:-1] + [list(kitchen_target), list(corridor_target)] + corridor_path[1:] + [list(boiler_room_point)] + boiler_path[1:]
        # Add the two finite transition bridges exactly once.
        full = room_path[:-1] + [list(kitchen_target), list(corridor_target)] + corridor_path[1:-1] + [list(boiler_corridor_point), list(boiler_room_point)] + boiler_path[1:]
        line = LineString(full)
        if line.intersects(stair_geom) or any(line.distance(LineString(other)) < 16.0 for other in leg_occupied):
            pairs.append(None); continue
        rounded = build_rounded_centerline(full, bend_radius_mm=80.0)
        pairs.append(
            {
                "path_mm": [list(p) for p in full],
                "length_mm": round(line.length, 3),
                "room_length_mm": round(LineString(room_path).length, 3),
                "corridor_length_mm": round(corridor_line.length, 3),
                "kitchen_transition_length_mm": round(LineString([kitchen_target, corridor_target]).length, 3),
                "boiler_transition_length_mm": round(bridge.length, 3),
                "boiler_room_length_mm": round(LineString(boiler_path).length, 3),
                "collector_terminal_mm": list(collector),
                "geometry_checks": {
                    "centerline_simple": bool(line.is_simple),
                    "pipe_outer_diameter_mm": 16.0,
                    "required_free_clearance_mm": 16.0,
                    "bend_radius_mm": 80.0,
                    "rounded_centerline_length_mm": round(rounded.length_mm, 3),
                    "bend_geometry_status": "VALID" if rounded.valid else "REQUIRES_ROUNDED_BEND_REVIEW",
                    "bend_diagnostics": list(rounded.diagnostics),
                    "stair_contact_zone_clear": not line.intersects(stair_geom),
                },
                "diagnostics": [] if rounded.valid and line.is_simple else ["BEND_GEOMETRY_REQUIRES_REVIEW"],
            }
        )
    if any(x is None for x in pairs):
        return None
    return {"SUPPLY": pairs[0], "RETURN": pairs[1]}


def build_project_routes(circuits, kitchen_opening, boiler_opening, corridor, boiler, stairs):
    corridor_geom = Polygon(corridor["useful_area_geometry_mm"]["outer_mm"])
    boiler_geom = Polygon(boiler["floor_global_boundary_mm"])
    stair_geom = Polygon(stairs)
    rows = []
    occupied = []
    for circuit in circuits:
        pair = _project_route(circuit, kitchen_opening, boiler_opening, corridor_geom, boiler_geom, stair_geom, occupied, len(rows))
        if pair is None:
            # Preserve the AUTO layout measurement even when building transit
            # is not yet solved.  Omitting it made an unconnected route look
            # indistinguishable from a missing/zero-length circuit.
            rows.append({
                "circuit_id": circuit["circuit_id"],
                "status": "UNVERIFIED",
                "MANIFOLD_CONNECTED": "UNVERIFIED",
                "INTERNAL_PIPE_LENGTH": circuit["INTERNAL_PIPE_LENGTH"],
                "TOTAL_CIRCUIT_LENGTH": None,
                "transit_layout_status": "UNRESOLVED_ENDPOINT_AND_LANE_ASSIGNMENT",
                "diagnostics": ["JOINT_SUPPLY_RETURN_NO_CLEAR_PAIR", "AUTO_LAYOUT_REQUIRES_DOOR_AWARE_ENDPOINT_ASSIGNMENT"],
            })
            continue
        occupied.extend([pair[role]["path_mm"] for role in ("SUPPLY", "RETURN")])
        s, r = pair["SUPPLY"], pair["RETURN"]
        total = circuit["INTERNAL_PIPE_LENGTH"] + s["room_length_mm"] + r["room_length_mm"] + s["corridor_length_mm"] + r["corridor_length_mm"] + s["kitchen_transition_length_mm"] + r["kitchen_transition_length_mm"] + s["boiler_transition_length_mm"] + r["boiler_transition_length_mm"] + s["boiler_room_length_mm"] + r["boiler_room_length_mm"]
        rows.append({"circuit_id": circuit["circuit_id"], "status": "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY", "MANIFOLD_CONNECTED": "UNVERIFIED", "INTERNAL_PIPE_LENGTH": circuit["INTERNAL_PIPE_LENGTH"], "IN_ROOM_SUPPLY_LENGTH": s["room_length_mm"], "IN_ROOM_RETURN_LENGTH": r["room_length_mm"], "IN_ROOM_CONNECTION_LENGTH": round(s["room_length_mm"] + r["room_length_mm"], 3), "CORRIDOR_SUPPLY_LENGTH": s["corridor_length_mm"], "CORRIDOR_RETURN_LENGTH": r["corridor_length_mm"], "DOOR_TRANSITION_SUPPLY_LENGTH": round(s["kitchen_transition_length_mm"] + s["boiler_transition_length_mm"], 3), "DOOR_TRANSITION_RETURN_LENGTH": round(r["kitchen_transition_length_mm"] + r["boiler_transition_length_mm"], 3), "BOILER_ROOM_SUPPLY_LENGTH": s["boiler_room_length_mm"], "BOILER_ROOM_RETURN_LENGTH": r["boiler_room_length_mm"], "VERTICAL_SUPPLY_LENGTH": 0.0, "VERTICAL_RETURN_LENGTH": 0.0, "TOTAL_CIRCUIT_LENGTH": round(total, 3), "exits": pair, "diagnostics": sorted(set(s["diagnostics"] + r["diagnostics"]))})
    return {"status": "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY", "manifold_options": [{"id": "SINGLE_MANIFOLD", "MANIFOLD_CONNECTED": "UNVERIFIED"}, {"id": "TWO_MANIFOLDS", "MANIFOLD_CONNECTED": "UNVERIFIED"}], "circuits": rows, "corridor_validation": {"status": "CHECKED_USING_SUPPLIED_CORRIDOR_POLYGON", "shared_route_collisions_checked": True, "occupied_route_clearance_mm": 16}}


def draw_pdf(result: dict[str, object], opening: dict[str, object], circuits: list[dict[str, object]], out_path: Path) -> None:
    doc = pymupdf.open(str(SOURCE))
    page = doc[0]
    colors = {"SUPPLY": (0.85, 0.08, 0.12), "RETURN": (0.08, 0.25, 0.85)}
    spiral_colors = [(0.02, 0.47, 0.28), (0.50, 0.34, 0.85), (0.85, 0.45, 0.05)]
    for index, circuit in enumerate(circuits):
        spiral_points = circuit.get("route_mm") or []
        if len(spiral_points) >= 2:
            page.draw_polyline([to_page(tuple(p)) for p in spiral_points], color=spiral_colors[index], width=0.8, overlay=True)
            # Keep annotations compact: the source plan contains handwritten
            # room labels, so a full generated circuit ID makes the preview
            # unreadable without adding useful installation information.
            label = f"AUTO Z{index + 1}: {circuit['INTERNAL_PIPE_LENGTH'] / 1000:.1f} m"
            label_point = (spiral_points[0][0] + 140.0, spiral_points[0][1] - 100.0)
            page.insert_text(to_page(label_point), label, fontsize=4.3, color=spiral_colors[index], overlay=True)
    rows = result["circuits"]
    for row in rows:
        for role, color in colors.items():
            points = (row.get("exits") or {}).get(role, {}).get("path_mm") or []
            if len(points) >= 2:
                page.draw_polyline([to_page(tuple(p)) for p in points], color=color, width=1.25, overlay=True)
    room_seg = [tuple(p) for p in opening["room_side_segment_mm"]]
    corr_seg = [tuple(p) for p in opening["corridor_side_segment_mm"]]
    poly = opening["transition_polygon_mm"]
    page.draw_polyline([to_page(p) for p in room_seg], color=(0.55, 0.0, 0.65), width=3.0, overlay=True)
    page.draw_polyline([to_page(p) for p in corr_seg], color=(0.55, 0.0, 0.65), width=3.0, overlay=True)
    page.draw_polyline([to_page(tuple(p)) for p in poly], color=(0.55, 0.0, 0.65), width=2.0, overlay=True)
    page.insert_text(to_page((12947, 7350)), "USER_SELECTED_PROPOSED_OPENING 800 mm / construction unverified", fontsize=6.2, color=(0.45, 0.0, 0.55), overlay=True)
    page.insert_text((18, 60), "PROJECT ROUTE PREVIEW — green/purple spirals; red supply / blue return; proposed boiler door 800 mm; construction and manifold unverified", fontsize=6.5, color=(0.55, 0.15, 0.05), overlay=True)
    temp = PACKAGE / "22_project_route_temp.pdf"
    doc.save(str(temp), garbage=4, deflate=True)
    doc.close()
    src = pymupdf.open(str(temp))
    out = pymupdf.open()
    out.insert_pdf(src)
    crop = pymupdf.Rect(335, 185, 430, 270)
    crop_page = out.new_page(width=crop.width * 4, height=crop.height * 4)
    crop_page.show_pdf_page(crop_page.rect, src, 0, clip=crop)
    crop_page.insert_text((12, 18), "Проектный проём котельной: 800 мм", fontsize=5.5, color=(0.45, 0.0, 0.55))
    out.save(str(out_path), garbage=4, deflate=True)
    out.close()
    src.close()
    temp.unlink(missing_ok=True)


def main() -> None:
    corridor = json.loads((PACKAGE / "18_COMMON_CORRIDOR_AREA.json").read_text(encoding="utf-8"))
    preview = json.loads((PACKAGE / "19_FIRST_FLOOR_TRANSIT_ROUTING_PREVIEW.json").read_text(encoding="utf-8"))
    summary, circuits = load_auto_kitchen_routes()
    boiler = next(r for r in json.loads(SUMMARY.read_text(encoding="utf-8"))["rooms"] if "2c35c0ccf04544b4" in r.get("room_hypothesis_id", ""))
    opening = project_boiler_opening()
    kitchen_opening = preview["door_transitions"]["kitchen_corridor"]
    result = build_project_routes(
        circuits,
        kitchen_opening,
        opening,
        corridor,
        boiler,
        corridor["stair_contact_zone_mm"],
    )
    for row in result["circuits"]:
        row["project_opening_id"] = opening["opening_id"]
        row["MANIFOLD_CONNECTED"] = "UNVERIFIED"
    total_rows = result["circuits"]
    result.update(
        {
            "status": "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY",
            "project_opening": opening,
            "inactive_source_candidate": {
                "opening_id": "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE",
                "source_gap_mm": 296,
                "status": "HISTORY_ONLY_INACTIVE_FOR_ROUTING",
                "reason": "USER_SELECTED_PROJECT_OPENING_REPLACES_296MM_SOURCE_FRAGMENT",
            },
            "chain": [
                "ROOM_3_KITCHEN",
                kitchen_opening["opening_id"],
                "ROOM_2_CORRIDOR",
                opening["opening_id"],
                "ROOM_4_BOILER",
                "COLLECTOR_PROJECT_ASSUMPTION",
            ],
            "project_parameters": {
                "boiler_opening_width_mm": 800,
                "collector_point_mm": [13100, 8000],
                "project_limit_mm": 90000,
                "pipe_outer_diameter_mm": 16,
                "clearance_mm": 16,
                "bend_radius_mm": 80,
            },
            "physical_checks": {
                "joint_supply_return_search": True,
                "occupied_corridor_routes_checked": True,
                "stairs_contact_zone_crossed": False,
                "manifold_connected": "UNVERIFIED",
                "construction_passage_authority": "UNVERIFIED",
                "bend_status": {str(r["circuit_id"]): {k: v.get("geometry_checks", {}).get("bend_geometry_status") for k, v in r.get("exits", {}).items()} for r in total_rows},
            },
            "kitchen_milestone_report": {
                "KITCHEN_CIRCUIT_COUNT": len(circuits),
                "ACCEPTED_CIRCUIT_COUNT": sum(r.get("status") == "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY" for r in total_rows),
                "SELECTED_KITCHEN_DOORWAY": kitchen_opening["opening_id"],
                "DOORWAY_PIPE_COUNT": 4,
                "DOORWAY_CAPACITY_STATUS": "CONFLICT_UNPROVEN_FOR_SECOND_CIRCUIT" if any(r.get("status") != "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY" for r in total_rows) else "PRELIMINARY_CAPACITY_CHECKED",
                "IN_ROOM_SUPPLY_LENGTH_PER_CIRCUIT": [r.get("IN_ROOM_SUPPLY_LENGTH") for r in total_rows],
                "IN_ROOM_RETURN_LENGTH_PER_CIRCUIT": [r.get("IN_ROOM_RETURN_LENGTH") for r in total_rows],
                "COVERAGE_LENGTH_PER_CIRCUIT": [r.get("INTERNAL_PIPE_LENGTH") for r in total_rows],
                "TOTAL_LENGTH_PER_CIRCUIT": [r.get("TOTAL_CIRCUIT_LENGTH") for r in total_rows],
                "ALL_CIRCUITS_CONTINUOUS": all(r.get("status") == "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY" for r in total_rows),
                "ALL_CIRCUITS_WITHIN_90M": all((r.get("TOTAL_CIRCUIT_LENGTH") is not None and r.get("TOTAL_CIRCUIT_LENGTH") <= 90000) for r in total_rows),
                "INTER_PIPE_CLEARANCE_VALID": all(r.get("status") == "PROJECT_GEOMETRY_PREVIEW_UNVERIFIED_AUTHORITY" for r in total_rows),
                "DOORWAY_PASSAGE_VALID": False,
                "UNRESOLVED_CONSTRUCTION_ASSUMPTIONS": ["USER_SELECTED_PROPOSED_OPENING_REQUIRES_CONSTRUCTION_CONFIRMATION", "MANIFOLD_LOCATION_UNVERIFIED", "90M_PREVIEW_LIMIT_EXCEEDED_FOR_ACCEPTED_CIRCUIT", "SECOND_KITCHEN_CIRCUIT_NEEDS_REPARTITION_OR_NEW_LANE_SEARCH"],
            },
        }
    )
    json_path = PACKAGE / "22_KITCHEN_PROJECT_OPENING_ROUTES.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    kitchen_json = {
        **result,
        "spirals": [
            {"circuit_id": c["circuit_id"], "spiral_route_id": c["spiral_route_id"], "orientation": c["door_oriented_strategy"], "coverage_length_mm": c["INTERNAL_PIPE_LENGTH"], "ordered_rounded_centerline_mm": c["route_mm"]}
            for c in circuits
        ],
        "complete_ordered_paths": [
            {
                "circuit_id": row["circuit_id"],
                "manifold_supply_port_mm": ((row.get("exits") or {}).get("SUPPLY") or {}).get("collector_terminal_mm"),
                "SUPPLY": ((row.get("exits") or {}).get("SUPPLY") or {}).get("path_mm"),
                "spiral": next((c["route_mm"] for c in circuits if c["circuit_id"] == row["circuit_id"]), None),
                "RETURN": ((row.get("exits") or {}).get("RETURN") or {}).get("path_mm"),
                "manifold_return_port_mm": ((row.get("exits") or {}).get("RETURN") or {}).get("collector_terminal_mm"),
                "total_length_mm": row.get("TOTAL_CIRCUIT_LENGTH"),
                "status": row.get("status"),
            }
            for row in total_rows
        ],
    }
    json_path.write_text(json.dumps(kitchen_json, ensure_ascii=False, indent=2), encoding="utf-8")
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="8500 5000 10500 12500">', '<rect x="8500" y="5000" width="10500" height="12500" fill="white" stroke="#777"/>', '<text x="8600" y="5200" font-size="120">KITCHEN CIRCUITS — DOOR ORIENTED — PROPOSED BOILER OPENING 800 mm</text>']
    # Show the complete oriented spiral centerlines in distinct colors.
    for index, circuit in enumerate(circuits):
        color = ("#067647", "#7f56d9", "#f79009")[index % 3]
        pts = circuit["route_mm"]
        svg.append(f'<polyline points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="none" stroke="{color}" stroke-width="12" opacity=".85"/>')
    for row in total_rows:
        for role, color in (("SUPPLY", "#d92d20"), ("RETURN", "#1570ef")):
            pts = (row.get("exits") or {}).get(role, {}).get("path_mm") or []
            if len(pts) >= 2:
                svg.append(f'<polyline points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="none" stroke="{color}" stroke-width="18"/>')
    pts = opening["transition_polygon_mm"]
    svg.append(f'<polygon points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="#9333ea" fill-opacity=".22" stroke="#9333ea" stroke-width="16"/>')
    svg.append('<text x="12600" y="7300" font-size="80" fill="#7e22ce">USER_SELECTED_PROPOSED_OPENING / 800 mm / UNVERIFIED CONSTRUCTION</text>')
    svg.append('<circle cx="13150" cy="8000" r="55" fill="#d92d20"/><circle cx="13300" cy="8200" r="55" fill="#1570ef"/>')
    svg.append('<text x="13210" y="7950" font-size="70">MANIFOLD S</text><text x="13350" y="8240" font-size="70">MANIFOLD R</text>')
    svg.append('</svg>')
    (PACKAGE / "22_KITCHEN_PROJECT_OPENING_ROUTES.svg").write_text("\n".join(svg), encoding="utf-8")
    draw_pdf(result, opening, circuits, PACKAGE / "22_KITCHEN_PROJECT_OPENING_ROUTES.pdf")

    connectivity_path = PACKAGE / "20_FIRST_FLOOR_GEOMETRY_CONNECTIVITY.json"
    connectivity = json.loads(connectivity_path.read_text(encoding="utf-8"))
    old = next((t for t in connectivity.get("transitions", []) if t.get("id") == "BOILER_TO_CORRIDOR"), None)
    connectivity["history"] = connectivity.get("history", []) + [{"opening_id": "FLOOR_1_PLAN-BOILER-UNDER-STAIR-CANDIDATE", "status": "INACTIVE_HISTORY_ONLY", "source_gap_mm": 296}]
    connectivity["transitions"] = [t for t in connectivity.get("transitions", []) if t.get("id") not in {"BOILER_TO_CORRIDOR", "BOILER_TO_CORRIDOR_PROJECT"}]
    connectivity["transitions"].append({"id": "BOILER_TO_CORRIDOR_PROJECT", "opening_id": opening["opening_id"], "room_id": opening["room_id"], "corridor_id": opening["corridor_id"], "status": "CONNECTED_CANDIDATE", "geometry_status": opening["geometry_status"], "passage_status": opening["passage_status"], "width_mm": opening["width_mm"], "wall_thickness_mm": opening["wall_thickness_mm"], "room_side_segment_mm": opening["room_side_segment_mm"], "corridor_side_segment_mm": opening["corridor_side_segment_mm"], "transition_polygon_mm": opening["transition_polygon_mm"], "stair_contact_overlap": False, "diagnostics": ["CONSTRUCTION_CONFIRMATION_REQUIRED"]})
    connectivity["chain"] = [{"from": "ROOM_3_KITCHEN", "via": kitchen_opening["opening_id"], "to": "ROOM_2_CORRIDOR", "status": "CONNECTED_CANDIDATE"}, {"from": "ROOM_2_CORRIDOR", "via": opening["opening_id"], "to": "ROOM_4_BOILER", "status": "CONNECTED_CANDIDATE"}, {"from": "ROOM_4_BOILER", "via": "COLLECTOR_PROJECT_ASSUMPTION", "to": "COLLECTOR", "status": "PROJECT_ASSUMPTION_UNVERIFIED"}]
    connectivity["status"] = "PROJECT_GEOMETRY_CONNECTED_CANDIDATE"
    connectivity["active_project_opening"] = opening
    connectivity["diagnostics"] = ["PROJECT_OPENING_USER_SELECTED", "CONSTRUCTION_CONFIRMATION_REQUIRED", "COLLECTOR_LOCATION_UNVERIFIED"]
    connectivity["project_route_artifact"] = "22_KITCHEN_PROJECT_OPENING_ROUTES.json"
    connectivity["parametric_test"] = {"artifact": "22_KITCHEN_PROJECT_OPENING_ROUTES.json", "status": result["status"], "active_boiler_opening": opening["opening_id"], "first_circuit_status": total_rows[0].get("status"), "first_circuit_total_mm": total_rows[0].get("TOTAL_CIRCUIT_LENGTH"), "second_circuit_status": total_rows[1].get("status") if len(total_rows) > 1 else "NOT_ATTEMPTED", "interpretation": "The 296 mm source candidate is retained only as history; active preliminary routing uses the user-selected 800 mm project opening."}
    connectivity_path.write_text(json.dumps(connectivity, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "opening": opening["opening_id"], "circuits": [{"id": r["circuit_id"], "status": r["status"], "total_mm": r.get("TOTAL_CIRCUIT_LENGTH")} for r in total_rows]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
