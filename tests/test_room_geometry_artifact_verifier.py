from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.verify_room_geometry_artifact import (
    EXIT_INVALID_INPUT,
    EXIT_NOT_READY,
    EXIT_READY,
    assess_artifact,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_room_geometry_artifact.py"
def ready_document() -> dict:
    return {
        "FormatVersion": "1.1", "ParserVersion": "test", "GeneratedAtUtc": "2026-01-01T00:00:00Z",
        "DrawingName": "ready.dwg", "DrawingFullPath": "C:\\private\\ready.dwg", "FoundMarkers": 1,
        "FoundBoundaryCandidates": 1, "ValidBoundaryCandidates": 1,
        "Rooms": [{"SourceHandle": "R1", "SourceLayer": "ROOM", "Position": {"X": 0, "Y": 0, "Z": 0},
                   "Code": "1", "Name": "Room", "Boundary": {"SourceHandle": "B1", "SourceObjectType": "LWPOLYLINE",
                   "SourceLayer": "ROOM", "IsClosed": True, "DrawingUnits": "Meters", "GeometrySource": "AutoCAD.ModelSpace.Polyline",
                   "Diagnostics": {"IsSupported": True, "IsValid": True}}}]}


def write_document(tmp_path: Path, document: dict) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "rooms.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def legacy_document() -> dict:
    document = ready_document()
    document["FormatVersion"] = "1.0"
    document["FoundBoundaryCandidates"] = 0
    document["ValidBoundaryCandidates"] = 0
    document["Rooms"][0].pop("Boundary")
    return document


def findings(path: Path) -> list[str]:
    return assess_artifact(path)["findings"]


def test_ready_artifact_and_cli_exit_code(tmp_path: Path) -> None:
    path = write_document(tmp_path, ready_document())
    assert assess_artifact(path)["status"] == "READY"
    run = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
    assert run.returncode == EXIT_READY
    assert json.loads(run.stdout) == {"findings": [], "room_count": 1, "status": "READY"}


def test_legacy_artifact_is_not_ready_and_never_leaks_path(
    tmp_path: Path,
) -> None:
    path = write_document(tmp_path, legacy_document())
    result = assess_artifact(path)
    assert result["status"] == "NOT_READY"
    assert result["findings"] == ["FORMAT_LEGACY_1_0", "ROOM_1_BOUNDARY_MISSING"]
    assert "DrawingFullPath" not in json.dumps(result)
    assert "C:\\private" not in json.dumps(result)
    run = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == EXIT_NOT_READY
    assert json.loads(run.stdout)["status"] == "NOT_READY"


def test_boundary_findings_and_counter_mismatch(tmp_path: Path) -> None:
    cases = [("missing", lambda d: d["Rooms"][0].pop("Boundary"), "ROOM_1_BOUNDARY_MISSING"),
             ("unsupported", lambda d: d["Rooms"][0]["Boundary"]["Diagnostics"].update(IsSupported=False), "ROOM_1_BOUNDARY_UNSUPPORTED"),
             ("invalid", lambda d: d["Rooms"][0]["Boundary"]["Diagnostics"].update(IsValid=False), "ROOM_1_BOUNDARY_INVALID"),
             ("open", lambda d: d["Rooms"][0]["Boundary"].update(IsClosed=False), "ROOM_1_BOUNDARY_OPEN")]
    for name, mutate, expected in cases:
        document = ready_document(); mutate(document)
        assert expected in findings(write_document(tmp_path / name, document))
    document = ready_document(); document["FoundBoundaryCandidates"] = 0
    assert "BOUNDARY_COUNTERS_INCONSISTENT" in findings(write_document(tmp_path / "counters", document))
    document = ready_document()
    document["Rooms"][0]["Boundary"]["Diagnostics"]["IsSupported"] = "yes"
    assert "ROOM_1_BOUNDARY_UNSUPPORTED" in findings(
        write_document(tmp_path / "coerced-supported", document)
    )
    document = ready_document()
    document["Rooms"][0]["Boundary"]["Diagnostics"]["IsValid"] = "yes"
    assert "ROOM_1_BOUNDARY_INVALID" in findings(
        write_document(tmp_path / "coerced-valid", document)
    )


def test_missing_rooms_format_and_drawing_name(tmp_path: Path) -> None:
    document = ready_document(); document["Rooms"] = []
    result = assess_artifact(write_document(tmp_path, document), "other.dwg")
    assert result["findings"] == ["ROOMS_MISSING", "DRAWING_NAME_MISMATCH"]
    document = ready_document(); document["FormatVersion"] = "1.0"
    assert "FORMAT_LEGACY_1_0" in findings(write_document(tmp_path / "legacy", document))


def test_malformed_oversized_and_strict_json_are_invalid(tmp_path: Path) -> None:
    bad_cases = {"malformed": b"{", "utf8": b"\xff", "root": b"[]", "duplicate": b'{"a": 1, "a": 2}', "nonfinite": b'{"x": NaN}'}
    for name, payload in bad_cases.items():
        path = tmp_path / name; path.write_bytes(payload)
        assert assess_artifact(path)["status"] == "INVALID"
    oversized = tmp_path / "oversized"; oversized.write_bytes(b" " * (10 * 1024 * 1024 + 1))
    assert assess_artifact(oversized)["status"] == "INVALID"
    run = subprocess.run([sys.executable, str(SCRIPT), str(oversized)], capture_output=True, text=True, check=False)
    assert run.returncode == EXIT_INVALID_INPUT


def test_schema_invalid_determinism_and_no_write(tmp_path: Path) -> None:
    document = ready_document(); document["Rooms"][0].pop("Code")
    path = write_document(tmp_path, document)
    before = path.read_bytes()
    first, second = assess_artifact(path), assess_artifact(path)
    assert first == second == {"findings": ["INVALID_INPUT"], "reason": "artifact does not satisfy the room report schema", "status": "INVALID"}
    assert path.read_bytes() == before
