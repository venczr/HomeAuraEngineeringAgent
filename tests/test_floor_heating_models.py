import unittest

from pydantic import ValidationError

from agent.floor_heating_models import (
    FloorHeatingPoint,
    FloorHeatingPolygon,
    FloorHeatingRequest,
)


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def rectangle() -> dict:
    return {
        "points": [
            point(0, 0),
            point(4000, 0),
            point(4000, 3000),
            point(0, 3000),
            point(0, 0),
        ]
    }


class FloorHeatingModelTests(unittest.TestCase):
    def request(self, **overrides):
        payload = {
            "project_id": "project-1",
            "room_id": "room-1",
            "boundary": rectangle(),
            "exclusion_zones": [],
            "collector_point": point(2000, 100),
            "wall_offset_mm": 100,
            "spacing_mm": 150,
        }
        payload.update(overrides)
        return FloorHeatingRequest.model_validate(payload)

    def test_strict_rectangle_and_allowed_spacing(self) -> None:
        request = self.request(spacing_mm=100)
        self.assertEqual(request.boundary.points[0].x_mm, 0)
        self.assertEqual(request.minimum_circuit_length_mm, 40000)
        self.assertEqual(request.maximum_circuit_length_mm, 80000)
        self.assertTrue(request.perimeter_priority_mode)
        for spacing in (100, 150, 200):
            self.assertEqual(self.request(spacing_mm=spacing).spacing_mm, spacing)

    def test_unknown_nonfinite_and_invalid_spacing_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.request(unexpected=True)
        with self.assertRaises(ValidationError):
            self.request(spacing_mm=125)
        with self.assertRaises(ValidationError):
            FloorHeatingPoint.model_validate({"x_mm": 1.5, "y_mm": 2})
        with self.assertRaises(ValidationError):
            self.request(
                minimum_circuit_length_mm=80001,
                maximum_circuit_length_mm=80000,
            )

    def test_polygon_requires_minimum_points_but_geometry_is_engine_validated(self) -> None:
        with self.assertRaises(ValidationError):
            FloorHeatingPolygon(points=[FloorHeatingPoint(x_mm=0, y_mm=0)])


if __name__ == "__main__":
    unittest.main()
