from __future__ import annotations

import json
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import agent.rooms_api as rooms_api
import agent.project_storage_api as project_storage_api
from agent.api import app
from agent.domain_adapter import adapt_rooms_payload
from agent.project_foundation import (
    build_canonical_project_preview,
    build_project_seed,
    canonical_json_bytes,
    sheet_manifest_reference,
)
from agent.project_models import (
    CanonicalProjectModel,
    ProjectLifecycleStatus,
)
from agent.project_storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
ROOMS_FIXTURE = ROOT / "tests" / "fixtures" / "rooms_v1_0.json"


def test_rooms_and_canonical_revision_workflow_share_project_safely() -> None:
    rooms_payload = json.loads(
        ROOMS_FIXTURE.read_text(encoding="utf-8")
    )
    domain = adapt_rooms_payload(
        rooms_payload,
        project_id="workflow-test",
    )
    revision_one = build_canonical_project_preview(
        domain,
        [],
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        sheet_manifest=sheet_manifest_reference(),
        status=ProjectLifecycleStatus.DRAFT,
    )
    revision_two = revision_one.model_copy(update={"revision": 2})

    with tempfile.TemporaryDirectory() as directory:
        projects_root = Path(directory) / "projects"
        store = ProjectStore(projects_root)
        with (
            patch.object(rooms_api, "PROJECTS_DIRECTORY", projects_root),
            patch.object(project_storage_api, "project_store", store),
            TestClient(
                app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            rooms_saved = client.post(
                "/api/v1/projects/Workflow/rooms",
                json=rooms_payload,
            )
            canonical_created = client.post(
                "/api/v1/projects/Workflow/canonical",
                content=canonical_json_bytes(revision_one),
                headers={"Content-Type": "application/json"},
            )
            canonical_loaded = client.get(
                "/api/v1/projects/Workflow/canonical"
            )
            canonical_advanced = client.post(
                "/api/v1/projects/Workflow/canonical",
                content=canonical_json_bytes(revision_two),
                headers={"Content-Type": "application/json"},
            )
            rooms_loaded = client.get(
                "/api/v1/projects/Workflow/rooms"
            )

    assert rooms_saved.status_code == 200
    assert canonical_created.status_code == 201
    assert canonical_loaded.content == canonical_json_bytes(revision_one)
    assert canonical_advanced.status_code == 201
    assert canonical_advanced.json()["revision"] == 2
    assert rooms_loaded.status_code == 200
    assert rooms_loaded.json()["DrawingName"] == rooms_payload["DrawingName"]
