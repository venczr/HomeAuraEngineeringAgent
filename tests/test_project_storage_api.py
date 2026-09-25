from __future__ import annotations

import json
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from fastapi.testclient import TestClient

import agent.project_storage_api as project_storage_api
from agent.api import app
from agent.domain_adapter import adapt_rooms_payload
from agent.project_foundation import (
    build_project_seed,
    canonical_json_bytes,
    sheet_manifest_reference,
)
from agent.project_models import (
    CanonicalProjectModel,
    ProjectLifecycleStatus,
)
from agent.project_storage import ProjectStorageError, ProjectStore
from agent.request_body_limit import MAX_REQUEST_BODY_BYTES


ROOT = Path(__file__).resolve().parents[1]
ROOMS_FIXTURE = ROOT / "tests" / "fixtures" / "rooms_v1_0.json"


def project_model(revision: int = 1) -> CanonicalProjectModel:
    rooms = json.loads(ROOMS_FIXTURE.read_text(encoding="utf-8"))
    domain = adapt_rooms_payload(rooms, project_id="storage-api-test")
    seed = build_project_seed(
        domain,
        [],
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    return CanonicalProjectModel(
        project_id=domain.project.stable_id,
        revision=revision,
        status=ProjectLifecycleStatus.DRAFT,
        domain=domain,
        seed=seed,
        sheet_manifest=sheet_manifest_reference(),
    )


@pytest.fixture
def storage_client():
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(Path(directory) / "projects")
        with (
            patch.object(project_storage_api, "project_store", store),
            TestClient(
                app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            yield client, store


def test_create_idempotent_get_and_advance(storage_client) -> None:
    client, _ = storage_client
    first = project_model()
    first_bytes = canonical_json_bytes(first)
    path = "/api/v1/projects/SafeProject/canonical"

    created = client.post(
        path,
        content=first_bytes,
        headers={"Content-Type": "application/json"},
    )
    repeated = client.post(
        path,
        content=first_bytes,
        headers={"Content-Type": "application/json"},
    )
    loaded = client.get(path)
    second = first.model_copy(update={"revision": 2})
    advanced = client.post(
        path,
        content=canonical_json_bytes(second),
        headers={"Content-Type": "application/json"},
    )

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert loaded.status_code == 200
    assert loaded.content == first_bytes
    assert advanced.status_code == 201
    assert set(created.json()) == {"project_id", "revision", "sha256"}
    assert created.json()["revision"] == 1
    assert client.get(path).content == canonical_json_bytes(second)


def test_loopback_is_required_for_both_routes(storage_client) -> None:
    _, _store = storage_client
    body = canonical_json_bytes(project_model())
    with TestClient(
        app,
        base_url="http://example.test",
        client=("198.51.100.20", 50000),
    ) as remote:
        post = remote.post(
            "/api/v1/projects/SafeProject/canonical",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        get = remote.get(
            "/api/v1/projects/SafeProject/canonical"
        )

    assert post.status_code == 403
    assert get.status_code == 403
    assert post.json()["detail"]["code"] == "loopback_required"
    assert get.json()["detail"]["code"] == "loopback_required"


@pytest.mark.parametrize(
    "code,status",
    [
        ("project_name_invalid", 400),
        ("project_path_escape", 400),
        ("project_json_invalid", 400),
        ("project_payload_too_large", 413),
        ("project_not_found", 404),
        ("project_identity_conflict", 409),
        ("project_revision_conflict", 409),
        ("project_history_conflict", 409),
        ("project_storage_corrupt", 500),
        ("project_storage_io", 500),
    ],
)
def test_storage_errors_have_stable_safe_http_mapping(
    storage_client,
    code: str,
    status: int,
) -> None:
    client, store = storage_client
    marker = "private-storage-path-marker"
    error = ProjectStorageError(code)
    error.__cause__ = OSError(marker)
    with patch.object(store, "load_current", side_effect=error):
        response = client.get(
            "/api/v1/projects/SafeProject/canonical"
        )

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert marker not in response.text


def test_global_limit_prevents_storage_call() -> None:
    mocked_store = Mock(spec=ProjectStore)
    with (
        patch.object(
            project_storage_api,
            "project_store",
            mocked_store,
        ),
        TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        ) as client,
    ):
        response = client.post(
            "/api/v1/projects/SafeProject/canonical",
            content=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    mocked_store.save_current_revision.assert_not_called()


def test_get_missing_project_is_safe(storage_client) -> None:
    client, _ = storage_client

    response = client.get(
        "/api/v1/projects/Missing/canonical"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "project_not_found"
    assert "projects" not in response.text.casefold()
