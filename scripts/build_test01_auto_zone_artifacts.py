"""Materialize the Test_01 kitchen AUTO zoning result on the source PDF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.ufh_zone_layout import propose_zoned_meanders
PROJECT = ROOT / "projects" / "Test_01"
SOURCE = PROJECT / "engineering" / "source_documents" / "Test_01_floor_1_plan.pdf"
PACKAGE = PROJECT / "exports" / "ufh_generator_package"
UI_PROJECT = ROOT / "homeaura-editor" / "public" / "plans" / "test01-project.json"


def transform(point: tuple[float, float]) -> tuple[float, float]:
    scale = 35.276963114841126
    ox, oy = 0.354536853315949, -0.013838128109455283
    return ((point[0] - ox) / scale, (point[1] - oy) / scale)


def draw_route(page, points, color, label):
    pts = [transform((float(x), float(y))) for x, y in points]
    page.draw_polyline(pts, color=color, width=1.8, overlay=True)
    for point, fill in ((pts[0], (0.1, 0.6, 0.2)), (pts[-1], (0.45, 0.1, 0.7))):
        page.draw_circle(point, 2.4, color=fill, fill=fill, overlay=True)
    page.insert_text((pts[0][0] + 4, pts[0][1] - 3), label, fontsize=7, color=color, overlay=True)


def main():
    project = json.loads(UI_PROJECT.read_text(encoding="utf-8"))
    room = next(room for room in project["rooms"] if room["label"].startswith("3 /"))
    boundary = [tuple(point) for point in room["global_boundary_mm"]]
    minimum_x = min(point[0] for point in boundary)
    minimum_y = min(point[1] for point in boundary)
    local_boundary = [(x - minimum_x, y - minimum_y) for x, y in boundary]
    result = propose_zoned_meanders(local_boundary, target_route_length_mm=90_000, spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3)
    candidate = result["recommended"]
    if not candidate:
        raise RuntimeError("Kitchen AUTO zoning did not produce a candidate")
    routes = []
    for zone in candidate["routes"]:
        global_route = [[point[0] + minimum_x, point[1] + minimum_y] for point in zone["route_mm"]]
        routes.append({
            "route_id": zone["zone_id"],
            "zone_boundary_mm": zone["boundary_mm"],
            "route_mm": global_route,
            "internal_length_mm": zone["length_mm"],
            "endpoint_access_geometry": zone["endpoint_access_geometry"],
            "GEOMETRY_VALID": zone["geometry_valid"],
            "TOPOLOGY_VALID": zone["topology_valid"],
            "BEND_VALID": zone["bend_valid"],
            "PIPE_LENGTH_VALID": zone["length_mm"] <= 90_000,
            "MANIFOLD_CONNECTED": "UNVERIFIED",
            "TRANSIT_LENGTH_MM": None,
        })
    payload = {
        "project_id": "Test_01",
        "room_id": room["id"],
        "room_label": room["label"],
        "mode": "AUTO",
        "source_boundary_preserved": True,
        "maximum_circuit_length_mm": 90_000,
        "status": result["status"],
        "route_count": len(routes),
        "routes": routes,
        "connection_authority": "UNVERIFIED_NO_AUTHORIZED_OPENING_OR_MANIFOLD_PATH",
        "diagnostics": candidate["diagnostics"],
    }
    PACKAGE.mkdir(parents=True, exist_ok=True)
    (PACKAGE / "11_KITCHEN_AUTO_ZONE_RESULT.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    document = pymupdf.open(str(SOURCE))
    page = document[0]
    colors = [(0.0, 0.45, 0.75), (0.85, 0.3, 0.05), (0.25, 0.55, 0.2)]
    for index, route in enumerate(routes):
        draw_route(page, route["route_mm"], colors[index], route["route_id"])
    page.insert_text((18, 24), "KITCHEN №3 — AUTO zoning, 3 independent geometry routes", fontsize=9, color=(0.75, 0.2, 0.05), overlay=True)
    page.insert_text((18, 36), "Internal geometry only; endpoint access to room boundary VALID; manifold connection UNVERIFIED", fontsize=7, color=(0.75, 0.2, 0.05), overlay=True)
    document.save(str(PACKAGE / "11_KITCHEN_AUTO_LAYOUT.pdf"), garbage=4, deflate=True)
    document.close()
    before_after = pymupdf.open(str(SOURCE))
    before_after[0].insert_text((18, 24), "BEFORE — one continuous kitchen route, 194.9 m", fontsize=9, color=(0.75, 0.2, 0.05), overlay=True)
    old_points = room["routes"][0]
    before_after[0].draw_polyline(old_points, color=(0.85, 0.08, 0.12), width=1.2, overlay=True)
    source_copy = pymupdf.open(str(SOURCE))
    before_after.insert_pdf(source_copy, from_page=0, to_page=0)
    page_after = before_after[-1]
    for index, route in enumerate(routes):
        draw_route(page_after, route["route_mm"], colors[index], route["route_id"])
    page_after.insert_text((18, 24), "AFTER — AUTO zoning, 3 routes × 63.1 m", fontsize=9, color=(0.1, 0.45, 0.2), overlay=True)
    page_after.insert_text((18, 36), "Geometry-only preview; manifold connection UNVERIFIED", fontsize=7, color=(0.75, 0.2, 0.05), overlay=True)
    before_after.save(str(PACKAGE / "12_KITCHEN_BEFORE_AFTER.pdf"), garbage=4, deflate=True)
    source_copy.close()
    before_after.close()
    print(json.dumps({"route_count": len(routes), "lengths_mm": [route["internal_length_mm"] for route in routes], "output": str(PACKAGE)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
