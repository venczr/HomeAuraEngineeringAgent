from __future__ import annotations

from shapely.geometry import Polygon

from agent.ufh_circuit_splitter import CircuitCandidate, build_independent_circuits
from agent.ufh_transit_router import (
    TransitRoute,
    build_synthetic_connection,
    render_full_connection_svg,
    route_transit,
    search_optimal_split,
    validate_full_connection,
)
from agent.ufh_circuit_splitter import build_circuits_with_boundaries, measure_pipe_coverage


L = Polygon([(0, 0), (10000, 0), (10000, 3000), (4000, 3000), (4000, 10000), (0, 10000)])
COLLECTOR = (2000.0, -400.0)


def _circuit(
    cid: str,
    sx: float,
    rx: float,
    *,
    zone: Polygon | None = None,
    centerline: list[tuple[float, float]] | None = None,
) -> CircuitCandidate:
    zone = zone or Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)])
    centerline = centerline or [(sx, 108.0), (sx - 100, 108.0), (sx - 100, 500.0), (rx, 500.0), (rx, 108.0)]
    return CircuitCandidate(
        cid, zone, centerline,
        coverage_length_mm=1000.0,
        terminal_supply_mm=(sx, 108.0),
        terminal_return_mm=(rx, 108.0),
        estimated_transit_mm=0.0, estimated_total_mm=1000.0,
        geometry_valid=True, length_valid=True,
    )


def _transit(cid: str, supply: list, ret: list) -> TransitRoute:
    import math
    def length(p):
        return sum(math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(1, len(p)))
    return TransitRoute(cid, supply, ret, length(supply), length(ret), length(supply) + length(ret) + 1000.0, True, True)


def test_full_connection_is_physically_valid() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    connection = build_synthetic_connection(L)
    transit = route_transit(result.circuits, connection)
    report = validate_full_connection(result.circuits, transit, connection)
    assert report["r80_valid"]
    assert report["containment_valid"]
    assert report["door_passage_valid"]
    assert report["wall_crossing_valid"]
    assert report["continuity_valid"]
    assert report["clearance_valid"]
    assert report["length_valid"]
    assert report["transit_valid"]
    assert report["full_circuit_valid"]


def test_every_circuit_rounded_length_fits_90m() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    connection = build_synthetic_connection(L)
    transit = route_transit(result.circuits, connection)
    for route in transit:
        assert route.rounded_total_mm <= 90_000.0
        assert route.r80_valid
        assert route.length_valid


def test_too_narrow_door_is_rejected() -> None:
    # terminals 20 mm apart -> door 120 mm wide < 2*edge(50)+spacing(32)=132 mm
    circuit = _circuit("C1", 1000.0, 1020.0)
    connection = build_synthetic_connection(
        Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]),
    )
    transit = [_transit("C1",
                        [(2000.0, -64.0), (1000.0, -64.0), (1000.0, 108.0)],
                        [(1020.0, 108.0), (1020.0, -64.0), (2000.0, -64.0)])]
    report = validate_full_connection([circuit], transit, connection)
    assert not report["door_passage_valid"]
    assert any("too narrow" in d for d in report["door_failures"])


def test_wall_crossing_outside_door_is_rejected() -> None:
    circuit = _circuit("C1", 1000.0, 1200.0)
    connection = build_synthetic_connection(
        Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]),
    )
    # supply crosses y=0 at x=1900, far outside the door [1150, 1250]
    transit = [_transit("C1",
                        [(2000.0, -64.0), (1900.0, -64.0), (1900.0, 108.0)],
                        [(1200.0, 108.0), (1200.0, -64.0), (2000.0, -64.0)])]
    report = validate_full_connection([circuit], transit, connection)
    assert not report["door_passage_valid"]
    assert report["door_failures"]


def test_short_bend_is_rejected_for_r80() -> None:
    # supply riser only 100 mm < 2*R80=160 mm -> tangent clearance violation
    circuit = _circuit("C1", 1000.0, 1200.0)
    connection = build_synthetic_connection(
        Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]),
    )
    transit = [_transit("C1",
                        [(2000.0, -64.0), (1000.0, -64.0), (1000.0, 108.0)],
                        [(1200.0, 108.0), (1200.0, -64.0), (2000.0, -64.0)])]
    # make the supply riser short: terminal y very close to corridor level
    circuit = _circuit("C1", 1000.0, 1200.0)
    transit = [_transit("C1",
                        [(2000.0, 50.0), (1000.0, 50.0), (1000.0, 108.0)],  # riser 58 mm
                        [(1200.0, 108.0), (1200.0, -64.0), (2000.0, -64.0)])]
    report = validate_full_connection([circuit], transit, connection)
    assert not report["r80_valid"]


def test_own_spiral_recross_away_from_terminal_is_rejected() -> None:
    # supply overlaps the coverage away from the terminal
    centerline = [(1000.0, 108.0), (1000.0, 900.0), (1200.0, 900.0), (1200.0, 108.0)]
    circuit = _circuit("C1", 1000.0, 1200.0, centerline=centerline)
    connection = build_synthetic_connection(
        Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]),
    )
    # supply climbs the coverage's left edge (x=1000, y 108..900) before
    # returning to the terminal: overlap length > 0 away from the terminal
    transit = [_transit("C1",
                        [(2000.0, -64.0), (1000.0, -64.0), (1000.0, 900.0), (1000.0, 108.0)],
                        [(1200.0, 108.0), (1200.0, -64.0), (2000.0, -64.0)])]
    report = validate_full_connection([circuit], transit, connection)
    assert not report["transit_valid"]
    # the supply backtracks over the coverage's left edge: a self-intersection
    # caught by the rounded-line topology / self-clearance checks, not a simple
    # "own pair" skip.
    assert report["topology_failures"] or report["self_clearance_violations"]


def test_self_clearance_between_16_and_32mm_is_rejected() -> None:
    # supply and return corridors 20 mm apart: > 16 mm (pipe diameter) but
    # < 32 mm (project minimum between non-adjacent axes) -> must block.
    circuit = _circuit("C1", 1000.0, 1200.0)
    connection = build_synthetic_connection(
        Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]),
    )
    transit = [_transit("C1",
                        [(2000.0, -64.0), (1000.0, -64.0), (1000.0, 108.0)],
                        [(1200.0, 108.0), (1200.0, -44.0), (2000.0, -44.0)])]
    report = validate_full_connection([circuit], transit, connection)
    assert not report["full_circuit_valid"]
    assert report["self_clearance_violations"]


def test_door_crossing_too_close_to_jamb_is_rejected() -> None:
    # terminals look fine (1000, 1200) but the supply actually crosses y=0 at
    # x=1240, only 10 mm from the right jamb (1250) -> must block.
    circuit = _circuit("C1", 1000.0, 1200.0)
    connection = build_synthetic_connection(
        Polygon([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]),
    )
    transit = [_transit("C1",
                        [(2000.0, -64.0), (1240.0, -64.0), (1240.0, 108.0), (1000.0, 108.0)],
                        [(1200.0, 108.0), (1200.0, -64.0), (2000.0, -64.0)])]
    report = validate_full_connection([circuit], transit, connection)
    assert not report["door_passage_valid"]
    assert report["door_failures"]


def test_svg_uses_rounded_geometry() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    connection = build_synthetic_connection(L)
    transit = route_transit(result.circuits, connection)
    svg = render_full_connection_svg(result.circuits, transit, connection)
    # R80 fillets are emitted as SVG arc commands (A ...), not only M/L
    assert "A " in svg
    assert "M " in svg


def test_optimized_boundaries_improve_coverage_above_96_percent() -> None:
    # shifting the internal boundaries to multiples of 2*pitch minimises the
    # bifilar residual cores and lifts coverage above the 96 % target.
    result = build_circuits_with_boundaries(
        L, COLLECTOR, vertical_bounds=(1200.0, 2800.0), horizontal_bound=6800.0,
    )
    connection = build_synthetic_connection(L)
    transit = route_transit(result.circuits, connection)
    report = validate_full_connection(result.circuits, transit, connection)
    assert report["transit_valid"]
    coverage = measure_pipe_coverage(result, L)
    assert coverage["coverage_ratio"] > 0.96


def test_search_returns_best_valid_candidate() -> None:
    result = search_optimal_split(L, (2000.0, -520.0))
    assert result["status"] == "FOUND_VALID_CANDIDATE"
    assert result["coverage_ratio"] > 0.96
    assert result["boundaries"]["vertical_bounds"] == [1200.0, 2800.0]
    assert result["boundaries"]["horizontal_bound"] == 6800.0


def test_rounded_coverage_is_measured_not_sharp() -> None:
    result = build_circuits_with_boundaries(
        L, COLLECTOR, vertical_bounds=(1200.0, 2800.0), horizontal_bound=6800.0,
    )
    cov = measure_pipe_coverage(result, L)
    # rounded (R80 fillets) coverage is slightly below the sharp-polyline value
    # (97.88 %); the official metric must be the rounded one (97.16 %).
    assert 0.968 < cov["coverage_ratio"] < 0.975


def test_missing_transit_route_fails_bijection() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    connection = build_synthetic_connection(L)
    transit = route_transit(result.circuits, connection)
    transit = transit[:-1]  # drop one route
    report = validate_full_connection(result.circuits, transit, connection)
    assert not report["full_circuit_valid"]
    assert not report["bijection_valid"]
    assert any("missing" in f for f in report["bijection_failures"])


def test_extra_transit_route_fails_bijection() -> None:
    result = build_independent_circuits(L, COLLECTOR)
    connection = build_synthetic_connection(L)
    transit = route_transit(result.circuits, connection)
    transit.append(transit[0])  # a duplicate route with an existing id
    # also add a route with an unknown id
    import copy
    extra = copy.deepcopy(transit[0])
    extra.circuit_id = "V9"
    transit.append(extra)
    report = validate_full_connection(result.circuits, transit, connection)
    assert not report["full_circuit_valid"]
    assert not report["bijection_valid"]
    assert any("duplicate" in f or "without circuit" in f for f in report["bijection_failures"])
