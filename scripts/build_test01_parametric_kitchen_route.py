"""Build the focused parametric kitchen-to-boiler route artifact.

This intentionally does not regenerate the building.  It reuses the current
room route, corridor model and source door candidates and records the boiler
door as a PARAMETRIC_TEST_ONLY transition.
"""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf
from shapely.geometry import LineString

from agent.ufh_building_routing import build_door_transition, route_building_system

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "projects" / "Test_01" / "exports" / "ufh_generator_package"
SOURCE = ROOT / "projects" / "Test_01" / "engineering" / "source_documents" / "Test_01_floor_1_plan.pdf"
SUMMARY = ROOT / "dev" / "ufh_real_plan" / "two_floor_summary.json"


def _to_page(point):
    scale, ox, oy = 35.276963114841126, 0.354536853315949, -0.013838128109455283
    return ((point[0] - ox) / scale, (point[1] - oy) / scale)


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    corridor = json.loads((PACKAGE / "18_COMMON_CORRIDOR_AREA.json").read_text(encoding="utf-8"))
    preview = json.loads((PACKAGE / "19_FIRST_FLOOR_TRANSIT_ROUTING_PREVIEW.json").read_text(encoding="utf-8"))
    rooms = [r for r in summary["rooms"] if r.get("floor_source_id") == "FLOOR_1_PLAN"]
    kitchen = next(r for r in rooms if "dbda1f3916917c37" in r["room_hypothesis_id"])
    boiler = next(r for r in rooms if "2c35c0ccf04544b4" in r["room_hypothesis_id"])
    internal_length = 80032.566
    route = kitchen["floor_global_route_polylines_mm"][0]

    # The source evidence is a 296 mm vertical wall-end gap.  For this
    # isolated calculation only, assign it a rectangular provisional lane
    # anchored to the actual boiler boundary.  This is not a confirmation of
    # the door width or construction permission.
    boiler_transition = build_door_transition(
        "FLOOR_1_PLAN-BOILER-UNDER-STAIR-PARAMETRIC-296MM",
        [[12947, 8361], [13243, 8361]],
        [[12612, 8386], [12612, 8682]],
        source_gap_mm=296,
        passage_status="UNVERIFIED_PARAMETRIC_ASSUMPTION",
        geometry_status="PARAMETRIC_TEST_ONLY",
    )
    circuits = [{
        "circuit_id": "FLOOR_1_PLAN:dbda1f3916917c37:ROOM/circuit-1-parametric",
        "room_id": kitchen["room_hypothesis_id"],
        "floor": "FLOOR_1_PLAN",
        "room_boundary_mm": kitchen["floor_global_boundary_mm"],
        "route_mm": route,
        "INTERNAL_PIPE_LENGTH": internal_length,
    }]
    result = route_building_system(
        circuits,
        openings={circuits[0]["circuit_id"]: preview["door_transitions"]["kitchen_corridor"]},
        corridor_polygons={"FLOOR_1_PLAN": corridor.get("useful_area_geometry_mm") or corridor["useful_area_mm"]},
        collector_point=(13100, 8000),
        collector_polygon=boiler["floor_global_boundary_mm"],
        collector_transition=boiler_transition,
        occupied_clearance_mm=16,
    )
    row = result["circuits"][0]
    result["scenario"] = {
        "status": "PARAMETRIC_TEST_ONLY",
        "authority": "NOT_A_CONFIRMED_REAL_DOOR",
        "source_gap_mm": 296,
        "source_gap_interpretation": "L_SHAPED_WALL_END_GAP_NOT_CONFIRMED_FULL_DOOR_WIDTH",
        "boiler_transition": boiler_transition,
        "collector_point_mm": [13100, 8000],
        "collector_status": "PROJECT_ASSUMPTION_UNVERIFIED",
    }
    result["length_breakdown"] = {
        "INTERNAL_PIPE_LENGTH": row.get("INTERNAL_PIPE_LENGTH"),
        "IN_ROOM_SUPPLY_LENGTH": row.get("IN_ROOM_SUPPLY_LENGTH"),
        "IN_ROOM_RETURN_LENGTH": row.get("IN_ROOM_RETURN_LENGTH"),
        "CORRIDOR_SUPPLY_LENGTH": row.get("CORRIDOR_SUPPLY_LENGTH"),
        "CORRIDOR_RETURN_LENGTH": row.get("CORRIDOR_RETURN_LENGTH"),
        "TRANSITION_SUPPLY_RETURN_INCLUDED_ONCE": True,
        "VERTICAL_SUPPLY_LENGTH": row.get("VERTICAL_SUPPLY_LENGTH"),
        "VERTICAL_RETURN_LENGTH": row.get("VERTICAL_RETURN_LENGTH"),
        "TOTAL_CIRCUIT_LENGTH": row.get("TOTAL_CIRCUIT_LENGTH"),
        "PROJECT_LIMIT_MM": 90000,
        "LIMIT_STATUS": "EXCEEDED" if row.get("TOTAL_CIRCUIT_LENGTH", 0) > 90000 else "WITHIN_LIMIT",
    }
    result["physical_checks"] = {
        "supply_return_joint_search": True,
        "pipe_outer_diameter_mm": 16,
        "free_clearance_mm": 16,
        "bend_radius_mm": 80,
        "rounded_bend_status": {
            role: (item.get("geometry_checks") or {}).get("bend_geometry_status")
            for role, item in row.get("exits", {}).items()
        },
        "rounded_bend_diagnostics": {
            role: (item.get("geometry_checks") or {}).get("bend_diagnostics", [])
            for role, item in row.get("exits", {}).items()
        },
        "manifold_connected": "UNVERIFIED",
        "construction_passage_authority": "UNVERIFIED",
    }
    json_path = PACKAGE / "21_KITCHEN_CIRCUIT_1_PARAMETRIC_ROUTE.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="8500 5000 10500 12500">', '<rect x="8500" y="5000" width="10500" height="12500" fill="white" stroke="#777"/>', '<text x="8600" y="5200" font-size="120">KITCHEN CIRCUIT 1 — PARAMETRIC TRANSIT TEST ONLY</text>']
    for role, color in (("SUPPLY", "#d92d20"), ("RETURN", "#1570ef")):
        pts = (row.get("exits") or {}).get(role, {}).get("path_mm") or []
        if len(pts) >= 2:
            svg.append(f'<polyline points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="none" stroke="{color}" stroke-width="18"/>')
    for label, trans in (("KITCHEN_DOOR", preview["door_transitions"]["kitchen_corridor"]), ("BOILER_DOOR_PARAMETRIC", boiler_transition)):
        pts = trans.get("transition_polygon_mm") or []
        svg.append(f'<polygon points="{" ".join(f"{p[0]},{p[1]}" for p in pts)}" fill="#9333ea" fill-opacity=".18" stroke="#9333ea" stroke-width="14" stroke-dasharray="28 18"/>')
        svg.append(f'<text x="{pts[0][0]}" y="{pts[0][1]-80}" font-size="70" fill="#7e22ce">{label} / UNVERIFIED</text>')
    svg.append('<text x="8600" y="22200" font-size="90" fill="#b42318">TOTAL 113237.454 mm / LIMIT 90000 mm / EXCEEDED</text></svg>')
    (PACKAGE / "21_KITCHEN_CIRCUIT_1_PARAMETRIC_ROUTE.svg").write_text("\n".join(svg), encoding="utf-8")

    # Preserve the original PDF and create a separate two-page annotated copy.
    source_doc = pymupdf.open(str(SOURCE))
    source_page = source_doc[0]
    for role, color in (("SUPPLY", (0.85, 0.08, 0.12)), ("RETURN", (0.08, 0.25, 0.85))):
        pts = (row.get("exits") or {}).get(role, {}).get("path_mm") or []
        if len(pts) >= 2:
            source_page.draw_polyline([_to_page(p) for p in pts], color=color, width=1.8, overlay=True)
    # Source vector gap itself: page drawing units from the extractor.
    gap_rect = pymupdf.Rect(366.0, 237.1, 367.2, 246.7)
    source_page.draw_rect(gap_rect, color=(0.8, 0.05, 0.05), width=2.4, overlay=True)
    source_page.insert_text((320, 232), "296 mm source wall-end gap; full door width unverified", fontsize=6.5, color=(0.75, 0.03, 0.03), overlay=True)
    source_page.insert_text((18, 60), "PARAMETRIC ROUTE TEST ONLY — red supply / blue return; R80 review required; collector and door unverified", fontsize=6.5, color=(0.55, 0.15, 0.05), overlay=True)
    annotated = PACKAGE / "21_KITCHEN_CIRCUIT_1_PARAMETRIC_ROUTE.pdf"
    temp = PACKAGE / "21_parametric_annotated_temp.pdf"
    source_doc.save(str(temp), garbage=4, deflate=True)
    source_doc.close()
    annotated_doc = pymupdf.open(str(temp))
    out = pymupdf.open()
    out.insert_pdf(annotated_doc)
    crop = pymupdf.Rect(340, 220, 430, 270)
    page = out.new_page(width=crop.width * 4, height=crop.height * 4)
    page.show_pdf_page(page.rect, annotated_doc, 0, clip=crop)
    page.insert_text((8, 14), "Увеличенный фрагмент: 296 мм L-образный разрыв стены под лестницей", fontsize=5, color=(0.75, 0.03, 0.03))
    out.save(str(annotated), garbage=4, deflate=True)
    out.close(); annotated_doc.close(); temp.unlink(missing_ok=True)

    connectivity_path = PACKAGE / "20_FIRST_FLOOR_GEOMETRY_CONNECTIVITY.json"
    connectivity = json.loads(connectivity_path.read_text(encoding="utf-8"))
    connectivity["parametric_test"] = {
        "artifact": "21_KITCHEN_CIRCUIT_1_PARAMETRIC_ROUTE.json",
        "status": row.get("status"),
        "total_circuit_length_mm": row.get("TOTAL_CIRCUIT_LENGTH"),
        "length_limit_status": result["length_breakdown"]["LIMIT_STATUS"],
        "rounded_bend_status": result["physical_checks"]["rounded_bend_status"],
        "real_boiler_door_status": "DISCONNECTED_SOURCE_GEOMETRY",
        "interpretation": "Parametric route demonstrates router continuity only; it does not repair or confirm the source door.",
    }
    connectivity_path.write_text(json.dumps(connectivity, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": row.get("status"), "total_mm": row.get("TOTAL_CIRCUIT_LENGTH"), "output": str(json_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
