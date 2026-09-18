import unittest

from fastapi.testclient import TestClient

from agent.api import app


def payload() -> dict:
    return {
        "schema_version": "1.0",
        "project_id": "project-1",
        "room_id": "room-1",
        "boundary": {
            "points": [
                {"x_mm": 0, "y_mm": 0},
                {"x_mm": 4000, "y_mm": 0},
                {"x_mm": 4000, "y_mm": 3000},
                {"x_mm": 0, "y_mm": 3000},
                {"x_mm": 0, "y_mm": 0},
            ]
        },
        "exclusion_zones": [],
        "collector_point": {"x_mm": 2000, "y_mm": 100},
        "wall_offset_mm": 100,
        "spacing_mm": 200,
    }


class FloorHeatingProjectPreviewApiTests(unittest.TestCase):
    def test_integrated_preview_is_deterministic_and_exact(self) -> None:
        with TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        ) as client:
            first = client.post(
                "/api/v1/projects/project-1/engineering/floor-heating/system-preview",
                json=payload(),
            )
            second = client.post(
                "/api/v1/projects/project-1/engineering/floor-heating/system-preview",
                json=payload(),
            )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.content, second.content)
        body = first.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["system_graph"]["circuit_count"], 1)
        self.assertEqual(
            body["specification"]["pipe_requirement"]["calculated_total_pipe_length_mm"],
            44100,
        )
        self.assertEqual(
            body["specification"]["collector_requirement"]["required_port_count"],
            1,
        )

    def test_path_identity_unknown_fields_and_loopback_are_bounded(self) -> None:
        with TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        ) as client:
            mismatch = client.post(
                "/api/v1/projects/other/engineering/floor-heating/system-preview",
                json=payload(),
            )
            unknown = payload()
            unknown["unexpected"] = True
            invalid = client.post(
                "/api/v1/projects/project-1/engineering/floor-heating/system-preview",
                json=unknown,
            )
        self.assertEqual(mismatch.status_code, 422)
        self.assertEqual(mismatch.json()["detail"]["code"], "floor_heating_project_id_mismatch")
        self.assertEqual(invalid.status_code, 422)
        with TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("192.0.2.10", 50000),
        ) as client:
            response = client.post(
                "/api/v1/projects/project-1/engineering/floor-heating/system-preview",
                json=payload(),
            )
        self.assertEqual(response.status_code, 403)

    def test_old_geometry_preview_remains_byte_compatible(self) -> None:
        with TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        ) as client:
            first = client.post(
                "/api/v1/engineering/floor-heating/preview",
                json=payload(),
            )
            second = client.post(
                "/api/v1/engineering/floor-heating/preview",
                json=payload(),
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.content, second.content)


if __name__ == "__main__":
    unittest.main()
