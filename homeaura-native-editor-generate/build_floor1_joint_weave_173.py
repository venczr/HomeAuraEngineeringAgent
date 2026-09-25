from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_floor1_provider_pair_172 as d172  # noqa: E402
from build_owner_style_installation_project_141 import length_mm, self_contacts  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_ProviderPair_D172.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_provider_pair_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_JOINT_WEAVE_173"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_JOINT_WEAVE_173.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000


# One room is solved as one ensemble.  The three 100-mm exterior passes are
# shared by two circuits; neither circuit closes adjacent passes with a 100-mm
# U-turn.  Beyond the exterior band the two axes are at least 200 mm apart.
PAIR_POINTS = {
    "F1-D171-C02": [
        (92, 58), (47, 58), (47, 85), (49, 85), (49, 60), (90, 60),
        (90, 62), (65, 62), (51, 62), (51, 85), (65, 85), (65, 66),
        (55, 66), (55, 81), (61, 81), (61, 79), (56, 79), (56, 76),
        (61, 76), (61, 71), (59, 71), (59, 74), (57, 74), (57, 69),
        (63, 69), (63, 76), (63, 83), (53, 83), (53, 64), (65, 64),
    ],
    "F1-D171-C01": [
        (48, 84), (48, 59), (92, 59), (92, 85), (67, 85), (67, 66),
        (88, 66), (88, 81), (71, 81), (71, 70), (84, 70), (84, 77),
        (75, 77), (75, 72), (80, 72), (80, 74), (77, 74), (77, 76),
        (82, 76), (82, 71), (73, 71), (73, 79), (86, 79), (86, 68),
        (69, 68), (69, 83), (90, 83), (90, 64), (67, 64),
    ],
}

CONTROL = {
    "F1-D171-C01": {"centre_start_index": 12, "centre_end_index": 18},
    "F1-D171-C02": {"centre_start_index": 17, "centre_end_index": 23},
}

# These are the useful continuous parts of each wall pass after the actual
# grid corner / field transition envelope.  Raw full-face percentages are kept
# separately and are deliberately not relabelled as a whole-wall PASS.
EXTERIOR_CONTINUOUS_PASSES = {
    "FLOOR_1-W001": [
        {"lane": 1, "axis": "Y", "coordinate_grid": 58, "from_grid": 47, "to_grid": 92},
        {"lane": 2, "axis": "Y", "coordinate_grid": 59, "from_grid": 48, "to_grid": 92},
        {"lane": 3, "axis": "Y", "coordinate_grid": 60, "from_grid": 49, "to_grid": 90},
    ],
    "FLOOR_1-W004": [
        {"lane": 1, "axis": "X", "coordinate_grid": 47, "from_grid": 58, "to_grid": 85},
        {"lane": 2, "axis": "X", "coordinate_grid": 48, "from_grid": 59, "to_grid": 84},
        {"lane": 3, "axis": "X", "coordinate_grid": 49, "from_grid": 60, "to_grid": 85},
    ],
}

PROVIDER_RUNS = [
    {
        "task_id": "HA-D172-CLAUDE-WEST-20260815-001",
        "provider": "CLAUDE",
        "prompt_file": "CLAUDE_WEST_CIRCUIT_TASK.md",
        "task_sha256": "588F2E1D230C0973D034FB851E66EBB740DA0481955AE66A80067C6FB2D50CC8",
        "state": "BLOCKED",
        "timed_out": True,
        "duration_ms": 600469,
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest().upper(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest().upper(),
        "usable_geometry_returned": False,
    },
    {
        "task_id": "HA-D172-KIMI-EAST-20260815-001",
        "provider": "KIMI",
        "prompt_file": "KIMI_EAST_CIRCUIT_TASK.md",
        "task_sha256": "AA4EAA9F728D946521CF18F30E2CE3F970474EE4C41631B23043CA7C402D6085",
        "state": "BLOCKED",
        "timed_out": True,
        "duration_ms": 601609,
        "stdout_bytes": 107,
        "stderr_bytes": 47655,
        "stdout_sha256": "150457008153FB0EBD9DE166EE8A3011979357BD046B623D9C02EA97A3F329DF",
        "stderr_sha256": "E74350FDFD8E898D22CD40E55F64EED6D5EFB4D5342D02A19D8C4AC049B50D45",
        "usable_geometry_returned": False,
    },
    {
        "task_id": "HA-D172-CLAUDE-WEST-20260815-002",
        "provider": "CLAUDE",
        "prompt_file": "CLAUDE_WEST_CIRCUIT_RETRY.md",
        "task_sha256": "D665582F92D6D7E73EF0D9E6C605E02B15D0E41B419CE669CB9DF6422A1EA817",
        "state": "BLOCKED",
        "timed_out": True,
        "duration_ms": 300468,
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest().upper(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest().upper(),
        "usable_geometry_returned": False,
    },
    {
        "task_id": "HA-D172-KIMI-EAST-20260815-002",
        "provider": "KIMI",
        "prompt_file": "KIMI_EAST_CIRCUIT_RETRY.md",
        "task_sha256": "DE23FDEABA07AC5A4B6F328FF279463F1C0991ABD1FF2F70E27625E5481583A6",
        "state": "COMPLETED",
        "timed_out": False,
        "duration_ms": 15844,
        "exit_code": 0,
        "stdout_sha256": "C48A5CDC6685B19D7EF22C18F8FA26A5F38821E21415847C5860B8C44AE446AC",
        "stderr_sha256": "DE413B47BEE13AFB83D0646FDDC45C2353F5B2C1587C7D36B45207B5357ECB4",
        "semantic_result": "INVALID_NO_PROBLEM_PROVIDED_NO_CONTOUR",
        "usable_geometry_returned": False,
    },
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def point_mm(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for start, end in sorted((min(a, b), max(a, b)) for a, b in intervals if a != b):
        if not result or start > result[-1][1]:
            result.append((start, end))
        else:
            result[-1] = (result[-1][0], max(result[-1][1], end))
    return result


def exterior_pass_audit(all_points: dict[str, list[tuple[int, int]]]) -> dict:
    segments = [
        (circuit_id, first, second)
        for circuit_id, points in all_points.items()
        for first, second in zip(points, points[1:])
    ]
    output: dict[str, object] = {}
    raw_required = {"FLOOR_1-W001": (46, 93), "FLOOR_1-W004": (57, 86)}
    for wall_id, passes in EXTERIOR_CONTINUOUS_PASSES.items():
        wall_records = []
        raw_from, raw_to = raw_required[wall_id]
        for item in passes:
            if item["axis"] == "Y":
                intervals = [
                    (first[0], second[0])
                    for _, first, second in segments
                    if first[1] == second[1] == item["coordinate_grid"]
                ]
            else:
                intervals = [
                    (first[1], second[1])
                    for _, first, second in segments
                    if first[0] == second[0] == item["coordinate_grid"]
                ]
            merged = merge_intervals(intervals)
            covered = sum(end - start for start, end in merged)
            expected = item["to_grid"] - item["from_grid"]
            exact_expected_covered = any(
                start <= item["from_grid"] and end >= item["to_grid"] for start, end in merged
            )
            wall_records.append({
                **item,
                "covered_intervals_grid": [list(value) for value in merged],
                "covered_length_mm": covered * 100,
                "raw_full_face_required_length_mm": (raw_to - raw_from) * 100,
                "raw_full_face_coverage_percent": covered * 100 / (raw_to - raw_from),
                "declared_continuous_turn_envelope_length_mm": expected * 100,
                "declared_continuous_turn_envelope_coverage_percent": covered * 100 / expected,
                "exact_declared_continuous_pass_present": exact_expected_covered,
            })
        output[wall_id] = wall_records
    return output


def provider_evidence() -> dict:
    prompt_root = ROOT / "agent-control" / "D172_OWNER_PAIR"
    runs = copy.deepcopy(PROVIDER_RUNS)
    for run in runs:
        prompt_path = prompt_root / run["prompt_file"]
        run["prompt_bytes"] = prompt_path.stat().st_size
        run["prompt_sha256"] = sha(prompt_path)
    return {
        "schema": "homeaura.provider.run.evidence.v1",
        "scope": "D172_CONTROL_PAIR_INPUTS_USED_FOR_D173_LOCAL_RECOVERY",
        "sanitized": True,
        "raw_provider_output_included": False,
        "accepted_provider_candidate_count": 0,
        "runs": runs,
        "conclusion": (
            "Neither provider produced an admissible ordered contour. D173 geometry is a local deterministic "
            "joint search result and is not attributed to Claude or Kimi."
        ),
    }


def render(project_file: Path, output: Path, command: str, room_id: str | None = None) -> None:
    args = [
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", command, str(project_file), str(output),
    ]
    if room_id is not None:
        args.append(room_id)
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)


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
        raise FileExistsError("D173 is append-only")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)

    project = json.loads(SOURCE_PROJECT.read_text(encoding="utf-8-sig"))
    source_project = copy.deepcopy(project)
    source_contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8-sig"))

    audits: dict[str, object] = {}
    for circuit_id, points in PAIR_POINTS.items():
        circuit = next(item for item in project["circuits"] if item["id"] == circuit_id)
        body_mm = length_mm(points)
        service_mm = d172.service_estimate_mm(points)
        bend = d172.bend_audit(points)
        centre_rule = CONTROL[circuit_id]
        centre = d172.centre_audit(points, centre_rule["centre_start_index"], centre_rule["centre_end_index"])
        if not centre["exact_owner_template_B_D4_match"]:
            raise RuntimeError({"owner_centre": circuit_id, "centre": centre})
        if bend["tangent_allocation_violation_count"] or bend["minimum_segment_mm"] < 200:
            raise RuntimeError({"R80": circuit_id, "bend": bend})
        if not LineString(points).is_simple or self_contacts(points):
            raise RuntimeError({"topology": circuit_id})
        circuit["ordered_points"] = [point_mm(point) for point in points]
        circuit["heating_body_start_index"] = 0
        circuit["heating_body_end_index"] = len(points) - 1
        circuit["concealed_service_length_mm"] = service_mm
        circuit["name"] = (
            f"{circuit_id.replace('D171', 'D173')} · совместная встречная раскладка F1-R08 · "
            f"тело {body_mm / 1000:.1f} м"
        )
        audits[circuit_id] = {
            "body_points_grid": [list(point) for point in points],
            "body_length_mm": body_mm,
            "provisional_manhattan_service_length_mm": service_mm,
            "provisional_complete_manhattan_length_mm": body_mm + service_mm,
            "provisional_complete_rounded_R80_length_mm": bend["rounded_body_length_mm"] + service_mm,
            "R80": bend,
            "centre": centre,
        }

    changed = set(PAIR_POINTS)
    for source_circuit in source_project["circuits"]:
        if source_circuit["id"] in changed:
            continue
        current = next(item for item in project["circuits"] if item["id"] == source_circuit["id"])
        if current["ordered_points"] != source_circuit["ordered_points"]:
            raise RuntimeError({"unexpected_change": source_circuit["id"]})

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
        raise RuntimeError({"global_contacts": contacts})

    room = next(item for item in project["rooms"] if item["id"] == "F1-R08")
    room_polygon = Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])
    wall_solids = [
        LineString([
            (wall["start"]["x_mm"], wall["start"]["y_mm"]),
            (wall["end"]["x_mm"], wall["end"]["y_mm"]),
        ]).buffer(wall["thickness_mm"] / 2, cap_style="square")
        for wall in project["walls"]
    ]
    for circuit_id, points in PAIR_POINTS.items():
        body = d172.line_mm(points)
        if not room_polygon.covers(body) or any(not body.intersection(wall).is_empty for wall in wall_solids):
            raise RuntimeError({"body_room_or_wall": circuit_id})

    pair_lines = {circuit_id: LineString(points) for circuit_id, points in PAIR_POINTS.items()}
    pair_union = unary_union(list(pair_lines.values()))
    domain = box(46, 57, 93, 86)
    served = domain.intersection(pair_union.buffer(1, quad_segs=16)).area
    samples = [
        Point(x / 2, y / 2).distance(pair_union)
        for x in range(46 * 2, 93 * 2 + 1)
        for y in range(57 * 2, 86 * 2 + 1)
    ]
    exterior_zone = unary_union([box(46, 57, 93, 60), box(46, 57, 49, 86)])
    outside_exterior = [line.difference(exterior_zone) for line in pair_lines.values()]
    raw_pair_distance = pair_lines["F1-D171-C01"].distance(pair_lines["F1-D171-C02"])
    field_pair_distance = outside_exterior[0].distance(outside_exterior[1])
    exterior = exterior_pass_audit(PAIR_POINTS)
    if any(
        not record["exact_declared_continuous_pass_present"]
        for records in exterior.values()
        for record in records
    ):
        raise RuntimeError({"continuous_exterior_pass": exterior})
    if served * 100 / domain.area < 98 or max(samples) > 1.5 + 1e-9:
        raise RuntimeError({"coverage": served * 100 / domain.area, "worst": max(samples) * 100})
    if raw_pair_distance < 1 - 1e-9 or field_pair_distance < 2 - 1e-9:
        raise RuntimeError({"pair_spacing": raw_pair_distance, "field_spacing": field_pair_distance})

    provisional_rounded = [item["provisional_complete_rounded_R80_length_mm"] for item in audits.values()]
    provider_path = OUTPUT / "provider_run_evidence.json"
    dump(provider_path, provider_evidence())

    project["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D173 joint room weave: no 100-mm U-turns, no empty seam, owner ACCEPTED-B centres",
        "notes": (
            "The two F1-R08 bodies are accepted only as a joint planar heating-body layout. "
            "All physical K1 transits remain unmaterialized; provisional service lengths are not a balance certificate."
        ),
    }
    project_path = OUTPUT / "HomeAura_Floor1_JointWeave_D173.homeaura.json"
    dump(project_path, project)

    contract = {
        "schema": "homeaura.floor1.joint_weave.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "JOINT_BODY_WEAVE_PASS_REWORK_ACTUAL_K1_TRANSITS_AND_BALANCE",
        "append_only": True,
        "supersession": {
            "supersedes_artifact_id": "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172",
            "supersedes_project_sha256": sha(SOURCE_PROJECT),
            "supersedes_contract_sha256": sha(SOURCE_CONTRACT),
            "immutable_predecessor": True,
            "errata": [{
                "source": "D172/README.md",
                "incorrect_claim": "rounded length spread < 2 m",
                "verified_D172_value_mm": 2296.991118430771,
                "correction": "below 3 m hard limit, above 2 m target",
            }],
        },
        "provider_run_evidence_file": provider_path.name,
        "provider_run_evidence_sha256": sha(provider_path),
        "changed_circuit_ids": list(PAIR_POINTS),
        "unchanged_circuit_ids": [
            item["id"] for item in project["circuits"] if item["id"] not in changed
        ],
        "control_pair": audits,
        "joint_validation": {
            "global_inter_circuit_contact_count": 0,
            "pair_centerline_minimum_mm": raw_pair_distance * 100,
            "pair_100mm_scope": "EXTERIOR_3X100_ZONE_ONLY",
            "field_pair_centerline_minimum_mm": field_pair_distance * 100,
            "R80_tangent_allocation_violation_count": 0,
            "minimum_body_segment_mm": min(
                min(d172.segment_lengths_mm(points)) for points in PAIR_POINTS.values()
            ),
            "exact_owner_template_B_centre_count": 2,
            "joint_domain_area_m2": domain.area / 100,
            "joint_round_100mm_served_m2": served / 100,
            "joint_round_100mm_served_percent": served * 100 / domain.area,
            "joint_50mm_sample_within_150mm_percent": sum(value <= 1.5 + 1e-9 for value in samples) * 100 / len(samples),
            "joint_maximum_sample_distance_mm": max(samples) * 100,
            "exterior_continuous_passes": exterior,
            "raw_full_face_90_percent_pass_count": sum(
                record["raw_full_face_coverage_percent"] + 1e-9 >= 90
                for records in exterior.values() for record in records
            ),
            "raw_full_face_90_percent_total_count": 6,
            "declared_turn_envelope_continuous_pass_count": 6,
            "window_projection_covered_by_all_three_left_passes": True,
        },
        "balance": {
            "basis": "PROVISIONAL_MANHATTAN_ENDPOINT_ESTIMATE_ONLY",
            "provisional_rounded_complete_length_spread_mm": max(provisional_rounded) - min(provisional_rounded),
            "accepted_as_balance_certificate": False,
            "reason": "ACTUAL_K1_TRANSIT_AXES_NOT_MATERIALIZED",
            "next_requirement": "MATERIALIZE_TWO_REAL_K1_TO_ROOM_ROUTE_PAIRS_AND_RECOMPUTE_ROUNDED_COMPLETE_LENGTHS",
        },
        "heating_bodies_may_cross_walls": False,
        "transits_may_cross_walls_perpendicularly": True,
        "complete_K1_route_count": 0,
        "installation_ready": False,
        "next_block": "D174_MATERIALIZE_JOINT_K1_TRANSITS_WITH_RIGHT_WALL_EXIT_AND_GLOBAL_BUNDLE_CHECK",
    }
    contract_path = OUTPUT / "floor1_joint_weave_contract.json"
    dump(contract_path, contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "body_pair_pass": True,
        "R80_violations": 0,
        "global_contacts": 0,
        "complete_K1_route_count": 0,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D173 · совместная раскладка двух контуров F1-R08\n\n"
        "D172 сохранён неизменным; его расчётный разброс был 2,297 м, а не менее 2 м. "
        "D173 заменяет только тела C01/C02. Три наружные полосы распределены между двумя контурами, "
        "поэтому между соседними полосами нет коротких 100-мм П-разворотов. Минимальный сегмент — 200 мм, "
        "нарушений R80 нет, тела не заходят на стены, глобальных контактов нет. Совместное покрытие комнаты "
        f"по диагностическому round-100 proxy — {served * 100 / domain.area:.3f}%.\n\n"
        "Это ещё не готовые полные петли: реальные оси четырёх подводок K1 не опубликованы. Поэтому большой "
        "разброс условных Manhattan-подводок не скрыт и не принят как баланс. Следующий блок D174 должен провести "
        "настоящие трассы через правую внутреннюю стену и сбалансировать уже полные округлённые длины.\n\n"
        "Диагностика полного лица стены остаётся строгой: часть внутренних полос короче 90% полного лица, "
        "поскольку их концы заняты угловым/полевым переходом. В контракте отдельно записаны как сырые проценты, "
        "так и фактически непрерывные участки; это не переименовано в полный фасадный PASS.\n",
        encoding="utf-8",
    )

    diagnostics_path = OUTPUT / "engineering_diagnostics.json"
    render(project_path, diagnostics_path, "--export-diagnostics")
    render(project_path, OUTPUT / "HomeAura_Floor1_D173_Editor_View.png", "--export-png")
    render(project_path, OUTPUT / "HomeAura_Floor1_D173_Clean_View.png", "--export-png-clean")
    render(project_path, OUTPUT / "HomeAura_Floor1_D173_F1-R08_Clean_Zoom.png", "--export-room-png-clean", "F1-R08")
    render(project_path, OUTPUT / "HomeAura_Floor1_D173_F1-R08_Diagnostics_Zoom.png", "--export-room-png-diagnostics", "F1-R08")
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "joint_coverage_percent": contract["joint_validation"]["joint_round_100mm_served_percent"],
        "worst_sample_mm": contract["joint_validation"]["joint_maximum_sample_distance_mm"],
        "R80_violations": 0,
        "field_pair_minimum_mm": contract["joint_validation"]["field_pair_centerline_minimum_mm"],
        "provisional_balance_accepted": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
