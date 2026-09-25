"""Generate an auditable result table for the independent UFH control cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.ufh_layout_engine import build_bifilar_spiral, build_meander, build_polygon_meander, validate_bifilar_topology
from agent.ufh_physical_validation import compare_rendered_route, validate_physical_route


def rectangle(width: int, height: int):
    return [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]


def result(name: str, route, boundary, *, requested_spiral=False, obstacles=()):
    physical = validate_physical_route(route, boundary, obstacles=obstacles, spacing_mm=200, minimum_bend_radius_mm=80)
    topology = None
    if requested_spiral and route:
        bounds = (min(x for x, _ in boundary), min(y for _, y in boundary), max(x for x, _ in boundary), max(y for _, y in boundary))
        topology = validate_bifilar_topology(route, bounds, boundary, spacing_mm=200, minimum_bend_radius_mm=80).as_dict()
    rendered = compare_rendered_route(route, route)
    return {
        "scenario": name,
        "status": "PASS" if physical.valid and (topology is None or topology["valid"]) else "REJECTED",
        "physical": physical.as_dict(),
        "topology": topology,
        "visualization": rendered,
    }


def main() -> None:
    obstacle = [(2800, 1000), (3200, 1000), (3200, 3000), (2800, 3000), (2800, 1000)]
    left = [(0, 0), (2800, 0), (2800, 4000), (0, 4000), (0, 0)]
    right = [(3200, 0), (6000, 0), (6000, 4000), (3200, 4000), (3200, 0)]
    first_room = rectangle(3000, 3000)
    second_room = [(3000, 0), (6000, 0), (6000, 3000), (3000, 3000), (3000, 0)]
    scenarios = [
        result("A_RECTANGLE_TRUE_SPIRAL", build_bifilar_spiral((0, 0, 3200, 3000), 200, 200), rectangle(3200, 3000), requested_spiral=True),
        result("B_RECTANGLE_CONTINUOUS_MEANDER", build_meander((0, 0, 7000, 4000), 200, 100), rectangle(7000, 4000)),
        result("C_L_SHAPE_CONTINUOUS_MEANDER", build_polygon_meander([(0, 0), (4000, 0), (4000, 2000), (2000, 2000), (2000, 4000), (0, 4000), (0, 0)]), [(0, 0), (4000, 0), (4000, 2000), (2000, 2000), (2000, 4000), (0, 4000), (0, 0)]),
        result("D_INTERNAL_OBSTACLE_LEFT_ZONE", build_meander((0, 0, 2800, 4000), 200, 100), left, obstacles=(obstacle,)),
        result("D_INTERNAL_OBSTACLE_RIGHT_ZONE", build_meander((3200, 0, 6000, 4000), 200, 100), right, obstacles=(obstacle,)),
        result("E_ADJACENT_ROOM_A_SEPARATE_CONTOUR", build_meander((0, 0, 3000, 3000), 200, 100), first_room),
        result("E_ADJACENT_ROOM_B_SEPARATE_CONTOUR", build_meander((3000, 0, 6000, 3000), 200, 100), second_room),
        result("F_SHARED_MANIFOLD_CIRCUIT_A", build_meander((0, 0, 3000, 3000), 200, 100), first_room),
        result("F_SHARED_MANIFOLD_CIRCUIT_B", build_meander((3000, 0, 6000, 3000), 200, 100), second_room),
        result("G_NARROW_SPIRAL_REJECTED", build_bifilar_spiral((0, 0, 1200, 800), 200, 100), rectangle(1200, 800), requested_spiral=True),
    ]
    output = Path("dev/ufh_diagnostics")
    output.mkdir(parents=True, exist_ok=True)
    (output / "control_scenarios.json").write_text(json.dumps({"scenarios": scenarios}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
