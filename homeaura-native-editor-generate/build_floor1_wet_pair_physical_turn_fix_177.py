from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import zipfile
from pathlib import Path

from shapely.geometry import LineString, box

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_WET_PAIR_176"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_WetPair_D176.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_wet_pair_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_WET_PAIR_PHYSICAL_TURN_FIX_177"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_WET_PAIR_PHYSICAL_TURN_FIX_177.zip"
ARTIFACT_ID = OUTPUT.name
RADIUS_MM = 80.0
PIPE_RADIUS_MM = 8.0
CHANGED_ID = "F1-D171-C11"
PAIR_IDS = {"F1-D171-C10", CHANGED_ID}

import sys
sys.path.insert(0, str(HERE))
from build_floor1_wet_pair_176 import (  # noqa: E402
    derive_transitions, exterior_evidence, route_metrics, transit_wall_audit, wet_coverage,
)


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


def circuit_specification(circuit: dict) -> dict:
    points = [
        (item["x_mm"], item["y_mm"], item.get("z_mm", circuit.get("axis_elevation_mm", 0)))
        for item in circuit["ordered_points"]
    ]
    ranges = [(item["start_index"], item["end_index"]) for item in circuit.get("heating_body_ranges", [])]
    transitions = [
        {
            "segment_index": item["segment_index"], "kind": item["kind"],
            "radius_mm": item["radius_mm"],
            "start_tangent_length_mm": item["start_tangent_length_mm"],
            "end_tangent_length_mm": item["end_tangent_length_mm"],
            "arc_samples_per_half": item["arc_samples_per_half"],
        }
        for item in circuit.get("vertical_transitions", [])
    ]
    return {"id": circuit["id"], "points": points, "ranges": ranges, "transitions": transitions}


def wall_solid(wall: dict):
    start = wall["start"]; end = wall["end"]; half = wall["thickness_mm"] / 2
    if start["x_mm"] == end["x_mm"]:
        return box(start["x_mm"] - half, min(start["y_mm"], end["y_mm"]),
                   start["x_mm"] + half, max(start["y_mm"], end["y_mm"]))
    return box(min(start["x_mm"], end["x_mm"]), start["y_mm"] - half,
               max(start["x_mm"], end["x_mm"]), start["y_mm"] + half)


def horizontal_turn_wall_audit(project: dict, circuit_ids: set[str]) -> dict:
    walls = [(wall, wall_solid(wall)) for wall in project["walls"]]
    details = []
    minimum_axis_clearance = math.inf
    for circuit in project["circuits"]:
        if circuit["id"] not in circuit_ids:
            continue
        points = circuit["ordered_points"]
        for point_index in range(1, len(points) - 1):
            previous = points[point_index - 1]; vertex = points[point_index]; following = points[point_index + 1]
            incoming = (vertex["x_mm"] - previous["x_mm"], vertex["y_mm"] - previous["y_mm"])
            outgoing = (following["x_mm"] - vertex["x_mm"], following["y_mm"] - vertex["y_mm"])
            incoming_length = math.hypot(*incoming); outgoing_length = math.hypot(*outgoing)
            incoming = (incoming[0] / incoming_length, incoming[1] / incoming_length)
            outgoing = (outgoing[0] / outgoing_length, outgoing[1] / outgoing_length)
            cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
            if abs(cross) < 1e-9 or abs(dot) > 1e-9:
                continue
            tangent_in = (vertex["x_mm"] - incoming[0] * RADIUS_MM,
                          vertex["y_mm"] - incoming[1] * RADIUS_MM)
            tangent_out = (vertex["x_mm"] + outgoing[0] * RADIUS_MM,
                           vertex["y_mm"] + outgoing[1] * RADIUS_MM)
            centre = (vertex["x_mm"] - incoming[0] * RADIUS_MM + outgoing[0] * RADIUS_MM,
                      vertex["y_mm"] - incoming[1] * RADIUS_MM + outgoing[1] * RADIUS_MM)
            start_angle = math.atan2(tangent_in[1] - centre[1], tangent_in[0] - centre[0])
            end_angle = math.atan2(tangent_out[1] - centre[1], tangent_out[0] - centre[0])
            if cross > 0:
                while end_angle < start_angle:
                    end_angle += 2 * math.pi
            else:
                while end_angle > start_angle:
                    end_angle -= 2 * math.pi
            arc = LineString([
                (centre[0] + RADIUS_MM * math.cos(start_angle + (end_angle - start_angle) * sample / 128),
                 centre[1] + RADIUS_MM * math.sin(start_angle + (end_angle - start_angle) * sample / 128))
                for sample in range(129)
            ])
            for wall, solid in walls:
                clearance = arc.distance(solid)
                minimum_axis_clearance = min(minimum_axis_clearance, clearance)
                if clearance + 1e-7 >= PIPE_RADIUS_MM:
                    continue
                details.append({
                    "circuit_id": circuit["id"], "point_index": point_index,
                    "wall_id": wall["id"], "axis_clearance_to_wall_solid_mm": clearance,
                    "pipe_surface_clearance_to_wall_solid_mm": clearance - PIPE_RADIUS_MM,
                })
    return {
        "method": "128-segment R80 quarter-arc versus exact wall solid; pipe radius 8 mm included",
        "scope_circuit_ids": sorted(circuit_ids), "radius_mm": RADIUS_MM,
        "pipe_radius_mm": PIPE_RADIUS_MM,
        "minimum_axis_clearance_to_any_wall_solid_mm": minimum_axis_clearance,
        "minimum_pipe_surface_clearance_to_any_wall_solid_mm": minimum_axis_clearance - PIPE_RADIUS_MM,
        "intrusion_count": len(details), "intrusions": details, "pass": not details,
    }


def collector_tail_evidence(project: dict, circuit_ids: set[str]) -> dict:
    collector = next(item for item in project["collectors"] if item["id"] == "K1")
    wall = next(item for item in project["walls"] if item["id"] == collector["mounting_wall_id"])
    angle = math.atan2(wall["end"]["y_mm"] - wall["start"]["y_mm"],
                       wall["end"]["x_mm"] - wall["start"]["x_mm"]) + math.radians(collector["rotation_degrees"])
    cosine = math.cos(angle); sine = math.sin(angle)
    by_index = {item["connection_index"]: item for item in collector["connection_points"]}
    records = []
    for circuit in project["circuits"]:
        if circuit["id"] not in circuit_ids:
            continue
        for leg, point, port_index in [
            ("SUPPLY", circuit["ordered_points"][0], circuit["supply_port_index"]),
            ("RETURN", circuit["ordered_points"][-1], circuit["return_port_index"]),
        ]:
            connection = by_index[port_index]; local = connection["local_position_mm"]
            target = {
                "x_mm": collector["position"]["x_mm"] + local["x_mm"] * cosine - local["y_mm"] * sine,
                "y_mm": collector["position"]["y_mm"] + local["x_mm"] * sine + local["y_mm"] * cosine,
                "z_mm": local["z_mm"],
            }
            distance = math.sqrt(
                (point["x_mm"] - target["x_mm"]) ** 2 +
                (point["y_mm"] - target["y_mm"]) ** 2 +
                ((point.get("z_mm") or 0) - target["z_mm"]) ** 2
            )
            records.append({
                "circuit_id": circuit["id"], "leg": leg, "assigned_port_index": port_index,
                "bounded_terminal_point_mm": point, "physical_eurocone_point_mm": target,
                "straight_line_gap_mm": distance, "fabrication_tail_materialized": False,
            })
    return {
        "classification": "DEFERRED_COLLECTOR_TAIL_FABRICATION_GEOMETRY_NOT_MICRO_STUBS",
        "records": records, "minimum_gap_mm": min(item["straight_line_gap_mm"] for item in records),
        "maximum_gap_mm": max(item["straight_line_gap_mm"] for item in records),
        "collector_continuous_route_count": 0,
    }


def build_project() -> tuple[dict, dict, dict, list[str]]:
    project = json.loads(SOURCE_PROJECT.read_text(encoding="utf-8-sig"))
    source = copy.deepcopy(project)
    circuit = next(item for item in project["circuits"] if item["id"] == CHANGED_ID)
    circuit["ordered_points"][56]["x_mm"] = 10600
    circuit["ordered_points"][57]["x_mm"] = 10600
    circuit["name"] = "F1-D177-C11 · физический R80-поворот вынесен из W015"
    specification = circuit_specification(circuit)
    specification["transitions"] = derive_transitions(specification)
    circuit["vertical_transitions"] = specification["transitions"]

    current = {item["id"]: item for item in project["circuits"]}
    unchanged = []
    for old in source["circuits"]:
        if old["id"] == CHANGED_ID:
            continue
        if current[old["id"]] != old:
            raise RuntimeError({"unexpected_D177_change": old["id"]})
        unchanged.append(old["id"])
    c10 = circuit_specification(current["F1-D171-C10"])
    return project, c10, specification, unchanged


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
        raise FileExistsError("D177 is append-only")
    project, c10, c11, unchanged = build_project()
    specifications = [c10, c11]
    metrics = {item["id"]: route_metrics(item) for item in specifications}
    spread = abs(metrics[c10["id"]]["rounded_physical_axis_length_mm"] -
                 metrics[c11["id"]]["rounded_physical_axis_length_mm"])
    if any(not 40_000 <= item["rounded_physical_axis_length_mm"] <= 80_000 for item in metrics.values()) or spread > 2_000:
        raise RuntimeError({"D177_length_or_balance_gate": metrics, "spread": spread})
    coverage = wet_coverage(specifications)
    exterior = exterior_evidence(specifications)
    wall_audit = transit_wall_audit(project, specifications)
    turn_wall_audit = horizontal_turn_wall_audit(project, PAIR_IDS)
    if not exterior["all_partition_aware_gates_pass"] or not wall_audit["pass"] or not turn_wall_audit["pass"]:
        raise RuntimeError({"D177_physical_wall_gate": turn_wall_audit, "sharp_wall": wall_audit, "exterior": exterior})
    tails = collector_tail_evidence(project, PAIR_IDS)

    temporary = ROOT / "tmp" / "D177_preflight.homeaura.json"
    temporary.parent.mkdir(exist_ok=True)
    dump(temporary, project)
    diagnostics_path = ROOT / "tmp" / "D177_preflight_diagnostics.json"
    run_editor(temporary, diagnostics_path, "--export-diagnostics")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))
    changed_diagnostics = {
        item["circuit_id"]: item for item in diagnostics["circuits"] if item["circuit_id"] in PAIR_IDS
    }
    for circuit_id, item in changed_diagnostics.items():
        if not item["topology_pass"] or not item["engineering_pass"] or item["self_intersections"] or \
                item["self_surface_clearance_violations"] or item["inter_circuit_intersections"] or \
                item["inter_circuit_surface_clearance_violations"] or item["bend_radius_violation_count"] or \
                item["heating_body_wall_intrusions"] or item["horizontal_turn_wall_intrusions"]:
            raise RuntimeError({"D177_CSharp_gate": circuit_id, "diagnostics": item})
        if abs(item["rounded_axis_length_mm"] - metrics[circuit_id]["rounded_physical_axis_length_mm"]) > 0.003:
            raise RuntimeError({"D177_length_disagreement": circuit_id})

    contract = {
        "schema": "homeaura.floor1.wet_pair_physical_turn_fix.v1", "artifact_id": ARTIFACT_ID,
        "status": "D176_PHYSICAL_TURN_SUPERSEDED_PASS_COLLECTOR_TAILS_DEFERRED",
        "append_only": True, "source_D176_project_sha256": sha(SOURCE_PROJECT),
        "source_D176_contract_sha256": sha(SOURCE_CONTRACT),
        "changed_circuit_ids": [CHANGED_ID], "unchanged_circuit_ids": unchanged,
        "exact_change": {"point_indices": [56,57], "old_x_mm": 10700, "new_x_mm": 10600,
                         "reason": "provide 150 mm axis offset from W015 west solid face before R80 filleting"},
        "supersedes": [{
            "artifact_id": SOURCE.name,
            "claims": ["C11 physical R80 wall-turn clearance", "collector micro-stub wording"],
            "disposition": "SUPERSEDED_BY_D177_PHYSICAL_TURN_AND_DEFERRED_COLLECTOR_TAIL_EVIDENCE",
        }],
        "route_metrics": metrics, "pair_rounded_length_spread_mm": spread,
        "wet_coverage": coverage, "exterior_3x100": exterior,
        "sharp_wall_solid_transit_audit": wall_audit,
        "physical_R80_turn_wall_audit": turn_wall_audit,
        "collector_tail_evidence": tails,
        "complete_K1_route_count": 0, "collector_continuous_route_count": 0,
        "bounded_terminal_grid_route_count": 6, "materialized_floor_plane_route_count": 6,
        "installation_ready": False,
        "remaining_blockers": [
            "four terminal-bank-to-Eurocone fabrication tails of about 2.4-2.6 m are not materialized",
            "C03 and C05-C09 retain inherited R80 debt",
            "hydraulic sizing and flow settings remain not evaluated",
        ],
        "next_block": "REBUILD_F1_R04_C05_C06_OWNER_STYLE_PAIR",
    }
    report = {
        "schema": "homeaura.floor1.wet_pair_physical_turn_fix.report.v1", "artifact_id": ARTIFACT_ID,
        "route_metrics": metrics, "pair_rounded_length_spread_mm": spread,
        "physical_R80_turn_wall_audit": turn_wall_audit,
        "collector_tail_evidence": tails, "CSharp_pair_diagnostics": changed_diagnostics,
    }

    OUTPUT.mkdir(parents=True); PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    project_path = OUTPUT / "HomeAura_Floor1_WetPairPhysicalTurnFix_D177.homeaura.json"
    dump(project_path, project)
    dump(OUTPUT / "floor1_wet_pair_physical_turn_fix_contract.json", contract)
    dump(OUTPUT / "wet_pair_physical_turn_fix_report.json", report)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID, "result": contract["status"],
        "physical_R80_turn_wall_intrusions": turn_wall_audit["intrusion_count"],
        "collector_continuous_route_count": 0, "bounded_terminal_grid_route_count": 6,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D177 · физическая коррекция R80 у стены W015\n\n"
        "D176 сохранён как история, но его C11 нельзя применять монтажно: две дуги R80 начинали поворот "
        "на расстоянии 50 мм от грани W015. В D177 только точки 56/57 C11 сдвинуты на 100 мм. "
        "Теперь дуги находятся вне стены вместе с оболочкой трубы Ø16; тела укладки не менялись.\n\n"
        "Четыре конца C10/C11 всё ещё не доведены до физических Eurocone: прямые расстояния порядка "
        f"{tails['minimum_gap_mm']/1000:.2f}–{tails['maximum_gap_mm']/1000:.2f} м. Это отложенные "
        "коллекторные хвосты, а не микроподводки. Коллекторно-непрерывных маршрутов: 0.\n",
        encoding="utf-8",
    )
    run_editor(project_path, OUTPUT / "engineering_diagnostics.json", "--export-diagnostics")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D177_Clean_View.png", "--export-png-clean")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D177_WetPair_Clean_Zoom.png", "--export-room-png-clean", "F1-R06")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D177_WetPair_3D_Debug.png", "--export-room-png-diagnostics", "F1-R06")
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID, "package_sha256": sha(PACKAGE),
        "rounded_lengths_mm": {key: value["rounded_physical_axis_length_mm"] for key,value in metrics.items()},
        "pair_spread_mm": spread, "turn_wall_intrusions": turn_wall_audit["intrusion_count"],
        "collector_tail_gap_range_mm": [tails["minimum_gap_mm"],tails["maximum_gap_mm"]],
        "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
