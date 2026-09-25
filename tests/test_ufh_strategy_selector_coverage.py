"""Coverage semantics and HYBRID partial-status guards for select_layout.

These tests pin the distinction between the legacy zone-tiling area
(``SPIRAL_COVERAGE_AREA`` / ``UNCOVERED_HEATABLE_AREA``) and the real pipe-band
coverage computed from the rounded BODY centerline, and guard that a HYBRID
partial result never advertises itself as a complete route.
"""

import json
from pathlib import Path

import pytest

from agent.ufh_strategy_selector import select_layout
from scripts.build_test01_generator_package import clear_unrouted_room_metrics, route_preview_status


# A room-8-shaped notched rectangle: the east wall recedes at y 8078..8131,
# which forces the selector onto the partial HYBRID path.
NOTCHED_ROOM = [
    (4269, 5415), (4269, 8802), (9295, 8802), (9295, 8131),
    (8890, 8114), (8890, 8096), (9295, 8078), (9295, 5415),
]


def test_zone_area_vs_pipe_band_coverage_differ():
    selection = select_layout(
        NOTCHED_ROOM, mode="AUTO", maximum_circuit_length_mm=90_000,
        spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3,
    )
    assert selection["strategy"] == "HYBRID_SPIRAL_MEANDER"
    zone_area = selection["SPIRAL_COVERAGE_AREA"]
    pipe_area = selection["PIPE_BAND_COVERAGE_AREA"]
    # The legacy field tiles the inscribed zone; the pipe-band field is the
    # actual rounded-centerline buffer, so it must be strictly smaller here.
    assert zone_area > pipe_area > 0
    assert selection["COVERAGE_AREA_SEMANTICS"] == "ZONE_AREA_TILING_LEGACY_NOT_PIPE_COVERAGE"
    assert selection["PIPE_COVERAGE_METHOD"] == "BODY_ROUNDED_CENTERLINE_BUFFER_SPACING_HALF_NO_TRANSIT"
    assert 0 < selection["PIPE_BAND_COVERAGE_PERCENT"] < 100
    route = selection["routes"][0]
    assert route["PIPE_BAND_COVERAGE_AREA"] < route["SPIRAL_COVERAGE_AREA"]


def test_hybrid_partial_is_not_a_complete_route():
    selection = select_layout(
        NOTCHED_ROOM, mode="AUTO", maximum_circuit_length_mm=90_000,
        spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3,
    )
    assert selection["strategy"] == "HYBRID_SPIRAL_MEANDER"
    assert selection["HYBRID_VALID"] is False
    assert selection["HYBRID_CONNECTION_VALID"] is False
    # The partial flags must also be exposed on the emitted route.
    assert selection["routes"][0]["HYBRID_VALID"] is False
    assert selection["routes"][0]["HYBRID_CONNECTION_VALID"] is False
    assert route_preview_status(selection) == "PARTIAL_HYBRID_RESIDUAL_UNROUTED"


def test_rectangle_route_exposes_pipe_band_fields():
    rectangle = [(0, 0), (4000, 0), (4000, 3000), (0, 3000), (0, 0)]
    selection = select_layout(
        rectangle, mode="AUTO", maximum_circuit_length_mm=90_000,
        spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3,
    )
    assert selection["strategy"] in ("BIFILAR_SPIRAL", "MULTI_BIFILAR_SPIRAL")
    assert selection["COVERAGE_AREA_SEMANTICS"] == "ZONE_AREA_TILING_LEGACY_NOT_PIPE_COVERAGE"
    assert 0 < selection["PIPE_BAND_COVERAGE_AREA"] <= selection["SPIRAL_COVERAGE_AREA"]
    assert 0 <= selection["PIPE_BAND_COVERAGE_PERCENT"] <= 100


def test_multi_route_coverage_is_scoped_to_each_zone():
    project_path = Path(__file__).parents[1] / "homeaura-editor/public/plans/test01-project.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    kitchen = next(room for room in project["rooms"] if room["label"].startswith("3 /"))
    selection = select_layout(kitchen["global_boundary_mm"], mode="AUTO", maximum_circuit_length_mm=90_000)
    assert selection["strategy"] == "MULTI_BIFILAR_SPIRAL"
    assert selection["PIPE_COVERAGE_DOMAIN"] == "SOURCE_ROOM"
    assert len(selection["routes"]) == 2
    assert all(route["PIPE_COVERAGE_DOMAIN"] == "ROUTE_ZONE" for route in selection["routes"])
    assert all(route["PIPE_BAND_COVERAGE_AREA"] < selection["PIPE_BAND_COVERAGE_AREA"] for route in selection["routes"])
    assert sum(route["PIPE_BAND_COVERAGE_AREA"] for route in selection["routes"]) == pytest.approx(selection["PIPE_BAND_COVERAGE_AREA"], abs=0.01)


def test_meander_reports_pipe_coverage_separately_from_zone_area():
    room = [(0, 0), (4000, 0), (4000, 3000), (0, 3000), (0, 0)]
    selection = select_layout(room, mode="MEANDER", maximum_circuit_length_mm=90_000)
    assert selection["strategy"] == "MEANDER_ONLY"
    assert selection["SPIRAL_COVERAGE_AREA"] == 0
    assert selection["MEANDER_COVERAGE_AREA"] == 12_000_000
    assert 0 < selection["PIPE_BAND_COVERAGE_AREA"] < selection["MEANDER_COVERAGE_AREA"]


def test_unrouted_room_drops_legacy_full_coverage_claim():
    room = {
        "floor_global_route_polylines_mm": [[[0, 0], [100, 0]]],
        "candidate_lengths_mm": [100],
        "route_validation": [{"GEOMETRY_VALID": True}],
        "coverage": 1.0,
    }
    clear_unrouted_room_metrics(room)
    assert room["floor_global_route_polylines_mm"] == []
    assert room["candidate_lengths_mm"] == []
    assert room["route_validation"] == []
    assert room["coverage"] == {}
