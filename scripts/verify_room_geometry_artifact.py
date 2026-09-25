#!/usr/bin/env python3
"""Read-only readiness verifier for exported HomeAura ``rooms.json`` evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.rooms_api import MAX_ROOMS_JSON_BYTES, RoomExportReport

EXIT_READY = 0
EXIT_NOT_READY = 1
EXIT_INVALID_INPUT = 2


class ArtifactInputError(ValueError):
    """An artifact cannot be safely interpreted as a rooms export."""


def _reject_constant(value: str) -> None:
    raise ArtifactInputError(f"non-finite JSON constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactInputError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _read_bounded(path: Path) -> bytes:
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_ROOMS_JSON_BYTES + 1)
    except OSError as exc:
        raise ArtifactInputError("artifact cannot be read") from exc
    if len(data) > MAX_ROOMS_JSON_BYTES:
        raise ArtifactInputError("artifact exceeds 10 MiB limit")
    return data


def _parse_artifact(path: Path) -> dict[str, Any]:
    try:
        text = _read_bounded(path).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactInputError("artifact is not valid UTF-8") from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ArtifactInputError, RecursionError) as exc:
        raise ArtifactInputError("artifact is not valid strict JSON") from exc
    if not isinstance(document, dict):
        raise ArtifactInputError("artifact root is not an object")
    try:
        RoomExportReport.model_validate(document)
    except ValueError as exc:
        raise ArtifactInputError("artifact does not satisfy the room report schema") from exc
    return document


def _boundary_findings(room: dict[str, Any], index: int) -> list[str]:
    prefix = f"ROOM_{index + 1}_"
    boundary = room.get("Boundary")
    if not isinstance(boundary, dict):
        return [prefix + "BOUNDARY_MISSING"]

    diagnostics = boundary.get("Diagnostics")
    if (
        not isinstance(diagnostics, dict)
        or diagnostics.get("IsSupported") is not True
    ):
        return [prefix + "BOUNDARY_UNSUPPORTED"]
    if diagnostics.get("IsValid") is not True:
        return [prefix + "BOUNDARY_INVALID"]
    if boundary.get("IsClosed") is not True:
        return [prefix + "BOUNDARY_OPEN"]
    return []


def assess_artifact(path: Path, expected_drawing_name: str | None = None) -> dict[str, Any]:
    """Return a deterministic, path-free readiness result for ``path``."""
    try:
        document = _parse_artifact(path)
    except ArtifactInputError as exc:
        return {"findings": ["INVALID_INPUT"], "reason": str(exc), "status": "INVALID"}

    findings: list[str] = []
    format_version = document["FormatVersion"]
    if format_version == "1.0":
        findings.append("FORMAT_LEGACY_1_0")
    elif format_version != "1.1":
        findings.append("FORMAT_UNSUPPORTED")

    rooms = document.get("Rooms", [])
    if not rooms:
        findings.append("ROOMS_MISSING")
    else:
        for index, room in enumerate(rooms):
            findings.extend(_boundary_findings(room, index))

    found = document.get("FoundBoundaryCandidates", 0)
    valid = document.get("ValidBoundaryCandidates", 0)
    exported_valid = sum(
        isinstance(room.get("Boundary"), dict)
        and room["Boundary"].get("IsClosed") is True
        and isinstance(room["Boundary"].get("Diagnostics"), dict)
        and room["Boundary"]["Diagnostics"].get("IsSupported") is True
        and room["Boundary"]["Diagnostics"].get("IsValid") is True
        for room in rooms
    )
    if (
        not isinstance(found, int)
        or isinstance(found, bool)
        or not isinstance(valid, int)
        or isinstance(valid, bool)
        or found < valid
        or valid < exported_valid
    ):
        findings.append("BOUNDARY_COUNTERS_INCONSISTENT")

    if expected_drawing_name is not None and document["DrawingName"] != expected_drawing_name:
        findings.append("DRAWING_NAME_MISMATCH")

    return {
        "findings": findings,
        "room_count": len(rooms),
        "status": "READY" if not findings else "NOT_READY",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="path to rooms.json")
    parser.add_argument("--expected-drawing-name")
    args = parser.parse_args(argv)
    result = assess_artifact(args.artifact, args.expected_drawing_name)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return {
        "READY": EXIT_READY,
        "NOT_READY": EXIT_NOT_READY,
        "INVALID": EXIT_INVALID_INPUT,
    }[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
