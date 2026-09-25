"""Primary deterministic HA-FH-VIS-001 fixture and package generator."""

from __future__ import annotations

import argparse
import json

from pathlib import Path

from agent.floor_heating_coverage import (
    FloorHeatingCoveragePlan,
    FloorHeatingCoverageRequest,
    solve_floor_heating_coverage,
)
from agent.floor_heating_svg_renderer import (
    FloorHeatingSvgBundle,
    render_floor_heating_layout,
    write_floor_heating_layout,
)


def _point(x_mm: int, y_mm: int) -> dict[str, int]:
    return {"x_mm": x_mm, "y_mm": y_mm}


def build_primary_fixture_request() -> FloorHeatingCoverageRequest:
    return FloorHeatingCoverageRequest.model_validate({
        "project_id": "Test_01",
        "room_id": "HA-FH-VIS-001-room-7000x3200",
        "boundary": {"points": [
            _point(0, 0),
            _point(7000, 0),
            _point(7000, 3200),
            _point(0, 3200),
            _point(0, 0),
        ]},
        "exclusion_zones": [{"points": [
            _point(1200, 800),
            _point(1400, 800),
            _point(1400, 840),
            _point(1200, 840),
            _point(1200, 800),
        ]}],
        "collector_point": _point(3500, 1100),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
        "minimum_circuit_length_mm": 40000,
        "maximum_circuit_length_mm": 80000,
        "field_spacing_mm": 200,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "installation_grid_spacing_mm": 100,
        "exterior_wall_segments": [{
            "reference": "exterior-wall-south",
            "start": _point(0, 0),
            "end": _point(7000, 0),
        }],
        "perimeter_priority_mode": True,
    })


def build_primary_fixture() -> tuple[
    FloorHeatingCoverageRequest,
    FloorHeatingCoveragePlan,
    FloorHeatingSvgBundle,
]:
    request = build_primary_fixture_request()
    plan = solve_floor_heating_coverage(request)
    bundle = render_floor_heating_layout(request, plan)
    return request, plan, bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    _, plan, bundle = build_primary_fixture()
    paths = write_floor_heating_layout(bundle, arguments.output)
    print(json.dumps({
        "verdict": bundle.verdict,
        "geometry_digest": bundle.geometry_digest,
        "coverage_status": plan.status,
        "coverage_ratio": plan.coverage_ratio,
        "circuit_count": len(plan.circuit_routes),
        "circuit_lengths_mm": [route.length_mm for route in plan.circuit_routes],
        "paths": {name: str(path.resolve()) for name, path in paths.items()},
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if bundle.verdict == "TWO_D_SVG_LAYOUT_READY_FOR_VISUAL_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_primary_fixture", "build_primary_fixture_request"]
