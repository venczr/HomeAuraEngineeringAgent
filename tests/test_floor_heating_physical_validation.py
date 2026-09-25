"""Physical R80 bend/clearance checks for the canonical routing engine.

The canonical ``floor_heating_engine`` emits an orthogonal sharp-corner
centerline.  Real 16 mm pipe cannot turn at a point, so every emitted circuit
must be checked for materializability at R80 (2R = 160 mm hairpin width) and
pipe-to-pipe clearance.  ``physical_bend_validation`` is the bridge from the
engine to :mod:`agent.ufh_bend_geometry`.

These tests pin two installation facts:

* the legacy counterflow spiral now widens its central reversal to the field
  pitch so it IS materializable at R80;
* a 200 mm pitch serpentine IS materializable at R80, while a 100 mm pitch
  serpentine is not.
"""
from __future__ import annotations

import pytest

from agent.floor_heating_engine import (
    calculate_floor_heating,
    physical_bend_validation,
)
from agent.floor_heating_models import FloorHeatingRequest


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def polygon(points: list[tuple[int, int]]) -> dict:
    return {"points": [point(x, y) for x, y in points]}


def make_request(
    *,
    width: int,
    height: int,
    spacing: int,
    routing_mode: str = "legacy",
    turn_radius_mm: int = 80,
) -> FloorHeatingRequest:
    payload = {
        "project_id": "hf-physical",
        "room_id": "room",
        "boundary": polygon([
            (0, 0), (width, 0), (width, height), (0, height), (0, 0),
        ]),
        "exclusion_zones": [],
        "collector_point": point(width // 2, height // 2),
        "wall_offset_mm": 100,
        "spacing_mm": spacing,
        "minimum_circuit_length_mm": 1000,
        "maximum_circuit_length_mm": 80_000,
        "requested_circuit_count": 1,
        "field_spacing_mm": spacing,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "turn_radius_mm": turn_radius_mm,
        "routing_mode": routing_mode,
        "exterior_wall_segments": [{
            "reference": "exterior-south",
            "start": point(0, 0),
            "end": point(width, 0),
        }],
        "perimeter_priority_mode": True,
    }
    return FloorHeatingRequest.model_validate(payload)


def route_points(result) -> list[tuple[int, int]]:
    route = result.circuit_routes[0]
    return [(item.x_mm, item.y_mm) for item in route.polyline]


def test_counterflow_spiral_central_uturn_is_r80_materializable() -> None:
    """The legacy counterflow spiral's central reversal now uses the field
    pitch (200 mm >= 2R = 160 mm), so it is R80 materializable."""
    width, height = 7000, 3200
    outer = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    result = calculate_floor_heating(
        make_request(width=width, height=height, spacing=200, routing_mode="legacy")
    )
    report = physical_bend_validation(route_points(result), outer, bend_radius_mm=80.0)

    assert report.valid is True
    assert report.radius_mm == 80.0
    assert report.bend_count == 22
    assert report.diagnostics == ()


def test_compact_sweep_200mm_pitch_is_r80_materializable() -> None:
    """A 200 mm pitch serpentine in a small room is R80 materializable."""
    width, height = 2000, 2000
    outer = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    result = calculate_floor_heating(
        make_request(
            width=width,
            height=height,
            spacing=200,
            routing_mode="non_crossing_visual",
        )
    )
    report = physical_bend_validation(route_points(result), outer, bend_radius_mm=80.0)

    assert report.valid is True
    assert report.minimum_non_adjacent_clearance_mm == pytest.approx(200.0)
    assert report.diagnostics == ()


def test_compact_sweep_100mm_pitch_is_not_r80_materializable() -> None:
    """A 100 mm pitch serpentine needs a 160 mm hairpin and is rejected at R80."""
    width, height = 2000, 2000
    outer = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    result = calculate_floor_heating(
        make_request(
            width=width,
            height=height,
            spacing=100,
            routing_mode="non_crossing_visual",
        )
    )
    report = physical_bend_validation(route_points(result), outer, bend_radius_mm=80.0)

    assert report.valid is False
    assert "BEND_TANGENT_CLEARANCE_VIOLATION" in report.diagnostics


def test_physical_bend_validation_emits_arc_svg_path() -> None:
    """The returned report must carry the rounded centerline as an SVG arc path
    so downstream renderers can draw the true pipe, not the sharp polyline."""
    width, height = 2000, 2000
    outer = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    result = calculate_floor_heating(
        make_request(
            width=width,
            height=height,
            spacing=200,
            routing_mode="non_crossing_visual",
        )
    )
    report = physical_bend_validation(route_points(result), outer, bend_radius_mm=80.0)

    assert "A 80.000000,80.000000" in report.svg_path_data
    assert report.rounded_points
