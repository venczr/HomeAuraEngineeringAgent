"""Review existing zone candidates without regenerating building routes."""
from __future__ import annotations

import json
import zipfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_endpoint_access import review_zone_route_endpoints

REVIEW = ROOT / "dev/ufh_real_plan/zone_decomposition_review.json"
OUT = ROOT / "dev/ufh_real_plan"


def _path(points):
    return " ".join(("M" if i == 0 else "L") + f" {x:.3f},{y:.3f}" for i, (x, y) in enumerate(points))


def enrich_review(payload: dict) -> dict:
    geometry_valid = 0
    geometry_invalid = 0
    for room in payload.get("long_route_rooms", []):
        decomposition = room.get("zone_decomposition") or {}
        for candidate in decomposition.get("candidates", []):
            routes = candidate.get("routes", [])
            for route in routes:
                review = review_zone_route_endpoints(
                    route.get("route_mm", []),
                    route.get("boundary_mm", []),
                    other_routes=[other.get("route_mm", []) for other in routes if other is not route],
                )
                route["endpoint_access_geometry"] = review
                route["rounded_exit_geometry"] = validate_rounded_centerline(
                    route.get("route_mm", []), route.get("boundary_mm", []), bend_radius_mm=80, pipe_outer_radius_mm=8
                ).as_dict()
            endpoint_states = [r.get("endpoint_access_geometry", {}).get("endpoint_access_state") for r in routes]
            candidate["endpoint_access_geometry"] = "VALID" if routes and all(s == "VALID" for s in endpoint_states) else "INVALID"
            candidate["opening_authority"] = "UNVERIFIED_NO_AUTHORIZED_OPENING"
            candidate["manifold_connected"] = "UNVERIFIED"
            if candidate["endpoint_access_geometry"] == "VALID":
                geometry_valid += 1
            else:
                geometry_invalid += 1
    payload["endpoint_access_review"] = {
        "method": "STRAIGHT_IN_ROOM_EXIT_TO_NEAREST_BOUNDARY",
        "pipe_outer_radius_mm": 8,
        "clearance_mm": 8,
        "geometric_candidates_with_boundary_exit": geometry_valid,
        "candidates_with_geometric_exit_blocker": geometry_invalid,
        "opening_authority": "UNVERIFIED_NO_AUTHORIZED_OPENING",
        "manifold_connected": "UNVERIFIED",
        "interpretation": "VALID means each endpoint reaches its own room boundary without crossing occupied routes; it does not authorize a wall crossing or collector connection.",
    }
    return payload


def build_room12_svg(payload: dict, target: Path) -> None:
    room = next((r for r in payload.get("long_route_rooms", []) if r.get("label", "").startswith("12 /")), None)
    if not room:
        return
    candidate = next((c for c in room["zone_decomposition"].get("candidates", []) if c.get("zone_count") == 2), None)
    if not candidate:
        return
    all_points = [p for z in candidate["routes"] for p in z["boundary_mm"] + z["route_mm"]]
    minx = min(p[0] for p in all_points) - 300
    miny = min(p[1] for p in all_points) - 300
    maxx = max(p[0] for p in all_points) + 300
    maxy = max(p[1] for p in all_points) + 300
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {maxx-minx} {maxy-miny}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="20" y="40" font-size="28">Room 12 — two geometric zones, endpoint access review</text>']
    colors = ("#7a3db8", "#0f766e")
    for index, zone in enumerate(candidate["routes"], 1):
        b = zone["boundary_mm"]
        svg.append(f'<path data-layer="zone-boundary" d="{_path(b)}" fill="none" stroke="#64748b" stroke-width="8"/>')
        rounded = zone["rounded_exit_geometry"].get("rounded_points", [])
        svg.append(f'<path data-layer="rounded-centerline" data-zone-id="{zone["zone_id"]}" d="{_path(rounded)}" fill="none" stroke="{colors[index-1]}" stroke-width="12"/>')
        access = zone["endpoint_access_geometry"]["endpoints"]
        for endpoint in access:
            ex, ey = endpoint["endpoint"]
            bx, by = endpoint["boundary_point"]
            svg.append(f'<line data-layer="geometric-exit" x1="{ex}" y1="{ey}" x2="{bx}" y2="{by}" stroke="#f59e0b" stroke-width="10" stroke-dasharray="20 12"/>')
            svg.append(f'<circle cx="{ex}" cy="{ey}" r="22" fill="#d92d20"/><circle cx="{bx}" cy="{by}" r="18" fill="#1570ef"/>')
        svg.append(f'<text x="{b[0][0]}" y="{b[0][1]-40}" font-size="24">{zone["zone_id"]} {zone["endpoint_access_geometry"]} / opening UNVERIFIED</text>')
    svg.append('</svg>')
    target.write_text("".join(svg), encoding="utf-8")


def main() -> None:
    payload = enrich_review(json.loads(REVIEW.read_text(encoding="utf-8")))
    enriched = OUT / "zone_endpoint_access_review.json"
    enriched.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    build_room12_svg(payload, OUT / "room12_zone_endpoint_access.svg")
    # Keep the original review untouched for before/after comparison.
    handoff = OUT.parent / "ufh_handoff" / "HomeAura_UFH_latest_review.zip"
    temp = handoff.with_suffix(".tmp.zip")
    with zipfile.ZipFile(handoff, "r") as src, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info.filename))
        dst.write(enriched, "zone_endpoint_access_review.json")
        dst.write(OUT / "room12_zone_endpoint_access.svg", "room12_zone_endpoint_access.svg")
    temp.replace(handoff)
    print(json.dumps(payload["endpoint_access_review"], ensure_ascii=False))


if __name__ == "__main__":
    main()
