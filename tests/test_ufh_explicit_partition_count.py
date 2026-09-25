import unittest

from pydantic import ValidationError

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
        "minimum_circuit_length_mm": 40_000,
        "maximum_circuit_length_mm": 80_000,
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


class ExplicitPartitionCountTests(unittest.TestCase):
    def assert_exact_valid_count(self, width: int, height: int, count: int) -> None:
        plan = solve_floor_heating_coverage(
            request(width, height, requested_circuit_count=count)
        )
        self.assertEqual(plan.status, "partial")
        self.assertEqual(plan.required_circuit_count, count)
        self.assertEqual(plan.collector_port_count, count)
        self.assertEqual(len(plan.zones), count)
        self.assertEqual(len(plan.circuit_routes), count)
        self.assertEqual(len(plan.circuit_budget), count)
        ids = [route.id for route in plan.circuit_routes]
        self.assertEqual(len(set(ids)), count)
        self.assertEqual(ids, [
            f"fh/coverage-project/room-{width}x{height}/coverage-zone-{index}/circuit-1"
            for index in range(1, count + 1)
        ])
        for route, budget in zip(plan.circuit_routes, plan.circuit_budget):
            self.assertTrue(route.validation.valid)
            self.assertTrue(route.validation.length_valid)
            self.assertTrue(budget.within_length_window)
            self.assertGreaterEqual(route.length_mm, 40_000)
            self.assertLessEqual(route.length_mm, 80_000)

    def test_legacy_automatic_mode_keeps_existing_plan_and_digest(self) -> None:
        implicit = solve_floor_heating_coverage(request(7000, 3200))
        explicit_none = solve_floor_heating_coverage(
            request(7000, 3200, requested_circuit_count=None)
        )
        self.assertEqual(implicit.model_dump(mode="json"), explicit_none.model_dump(mode="json"))
        self.assertEqual(implicit.required_circuit_count, 2)
        self.assertEqual([r.length_mm for r in implicit.circuit_routes], [41_700, 41_700])
        self.assertEqual(
            implicit.plan_digest,
            "233d7de7596e990060d6af1733ee5da1206b6ab4c43d9e73ded9844c9e1153f6",
        )

    def test_force_one_circuit(self) -> None:
        self.assert_exact_valid_count(4000, 3000, 1)

    def test_force_two_circuits_and_make_distinct_candidate(self) -> None:
        one = solve_floor_heating_coverage(
            request(7000, 3200, requested_circuit_count=1)
        )
        two = solve_floor_heating_coverage(
            request(7000, 3200, requested_circuit_count=2)
        )
        self.assert_exact_valid_count(7000, 3200, 2)
        self.assertEqual(one.required_circuit_count, 1)
        self.assertNotEqual(one.plan_digest, two.plan_digest)
        self.assertNotEqual(one.circuit_routes[0].polyline, two.circuit_routes[0].polyline)

    def test_force_three_circuits(self) -> None:
        self.assert_exact_valid_count(9000, 3500, 3)

    def test_infeasible_44_1m_candidate_does_not_fallback(self) -> None:
        plan = solve_floor_heating_coverage(
            request(4000, 3000, requested_circuit_count=2)
        )
        self.assertEqual(plan.status, "impossible")
        self.assertEqual(plan.required_circuit_count, 0)
        self.assertEqual(plan.circuit_routes, [])
        self.assertIn("REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE", plan.diagnostics)
        self.assertIn("fh-zone-1:impossible_counterflow_geometry", plan.diagnostics)

    def test_count_three_can_fail_legacy_minimum_length_without_fallback(self) -> None:
        plan = solve_floor_heating_coverage(
            request(9000, 2500, requested_circuit_count=3)
        )
        self.assertEqual(plan.status, "impossible")
        self.assertEqual(plan.circuit_routes, [])
        self.assertIn("REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE", plan.diagnostics)
        self.assertIn("fh-zone-1:ACTUAL_LENGTH_MM=32100", plan.diagnostics)
        self.assertIn("fh-zone-1:ROUTE_LENGTH_INVALID", plan.diagnostics)

    def test_invalid_counts_fail_validation(self) -> None:
        for value in (0, -1, 4, True, 2.0, "2"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError) as raised:
                    request(7000, 3200, requested_circuit_count=value)
                self.assertIn(
                    "INVALID_REQUESTED_CIRCUIT_COUNT",
                    str(raised.exception),
                )

    def test_exact_count_is_deterministic(self) -> None:
        first = solve_floor_heating_coverage(
            request(9000, 3500, requested_circuit_count=3)
        )
        second = solve_floor_heating_coverage(
            request(9000, 3500, requested_circuit_count=3)
        )
        self.assertEqual(first.model_dump(mode="json"), second.model_dump(mode="json"))


if __name__ == "__main__":
    unittest.main()
