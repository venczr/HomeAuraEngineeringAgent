from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from build_floor1_physical_four_loop_175 import fillet  # noqa: E402
from build_floor1_wet_pair_176 import derive_transitions, route_metrics, transit_wall_audit  # noqa: E402
from build_floor1_wet_pair_physical_turn_fix_177 import (  # noqa: E402
    collector_tail_evidence,
    horizontal_turn_wall_audit,
)

PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_WET_PAIR_PHYSICAL_TURN_FIX_177"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_WetPairPhysicalTurnFix_D177.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_wet_pair_physical_turn_fix_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178.zip"
ARTIFACT_ID = OUTPUT.name
CHANGED_IDS = {"F1-D171-C05", "F1-D171-C06"}
BODY_Z = 108
LOW_Z = 70
HIGH_Z = 135


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_editor(project_path: Path, output_path: Path, command: str, room_id: str | None = None) -> None:
    args = [
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", command, str(project_path), str(output_path),
    ]
    if room_id:
        args.append(room_id)
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError({"command": args, "stdout": completed.stdout, "stderr": completed.stderr})


def c05_spec() -> dict:
    points = [
        (15900,8800,HIGH_Z),(16400,8800,BODY_Z),(21000,8800,BODY_Z),(21000,11600,BODY_Z),
        (21000,12200,HIGH_Z),(20800,12200,HIGH_Z),(20800,11600,BODY_Z),(20800,9000,BODY_Z),
        (16400,9000,BODY_Z),(15900,9000,HIGH_Z),(15900,9200,HIGH_Z),(16400,9200,BODY_Z),
        (18200,9200,BODY_Z),(18200,9400,BODY_Z),(16400,9400,BODY_Z),(16400,9600,BODY_Z),
        (18200,9600,BODY_Z),(18200,9800,BODY_Z),(16400,9800,BODY_Z),(16400,10000,BODY_Z),
        (18200,10000,BODY_Z),(18200,10200,BODY_Z),(16400,10200,BODY_Z),(16400,10400,BODY_Z),
        (18200,10400,BODY_Z),(18200,10600,BODY_Z),(16400,10600,BODY_Z),(16400,10800,BODY_Z),
        (18200,10800,BODY_Z),(18200,11000,BODY_Z),(16400,11000,BODY_Z),(16400,11200,BODY_Z),
        (18200,11200,BODY_Z),(18200,11400,BODY_Z),(16400,11400,BODY_Z),(16400,11600,BODY_Z),
        (18200,11600,BODY_Z),(18500,11600,HIGH_Z),(18500,9100,HIGH_Z),(17000,9100,HIGH_Z),
    ]
    return {
        "id": "F1-D171-C05", "room_id": "F1-R04", "ports": (8,9), "points": points,
        "ranges": [(1,3),(6,8),(11,36)],
        "name": "F1-D178-C05 · котельная · E1+E3+заполняющая змейка · Point3",
        "grammar": "INDEPENDENT_EXTERIOR_L_RANGES_PLUS_OWNER_APPROVED_VOID_FILL_SERPENTINE",
    }


def c06_spec() -> dict:
    points = [
        (15800,8900,HIGH_Z),(16400,8900,BODY_Z),(20900,8900,BODY_Z),(20900,11600,BODY_Z),
        (20900,12200,LOW_Z),(20600,12200,LOW_Z),(20600,11600,BODY_Z),(18400,11600,BODY_Z),
        (18400,11400,BODY_Z),(20600,11400,BODY_Z),(20600,11200,BODY_Z),(18400,11200,BODY_Z),
        (18400,11000,BODY_Z),(20600,11000,BODY_Z),(20600,10800,BODY_Z),(18400,10800,BODY_Z),
        (18400,10600,BODY_Z),(20600,10600,BODY_Z),(20600,10400,BODY_Z),(18400,10400,BODY_Z),
        (18400,10200,BODY_Z),(20600,10200,BODY_Z),(20600,10000,BODY_Z),(18400,10000,BODY_Z),
        (18400,9800,BODY_Z),(20600,9800,BODY_Z),(20600,9600,BODY_Z),(18400,9600,BODY_Z),
        (18400,9400,BODY_Z),(20600,9400,BODY_Z),(20600,9200,BODY_Z),(18400,9200,BODY_Z),
        (18400,8800,LOW_Z),(20300,8800,LOW_Z),(20300,9400,LOW_Z),(17000,9400,LOW_Z),
    ]
    return {
        "id": "F1-D171-C06", "room_id": "F1-R04", "ports": (10,11), "points": points,
        "ranges": [(1,3),(6,31)],
        "transition_tangent_overrides": {31: (80.0,216.48188564313972)},
        "name": "F1-D178-C06 · котельная · E2+заполняющая змейка · Point3",
        "grammar": "INDEPENDENT_EXTERIOR_L_RANGE_PLUS_OWNER_APPROVED_VOID_FILL_SERPENTINE",
    }


def apply_specification(project: dict, specification: dict) -> None:
    specification["transitions"] = derive_transitions(specification)
    circuit = next(item for item in project["circuits"] if item["id"] == specification["id"])
    circuit["name"] = specification["name"]
    circuit["ordered_points"] = [
        {"x_mm": x, "y_mm": y, "z_mm": z} for x, y, z in specification["points"]
    ]
    circuit["heating_body_start_index"] = None
    circuit["heating_body_end_index"] = None
    circuit["heating_body_ranges"] = [
        {"start_index": start, "end_index": end} for start, end in specification["ranges"]
    ]
    circuit["vertical_transitions"] = specification["transitions"]
    circuit["concealed_service_length_mm"] = 0
    circuit["out_of_plane_length_mm"] = 0
    circuit["system_role"] = "FLOOR_HEATING_LOOP"
    circuit["supply_port_index"], circuit["return_port_index"] = specification["ports"]


def build_project() -> tuple[dict, list[dict], list[str]]:
    project = json.loads(SOURCE_PROJECT.read_text(encoding="utf-8-sig"))
    source = copy.deepcopy(project)
    specifications = [c05_spec(), c06_spec()]
    for specification in specifications:
        apply_specification(project, specification)
    current = {item["id"]: item for item in project["circuits"]}
    unchanged = []
    for previous in source["circuits"]:
        if previous["id"] in CHANGED_IDS:
            continue
        if current[previous["id"]] != previous:
            raise RuntimeError({"unexpected_D178_change": previous["id"]})
        unchanged.append(previous["id"])
    return project, specifications, unchanged


def body_lines(specification: dict, rounded: bool) -> list[LineString]:
    result = []
    for start, end in specification["ranges"]:
        coordinates = [(x / 100, y / 100) for x, y, _ in specification["points"][start:end + 1]]
        result.append(LineString(fillet(coordinates)) if rounded else LineString(coordinates))
    return result


def boiler_coverage(specifications: list[dict]) -> dict:
    domain = box(163,87,211,117)

    def measure(lines: list[LineString]) -> dict:
        merged = unary_union(lines)
        served = domain.intersection(merged.buffer(1, quad_segs=16)).area
        samples = [
            Point(x / 2, y / 2).distance(merged)
            for x in range(math.ceil(domain.bounds[0] * 2), math.floor(domain.bounds[2] * 2) + 1)
            for y in range(math.ceil(domain.bounds[1] * 2), math.floor(domain.bounds[3] * 2) + 1)
            if domain.covers(Point(x / 2, y / 2))
        ]
        return {
            "served_area_m2": served / 100,
            "served_percent": served * 100 / domain.area,
            "unserved_proxy_area_m2": (domain.area - served) / 100,
            "sample_grid_mm": 50, "sample_count": len(samples),
            "sample_within_200mm_percent": sum(value <= 2 + 1e-9 for value in samples) * 100 / len(samples),
            "sample_over_200mm_count": sum(value > 2 + 1e-9 for value in samples),
            "maximum_sample_distance_mm": max(samples) * 100,
            "q16_buffer_resolution": 16,
        }

    sharp = [line for item in specifications for line in body_lines(item, False)]
    physical = [line for item in specifications for line in body_lines(item, True)]
    return {
        "domain_definition": "F1-R04 exact inner wall faces x16300..21100, y8700..11700",
        "domain_bbox_mm": [16300,8700,21100,11700], "domain_area_m2": domain.area / 100,
        "sharp_axis_round100": measure(sharp), "physical_R80_axis_round100": measure(physical),
        "proxy_is_heat_loss_or_hydraulic_certificate": False,
    }


def exterior_evidence(specifications: list[dict]) -> dict:
    segments = []
    for specification in specifications:
        for start, end in specification["ranges"]:
            for index in range(start, end):
                segments.append((specification["id"], specification["points"][index], specification["points"][index + 1]))

    expected = [
        {"lane": 1, "circuit_id": "F1-D171-C05", "horizontal": [16400,8800,21000,8800],
         "vertical": [21000,8800,21000,11600]},
        {"lane": 2, "circuit_id": "F1-D171-C06", "horizontal": [16400,8900,20900,8900],
         "vertical": [20900,8900,20900,11600]},
        {"lane": 3, "circuit_id": "F1-D171-C05", "horizontal": [16400,9000,20800,9000],
         "vertical": [20800,9000,20800,11600]},
    ]

    def contains(record: dict, key: str) -> bool:
        x1, y1, x2, y2 = record[key]
        return any(
            circuit_id == record["circuit_id"] and
            ((a[0], a[1], b[0], b[1]) == (x1, y1, x2, y2) or
             (b[0], b[1], a[0], a[1]) == (x1, y1, x2, y2))
            for circuit_id, a, b in segments
        )

    for record in expected:
        record["horizontal_body_pass"] = contains(record, "horizontal")
        record["vertical_body_pass"] = contains(record, "vertical")
        record["spacing_from_inner_faces_mm"] = record["lane"] * 100
        record["pass"] = record["horizontal_body_pass"] and record["vertical_body_pass"]
    return {
        "classification": "EXACT_INDEPENDENT_BODY_L_RANGES_WITHOUT_100MM_U_TURNS",
        "top_exterior_wall_id": "FLOOR_1-W022", "right_exterior_wall_id": "FLOOR_1-W023",
        "top_inner_face_y_mm": 8700, "right_inner_face_x_mm": 21100,
        "lanes": expected, "all_three_body_lanes_pass": all(item["pass"] for item in expected),
        "window_count_in_room": 0, "transit_may_satisfy_exterior_lane": False,
    }


def package_output() -> None:
    payloads = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID, "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in payloads],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [*payloads, OUTPUT / "artifact_manifest.json"]:
            archive.write(path, path.name)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D178 is append-only")
    project, specifications, unchanged = build_project()
    metrics = {item["id"]: route_metrics(item) for item in specifications}
    spread = abs(metrics["F1-D171-C05"]["rounded_physical_axis_length_mm"] -
                 metrics["F1-D171-C06"]["rounded_physical_axis_length_mm"])
    coverage = boiler_coverage(specifications)
    exterior = exterior_evidence(specifications)
    sharp_walls = transit_wall_audit(project, specifications)
    turn_walls = horizontal_turn_wall_audit(project, CHANGED_IDS)
    tails = collector_tail_evidence(project, CHANGED_IDS)
    if any(not 40_000 <= item["rounded_physical_axis_length_mm"] <= 80_000 for item in metrics.values()) or spread > 2_000:
        raise RuntimeError({"D178_length_or_balance_gate": metrics, "spread": spread})
    physical = coverage["physical_R80_axis_round100"]
    if physical["served_percent"] < 96 or physical["maximum_sample_distance_mm"] > 200 or physical["sample_over_200mm_count"]:
        raise RuntimeError({"D178_physical_coverage_gate": physical})
    if not exterior["all_three_body_lanes_pass"] or not sharp_walls["pass"] or not turn_walls["pass"]:
        raise RuntimeError({"D178_exterior_or_wall_gate": [exterior, sharp_walls, turn_walls]})

    ports = sorted(
        value for circuit in project["circuits"] if circuit.get("collector_id") == "K1"
        for value in [circuit.get("supply_port_index"), circuit.get("return_port_index")] if value is not None
    )
    if ports != list(range(28)):
        raise RuntimeError({"D178_port_ownership": ports})

    temporary = ROOT / "tmp" / "D178_preflight.homeaura.json"
    temporary.parent.mkdir(exist_ok=True)
    dump(temporary, project)
    diagnostics_path = ROOT / "tmp" / "D178_preflight_diagnostics.json"
    run_editor(temporary, diagnostics_path, "--export-diagnostics")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))
    changed_diagnostics = {
        item["circuit_id"]: item for item in diagnostics["circuits"] if item["circuit_id"] in CHANGED_IDS
    }
    for circuit_id, item in changed_diagnostics.items():
        if not item["topology_pass"] or not item["engineering_pass"] or item["self_intersections"] or \
                item["self_surface_clearance_violations"] or item["inter_circuit_intersections"] or \
                item["inter_circuit_surface_clearance_violations"] or item["bend_radius_violation_count"] or \
                item["heating_body_wall_intrusions"] or item["horizontal_turn_wall_intrusions"]:
            raise RuntimeError({"D178_CSharp_gate": circuit_id, "diagnostics": item})
        if abs(item["rounded_axis_length_mm"] - metrics[circuit_id]["rounded_physical_axis_length_mm"]) > 0.003:
            raise RuntimeError({"D178_length_disagreement": circuit_id})

    contract = {
        "schema": "homeaura.floor1.boiler_pair.v1", "artifact_id": ARTIFACT_ID,
        "status": "F1_R04_TWO_OWNER_BODY_POINT3_ROUTES_PASS_COLLECTOR_TAILS_DEFERRED",
        "append_only": True, "source_D177_project_sha256": sha(SOURCE_PROJECT),
        "source_D177_contract_sha256": sha(SOURCE_CONTRACT),
        "changed_circuit_ids": sorted(CHANGED_IDS), "unchanged_circuit_ids": unchanged,
        "room_contract": {"room_id": "F1-R04", "name": "Котельная", "window_count": 0,
                          "exclusion_count": 0, "inner_face_domain_area_m2": 14.4},
        "owner_grammar": {
            "exterior": "three independent BODY L-ranges at 100/200/300 mm; no 100 mm two-turn connector",
            "field": "deliberate owner-approved void-fill serpentine at 200 mm pitch",
            "body_may_cross_wall": False, "transit_may_cross_wall_perpendicularly": True, "sleeves_added": False,
        },
        "route_metrics": metrics, "pair_rounded_length_spread_mm": spread,
        "boiler_coverage": coverage, "exterior_3x100": exterior,
        "sharp_wall_solid_transit_audit": sharp_walls,
        "physical_R80_turn_wall_audit": turn_walls,
        "collector_tail_evidence": tails,
        "K1_port_ownership": {"connection_indices": ports, "unique_count": len(set(ports)),
                              "C05_ports": [8,9], "C06_ports": [10,11]},
        "complete_K1_route_count": 0, "collector_continuous_route_count": 0,
        "bounded_terminal_grid_route_count": 8, "materialized_floor_plane_route_count": 8,
        "installation_ready": False,
        "remaining_blockers": [
            "terminal-grid-to-Eurocone fabrication tails are not materialized",
            "C03 and C07-C09 retain inherited R80 debt",
            "hydraulic flow settings and pressure-loss calculation remain not evaluated",
        ],
        "next_block": "REBUILD_NEXT_WORST_R80_OR_COVERAGE_ROOM",
    }
    report = {
        "schema": "homeaura.floor1.boiler_pair.report.v1", "artifact_id": ARTIFACT_ID,
        "route_metrics": metrics, "pair_rounded_length_spread_mm": spread,
        "boiler_coverage": coverage, "exterior_3x100": exterior,
        "sharp_wall_solid_transit_audit": sharp_walls,
        "physical_R80_turn_wall_audit": turn_walls,
        "collector_tail_evidence": tails, "CSharp_pair_diagnostics": changed_diagnostics,
    }

    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    project_path = OUTPUT / "HomeAura_Floor1_BoilerPair_D178.homeaura.json"
    dump(project_path, project)
    dump(OUTPUT / "floor1_boiler_pair_contract.json", contract)
    dump(OUTPUT / "boiler_pair_report.json", report)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID, "result": contract["status"],
        "physical_R80_coverage_percent": physical["served_percent"],
        "maximum_uncovered_distance_mm": physical["maximum_sample_distance_mm"],
        "pair_spread_mm": spread, "collector_continuous_route_count": 0, "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D178 · два контура котельной без больших пустот\n\n"
        "C05/C06 полностью перестроены. У наружных стен работают три независимые L-полосы BODY "
        "на 100/200/300 мм. Между ними нет запрещённых 100-мм U-разворотов: полосы связаны "
        "многоуровневыми транзитами. Основное поле заполнено змейкой с шагом 200 мм — именно "
        "как локальное заполнение пустот, а не как бессмысленное удлинение.\n\n"
        f"Физическое R80-покрытие: {physical['served_percent']:.3f}%; максимальный просвет "
        f"{physical['maximum_sample_distance_mm']:.1f} мм. Длины: "
        f"{metrics['F1-D171-C05']['rounded_physical_axis_length_mm']/1000:.2f} и "
        f"{metrics['F1-D171-C06']['rounded_physical_axis_length_mm']/1000:.2f} м; "
        f"разброс {spread/1000:.2f} м.\n\n"
        "Тела не входят в стены. Стены пересекают только TRANSIT-участки, коротко и "
        "перпендикулярно. Гильзы не добавлены. Физические хвосты от терминальной сетки до "
        "Eurocone пока не нарисованы, поэтому коллекторно-непрерывных маршрутов всё ещё 0.\n",
        encoding="utf-8",
    )
    run_editor(project_path, OUTPUT / "engineering_diagnostics.json", "--export-diagnostics")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D178_Clean_View.png", "--export-png-clean")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D178_Boiler_Clean_Zoom.png", "--export-room-png-clean", "F1-R04")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D178_Boiler_3D_Debug.png", "--export-room-png-diagnostics", "F1-R04")
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID, "package_sha256": sha(PACKAGE),
        "rounded_lengths_mm": {key: value["rounded_physical_axis_length_mm"] for key, value in metrics.items()},
        "pair_spread_mm": spread, "physical_R80_coverage_percent": physical["served_percent"],
        "maximum_sample_distance_mm": physical["maximum_sample_distance_mm"],
        "wall_turn_intrusions": turn_walls["intrusion_count"], "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
