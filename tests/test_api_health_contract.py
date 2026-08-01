from __future__ import annotations

from fastapi.testclient import TestClient

from agent.api import app


def test_health_exposes_stable_homeaura_identity() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "HomeAura Engineering Agent API"
    assert payload["version"] == app.version
