from __future__ import annotations

import pytest
from shapely.geometry import LineString, Polygon

from agent.ufh_circuit_splitter import build_independent_circuits, measure_pipe_coverage


L = Polygon([(0, 0), (10000, 0), (10000, 3000), (4000, 3000), (4000, 10000), (0, 10000)])
COLLECTOR = (2000.0, -400.0)


def test_five_circuits_tile_the_l_shape() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    assert len(result.circuits) == 5
    # zones tile the L-shape exactly (no uncovered area)
    assert result.uncovered_area_m2 == pytest.approx(0.0, abs=1e-6)
    assert result.coverage_area_m2 == pytest.approx(L.area / 1e6, abs=1e-6)


def test_each_circuit_geometry_is_valid() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    for circuit in result.circuits:
        assert circuit.geometry_valid
        assert len(circuit.centerline_mm) >= 4
        assert LineString(circuit.centerline_mm).is_simple


def test_each_circuit_fits_ninety_meters_with_estimated_transit() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    for circuit in result.circuits:
        assert circuit.estimated_total_mm <= 90_000.0
        assert circuit.length_valid


def test_transit_is_not_promoted_to_physical() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    for circuit in result.circuits:
        assert circuit.transit_valid is False  # straight candidates, not physical routes


def test_joint_layout_has_no_intersections_and_clearance() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    assert result.joint_intersections == []
    assert result.min_inter_circuit_clearance_mm >= 32.0
    assert result.joint_layout_valid


def test_concave_room_needs_multiple_circuits() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    # a single spiral over the whole L would far exceed 90 m
    assert len(result.circuits) > 2


def test_pipe_coverage_is_less_than_zone_tiling() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    # zones tile exactly (0 gap), but actual pipe bands leave wall-offset/core gaps
    assert result.uncovered_area_m2 == pytest.approx(0.0, abs=1e-6)
    coverage = measure_pipe_coverage(result, L)
    assert coverage["coverage_ratio"] < 1.0
    assert coverage["gap_area_m2"] > 0.0
