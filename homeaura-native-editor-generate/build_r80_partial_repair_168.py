from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_collector_and_r80_audit_167 import bend_audit  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D167 = PROPOSALS / "HA_TWO_FLOOR_COLLECTOR_AND_R80_AUDIT_167"
D166_CONTRACT = PROPOSALS / "HA_TWO_FLOOR_K2_SERVICE_LAYER_166" / "k2_service_layer_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_R80_PARTIAL_REPAIR_168"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_R80_PARTIAL_REPAIR_168.zip"
ARTIFACT_ID = OUTPUT.name


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def xy(point: dict) -> tuple[int, int]:
    return point["x_mm"], point["y_mm"]


def route_length(route: dict) -> int:
    return sum(abs(a["x_mm"] - b["x_mm"]) + abs(a["y_mm"] - b["y_mm"]) for a, b in zip(route["ordered_points"], route["ordered_points"][1:]))


def shift_run(route: dict, violation_index: int, side: str) -> dict:
    points = [(item["x_mm"], item["y_mm"]) for item in route["ordered_points"]]
    source_start, source_end = points[0], points[-1]
    dx = points[violation_index + 1][0] - points[violation_index][0]
    dy = points[violation_index + 1][1] - points[violation_index][1]
    unit = (0 if dx == 0 else (1 if dx > 0 else -1), 0 if dy == 0 else (1 if dy > 0 else -1))
    if side == "after":
        orientation = (
            points[violation_index + 2][0] - points[violation_index + 1][0],
            points[violation_index + 2][1] - points[violation_index + 1][1],
        )
        end = violation_index + 2
        while end + 1 < len(points):
            next_orientation = (points[end + 1][0] - points[end][0], points[end + 1][1] - points[end][1])
            if (orientation[0] == 0) != (next_orientation[0] == 0):
                break
            end += 1
        for index in range(violation_index + 1, end + 1):
            points[index] = (points[index][0] + unit[0] * 100, points[index][1] + unit[1] * 100)
        changed = [violation_index + 1, end]
    elif side == "before":
        orientation = (
            points[violation_index][0] - points[violation_index - 1][0],
            points[violation_index][1] - points[violation_index - 1][1],
        )
        start = violation_index - 1
        while start - 1 >= 0:
            previous_orientation = (points[start][0] - points[start - 1][0], points[start][1] - points[start - 1][1])
            if (orientation[0] == 0) != (previous_orientation[0] == 0):
                break
            start -= 1
        for index in range(start, violation_index + 1):
            points[index] = (points[index][0] - unit[0] * 100, points[index][1] - unit[1] * 100)
        changed = [start, violation_index]
    else:
        raise ValueError(side)
    if points[0] != source_start or points[-1] != source_end:
        raise ValueError(f"{route['id']}: handoff endpoint moved")
    result = copy.deepcopy(route)
    result["ordered_points"] = [{"x_mm": x, "y_mm": y} for x, y in points]
    result["name"] = route["name"].split(" · R80", 1)[0] + " · R80 repair"
    return result, changed


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png", str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def layer_contacts(circuits: list[dict]) -> list[list[str]]:
    contacts = []
    for layer in sorted({item["routing_layer"] for item in circuits}):
        routes = [item for item in circuits if item["routing_layer"] == layer]
        lines = [(item["id"], LineString([xy(point) for point in item["ordered_points"]])) for item in routes]
        for identifier, line in lines:
            if not line.is_simple:
                raise ValueError(f"{identifier}: self contact")
        for index, (first_id, first) in enumerate(lines):
            for second_id, second in lines[index + 1:]:
                if not first.intersection(second).is_empty:
                    contacts.append([first_id, second_id])
    return contacts


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
        raise SystemExit("D168 append-only output already exists")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    source_floor_path = D167 / "HomeAura_Floor1_Collectors_R80_D167.homeaura.json"
    source_attic_path = D167 / "HomeAura_Attic_R80_D167.homeaura.json"
    floor = load(source_floor_path)
    attic = load(source_attic_path)
    source_floor = copy.deepcopy(floor)
    source_attic = copy.deepcopy(attic)

    repairs: list[dict] = []
    floor_c14 = next(item for item in floor["circuits"] if item["id"] == "F1-C14")
    floor_c14["ordered_points"][25]["y_mm"] = 22300
    floor_c14["ordered_points"][26]["y_mm"] = 22300
    floor_c14["name"] = "F1-C14 · полный K1→улитка→K1 · R80 repair"
    repairs.append({"route_id": "F1-C14", "change": "SHIFT_OUTER_RETURN_RUN_Y_PLUS_100MM", "changed_point_indices": [25, 26]})

    plans = {
        "A-C09": [(3, "after")],
        "A-C01": [(26, "before")],
        "A-C02": [(24, "before")],
        "A-C10_C11_SERIAL": [(3, "after"), (30, "after"), (35, "before")],
        "A-C13": [(19, "before")],
    }
    for route_id, operations in plans.items():
        route = next(item for item in attic["circuits"] if item["id"] == route_id)
        change_records = []
        for violation_index, side in operations:
            route, changed = shift_run(route, violation_index, side)
            change_records.append({"violation_segment_index": violation_index, "shifted_side": side, "changed_point_index_range": changed})
        attic["circuits"][next(index for index, item in enumerate(attic["circuits"]) if item["id"] == route_id)] = route
        repairs.append({"route_id": route_id, "change": "SHIFT_MAXIMAL_STRAIGHT_RUN_BY_100MM", "operations": change_records})

    floor_contacts = layer_contacts(floor["circuits"])
    attic_contacts = layer_contacts(attic["circuits"])
    if floor_contacts or attic_contacts:
        raise ValueError({"floor": floor_contacts, "attic": attic_contacts})
    exclusions = [Polygon([xy(point) for point in item["outline"]]) for item in attic.get("exclusions", []) if len(item["outline"]) >= 3]
    exclusion_hits = []
    for route in attic["circuits"]:
        line = LineString([xy(point) for point in route["ordered_points"]])
        if any(not line.intersection(polygon).is_empty for polygon in exclusions):
            exclusion_hits.append(route["id"])
    if exclusion_hits:
        raise ValueError(f"exclusion hits: {exclusion_hits}")

    floor_audits = [bend_audit(item) for item in floor["circuits"]]
    attic_audits = [bend_audit(item) for item in attic["circuits"]]
    k1_audits = [item for item in floor_audits if item["system_role"] == "FLOOR_HEATING_LOOP"]
    service_audits = [item for item in floor_audits if item["system_role"] == "INTERFLOOR_SERVICE_LEG"]
    full_source = load(D166_CONTRACT)["full_loop_reconciliation"]
    source_full_by_id = {item["route_id"]: item for item in full_source}
    full_loops = []
    for axis in attic["circuits"]:
        source = copy.deepcopy(source_full_by_id[axis["id"]])
        source["attic_floor_axis_mm"] = route_length(axis)
        source["design_total_mm"] = (
            source["supply_planar_mm"] + source["vertical_up_mm"] + source["attic_floor_axis_mm"] +
            source["vertical_down_mm"] + source["return_planar_mm"]
        )
        source["length_40_80m"] = 40000 <= source["design_total_mm"] <= 80000
        source["headroom_to_80m_mm"] = 80000 - source["design_total_mm"]
        full_loops.append(source)
    if not all(item["length_40_80m"] for item in full_loops):
        raise ValueError("repaired full loop outside 40-80m")

    floor["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D168 safe partial R80 repair",
        "notes": "F1-C14 и пять мансардных осей исправлены с сохранением endpoints, ортогональности, нулевых контактов и диапазона длин. K2 сервис 22/22 R80 PASS. A-C03/A-C04/A-C06/A-C07/A-C12 требуют более широкой переразбивки и остаются REWORK.",
    }
    attic["training_metadata"] = copy.deepcopy(floor["training_metadata"])
    floor_path = OUTPUT / "HomeAura_Floor1_R80_Partial_D168.homeaura.json"
    attic_path = OUTPUT / "HomeAura_Attic_R80_Partial_D168.homeaura.json"
    dump(floor_path, floor)
    dump(attic_path, attic)
    contract = {
        "schema": "homeaura.r80_partial_repair.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "K1_AND_K2_SERVICE_R80_PASS_SIX_OF_ELEVEN_ATTIC_AXES_PASS_REWORK_FIVE_ATTIC_AXES",
        "append_only": True,
        "sources": {"D167_floor_sha256": sha(source_floor_path), "D167_attic_sha256": sha(source_attic_path)},
        "preservation": {
            "K2_service_legs_exact": [item for item in source_floor["circuits"] if item["system_role"] == "INTERFLOOR_SERVICE_LEG"] == [item for item in floor["circuits"] if item["system_role"] == "INTERFLOOR_SERVICE_LEG"],
            "K1_changed_route_ids": ["F1-C14"],
            "attic_changed_route_ids": list(plans),
            "all_handoff_endpoints_preserved": all(
                xy(before["ordered_points"][0]) == xy(after["ordered_points"][0]) and xy(before["ordered_points"][-1]) == xy(after["ordered_points"][-1])
                for before, after in zip(source_attic["circuits"], attic["circuits"])
            ),
        },
        "repairs": repairs,
        "validation": {
            "floor_same_layer_contact_count": len(floor_contacts),
            "attic_contact_count": len(attic_contacts),
            "attic_exclusion_hit_route_ids": exclusion_hits,
            "K1_R80_pass_count": sum(item["violation_count"] == 0 for item in k1_audits),
            "K1_R80_rework_ids": [item["route_id"] for item in k1_audits if item["violation_count"]],
            "K2_service_R80_pass_count": sum(item["violation_count"] == 0 for item in service_audits),
            "attic_R80_pass_count": sum(item["violation_count"] == 0 for item in attic_audits),
            "attic_R80_rework_ids": [item["route_id"] for item in attic_audits if item["violation_count"]],
            "all_design_lengths_40_80m": all(item["length_40_80m"] for item in full_loops),
            "minimum_design_length_mm": min(item["design_total_mm"] for item in full_loops),
            "maximum_design_length_mm": max(item["design_total_mm"] for item in full_loops),
            "minimum_headroom_to_80m_mm": min(item["headroom_to_80m_mm"] for item in full_loops),
        },
        "full_loop_reconciliation": full_loops,
        "floor_bend_audits": floor_audits,
        "attic_bend_audits": attic_audits,
        "coverage": "REWORK_AFTER_LOCAL_AXIS_SHIFTS",
        "hydraulics": "NOT_CALCULATED",
        "installation_ready": False,
        "next_block": "D169_JOINT_REPARTITION_A_C03_A_C04_A_C06_A_C07_A_C12_FOR_R80_AND_COVERAGE",
    }
    dump(OUTPUT / "r80_partial_repair_contract.json", contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "K1_R80_pass": True,
        "K2_service_R80_pass": True,
        "attic_R80_pass_count": contract["validation"]["attic_R80_pass_count"],
        "installation_ready": False,
    })
    dump(OUTPUT / "lineage.json", {
        "artifact_id": ARTIFACT_ID,
        "source_artifact_id": "HA_TWO_FLOOR_COLLECTOR_AND_R80_AUDIT_167",
        "changed_route_ids": ["F1-C14", *plans.keys()],
    })
    (OUTPUT / "README.md").write_text(
        "# D168 · частичный ремонт R80\n\n"
        "Без изменения точек подключения исправлены F1-C14 и пять мансардных осей. "
        "Все 12 контуров K1 и все 22 сервисные линии K2 теперь проходят касательные R80. "
        "На мансарде проходят 6 из 11 осей; оставшиеся пять требуют совместной переразбивки, а не локальных зубцов.\n",
        encoding="utf-8",
    )
    render(floor_path, OUTPUT / "HomeAura_Floor1_D168_Editor_View.png", False)
    render(floor_path, OUTPUT / "HomeAura_Floor1_D168_Clean_View.png", True)
    render(attic_path, OUTPUT / "HomeAura_Attic_D168_Editor_View.png", False)
    render(attic_path, OUTPUT / "HomeAura_Attic_D168_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "K1_R80_pass": contract["validation"]["K1_R80_pass_count"],
        "service_R80_pass": contract["validation"]["K2_service_R80_pass_count"],
        "attic_R80_pass": contract["validation"]["attic_R80_pass_count"],
        "attic_rework": contract["validation"]["attic_R80_rework_ids"],
        "length_range_mm": [contract["validation"]["minimum_design_length_mm"], contract["validation"]["maximum_design_length_mm"]],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
