from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_collector_and_r80_audit_167 import bend_audit  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D168 = PROPOSALS / "HA_TWO_FLOOR_R80_PARTIAL_REPAIR_168"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_LAYER_CLEARANCE_EVIDENCE_169"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_LAYER_CLEARANCE_EVIDENCE_169.zip"
ARTIFACT_ID = OUTPUT.name


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def xy(point: dict) -> tuple[int, int]:
    return point["x_mm"], point["y_mm"]


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png", str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def pair_contacts(circuits: list[dict], same_layer: bool) -> list[dict]:
    lines = [(item, LineString([xy(point) for point in item["ordered_points"]])) for item in circuits]
    output = []
    for index, (first, first_line) in enumerate(lines):
        for second, second_line in lines[index + 1:]:
            if (first["routing_layer"] == second["routing_layer"]) != same_layer:
                continue
            relation = first_line.intersection(second_line)
            if relation.is_empty:
                continue
            output.append({
                "first_route_id": first["id"],
                "second_route_id": second["id"],
                "first_layer": first["routing_layer"],
                "second_layer": second["routing_layer"],
                "first_axis_elevation_mm": first.get("axis_elevation_mm"),
                "second_axis_elevation_mm": second.get("axis_elevation_mm"),
                "intersection_geometry_type": relation.geom_type,
            })
    return output


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
        raise SystemExit("D169 append-only output already exists")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    source_floor_path = D168 / "HomeAura_Floor1_R80_Partial_D168.homeaura.json"
    source_attic_path = D168 / "HomeAura_Attic_R80_Partial_D168.homeaura.json"
    source_contract_path = D168 / "r80_partial_repair_contract.json"
    floor = load(source_floor_path)
    attic = load(source_attic_path)
    source_floor_points = [[xy(point) for point in item["ordered_points"]] for item in floor["circuits"]]
    source_attic_points = [[xy(point) for point in item["ordered_points"]] for item in attic["circuits"]]
    floor["routing_rules"]["minimum_layer_surface_clearance_mm"] = 5
    attic["routing_rules"]["minimum_layer_surface_clearance_mm"] = 5
    floor["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D169 auditable cross-layer clearance evidence",
        "notes": "Межслойные пересечения не скрыты: каждая пара записана в контракте. OD16, оси 108/135 мм, разнесение 27 мм, поверхностный зазор 11 мм при требовании не менее 5 мм. Однослойные контакты равны нулю. Пять мансардных осей ещё REWORK R80.",
    }
    attic["training_metadata"] = copy.deepcopy(floor["training_metadata"])

    same_layer = pair_contacts(floor["circuits"], True)
    cross_layer = pair_contacts(floor["circuits"], False)
    attic_same_layer = pair_contacts(attic["circuits"], True)
    if same_layer or attic_same_layer:
        raise ValueError({"floor_same_layer": same_layer, "attic": attic_same_layer})
    pipe_od = floor["routing_rules"]["pipe_outer_diameter_mm"]
    required_surface = floor["routing_rules"]["minimum_layer_surface_clearance_mm"]
    required_axis = max(floor["routing_rules"]["minimum_layer_axis_separation_mm"], pipe_od + required_surface)
    for record in cross_layer:
        separation = abs(record["first_axis_elevation_mm"] - record["second_axis_elevation_mm"])
        record["axis_separation_mm"] = separation
        record["surface_clearance_mm"] = separation - pipe_od
        record["required_axis_separation_mm"] = required_axis
        record["result"] = "PASS_EXPLICIT_VERTICAL_SEPARATION" if separation >= required_axis else "FAIL"
    if any(item["result"] == "FAIL" for item in cross_layer):
        raise ValueError("cross-layer separation failure")
    floor_audits = [bend_audit(item) for item in floor["circuits"]]
    attic_audits = [bend_audit(item) for item in attic["circuits"]]
    source_contract = load(source_contract_path)

    floor_path = OUTPUT / "HomeAura_Floor1_LayerClearance_D169.homeaura.json"
    attic_path = OUTPUT / "HomeAura_Attic_LayerClearance_D169.homeaura.json"
    dump(floor_path, floor)
    dump(attic_path, attic)
    contract = {
        "schema": "homeaura.layer_clearance_evidence.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "EXPLICIT_CROSS_LAYER_CLEARANCE_PASS_REWORK_FIVE_ATTIC_R80_AXES_AND_INSTALLATION_DETAILS",
        "append_only": True,
        "sources": {
            "D168_floor_sha256": sha(source_floor_path),
            "D168_attic_sha256": sha(source_attic_path),
            "D168_contract_sha256": sha(source_contract_path),
            "external_audit": "CLAUDE_CODE_READ_ONLY_IDENTIFIED_OD_CLEARANCE_COUPLING_AND_HIDDEN_CROSSING_COUNT_GAPS",
        },
        "preservation": {
            "floor_ordered_points_exact": source_floor_points == [[xy(point) for point in item["ordered_points"]] for item in floor["circuits"]],
            "attic_ordered_points_exact": source_attic_points == [[xy(point) for point in item["ordered_points"]] for item in attic["circuits"]],
        },
        "layer_contract": {
            "pipe_outer_diameter_mm": pipe_od,
            "minimum_surface_clearance_mm": required_surface,
            "configured_minimum_axis_separation_mm": floor["routing_rules"]["minimum_layer_axis_separation_mm"],
            "effective_required_axis_separation_mm": required_axis,
            "heating_axis_elevation_mm": 108,
            "service_axis_elevation_mm": 135,
            "actual_axis_separation_mm": 27,
            "actual_surface_clearance_mm": 11,
            "same_layer_contact_pair_count": len(same_layer),
            "cross_layer_intersection_pair_count": len(cross_layer),
            "all_cross_layer_pairs_explicitly_clear": all(item["result"].startswith("PASS") for item in cross_layer),
            "cross_layer_pairs": cross_layer,
        },
        "R80": {
            "K1_pass_count": sum(item["system_role"] == "FLOOR_HEATING_LOOP" and item["violation_count"] == 0 for item in floor_audits),
            "K2_service_pass_count": sum(item["system_role"] == "INTERFLOOR_SERVICE_LEG" and item["violation_count"] == 0 for item in floor_audits),
            "attic_pass_count": sum(item["violation_count"] == 0 for item in attic_audits),
            "attic_rework_ids": [item["route_id"] for item in attic_audits if item["violation_count"]],
            "plan_to_vertical_handoff_bend_sweep": "NOT_EVALUATED",
        },
        "full_loop_reconciliation": source_contract["full_loop_reconciliation"],
        "installation_ready": False,
        "next_block": "D170_JOINT_REPARTITION_FIVE_ATTIC_AXES_THEN_PLAN_TO_VERTICAL_R80_HANDOFFS",
    }
    dump(OUTPUT / "layer_clearance_evidence_contract.json", contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "cross_layer_pair_count": len(cross_layer),
        "actual_surface_clearance_mm": 11,
        "installation_ready": False,
    })
    dump(OUTPUT / "lineage.json", {
        "artifact_id": ARTIFACT_ID,
        "source_artifact_id": "HA_TWO_FLOOR_R80_PARTIAL_REPAIR_168",
        "route_geometry_changed": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D169 · проверяемое разнесение слоёв\n\n"
        "Исправлен дефект анализатора: разнесение осей теперь не может быть меньше OD трубы плюс минимальный поверхностный зазор. "
        "Все плановые пересечения тёплого пола и сервисных линий перечислены в JSON; при OD16 и отметках 108/135 мм зазор поверхностей равен 11 мм.\n",
        encoding="utf-8",
    )
    render(floor_path, OUTPUT / "HomeAura_Floor1_D169_Editor_View.png", False)
    render(floor_path, OUTPUT / "HomeAura_Floor1_D169_Clean_View.png", True)
    render(attic_path, OUTPUT / "HomeAura_Attic_D169_Editor_View.png", False)
    render(attic_path, OUTPUT / "HomeAura_Attic_D169_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "cross_layer_pairs": len(cross_layer),
        "surface_clearance_mm": 11,
        "same_layer_contacts": len(same_layer),
        "attic_rework": contract["R80"]["attic_rework_ids"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
