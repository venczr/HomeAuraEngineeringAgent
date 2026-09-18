import unittest

from pydantic import ValidationError

from agent.floor_heating_coverage import FloorHeatingCoverageRequest
from agent.floor_heating_sizing import (
    UFHSizingRequest,
    size_ufh_requirement,
)


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def coverage_request(width: int, height: int) -> FloorHeatingCoverageRequest:
    return FloorHeatingCoverageRequest.model_validate({
        "project_id": "sizing-project",
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
    })


def sizing_request(
    width: int,
    height: int,
    *,
    wall_u: float = 0.18,
    air_changes: float = 0.4,
    output_100: float = 100.0,
    output_200: float = 70.0,
    thermal_bridge_percent: float = 5.0,
    design_margin_percent: float = 10.0,
    opening_u: float = 1.1,
) -> UFHSizingRequest:
    return UFHSizingRequest.model_validate({
        "coverage_request": coverage_request(width, height).model_dump(mode="json"),
        "room": {
            "room_area_mm2": width * height,
            "room_height_mm": 2700,
            "exterior_wall_length_mm": width,
            "openings": [{
                "opening_id": "window-1",
                "kind": "window",
                "width_mm": 1200,
                "height_mm": 1400,
                "u_value_w_m2k": opening_u,
            }],
            "insulation": {
                "exterior_wall_u_value_w_m2k": wall_u,
                "floor_u_value_w_m2k": 0.2,
                "ceiling_u_value_w_m2k": 0.15,
                "air_changes_per_hour": air_changes,
                "ventilation_heat_capacity_factor_wh_m3k": 0.33,
                "thermal_bridge_allowance_percent": thermal_bridge_percent,
                "design_margin_percent": design_margin_percent,
                "floor_boundary_temperature_c": 10.0,
                "ceiling_boundary_temperature_c": 10.0,
            },
            "indoor_temperature_c": 21.0,
            "outdoor_design_temperature_c": -20.0,
        },
        "floor_construction": {
            "declared_output_at_100mm_w_m2": output_100,
            "declared_output_at_200mm_w_m2": output_200,
            "output_basis_reference": "explicit test construction declaration",
        },
    })


class FloorHeatingSizingTests(unittest.TestCase):
    def test_small_room_is_accepted_with_one_validated_route(self) -> None:
        result = size_ufh_requirement(sizing_request(4000, 3000))

        self.assertEqual(result.coverage_status, "accepted")
        self.assertEqual(result.recommended_spacing_mm, 200)
        self.assertEqual(result.required_circuit_count, 1)
        self.assertEqual(result.coverage_integration.valid_route_count, 1)
        self.assertTrue(result.coverage_integration.accepted)
        self.assertGreater(result.required_heat_w, 0)
        self.assertEqual(result.estimated_heat_loss_w, 383)
        self.assertEqual(result.required_heat_w, 421)

    def test_medium_room_is_accepted_with_two_validated_routes(self) -> None:
        result = size_ufh_requirement(sizing_request(7000, 3200, wall_u=0.22))

        self.assertEqual(result.coverage_status, "accepted")
        self.assertEqual(result.required_circuit_count, 2)
        self.assertEqual(result.coverage_integration.geometry_required_circuit_count, 2)
        self.assertEqual(result.coverage_integration.valid_route_count, 2)
        self.assertLessEqual(
            result.coverage_integration.required_coverage_ratio,
            result.coverage_integration.geometric_coverage_ratio,
        )

    def test_high_loss_room_reports_output_and_coverage_failure(self) -> None:
        result = size_ufh_requirement(sizing_request(
            7000,
            3200,
            wall_u=1.5,
            air_changes=1.5,
            output_100=80.0,
            output_200=45.0,
            thermal_bridge_percent=20.0,
            design_margin_percent=20.0,
            opening_u=3.0,
        ))

        self.assertEqual(result.recommended_spacing_mm, 100)
        self.assertEqual(result.coverage_status, "insufficient")
        self.assertIn("UFH_OUTPUT_CAPACITY_INSUFFICIENT", result.diagnostics)
        self.assertIn(
            "UFH_100MM_FIELD_ROUTE_NOT_AVAILABLE_IN_ACCEPTED_V2",
            result.diagnostics,
        )
        self.assertFalse(result.coverage_integration.accepted)

    def test_insufficient_geometric_coverage_is_detected(self) -> None:
        result = size_ufh_requirement(sizing_request(
            7000,
            3200,
            wall_u=0.65,
            air_changes=0.8,
            output_100=110.0,
            output_200=90.0,
            thermal_bridge_percent=10.0,
            design_margin_percent=15.0,
            opening_u=1.8,
        ))

        self.assertEqual(result.recommended_spacing_mm, 200)
        self.assertGreater(result.recommended_coverage_ratio, 0.0)
        self.assertEqual(result.coverage_status, "insufficient")
        self.assertIn("UFH_GEOMETRIC_COVERAGE_INSUFFICIENT", result.diagnostics)

    def test_excessive_circuit_count_is_detected(self) -> None:
        result = size_ufh_requirement(sizing_request(
            9000,
            3500,
            wall_u=0.8,
            air_changes=1.0,
            output_100=125.0,
            output_200=100.0,
            thermal_bridge_percent=10.0,
            design_margin_percent=10.0,
            opening_u=2.0,
        ))

        self.assertTrue(result.excessive_circuit_count)
        self.assertGreater(result.required_circuit_count, 3)
        self.assertIn("UFH_REQUIRED_CIRCUIT_COUNT_EXCEEDS_THREE", result.diagnostics)
        self.assertEqual(result.coverage_status, "insufficient")

    def test_repeat_is_deterministic(self) -> None:
        request = sizing_request(7000, 3200, wall_u=0.22)
        first = size_ufh_requirement(request)
        second = size_ufh_requirement(request)

        self.assertEqual(first.sizing_digest, second.sizing_digest)
        self.assertEqual(first.model_dump(mode="json"), second.model_dump(mode="json"))

    def test_required_assumptions_cannot_be_inferred(self) -> None:
        payload = sizing_request(4000, 3000).model_dump(mode="json")
        del payload["floor_construction"]

        with self.assertRaises(ValidationError):
            UFHSizingRequest.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
