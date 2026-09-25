import json
from pathlib import Path

from agent.ufh_threshold_access import check_threshold_access


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "dev" / "ufh_real_plan" / "room_threshold_access.json"


def rect(width, height):
    return [(0, 0), (width, 0), (width, height), (0, height)]


def test_two_independent_paths_reach_a_wide_threshold():
    room = rect(6000, 4000)
    threshold = [[2000, 0], [3000, 0]]
    endpoints = [[3000, 3000], [1000, 3000]]
    result = check_threshold_access(room, threshold, endpoints)
    assert result.status == "TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID"
    assert result.two_independent_paths_valid is True
    assert result.endpoint_to_threshold_path_valid is True
    assert result.minimum_pair_separation_mm >= result.required_pair_separation_mm
    assert result.wall_clearance_min_mm >= 100.0
    # Geometry alone never authorizes the passage or the manifold.
    assert result.door_passage_authorized == "UNVERIFIED"
    assert result.manifold_connected == "UNVERIFIED"


def test_narrow_room_cannot_provide_two_independent_paths():
    room = rect(800, 3000)
    threshold = [[300, 0], [500, 0]]
    endpoints = [[400, 2500], [400, 1500]]
    result = check_threshold_access(room, threshold, endpoints)
    assert result.status != "TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID"
    assert result.two_independent_paths_valid is False


def test_invalid_room_boundary_is_rejected_fail_closed():
    room = [(0, 0), (1000, 1000), (1000, 0), (0, 1000)]
    result = check_threshold_access(room, [[200, 0], [400, 0]], [[500, 500], [600, 600]])
    assert result.status in {"GEOMETRY_INVALID", "WALL_OFFSET_EXCEEDS_ROOM", "THRESHOLD_UNREACHABLE"}
    assert result.two_independent_paths_valid is False
    assert result.manifold_connected == "UNVERIFIED"


def test_threshold_access_artifact_keeps_authority_unverified():
    if not ARTIFACT.is_file():
        return
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["rooms_total"] == len(payload["rooms"])
    assert payload["statuses"]["DOOR_PASSAGE_AUTHORIZED"] == "UNVERIFIED"
    assert payload["statuses"]["MANIFOLD_CONNECTED"] == "UNVERIFIED"
    for row in payload["rooms"]:
        assert row["status"]
        assert row.get("door_passage_authorized") == "UNVERIFIED"
        assert row.get("manifold_connected") == "UNVERIFIED"
    valid = [
        row for row in payload["rooms"]
        if row["status"] == "TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID"
    ]
    assert len(valid) == payload["two_independent_paths_geometric_valid"]
    # Every validated room must report its own source threshold and clearance.
    for row in valid:
        assert row["threshold"]["room_threshold_mm"]
        assert row["wall_clearance_min_mm"] >= 99.0
        assert row["minimum_pair_separation_mm"] >= row["required_pair_separation_mm"]
