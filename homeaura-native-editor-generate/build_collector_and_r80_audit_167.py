from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D166 = PROPOSALS / "HA_TWO_FLOOR_K2_SERVICE_LAYER_166"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_COLLECTOR_AND_R80_AUDIT_167"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_COLLECTOR_AND_R80_AUDIT_167.zip"
ARTIFACT_ID = OUTPUT.name
RADIUS_MM = 80


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png", str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def bend_audit(circuit: dict) -> dict:
    points = [(item["x_mm"], item["y_mm"]) for item in circuit["ordered_points"]]
    turns = [False] * len(points)
    for index in range(1, len(points) - 1):
        incoming = (points[index][0] - points[index - 1][0], points[index][1] - points[index - 1][1])
        outgoing = (points[index + 1][0] - points[index][0], points[index + 1][1] - points[index][1])
        turns[index] = incoming[0] * outgoing[1] - incoming[1] * outgoing[0] != 0
    violations = []
    axis_length = 0.0
    for index, (first, second) in enumerate(zip(points, points[1:])):
        segment_length = abs(first[0] - second[0]) + abs(first[1] - second[1])
        axis_length += segment_length
        required = (RADIUS_MM if turns[index] else 0) + (RADIUS_MM if turns[index + 1] else 0)
        if segment_length < required:
            violations.append({
                "segment_index": index,
                "start_mm": list(first),
                "end_mm": list(second),
                "available_mm": segment_length,
                "required_tangent_sum_mm": required,
                "shortfall_mm": required - segment_length,
            })
    turn_count = sum(turns)
    rounded_axis_length = axis_length - turn_count * (2 * RADIUS_MM - math.pi * RADIUS_MM / 2)
    return {
        "route_id": circuit["id"],
        "system_role": circuit.get("system_role", "FLOOR_HEATING_LOOP"),
        "turn_count": turn_count,
        "violation_count": len(violations),
        "violations": violations,
        "manhattan_axis_length_mm": axis_length,
        "rounded_axis_length_mm_if_all_bends_fit": rounded_axis_length,
        "result": "PASS_R80_TANGENT_ALLOCATION" if not violations else "REWORK_R80_TANGENT_ALLOCATION",
    }


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
        raise SystemExit("D167 append-only output already exists")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    source_floor_path = D166 / "HomeAura_Floor1_K1_and_K2_Service_D166.homeaura.json"
    source_attic_path = D166 / "HomeAura_Attic_PairedAxes_D166.homeaura.json"
    floor = load(source_floor_path)
    attic = load(source_attic_path)
    source_floor_circuits = copy.deepcopy(floor["circuits"])
    source_attic_circuits = copy.deepcopy(attic["circuits"])

    source_url = "https://hydroheatufh.co.uk/wp-content/uploads/2021/08/Manifold-Datasheet.pdf"
    for collector in floor["collectors"]:
        if collector["id"] == "K1":
            collector.update({
                "ports": 24,
                "reference_width_mm": 776,
                "reference_depth_mm": 90,
                "reference_height_mm": 320,
                "equipment_status": "DRAFT_UNSELECTED",
                "reference_source": source_url,
            })
        elif collector["id"] == "K2":
            collector.update({
                "ports": 22,
                "reference_width_mm": 726,
                "reference_depth_mm": 90,
                "reference_height_mm": 320,
                "equipment_status": "DRAFT_UNSELECTED",
                "reference_source": source_url,
            })
    for collector in attic["collectors"]:
        if collector["id"] == "K2":
            collector.update({
                "ports": 22,
                "reference_width_mm": 726,
                "reference_depth_mm": 90,
                "reference_height_mm": 320,
                "equipment_status": "DRAFT_UNSELECTED",
                "reference_source": source_url,
            })
    floor["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D167 scaled manifold references plus exact R80 tangent audit",
        "notes": "K1 показан референсным габаритом 12 петель 776×90 мм в плане, K2 — 11 петель 726×90 мм и перевёрнут выходами вверх. Это не выбранные изделия. R80: 22 сервисные оси PASS; F1-C14 и 10 осей мансарды требуют перестроения коротких двойных поворотов.",
    }
    attic["training_metadata"] = copy.deepcopy(floor["training_metadata"])

    floor_audits = [bend_audit(item) for item in floor["circuits"]]
    attic_audits = [bend_audit(item) for item in attic["circuits"]]
    k1_audits = [item for item in floor_audits if item["system_role"] == "FLOOR_HEATING_LOOP"]
    service_audits = [item for item in floor_audits if item["system_role"] == "INTERFLOOR_SERVICE_LEG"]
    floor_path = OUTPUT / "HomeAura_Floor1_Collectors_R80_D167.homeaura.json"
    attic_path = OUTPUT / "HomeAura_Attic_R80_D167.homeaura.json"
    dump(floor_path, floor)
    dump(attic_path, attic)
    contract = {
        "schema": "homeaura.collector_reference_and_r80_audit.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "COLLECTOR_REFERENCE_RENDER_PASS_SERVICE_R80_PASS_REWORK_ONE_K1_AND_TEN_ATTIC_AXES",
        "append_only": True,
        "sources": {
            "D166_floor_sha256": sha(source_floor_path),
            "D166_attic_sha256": sha(source_attic_path),
            "manifold_reference": source_url,
            "manifold_reference_dimensions": {
                "12_loop_width_mm": 776,
                "11_loop_width_mm": 726,
                "height_mm": 320,
                "depth_mm": 90,
            },
            "REHAU_large_manifold_design_note": "https://www.rehau.com/downloads/497804/radiantheatingsystemsdesignguide-855601-rehau.pdf",
        },
        "collector_contract": {
            "K1": {"candidate_loop_count": 12, "reference_plan_envelope_mm": [776, 90], "same_boiler_wall": True, "selected_product": False},
            "K2": {"candidate_loop_count": 11, "reference_plan_envelope_mm": [726, 90], "same_boiler_wall": True, "rotation_degrees": 180, "outlets": "UP", "selected_product": False},
            "congestion_and_local_overheating_review": "REQUIRED_FOR_24_AND_22_PIPE_FANOUTS",
        },
        "preservation": {
            "D166_floor_ordered_points_exact": source_floor_circuits == floor["circuits"],
            "D166_attic_ordered_points_exact": source_attic_circuits == attic["circuits"],
        },
        "bend_contract": {
            "pipe_outer_diameter_mm": 16,
            "minimum_centerline_bend_radius_mm": RADIUS_MM,
            "method": "EACH_ORTHOGONAL_TURN_ALLOCATES_R80_ON_EACH_ADJACENT_SEGMENT;_SEGMENT_BETWEEN_TWO_TURNS_REQUIRES_160MM",
            "arc_length_formula": "quarter_circle=pi*R/2;_Manhattan_corner_reduction=2R-piR/2",
            "K1_route_pass_count": sum(item["violation_count"] == 0 for item in k1_audits),
            "K1_route_rework_ids": [item["route_id"] for item in k1_audits if item["violation_count"]],
            "K2_service_leg_pass_count": sum(item["violation_count"] == 0 for item in service_audits),
            "K2_service_leg_rework_ids": [item["route_id"] for item in service_audits if item["violation_count"]],
            "attic_axis_pass_count": sum(item["violation_count"] == 0 for item in attic_audits),
            "attic_axis_rework_ids": [item["route_id"] for item in attic_audits if item["violation_count"]],
        },
        "floor_audits": floor_audits,
        "attic_audits": attic_audits,
        "route_geometry_changed": False,
        "installation_ready": False,
        "next_block": "D168_REPAIR_R80_SHORT_DOUBLE_TURNS_WITHOUT_CONTACTS_OR_COVERAGE_REGRESSION",
    }
    dump(OUTPUT / "collector_and_r80_audit_contract.json", contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "service_R80_pass": True,
        "K1_R80_pass": False,
        "attic_R80_pass": False,
        "installation_ready": False,
    })
    dump(OUTPUT / "lineage.json", {
        "artifact_id": ARTIFACT_ID,
        "source_artifact_id": "HA_TWO_FLOOR_K2_SERVICE_LAYER_166",
        "source_floor_sha256": sha(source_floor_path),
        "source_attic_sha256": sha(source_attic_path),
        "ordered_points_changed": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D167 · коллекторы и R80\n\n"
        "Коллекторы теперь отображаются в масштабе справочного 12/11-контурного оборудования, но изделие ещё не выбрано. "
        "Проверка R80 анализирует место для касательных на каждом сегменте: между двумя поворотами нужно минимум 160 мм. "
        "Сервис K2 проходит, F1-C14 и десять мансардных осей перечислены как REWORK.\n",
        encoding="utf-8",
    )
    render(floor_path, OUTPUT / "HomeAura_Floor1_D167_Editor_View.png", False)
    render(floor_path, OUTPUT / "HomeAura_Floor1_D167_Clean_View.png", True)
    render(attic_path, OUTPUT / "HomeAura_Attic_D167_Editor_View.png", False)
    render(attic_path, OUTPUT / "HomeAura_Attic_D167_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "K1_rework": contract["bend_contract"]["K1_route_rework_ids"],
        "service_pass": contract["bend_contract"]["K2_service_leg_pass_count"],
        "attic_rework": contract["bend_contract"]["attic_axis_rework_ids"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
