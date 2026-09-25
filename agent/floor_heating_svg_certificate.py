"""Independent certificate for the exact HA-FH-VIS-001-v2 artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from pathlib import Path
from typing import Any


EXPECTED_SVG_SHA256 = "cce0a1d361ba7135d77c53dea3cae402475a7ecba73f3e0a5d2f3230c2452d18"
EXPECTED_GEOMETRY_DIGEST = "c32392934059e572b866b47adbc511415748560868177c38a5c7b0ea3885c287"
SOURCE_NAMES = (
    "floor_heating_layout.svg",
    "floor_heating_layout.html",
    "floor_heating_layout_report.json",
    "floor_heating_layout_geometry.json",
)
REQUIRED_CAPTURE_NAMES = (
    "full-layout.png",
    "room-close-up.png",
    "collector-close-up.png",
    "central-turn-close-up.png",
    "pipes-only.png",
    "engineering-debug.png",
)
Point = tuple[int, int]
Segment = tuple[Point, Point]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _segments(points: list[Point]) -> list[Segment]:
    return list(zip(points, points[1:]))


def _length(points: list[Point]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in _segments(points))


def _cross(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, point: Point) -> bool:
    return (
        _cross(a, b, point) == 0
        and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _intersects(first: Segment, second: Segment) -> bool:
    a, b = first
    c, d = second
    first_values = (_cross(a, b, c), _cross(a, b, d))
    second_values = (_cross(c, d, a), _cross(c, d, b))
    if first_values[0] == first_values[1] == second_values[0] == second_values[1] == 0:
        return not (
            max(a[0], b[0]) < min(c[0], d[0])
            or max(c[0], d[0]) < min(a[0], b[0])
            or max(a[1], b[1]) < min(c[1], d[1])
            or max(c[1], d[1]) < min(a[1], b[1])
        )
    return (
        (first_values[0] == 0 or first_values[1] == 0 or (first_values[0] < 0) != (first_values[1] < 0))
        and (second_values[0] == 0 or second_values[1] == 0 or (second_values[0] < 0) != (second_values[1] < 0))
    )


def _point_inside(point: Point, polygon: list[Point]) -> bool:
    for edge in _segments(polygon):
        if _on_segment(*edge, point):
            return True
    x, y = point
    inside = False
    for first, second in _segments(polygon):
        if (first[1] > y) != (second[1] > y):
            cross_x = (second[0] - first[0]) * (y - first[1]) / (second[1] - first[1]) + first[0]
            if x < cross_x:
                inside = not inside
    return inside


def _self_intersection_count(points: list[Point]) -> int:
    segments = _segments(points)
    return sum(
        _intersects(segments[first], segments[second])
        for first in range(len(segments))
        for second in range(first + 2, len(segments))
    )


def _graph_counts(points: list[Point]) -> tuple[int, int, int]:
    neighbours: dict[Point, set[Point]] = {}
    for first, second in _segments(points):
        neighbours.setdefault(first, set()).add(second)
        neighbours.setdefault(second, set()).add(first)
    remaining = set(neighbours)
    components = 0
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            for neighbour in neighbours[stack.pop()]:
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    stack.append(neighbour)
    endpoints = sum(len(values) == 1 for values in neighbours.values())
    branches = sum(len(values) > 2 for values in neighbours.values())
    return components, endpoints, branches


def _parse_svg_path(value: str) -> list[Point]:
    commands = re.findall(r"([ML])\s+(-?\d+)\s+(-?\d+)", value)
    if not commands or commands[0][0] != "M" or any(command != "L" for command, _, _ in commands[1:]):
        raise ValueError("SVG path must contain exactly one M followed by ordered L commands")
    return [(int(x), int(y)) for _, x, y in commands]


def _line_distance(first: Segment, second: Segment) -> float | None:
    (a, b), (c, d) = first, second
    if a[1] == b[1] and c[1] == d[1]:
        if max(min(a[0], b[0]), min(c[0], d[0])) >= min(max(a[0], b[0]), max(c[0], d[0])):
            return None
        return float(abs(a[1] - c[1]))
    if a[0] == b[0] and c[0] == d[0]:
        if max(min(a[1], b[1]), min(c[1], d[1])) >= min(max(a[1], b[1]), max(c[1], d[1])):
            return None
        return float(abs(a[0] - c[0]))
    return None


def _collinear_overlap_length(reference: Segment, candidate: Segment) -> int:
    (a, b), (c, d) = reference, candidate
    if a[1] == b[1] == c[1] == d[1]:
        return max(0, min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0])))
    if a[0] == b[0] == c[0] == d[0]:
        return max(0, min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1])))
    return 0


def _point(value: dict[str, int]) -> Point:
    return value["x_mm"], value["y_mm"]


def _spacing_certificate(
    circuits: list[dict[str, Any]],
    perimeter_band_depth_mm: int,
) -> dict[str, Any]:
    expected_references = {
        f"{side}-track-{track}-to-{track + 1}"
        for side in ("bottom", "top", "left", "right")
        for track in (1, 2, 3)
    }
    records: list[dict[str, Any]] = []
    route_completeness: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    for circuit in circuits:
        points = [_point(value) for value in circuit["ordered_points"]]
        pipe_segments = _segments(points)
        roles: list[str | None] = []
        for first, second in pipe_segments:
            length = abs(first[0] - second[0]) + abs(first[1] - second[1])
            roles.append(
                None
                if length <= 400
                else "OUTER_WALL_BAND"
                if first[1] == second[1]
                and max(first[1], second[1]) <= perimeter_band_depth_mm
                else "FIELD"
            )
        for segment_index in range(len(roles) - 1):
            first_role = roles[segment_index]
            second_role = roles[segment_index + 1]
            if first_role is None or second_role is None or first_role == second_role:
                continue
            connected = pipe_segments[segment_index][1] == pipe_segments[segment_index + 1][0]
            transitions.append({
                "route_id": circuit["route_id"],
                "first_segment_index": segment_index,
                "second_segment_index": segment_index + 1,
                "from_role": first_role,
                "to_role": second_role,
                "shared_point": {
                    "x_mm": pipe_segments[segment_index][1][0],
                    "y_mm": pipe_segments[segment_index][1][1],
                },
                "same_canonical_route": True,
                "connected_without_gap": connected,
                "status": "PASS" if connected else "FAIL",
            })
        actual_references = {value["reference"] for value in circuit["spacing_segments"]}
        route_completeness.append({
            "route_id": circuit["route_id"],
            "expected_reference_count": 12,
            "actual_reference_count": len(actual_references),
            "missing_references": sorted(expected_references - actual_references),
            "unexpected_references": sorted(actual_references - expected_references),
            "complete": actual_references == expected_references,
        })
        for sample in circuit["spacing_segments"]:
            first = (_point(sample["first_start"]), _point(sample["first_end"]))
            second = (_point(sample["second_start"]), _point(sample["second_end"]))
            observed = _line_distance(first, second)
            first_matches = [
                {"segment_index": index, "overlap_length_mm": _collinear_overlap_length(first, segment)}
                for index, segment in enumerate(pipe_segments)
                if _collinear_overlap_length(first, segment) > 0
            ]
            second_matches = [
                {"segment_index": index, "overlap_length_mm": _collinear_overlap_length(second, segment)}
                for index, segment in enumerate(pipe_segments)
                if _collinear_overlap_length(second, segment) > 0
            ]
            requested = sample["spacing_mm"]
            deviation = None if observed is None else observed - requested
            passed = (
                observed is not None
                and abs(deviation or 0.0) <= 1.0
                and bool(first_matches)
                and bool(second_matches)
            )
            records.append({
                "route_id": circuit["route_id"],
                "reference": sample["reference"],
                "zone_role": sample["zone_role"],
                "requested_spacing_mm": requested,
                "observed_spacing_mm": observed,
                "deviation_mm": deviation,
                "tolerance_mm": 1.0,
                "first_line_pipe_matches": first_matches,
                "second_line_pipe_matches": second_matches,
                "status": "PASS" if passed else "FAIL",
            })
    perimeter = [value for value in records if value["zone_role"] == "OUTER_WALL_BAND"]
    field = [value for value in records if value["zone_role"] == "FIELD"]
    complete = all(value["complete"] for value in route_completeness)
    passed = (
        complete
        and bool(transitions)
        and all(value["status"] == "PASS" for value in records)
        and all(value["status"] == "PASS" for value in transitions)
    )
    return {
        "basis": "ALL_DECLARED_APPLICABLE_TRACK_PAIRS_FROM_ACCEPTED_ROUTE_OUTPUT",
        "completeness_contract": "Each four-track route must expose bottom/top/left/right pairs for transitions 1-2, 2-3 and 3-4.",
        "route_completeness": route_completeness,
        "applicable_pair_count": len(records),
        "perimeter_pair_count": len(perimeter),
        "field_pair_count": len(field),
        "perimeter_observed_minimum_mm": min(value["observed_spacing_mm"] for value in perimeter),
        "perimeter_observed_maximum_mm": max(value["observed_spacing_mm"] for value in perimeter),
        "field_observed_minimum_mm": min(value["observed_spacing_mm"] for value in field),
        "field_observed_maximum_mm": max(value["observed_spacing_mm"] for value in field),
        "transition_count": len(transitions),
        "transitions": transitions,
        "records": records,
        "status": "PASS" if passed else "FAIL",
    }


def certify_exact_v2(source_directory: Path) -> dict[str, Any]:
    paths = {name: source_directory / name for name in SOURCE_NAMES}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing exact v2 artifacts: " + ", ".join(missing))
    source_hashes = {name: _sha256(path) for name, path in paths.items()}
    if source_hashes["floor_heating_layout.svg"] != EXPECTED_SVG_SHA256:
        raise ValueError("BLOCKED_VISUAL_ARTIFACT_IDENTITY_MISMATCH: SVG SHA-256")
    geometry = json.loads(paths["floor_heating_layout_geometry.json"].read_text(encoding="utf-8"))
    report = json.loads(paths["floor_heating_layout_report.json"].read_text(encoding="utf-8"))
    if geometry.get("geometry_digest") != EXPECTED_GEOMETRY_DIGEST or report.get("geometry_digest") != EXPECTED_GEOMETRY_DIGEST:
        raise ValueError("BLOCKED_VISUAL_ARTIFACT_IDENTITY_MISMATCH: geometry digest")
    svg_root = ET.fromstring(paths["floor_heating_layout.svg"].read_text(encoding="utf-8"))
    svg_by_id = {element.get("id"): element for element in svg_root.iter() if element.get("id")}
    boundary = [_point(value) for value in geometry["room_boundary"]["points"]]
    exclusions = [[_point(value) for value in zone["points"]] for zone in geometry["exclusion_zones"]]
    circuit_certificates: list[dict[str, Any]] = []
    parsed_routes: list[tuple[str, list[Point]]] = []
    failures: list[str] = []
    for index, circuit in enumerate(geometry["circuits"], 1):
        route_id = circuit["route_id"]
        path_id = f"CIRCUIT_ROUTE_{index}"
        element = svg_by_id.get(path_id)
        if element is None:
            failures.append(f"{route_id}:SVG_PATH_MISSING")
            continue
        source_points = [_point(value) for value in circuit["ordered_points"]]
        rendered_points = _parse_svg_path(element.attrib["d"])
        components, endpoints, branches = _graph_counts(source_points)
        self_intersections = _self_intersection_count(source_points)
        boundary_violations = sum(not _point_inside(point, boundary) for point in source_points)
        exclusion_intersections = sum(
            _intersects(pipe, edge) or _point_inside(pipe[0], exclusion) or _point_inside(pipe[1], exclusion)
            for pipe in _segments(source_points)
            for exclusion in exclusions
            for edge in _segments(exclusion)
        )
        source_length = _length(source_points)
        rendered_length = _length(rendered_points)
        supply = _point(circuit["collector_supply_point"])
        return_point = _point(circuit["collector_return_point"])
        checks = {
            "point_order_exact": rendered_points == source_points,
            "one_connected_component": components == 1,
            "two_endpoints": endpoints == 2,
            "zero_branches": branches == 0,
            "zero_self_intersections": self_intersections == 0,
            "zero_boundary_violations": boundary_violations == 0,
            "zero_exclusion_intersections": exclusion_intersections == 0,
            "supply_binding": source_points[0] == supply,
            "return_binding": source_points[-1] == return_point,
            "ports_distinct": supply != return_point,
            "length_delta_within_1mm": abs(source_length - rendered_length) <= 1.0,
            "length_40_to_80m": 40_000 <= source_length <= 80_000,
        }
        local_failures = [name for name, passed in checks.items() if not passed]
        failures.extend(f"{route_id}:{name}" for name in local_failures)
        circuit_certificates.append({
            "route_id": route_id,
            "svg_path_id": path_id,
            "ordered_source_point_count": len(source_points),
            "rendered_command_count": len(rendered_points),
            "rendered_segment_count": len(rendered_points) - 1,
            "start_point": {"x_mm": source_points[0][0], "y_mm": source_points[0][1]},
            "end_point": {"x_mm": source_points[-1][0], "y_mm": source_points[-1][1]},
            "assigned_supply_port": circuit["collector_supply_point"],
            "assigned_return_port": circuit["collector_return_point"],
            "endpoint_count": endpoints,
            "connected_component_count": components,
            "branch_node_count": branches,
            "non_adjacent_self_intersection_count": self_intersections,
            "room_boundary_violation_count": boundary_violations,
            "exclusion_intersection_count": exclusion_intersections,
            "canonical_length_mm": source_length,
            "rendered_length_mm": rendered_length,
            "length_delta_mm": abs(source_length - rendered_length),
            "checks": checks,
            "valid": not local_failures,
        })
        parsed_routes.append((route_id, source_points))

    crossing_records: list[dict[str, Any]] = []
    for first_index, (first_id, first_points) in enumerate(parsed_routes):
        for second_id, second_points in parsed_routes[first_index + 1:]:
            for first_segment, first in enumerate(_segments(first_points)):
                for second_segment, second in enumerate(_segments(second_points)):
                    if _intersects(first, second):
                        crossing_records.append({
                            "first_route_id": first_id,
                            "first_segment_index": first_segment,
                            "second_route_id": second_id,
                            "second_segment_index": second_segment,
                        })
    if crossing_records:
        failures.append("INTER_CIRCUIT_CROSSINGS")

    port_owners: dict[Point, list[str]] = {}
    port_mapping: list[dict[str, Any]] = []
    for certificate in circuit_certificates:
        supply = _point(certificate["assigned_supply_port"])
        return_point = _point(certificate["assigned_return_port"])
        port_owners.setdefault(supply, []).append(certificate["route_id"] + ":SUPPLY")
        port_owners.setdefault(return_point, []).append(certificate["route_id"] + ":RETURN")
        port_mapping.append({
            "route_id": certificate["route_id"],
            "supply_port": certificate["assigned_supply_port"],
            "return_port": certificate["assigned_return_port"],
            "supply_unique": True,
            "return_unique": True,
            "direction_source": "ordered canonical geometry",
        })
    duplicate_ports = {
        f"{point[0]},{point[1]}": owners
        for point, owners in port_owners.items()
        if len(owners) != 1
    }
    if duplicate_ports:
        failures.append("DUPLICATE_COLLECTOR_PORT_OWNERSHIP")
    spacing = _spacing_certificate(
        geometry["circuits"],
        geometry["perimeter_band_depth_mm"],
    )
    if spacing["status"] != "PASS":
        failures.append("EXHAUSTIVE_SPACING_FAILED")

    certificate = {
        "certificate_version": "HA-FH-VIS-002/1.0",
        "artifact_identity": {
            "source_directory": str(source_directory.resolve()),
            "source_hashes": source_hashes,
            "expected_svg_sha256": EXPECTED_SVG_SHA256,
            "expected_geometry_digest": EXPECTED_GEOMETRY_DIGEST,
            "geometry_digest": geometry["geometry_digest"],
            "status": "PASS",
        },
        "topology": {
            "circuits": circuit_certificates,
            "inter_circuit_crossing_count": len(crossing_records),
            "inter_circuit_crossings": crossing_records,
            "status": "PASS" if all(value["valid"] for value in circuit_certificates) and not crossing_records else "FAIL",
        },
        "spacing": spacing,
        "collector": {
            "mapping": port_mapping,
            "duplicate_port_ownership": duplicate_ports,
            "status": "PASS" if not duplicate_ports and len(port_mapping) == len(geometry["circuits"]) else "FAIL",
        },
        "coverage_disclosure": {
            "coverage_ratio": report["coverage"]["coverage_ratio"],
            "full_coverage_claimed": report["coverage"]["full_coverage_claimed"],
            "estimated_uncovered_area_mm2": report["coverage"]["estimated_uncovered_area_mm2"],
            "unresolved_region_geometry_available": report["coverage"]["unresolved_region_geometry_available"],
            "installation_ready_whole_room_plan": False,
            "label": "PARTIAL-COVERAGE GEOMETRY FIXTURE",
        },
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }
    certificate["certificate_digest"] = _canonical_digest(certificate)
    return certificate


def build_review_manifest(
    source_directory: Path,
    review_directory: Path,
    certificate: dict[str, Any],
) -> dict[str, Any]:
    artifacts = sorted(
        path for path in review_directory.iterdir()
        if path.is_file() and path.name != "review_manifest.json"
    )
    manifest = {
        "manifest_version": "HA-FH-VIS-002/1.0",
        "source_directory": str(source_directory.resolve()),
        "source_svg_sha256": _sha256(source_directory / "floor_heating_layout.svg"),
        "source_geometry_digest": certificate["artifact_identity"]["geometry_digest"],
        "review_artifacts": [
            {"name": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in artifacts
        ],
        "certificate_status": certificate["status"],
    }
    manifest["manifest_digest"] = _canonical_digest(manifest)
    return manifest


def _write_json_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite review evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def capture_git_status(repository: Path) -> dict[str, Any]:
    def run(*arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.stdout.rstrip("\n")

    status = subprocess.run(
        [
            "git", "-C", str(repository), "status", "--porcelain=v1", "-z",
            "--untracked-files=all", "--ignored=matching",
        ],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8", errors="strict")
    entries = [value for value in status.split("\0") if value]
    return {
        "repository": str(repository.resolve()),
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "status_porcelain_v1_entries": entries,
        "status_entry_count": len(entries),
        "status_digest": _canonical_digest(entries),
    }


def prepare_review_bundle(
    source_directory: Path,
    build_directory: Path,
    repositories: list[Path],
) -> dict[str, Any]:
    if build_directory.exists():
        raise FileExistsError(f"review build target already exists: {build_directory}")
    certificate = certify_exact_v2(source_directory)
    if certificate["status"] != "PASS":
        raise ValueError("REWORK_SOURCE_GEOMETRY")
    build_directory.mkdir(parents=True)
    _write_json_new(build_directory / "exhaustive_geometry_certificate.json", certificate)
    _write_json_new(
        build_directory / "git_status_baseline.json",
        {"repositories": [capture_git_status(repository) for repository in repositories]},
    )
    return certificate


def finalize_review_bundle(
    source_directory: Path,
    build_directory: Path,
    final_directory: Path,
    repositories: list[Path],
) -> dict[str, Any]:
    if final_directory.exists():
        raise FileExistsError(f"final review bundle already exists: {final_directory}")
    if not build_directory.is_dir():
        raise FileNotFoundError(f"review build directory is missing: {build_directory}")
    certificate = json.loads(
        (build_directory / "exhaustive_geometry_certificate.json").read_text(encoding="utf-8")
    )
    if certificate["status"] != "PASS":
        raise ValueError("REWORK_SOURCE_GEOMETRY")
    for name in REQUIRED_CAPTURE_NAMES:
        path = build_directory / name
        if not path.is_file() or path.stat().st_size < 100 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"BLOCKED_RENDER_CAPTURE: {name}")
    provenance = json.loads((build_directory / "capture_provenance.json").read_text(encoding="utf-8"))
    if provenance.get("source_svg_sha256") != EXPECTED_SVG_SHA256:
        raise ValueError("BLOCKED_VISUAL_ARTIFACT_IDENTITY_MISMATCH: capture provenance")
    source_svg_hash = _sha256(source_directory / "floor_heating_layout.svg")
    if source_svg_hash != EXPECTED_SVG_SHA256:
        raise ValueError("BLOCKED_VISUAL_ARTIFACT_IDENTITY_MISMATCH: source changed during capture")
    final_directory.parent.mkdir(parents=True, exist_ok=True)
    os.replace(build_directory, final_directory)
    _write_json_new(
        final_directory / "git_status_final.json",
        {"repositories": [capture_git_status(repository) for repository in repositories]},
    )
    manifest = build_review_manifest(source_directory, final_directory, certificate)
    _write_json_new(final_directory / "review_manifest.json", manifest)
    return manifest


__all__ = [
    "EXPECTED_GEOMETRY_DIGEST",
    "EXPECTED_SVG_SHA256",
    "REQUIRED_CAPTURE_NAMES",
    "build_review_manifest",
    "capture_git_status",
    "certify_exact_v2",
    "finalize_review_bundle",
    "prepare_review_bundle",
]
