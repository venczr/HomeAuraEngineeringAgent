import unittest

from fastapi.testclient import TestClient

from agent.api import app


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def payload() -> dict:
    return {
        "schema_version": "1.0",
        "project_id": "editor-project",
        "room_id": "room-7000x3200",
        "boundary": {"points": [point(0, 0), point(7000, 0), point(7000, 3200), point(0, 3200), point(0, 0)]},
        "exclusion_zones": [],
        "collector_point": point(3500, 1100),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
        "minimum_circuit_length_mm": 40000,
        "maximum_circuit_length_mm": 80000,
        "field_spacing_mm": 200,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "installation_grid_spacing_mm": 100,
        "perimeter_priority_mode": True,
        "exterior_wall_segments": [{"reference": "south", "start": point(0, 0), "end": point(7000, 0)}],
    }


class FloorHeatingCoveragePreviewApiTests(unittest.TestCase):
    def test_two_route_preview_is_deterministic_and_read_only(self) -> None:
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
            first = client.post("/api/v1/engineering/floor-heating/coverage-preview", json=payload())
            second = client.post("/api/v1/engineering/floor-heating/coverage-preview", json=payload())
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.content, second.content)
        body = first.json()
        self.assertEqual(body["required_circuit_count"], 2)
        self.assertEqual(len(body["circuit_routes"]), 2)
        self.assertTrue(all(route["validation"]["valid"] for route in body["circuit_routes"]))
        self.assertFalse(body["full_coverage_claimed"])

    def test_non_loopback_and_invalid_payload_fail_closed(self) -> None:
        with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.10", 50000)) as client:
            forbidden = client.post("/api/v1/engineering/floor-heating/coverage-preview", json=payload())
        self.assertEqual(forbidden.status_code, 403)
        invalid = payload()
        invalid["unknown"] = True
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
            response = client.post("/api/v1/engineering/floor-heating/coverage-preview", json=invalid)
        self.assertEqual(response.status_code, 422)

    def test_malformed_and_oversized_bodies_fail_closed(self) -> None:
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
            malformed = client.post(
                "/api/v1/engineering/floor-heating/coverage-preview",
                content=b"not-json",
                headers={"content-type": "application/json"},
            )
            oversized = client.post(
                "/api/v1/engineering/floor-heating/coverage-preview",
                content=b"{" + b" " * (2 * 1024 * 1024),
                headers={"content-type": "application/json"},
            )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(oversized.status_code, 413)

    def test_exclusion_failure_keeps_engine_reason(self) -> None:
        blocked = payload()
        blocked["exclusion_zones"] = [{"points": [
            point(100, 100), point(3300, 100), point(3300, 3000),
            point(100, 3000), point(100, 100),
        ]}]
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
            response = client.post(
                "/api/v1/engineering/floor-heating/coverage-preview",
                json=blocked,
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "impossible")
        self.assertTrue(any(item.startswith("fh-zone-1:") for item in body["diagnostics"]))


if __name__ == "__main__":
    unittest.main()
