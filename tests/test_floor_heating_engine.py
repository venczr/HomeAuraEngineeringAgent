import unittest

from agent.floor_heating_engine import (
    _LaneSegment,
    _body_for_segments,
    _self_intersects,
    calculate_floor_heating,
    generate_counterflow_spiral,
)
from agent.floor_heating_models import FloorHeatingRequest


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def polygon(points: list[tuple[int, int]]) -> dict:
    return {"points": [point(x, y) for x, y in points]}


def request(**overrides) -> FloorHeatingRequest:
    payload = {
        "project_id": "hf-v2-project",
        "room_id": "room-7000x3200",
        "boundary": polygon([
            (0, 0), (7000, 0), (7000, 3200), (0, 3200), (0, 0),
        ]),
        "exclusion_zones": [polygon([
            (3000, 2050), (3200, 2050),
            (3200, 2090), (3000, 2090), (3000, 2050),
        ])],
        "collector_point": point(3500, 1100),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
        "minimum_circuit_length_mm": 40000,
        "maximum_circuit_length_mm": 80000,
        "requested_circuit_count": 1,
        "field_spacing_mm": 200,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "exterior_wall_segments": [{
            "reference": "exterior-wall-south",
            "start": point(0, 0),
            "end": point(7000, 0),
        }],
        "perimeter_priority_mode": True,
    }
    payload.update(overrides)
    return FloorHeatingRequest.model_validate(payload)


def route_length(points) -> int:
    return sum(
        abs(points[index].x_mm - points[index - 1].x_mm)
        + abs(points[index].y_mm - points[index - 1].y_mm)
        for index in range(1, len(points))
    )


class FloorHeatingRoutingEngineV2Tests(unittest.TestCase):
    def test_rectangle_returns_one_validated_continuous_polyline(self) -> None:
        first = calculate_floor_heating(request())
        second = calculate_floor_heating(request())

        self.assertEqual(first.status, "ok")
        self.assertEqual(first.result_digest, second.result_digest)
        self.assertEqual(first.circuit_count, 1)
        self.assertEqual(len(first.circuit_routes), 1)
        route = first.circuit_routes[0]
        circuit = first.circuits[0]
        self.assertEqual(route.polyline, circuit.points)
        self.assertEqual(route.polyline[0], route.collector_supply_point)
        self.assertEqual(route.polyline[-1], route.collector_return_point)
        self.assertNotEqual(route.polyline[0], route.polyline[-1])
        self.assertEqual(route.length_mm, route_length(route.polyline))
        self.assertEqual(route.length_mm, 69700)
        self.assertGreaterEqual(route.length_mm, 40000)
        self.assertLessEqual(route.length_mm, 80000)
        self.assertTrue(route.validation.valid)
        self.assertEqual(route.validation.polyline_count, 1)

    def test_generator_returns_flat_points_and_bypasses_collector_body(self) -> None:
        value = request()
        points = generate_counterflow_spiral(value)
        self.assertTrue(points)
        self.assertIsInstance(points[0], tuple)
        self.assertIsInstance(points[0][0], int)

        result = calculate_floor_heating(value)
        route = result.circuit_routes[0]
        collector = value.collector_point
        self.assertNotIn(collector, route.polyline)
        self.assertEqual(route.collector_supply_point.x_mm, collector.x_mm + 300)
        self.assertEqual(route.collector_return_point.x_mm, collector.x_mm + 300)
        self.assertEqual(
            abs(
                route.collector_supply_point.y_mm
                - route.collector_return_point.y_mm
            ),
            100,
        )
        self.assertEqual(circuit_points(result)[:2], result.circuits[0].supply_transit)
        self.assertEqual(circuit_points(result)[-2:], result.circuits[0].return_transit)

    def test_central_uturn_is_part_of_the_same_polyline(self) -> None:
        route = calculate_floor_heating(request()).circuit_routes[0]
        points = [(item.x_mm, item.y_mm) for item in route.polyline]
        # The only transition from the inward even track to the interleaved
        # outward track is an orthogonal U-turn inside the common spiral gate.
        self.assertIn((3400, 300), points)
        self.assertIn((3400, 500), points)
        first = points.index((3400, 300))
        self.assertEqual(
            points[first:first + 2],
            [(3400, 300), (3400, 500)],
        )

    def test_no_self_intersection_and_no_branches(self) -> None:
        validation = calculate_floor_heating(request()).circuit_routes[0].validation
        self.assertTrue(validation.connected)
        self.assertFalse(validation.self_intersection)
        self.assertFalse(validation.branches)
        self.assertTrue(validation.inside_boundary)
        self.assertTrue(validation.exclusion_clear)
        self.assertTrue(validation.endpoints_valid)

    def test_multi_reflex_compact_sweep_uses_monotone_connectors(self) -> None:
        outer = [(0, 0), (6000, 0), (6000, 4000), (0, 4000), (0, 0)]
        segments = [
            _LaneSegment(0, 300, 300, 5700, (300, 300), (5700, 300)),
            _LaneSegment(1, 500, 900, 5200, (5200, 500), (900, 500)),
            _LaneSegment(2, 700, 500, 5500, (500, 700), (5500, 700)),
            _LaneSegment(3, 900, 1200, 4800, (4800, 900), (1200, 900)),
        ]
        body = _body_for_segments(segments, outer, [], 100)
        self.assertIsNotNone(body)
        self.assertFalse(_self_intersects(body))

    def test_perimeter_priority_changes_spacing_from_100_to_200(self) -> None:
        route = calculate_floor_heating(request()).circuit_routes[0]
        outer = [
            item for item in route.spacing_segments
            if item.zone_role == "OUTER_WALL_BAND"
        ]
        field = [
            item for item in route.spacing_segments
            if item.zone_role == "FIELD"
        ]
        self.assertTrue(outer)
        self.assertTrue(field)
        self.assertEqual({item.spacing_mm for item in outer}, {100, 200})
        self.assertEqual({item.spacing_mm for item in field}, {200})
        self.assertTrue(route.outer_wall_segments)
        self.assertTrue(route.field_segments)
        self.assertTrue(route.validation.step_valid)

    def test_exclusion_is_clear_and_blocking_exclusion_fails_closed(self) -> None:
        accepted = calculate_floor_heating(request())
        self.assertEqual(accepted.status, "ok")
        self.assertTrue(accepted.circuit_routes[0].validation.exclusion_clear)

        blocked = calculate_floor_heating(
            request(
                exclusion_zones=[polygon([
                    (6400, 2400), (6800, 2400),
                    (6800, 2800), (6400, 2800), (6400, 2400),
                ])]
            )
        )
        self.assertEqual(blocked.status, "impossible")
        self.assertEqual(blocked.circuits, [])
        self.assertEqual(len(blocked.circuit_routes), 1)
        self.assertFalse(blocked.circuit_routes[0].validation.valid)
        self.assertFalse(blocked.circuit_routes[0].validation.exclusion_clear)

    def test_impossible_geometry_and_length_are_rejected(self) -> None:
        l_shape = polygon([
            (0, 0), (4000, 0), (4000, 2000),
            (2000, 2000), (2000, 4000), (0, 4000), (0, 0),
        ])
        geometry = calculate_floor_heating(
            request(
                boundary=l_shape,
                exclusion_zones=[],
                collector_point=point(500, 500),
                exterior_wall_segments=[{
                    "reference": "exterior-wall-south",
                    "start": point(0, 0),
                    "end": point(4000, 0),
                }],
            )
        )
        self.assertEqual(geometry.status, "impossible")
        self.assertEqual(
            geometry.diagnostics[0].code,
            "impossible_counterflow_geometry",
        )

        overlong = calculate_floor_heating(
            request(maximum_circuit_length_mm=60000)
        )
        self.assertEqual(overlong.status, "impossible")
        self.assertFalse(overlong.circuit_routes[0].validation.length_valid)
        self.assertEqual(overlong.circuits, [])

    def test_multiple_requested_circuits_do_not_reenable_old_partitioning(self) -> None:
        result = calculate_floor_heating(
            request(requested_circuit_count=2)
        )
        self.assertEqual(result.status, "impossible")
        self.assertEqual(
            result.diagnostics[0].code,
            "continuous_route_requires_one_circuit",
        )


def circuit_points(result):
    return result.circuits[0].points


if __name__ == "__main__":
    unittest.main()
