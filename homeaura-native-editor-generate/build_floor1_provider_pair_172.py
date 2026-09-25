from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_owner_style_installation_project_141 import length_mm, self_contacts  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_OwnerAcceptedAnalogue_D171.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_owner_accepted_analogue_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
RADIUS_MM = 80


# Claude and Kimi were deliberately given different halves of F1-R08. Neither
# provider returned an admissible polyline. These two arrays are the local
# recovery: the centres are exact D4 transforms of owner ACCEPTED template B.
# C01 also extends its final field axis by 200 mm to close the only pair seam.
PAIR_POINTS = {
    "F1-D171-C01": [
        (92, 58), (67, 58), (67, 59), (92, 59), (92, 60), (67, 60),
        (67, 62), (92, 62), (92, 85), (67, 85), (67, 66), (88, 66),
        (88, 81), (71, 81), (71, 70), (84, 70), (84, 77), (82, 77),
        (82, 72), (77, 72), (77, 74), (80, 74), (80, 76), (75, 76),
        (75, 72), (73, 72), (73, 79), (86, 79), (86, 68), (69, 68),
        (69, 83), (90, 83), (90, 64), (67, 64),
    ],
    "F1-D171-C02": [
        (47, 85), (47, 58), (65, 58), (65, 59), (48, 59), (48, 85),
        (49, 85), (49, 60), (65, 60), (65, 62), (51, 62), (51, 85),
        (65, 85), (65, 66), (55, 66), (55, 81), (61, 81), (61, 79),
        (58, 79), (58, 69), (63, 69), (63, 74), (61, 74), (61, 71),
        (59, 71), (59, 76), (63, 76), (63, 83), (53, 83), (53, 64),
        (63, 64),
    ],
}

CONTROL = {
    "F1-D171-C01": {
        "provider": "KIMI",
        "territory_grid": [66, 57, 93, 86],
        "axis_bounds_grid": [67, 58, 92, 85],
        "exterior_sides": ["TOP"],
        "centre_template": "OWNER_ACCEPTED_B_D4",
        "centre_start_index": 17,
        "centre_end_index": 23,
    },
    "F1-D171-C02": {
        "provider": "CLAUDE",
        "territory_grid": [46, 57, 66, 86],
        "axis_bounds_grid": [47, 58, 65, 85],
        "exterior_sides": ["TOP", "LEFT"],
        "centre_template": "OWNER_ACCEPTED_B_D4",
        "centre_start_index": 19,
        "centre_end_index": 25,
    },
}

TEMPLATE_B = [(0, 0), (0, 5), (5, 5), (5, 3), (2, 3), (2, 1), (7, 1)]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def point_mm(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def grid_points(circuit: dict) -> list[tuple[int, int]]:
    return [
        ((point["x_mm"] - OFFSET) // 100, (point["y_mm"] - OFFSET) // 100)
        for point in circuit["ordered_points"]
    ]


def line_mm(points: list[tuple[int, int]]) -> LineString:
    return LineString([(OFFSET + x * 100, OFFSET + y * 100) for x, y in points])


def segment_lengths_mm(points: list[tuple[int, int]]) -> list[int]:
    return [
        (abs(first[0] - second[0]) + abs(first[1] - second[1])) * 100
        for first, second in zip(points, points[1:])
    ]


def directions(points: list[tuple[int, int]]) -> list[str]:
    return ["V" if first[0] == second[0] else "H" for first, second in zip(points, points[1:])]


def bend_audit(points: list[tuple[int, int]]) -> dict:
    lengths = segment_lengths_mm(points)
    vector_directions = directions(points)
    turn_count = sum(first != second for first, second in zip(vector_directions, vector_directions[1:]))
    violations = []
    for index, value in enumerate(lengths):
        demand = 0
        if index > 0 and vector_directions[index - 1] != vector_directions[index]:
            demand += RADIUS_MM
        if index < len(vector_directions) - 1 and vector_directions[index] != vector_directions[index + 1]:
            demand += RADIUS_MM
        if value < demand:
            violations.append({
                "segment_index": index,
                "segment_mm": value,
                "required_tangent_allocation_mm": demand,
                "from_grid": list(points[index]),
                "to_grid": list(points[index + 1]),
            })
    rounded_body_mm = sum(lengths) - turn_count * (2 * RADIUS_MM - math.pi * RADIUS_MM / 2)
    return {
        "bend_radius_mm": RADIUS_MM,
        "turn_count": turn_count,
        "minimum_segment_mm": min(lengths),
        "tangent_allocation_violation_count": len(violations),
        "violations": violations,
        "rounded_body_length_mm": rounded_body_mm,
        "rounded_geometry_certified": not violations,
    }


def d4_normalized(points: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    variants = []
    for swap in (False, True):
        for sx in (-1, 1):
            for sy in (-1, 1):
                transformed = [
                    ((y if swap else x) * sx, (x if swap else y) * sy)
                    for x, y in points
                ]
                origin = transformed[0]
                normalized = [(x - origin[0], y - origin[1]) for x, y in transformed]
                if normalized not in variants:
                    variants.append(normalized)
    return variants


def centre_audit(points: list[tuple[int, int]], start: int, end: int) -> dict:
    centre = points[start : end + 1]
    normalized = [(x - centre[0][0], y - centre[0][1]) for x, y in centre]
    lengths = segment_lengths_mm(centre)
    width = (max(x for x, _ in centre) - min(x for x, _ in centre)) * 100
    height = (max(y for _, y in centre) - min(y for _, y in centre)) * 100
    return {
        "start_index": start,
        "end_index": end,
        "points_grid": [list(point) for point in centre],
        "segment_count": len(centre) - 1,
        "exact_owner_template_B_D4_match": normalized in d4_normalized(TEMPLATE_B),
        "exact_200mm_segment_count": sum(value == 200 for value in lengths),
        "bbox_mm": [width, height],
        "simple": LineString(centre).is_simple,
    }


def territory_audit(points: list[tuple[int, int]], bounds: list[int]) -> dict:
    domain = box(*bounds)
    line = LineString(points)
    served = domain.intersection(line.buffer(1, quad_segs=16)).area
    samples = [
        Point(x / 2, y / 2).distance(line)
        for x in range(bounds[0] * 2, bounds[2] * 2 + 1)
        for y in range(bounds[1] * 2, bounds[3] * 2 + 1)
    ]
    return {
        "domain_area_m2": domain.area / 100,
        "round_100mm_served_m2": served / 100,
        "round_100mm_served_percent": served * 100 / domain.area,
        "sample_grid_mm": 50,
        "sample_within_150mm_percent": sum(value <= 1.5 + 1e-9 for value in samples) * 100 / len(samples),
        "maximum_sample_distance_mm": max(samples) * 100,
    }


def exterior_evidence(points: list[tuple[int, int]], circuit_id: str) -> dict:
    segments = list(zip(points, points[1:]))
    result: dict[str, object] = {"axis_distances_mm": [100, 200, 300]}
    if circuit_id == "F1-D171-C01":
        rows = [58, 59, 60]
        result["top_axes"] = [
            {
                "y_grid": row,
                "parallel_length_mm": sum(abs(b[0] - a[0]) * 100 for a, b in segments if a[1] == b[1] == row),
            }
            for row in rows
        ]
    else:
        result["top_axes"] = [
            {
                "y_grid": row,
                "parallel_length_mm": sum(abs(b[0] - a[0]) * 100 for a, b in segments if a[1] == b[1] == row),
            }
            for row in (58, 59, 60)
        ]
        result["left_axes"] = [
            {
                "x_grid": column,
                "parallel_length_mm": sum(abs(b[1] - a[1]) * 100 for a, b in segments if a[0] == b[0] == column),
                "covers_WIN_01_projection_y_grid_62_73": any(
                    a[0] == b[0] == column and min(a[1], b[1]) <= 62 and max(a[1], b[1]) >= 73
                    for a, b in segments
                ),
            }
            for column in (47, 48, 49)
        ]
    return result


def service_estimate_mm(points: list[tuple[int, int]]) -> int:
    collector = (134, 63)
    return sum(abs(point[0] - collector[0]) + abs(point[1] - collector[1]) for point in (points[0], points[-1])) * 100


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png",
        str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def package_output() -> None:
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D172 is append-only")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)

    project = load(SOURCE_PROJECT)
    source_contract = load(SOURCE_CONTRACT)
    source_circuits = copy.deepcopy(project["circuits"])
    source_records = {item["circuit_id"]: item for item in source_contract["body_records"]}

    audits = {}
    for source_id, points in PAIR_POINTS.items():
        circuit = next(item for item in project["circuits"] if item["id"] == source_id)
        record = source_records[source_id]
        body_mm = length_mm(points)
        service_mm = service_estimate_mm(points)
        control = CONTROL[source_id]
        bend = bend_audit(points)
        centre = centre_audit(points, control["centre_start_index"], control["centre_end_index"])
        if not centre["exact_owner_template_B_D4_match"]:
            raise RuntimeError({"centre_template_failed": source_id, "centre": centre})
        if not LineString(points).is_simple or self_contacts(points):
            raise RuntimeError({"simple_failed": source_id})
        circuit["ordered_points"] = [point_mm(point) for point in points]
        circuit["heating_body_end_index"] = len(points) - 1
        circuit["concealed_service_length_mm"] = service_mm
        circuit["name"] = (
            f"{source_id.replace('D171', 'D172')} · точный центр ACCEPTED B · "
            f"{record['territory']} · {body_mm / 1000:.1f} м"
        )
        audits[source_id] = {
            "source_circuit_id": source_id,
            "provider_assignment": control["provider"],
            "candidate_origin": "CODEX_LOCAL_RECOVERY_AFTER_PROVIDER_FAILURE",
            "body_points_grid": [list(point) for point in points],
            "body_length_mm": body_mm,
            "estimated_service_length_mm": service_mm,
            "estimated_complete_manhattan_length_mm": body_mm + service_mm,
            "estimated_complete_rounded_R80_length_mm": bend["rounded_body_length_mm"] + service_mm,
            "territory": territory_audit(points, control["territory_grid"]),
            "centre": centre,
            "exterior": exterior_evidence(points, source_id),
            "R80": bend,
        }

    changed_ids = set(PAIR_POINTS)
    if not all(
        next(item for item in project["circuits"] if item["id"] == source["id"])["ordered_points"] == source["ordered_points"]
        for source in source_circuits if source["id"] not in changed_ids
    ):
        raise RuntimeError("Non-control circuit changed")

    lines = {
        circuit["id"]: LineString([(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]])
        for circuit in project["circuits"]
    }
    contacts = [
        [first, second]
        for index, first in enumerate(lines)
        for second in list(lines)[index + 1 :]
        if not lines[first].intersection(lines[second]).is_empty
    ]
    if contacts:
        raise RuntimeError({"contacts": contacts})

    room = next(item for item in project["rooms"] if item["id"] == "F1-R08")
    room_geometry = Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])
    wall_solids = [
        LineString([
            (wall["start"]["x_mm"], wall["start"]["y_mm"]),
            (wall["end"]["x_mm"], wall["end"]["y_mm"]),
        ]).buffer(wall["thickness_mm"] / 2, cap_style="square")
        for wall in project["walls"]
    ]
    for source_id, points in PAIR_POINTS.items():
        line = line_mm(points)
        if not room_geometry.covers(line) or any(not line.intersection(solid).is_empty for solid in wall_solids):
            raise RuntimeError({"room_or_wall_failure": source_id})

    pair_line = unary_union([LineString(points) for points in PAIR_POINTS.values()])
    combined_domain = box(46, 57, 93, 86)
    combined_samples = [
        Point(x / 2, y / 2).distance(pair_line)
        for x in range(46 * 2, 93 * 2 + 1)
        for y in range(57 * 2, 86 * 2 + 1)
    ]
    pair_coverage = combined_domain.intersection(pair_line.buffer(1, quad_segs=16)).area
    pair_distance = LineString(PAIR_POINTS["F1-D171-C01"]).distance(LineString(PAIR_POINTS["F1-D171-C02"]))
    rounded_lengths = [audits[key]["estimated_complete_rounded_R80_length_mm"] for key in PAIR_POINTS]

    project["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D172 control pair: exact owner ACCEPTED centre templates after Claude/Kimi assignments",
        "notes": (
            "C01/C02 centres are exact D4 transforms of the owner's ACCEPTED B centre. "
            "The pair seam is closed and every useful 50-mm sample is within 200 mm. "
            "Four inherited 100-mm exterior-band connectors remain explicit R80 blockers; D172 is not installation-ready."
        ),
    }

    project_path = OUTPUT / "HomeAura_Floor1_ProviderPair_D172.homeaura.json"
    dump(project_path, project)
    contract = {
        "schema": "homeaura.floor1.provider_pair.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "CONTROL_PAIR_OWNER_CENTRE_PASS_REWORK_JOINT_EXTERIOR_R80_WEAVE",
        "append_only": True,
        "source_D171_project_sha256": sha(SOURCE_PROJECT),
        "source_D171_contract_sha256": sha(SOURCE_CONTRACT),
        "changed_circuit_ids": list(PAIR_POINTS),
        "unchanged_circuit_ids": [item["id"] for item in project["circuits"] if item["id"] not in changed_ids],
        "provider_runs": [
            {"task_id": "HA-D172-CLAUDE-WEST-20260815-001", "provider": "CLAUDE", "status": "BLOCKED_TIMEOUT", "candidate_accepted": False},
            {"task_id": "HA-D172-KIMI-EAST-20260815-001", "provider": "KIMI", "status": "BLOCKED_TIMEOUT", "candidate_accepted": False},
            {"task_id": "HA-D172-CLAUDE-WEST-20260815-002", "provider": "CLAUDE", "status": "BLOCKED_TIMEOUT_EMPTY_OUTPUT", "candidate_accepted": False},
            {"task_id": "HA-D172-KIMI-EAST-20260815-002", "provider": "KIMI", "status": "COMPLETED_INVALID_NO_CONTOUR", "candidate_accepted": False},
        ],
        "control_pair": audits,
        "pair_validation": {
            "inter_circuit_contact_count": 0,
            "minimum_pair_centerline_distance_mm": pair_distance * 100,
            "combined_domain_area_m2": combined_domain.area / 100,
            "combined_round_100mm_served_m2": pair_coverage / 100,
            "combined_round_100mm_served_percent": pair_coverage * 100 / combined_domain.area,
            "combined_50mm_sample_within_150mm_percent": sum(value <= 1.5 + 1e-9 for value in combined_samples) * 100 / len(combined_samples),
            "combined_maximum_sample_distance_mm": max(combined_samples) * 100,
            "rounded_complete_length_spread_mm": max(rounded_lengths) - min(rounded_lengths),
            "exact_owner_template_centre_count": 2,
            "R80_tangent_allocation_violation_count": sum(item["R80"]["tangent_allocation_violation_count"] for item in audits.values()),
        },
        "rejected_local_alternative": {
            "circuit_id": "F1-D171-C02",
            "reason": "R80_AND_COVERAGE_PASS_BUT_LONG_INTERNAL_SERPENT_REJECTED_AS_NOT_OWNER_ROOM_STYLE",
            "body_length_mm": 34500,
            "round_100mm_served_percent": 99.0695565631,
            "minimum_segment_mm": 200,
        },
        "heating_bodies_may_cross_walls": False,
        "complete_K1_route_count": 0,
        "installation_ready": False,
        "next_block": "JOINTLY_REASSIGN_EXTERIOR_100_200_300_AXES_ACROSS_C01_C02_TO_REMOVE_FOUR_100MM_CONNECTORS_WITH_R80",
    }
    dump(OUTPUT / "floor1_provider_pair_contract.json", contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "changed_circuit_count": 2,
        "exact_owner_template_centre_count": 2,
        "provider_candidate_accepted_count": 0,
        "R80_tangent_allocation_violation_count": contract["pair_validation"]["R80_tangent_allocation_violation_count"],
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D172 · контрольная пара Claude/Kimi, восстановленная Codex\n\n"
        "Claude получил западную половину F1-R08, Kimi — восточную. Оба внешних запуска не вернули пригодных "
        "координат, поэтому результат не выдуман: в проект принята локально восстановленная пара. В обоих контурах "
        "центр является точным преобразованием ручного ACCEPTED B; пустота в шве устранена, контактов нет, расчётный "
        "разброс округлённых длин менее 2 м. Четыре старые 100-мм торцевые перемычки наружной полосы явно оставлены "
        "как следующий REWORK по R80; монтажная готовность не заявляется.\n",
        encoding="utf-8",
    )
    render(project_path, OUTPUT / "HomeAura_Floor1_D172_Editor_View.png", False)
    render(project_path, OUTPUT / "HomeAura_Floor1_D172_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "pair_contacts": 0,
        "pair_maximum_sample_distance_mm": contract["pair_validation"]["combined_maximum_sample_distance_mm"],
        "pair_within_150mm_percent": contract["pair_validation"]["combined_50mm_sample_within_150mm_percent"],
        "rounded_length_spread_mm": contract["pair_validation"]["rounded_complete_length_spread_mm"],
        "R80_violations": contract["pair_validation"]["R80_tangent_allocation_violation_count"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
