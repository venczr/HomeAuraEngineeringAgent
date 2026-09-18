import json
import subprocess
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import agent.floor_heating_engine as floor_heating_engine
import agent.floor_heating_preview_api as floor_heating_preview_api
from agent.api import app
from agent.floor_heating_models import FloorHeatingResult


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def payload() -> dict:
    return {
        "schema_version": "1.0",
        "project_id": "project-1",
        "room_id": "room-1",
        "boundary": {"points": [point(0, 0), point(4000, 0), point(4000, 3000), point(0, 3000), point(0, 0)]},
        "exclusion_zones": [],
        "collector_point": point(2000, 100),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
    }


class FloorHeatingPreviewApiTests(unittest.TestCase):
    def test_preview_success_is_deterministic_and_strict(self) -> None:
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
            first = client.post("/api/v1/engineering/floor-heating/preview", json=payload())
            second = client.post("/api/v1/engineering/floor-heating/preview", json=payload())
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.content, second.content)
        result = FloorHeatingResult.model_validate_json(first.content)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.result_digest), 64)

    def test_invalid_input_and_non_loopback_are_bounded(self) -> None:
        invalid = payload()
        invalid["unknown"] = True
        with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
            response = client.post("/api/v1/engineering/floor-heating/preview", json=invalid)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "floor_heating_request_invalid")
        with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.10", 50000)) as client:
            response = client.post("/api/v1/engineering/floor-heating/preview", json=payload())
        self.assertEqual(response.status_code, 403)

    def test_preview_has_no_external_side_effects(self) -> None:
        body = json.dumps(payload()).encode("utf-8")
        forbidden = AssertionError("floor-heating preview side effect")
        with (
            patch.object(Path, "read_bytes", side_effect=forbidden),
            patch.object(Path, "write_bytes", side_effect=forbidden),
            patch("builtins.open", side_effect=forbidden),
            patch.object(subprocess, "Popen", side_effect=forbidden),
            patch.object(floor_heating_preview_api, "calculate_floor_heating", wraps=floor_heating_engine.calculate_floor_heating) as calculate,
        ):
            with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
                response = client.post(
                    "/api/v1/engineering/floor-heating/preview",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )
        self.assertEqual(response.status_code, 200, response.text)
        calculate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
