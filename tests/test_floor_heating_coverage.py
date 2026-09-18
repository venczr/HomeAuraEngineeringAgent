import unittest

from agent.floor_heating_coverage import (
    FloorHeatingCoverageRequest,
    solve_floor_heating_coverage,
)


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def request(width: int, height: int, **overrides) -> FloorHeatingCoverageRequest:
    payload = {
        "project_id": "coverage-project",
        "room_id": f"room-{width}x{height}",
        "boundary": {"points": [
            point(0, 0), point(width, 0), point(width, height),
            point(0, height), point(0, 0),
        ]},
        "exclusion_zones": [],
        "collector_point": point(width // 2, 1100),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
        "minimum_circuit_length_mm": 40000,
        "maximum_circuit_length_mm": 80000,
        "field_spacing_mm": 200,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "exterior_wall_segments": [{
            "reference": "exterior-wall-south",
            "start": point(0, 0),
            "end": point(width, 0),
        }],
    }
    payload.update(overrides)
    return FloorHeatingCoverageRequest.model_validate(payload)


class FloorHeatingCoverageSolverTests(unittest.TestCase):
    def assert_valid_plan(self, width: int, height: int, expected: int) -> None:
        plan = solve_floor_heating_coverage(request(width, height))
        self.assertEqual(plan.required_circuit_count, expected)
        self.assertEqual(plan.collector_port_count, expected)
        self.assertEqual(len(plan.zones), expected)
        self.assertEqual(len(plan.circuit_routes), expected)
        self.assertEqual(len(plan.circuit_budget), expected)
        self.assertEqual(
            len({route.id for route in plan.circuit_routes}),
            expected,
        )
        for route, budget in zip(plan.circuit_routes, plan.circuit_budget):
            self.assertTrue(route.validation.valid)
            self.assertFalse(route.validation.self_intersection)
            self.assertFalse(route.validation.branches)
            self.assertGreaterEqual(route.length_mm, 40000)
            self.assertLessEqual(route.length_mm, 80000)
            self.assertTrue(budget.within_length_window)
        self.assertFalse(plan.full_coverage_claimed)
        self.assertEqual(plan.status, "partial")
        self.assertIn(
            "COVERAGE_ESTIMATE_ONLY_FULL_COVERAGE_NOT_CLAIMED",
            plan.diagnostics,
        )
        self.assertLess(plan.coverage_ratio, 1.0)
        self.assertGreater(plan.coverage_ratio, 0.0)

    def test_small_room_requires_one_valid_circuit(self) -> None:
        self.assert_valid_plan(4000, 3000, 1)

    def test_large_room_requires_two_valid_circuits(self) -> None:
        self.assert_valid_plan(7000, 3200, 2)

    def test_larger_room_requires_three_valid_circuits(self) -> None:
        self.assert_valid_plan(9000, 3500, 3)

    def test_exclusion_is_assigned_without_false_coverage_claim(self) -> None:
        exclusion = {"points": [
            point(1600, 1500), point(1700, 1500),
            point(1700, 1600), point(1600, 1600), point(1600, 1500),
        ]}
        plan = solve_floor_heating_coverage(
            request(7000, 3200, exclusion_zones=[exclusion])
        )
        self.assertEqual(plan.required_circuit_count, 2)
        self.assertEqual(sum(len(zone.exclusion_zones) for zone in plan.zones), 1)
        self.assertTrue(all(route.validation.exclusion_clear for route in plan.circuit_routes))
        self.assertFalse(plan.full_coverage_claimed)

    def test_impossible_geometry_and_more_than_three_are_fail_closed(self) -> None:
        l_shape = {"points": [
            point(0, 0), point(4000, 0), point(4000, 2000),
            point(2000, 2000), point(2000, 4000),
            point(0, 4000), point(0, 0),
        ]}
        geometry = solve_floor_heating_coverage(
            request(4000, 4000, boundary=l_shape)
        )
        self.assertEqual(geometry.status, "impossible")
        self.assertEqual(geometry.required_circuit_count, 0)
        self.assertEqual(geometry.circuit_routes, [])

        too_large = solve_floor_heating_coverage(request(12000, 6000))
        self.assertEqual(too_large.status, "impossible")
        self.assertIn(
            "COVERAGE_REQUIRES_MORE_THAN_THREE_CIRCUITS",
            too_large.diagnostics,
        )

    def test_plan_is_deterministic(self) -> None:
        first = solve_floor_heating_coverage(request(7000, 3200))
        second = solve_floor_heating_coverage(request(7000, 3200))
        self.assertEqual(first.model_dump(mode="json"), second.model_dump(mode="json"))

    def test_uneven_partition_remains_on_installation_grid(self) -> None:
        plan = solve_floor_heating_coverage(request(9100, 3500))
        self.assertEqual(plan.required_circuit_count, 3)
        for zone in plan.zones:
            for boundary_point in zone.boundary.points:
                self.assertEqual(boundary_point.x_mm % 100, 0)
                self.assertEqual(boundary_point.y_mm % 100, 0)

    def test_impossible_plan_digest_covers_input_geometry(self) -> None:
        first = solve_floor_heating_coverage(request(12000, 6000))
        second = solve_floor_heating_coverage(
            request(12100, 6000, room_id="different-impossible-room")
        )
        self.assertEqual(first.status, "impossible")
        self.assertEqual(second.status, "impossible")
        self.assertNotEqual(first.plan_digest, second.plan_digest)

    def test_collector_anchor_is_projected_into_each_zone_and_changes_routes(self) -> None:
        left = solve_floor_heating_coverage(request(7000, 3200, collector_point=point(900, 1100)))
        right = solve_floor_heating_coverage(request(7000, 3200, collector_point=point(6100, 1100)))

        self.assertEqual(left.status, "partial")
        self.assertEqual(right.status, "partial")
        self.assertNotEqual(left.plan_digest, right.plan_digest)
        self.assertNotEqual([zone.route_anchor_point for zone in left.zones], [zone.route_anchor_point for zone in right.zones])
        self.assertNotEqual([route.polyline for route in left.circuit_routes], [route.polyline for route in right.circuit_routes])
        for plan in (left, right):
            for zone, route in zip(plan.zones, plan.circuit_routes):
                self.assertTrue(route.validation.valid)
                self.assertEqual(zone.route_anchor_point.x_mm % 100, 0)
                self.assertEqual(zone.route_anchor_point.y_mm % 100, 0)


if __name__ == "__main__":
    unittest.main()
