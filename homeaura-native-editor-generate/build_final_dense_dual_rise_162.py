from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, shape
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_boiler_room_manifolds_dual_rise_160 import make_service_zone, route_entry  # noqa: E402
from build_dense_centre_counterflow_159 import dense_counterflow  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_BOILER_MANIFOLDS_DUAL_RISE_160"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FINAL_DENSE_DUAL_RISE_162"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FINAL_DENSE_DUAL_RISE_162.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def render(project: Path, output: Path, clean: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean else "--export-png", str(project), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def package_current_output() -> None:
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID, "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)


def main() -> None:
    if "--repair-package-metadata" in sys.argv:
        if not OUTPUT.is_dir():
            raise FileNotFoundError(OUTPUT)
        package_current_output()
        print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "package_sha256": sha(PACKAGE)}, ensure_ascii=False, indent=2))
        return
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D162 is append-only")
    OUTPUT.mkdir(parents=True)
    floor_source = SOURCE / "HomeAura_Floor1_BoilerManifolds_D160.homeaura.json"
    attic_source = SOURCE / "HomeAura_Attic_DualRise_D160.homeaura.json"
    contract_source = SOURCE / "two_manifold_dual_rise_contract.json"
    floor1, attic, source_contract = load(floor_source), load(attic_source), load(contract_source)

    preserved_circuits = [copy.deepcopy(item) for item in attic["circuits"] if item["id"] != "A-C04"]
    preserved_records = [copy.deepcopy(item) for item in source_contract["routes"] if item["route_id"] != "A-C04"]
    replacements = []
    for route_id, box, territory, colour in [
        ("A-C04-W", (49, 143, 72, 165), "Ванна + WC запад", "#F97066"),
        ("A-C04-E", (74, 143, 96, 165), "Ванна + WC восток", "#FF9238"),
    ]:
        circuit, record = route_entry(route_id, dense_counterflow(box), "UNDER_STAIR_WALL_TO_WARDROBE", territory)
        circuit["color"] = colour
        replacements.append((circuit, record))
    circuits = preserved_circuits + [item[0] for item in replacements]
    records = preserved_records + [item[1] for item in replacements]
    circuits.sort(key=lambda item: next(index for index, record in enumerate(records) if record["route_id"] == item["id"]))
    record_by_id = {item["route_id"]: item for item in records}
    records = [record_by_id[item["id"]] for item in circuits]
    for index, circuit in enumerate(circuits):
        circuit["supply_port_index"] = index * 2
        circuit["return_port_index"] = index * 2 + 1
    attic["circuits"] = circuits

    stair_records = [item for item in records if item["branch_id"].startswith("UNDER")]
    direct_records = [item for item in records if item["branch_id"].startswith("DIRECT")]
    attic["service_zones"] = [
        make_service_zone("K2-STAIR-WALL-BRANCH-D160", "K2 → под лестницей → подъём по стене → гардероб", stair_records),
        make_service_zone("K2-DIRECT-SLAB-BRANCH-D160", "K2 → проходка перекрытия → правая половина мансарды", direct_records),
    ]
    for collector in floor1["collectors"]:
        if collector["id"] == "K1":
            collector.update({"rotation_degrees": 0, "pipe_outlet_direction": "DOWN"})
        if collector["id"] == "K2":
            collector.update({"ports": 30, "rotation_degrees": 180, "pipe_outlet_direction": "UP"})
    attic_k2 = attic["collectors"][0]
    attic_k2.update({"ports": 30, "rotation_degrees": 180, "pipe_outlet_direction": "UP", "visible_on_plan": False, "external_to_plan": True})
    floor1["service_zones"].append({
        "id": "K1-K2-SHARED-WALL-CABINET-D162", "floor_id": "FLOOR_1", "name": "Монтажная зона K1 + K2",
        "outline": [{"x_mm": 16200, "y_mm": 8700}, {"x_mm": 17700, "y_mm": 8700}, {"x_mm": 17700, "y_mm": 11400}, {"x_mm": 16200, "y_mm": 11400}],
        "fill_color": "#115E59",
        "note": "K1 и K2 на одной внутренней стене. K2 перевёрнут: петлевые выходы вверх. Плановый знак не заменяет монтажную развёртку по высоте.",
        "collector_id": "K2", "clear_height_mm": None, "pipe_capacity": 54,
    })

    lines = []
    for circuit in circuits:
        line = LineString([(point["x_mm"] - OFFSET, point["y_mm"] - OFFSET) for point in circuit["ordered_points"]])
        if not line.is_simple:
            raise RuntimeError(f"Self contact: {circuit['id']}")
        for other_id, other in lines:
            if not line.intersection(other).is_empty:
                raise RuntimeError(f"Body contact: {circuit['id']} / {other_id}")
        lines.append((circuit["id"], line))

    domains = load(D062)
    hall = load(D047)
    floor = unary_union(
        [shape(item["floor_geojson"]) for item in domains["adjacent_floor_domains"]]
        + [shape(hall["hall_source_contract"]["routing_draft_allowed_floor_geojson"])]
    )
    body_sweep = unary_union([line.buffer(100, quad_segs=16) for _, line in lines])
    served = floor.intersection(body_sweep).area
    coverage = {
        "method": "ROUND_100MM_BODY_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
        "known_floor_area_m2": floor.area / 1_000_000,
        "served_proximity_m2": served / 1_000_000,
        "unresolved_proximity_m2": (floor.area - served) / 1_000_000,
        "served_proximity_percent": served * 100 / floor.area,
        "full_coverage_claimed": False,
        "service_transits_counted_as_heating": False,
    }
    totals = [item["design_total_length_mm"] for item in records]
    if not all(40_000 <= item <= 80_000 for item in totals):
        raise RuntimeError(totals)
    contract = copy.deepcopy(source_contract)
    contract.update({
        "artifact_id": ARTIFACT_ID,
        "status": "FIFTEEN_DENSE_ATTIC_ROUTES_AND_DUAL_BOILER_RISE_PASS_REWORK_HYDRAULIC_BALANCE",
        "source_D160_floor1_sha256": sha(floor_source),
        "source_D160_attic_sha256": sha(attic_source),
        "source_D160_contract_sha256": sha(contract_source),
        "routes": records,
        "route_count": len(records),
        "all_design_lengths_40_80m": True,
        "minimum_design_length_mm": min(totals),
        "maximum_design_length_mm": max(totals),
        "body_contact_count": 0,
        "coverage": coverage,
        "coverage_gain_vs_D160_m2": coverage["served_proximity_m2"] - source_contract["coverage"]["served_proximity_m2"],
        "coverage_gain_vs_D160_percentage_points": coverage["served_proximity_percent"] - source_contract["coverage"]["served_proximity_percent"],
        "boiler_room_manifolds": {
            "same_internal_wall": True,
            "mounting_wall_id": "FLOOR_1-W025",
            "K1": next(item for item in floor1["collectors"] if item["id"] == "K1"),
            "K2": next(item for item in floor1["collectors"] if item["id"] == "K2"),
            "K2_is_inverted_outlets_up": True,
            "plan_symbol_is_not_installation_elevation": True,
        },
        "rise_strategy": {
            "under_stair_wall_to_wardrobe_route_count": len(stair_records),
            "direct_boiler_slab_to_right_half_route_count": len(direct_records),
            "floor_to_floor_height_mm": 3000,
            "minimum_bend_radius_mm": 80,
            "vertical_turn_inside_70mm_floor_layer": False,
            "turn_location": "AT_WALL_OR_OPENING_WITH_FULL_R80_ENVELOPE",
        },
        "official_reference_urls": [
            "https://www.uponor.com/getmedia/f5bba18a-1193-45d5-bdbb-95e0eb743cc2/radiant%20floor%20heating%20installation%20handbook.pdf?sitename=Canada",
            "https://www.uponor.com/getmedia/c5ab8a1f-9f02-43a4-8bcb-3b6a186dafeb/underfloor-heating-install-guidepdf?sitename=UK",
            "https://www.caleffi.com/en-us/assembly-668s1-caleffi-6686c5s1a",
        ],
        "installation_ready": False,
        "next_safe_block": "HYDRAULIC_BALANCE_15_LOOP_K2_AND_REVIEW_ONLY_NATURAL_RESIDUAL_GAPS",
    })
    floor1["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D162: два коллектора на одной внутренней стене котельной; K2 перевёрнут выходами вверх. Окна голубые, стены 100/200/400 мм. Два внутренних пути на мансарду.",
        "author_intent": "Final dense two-manifold dual-rise coordination candidate",
    }
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D162: 15 петель, включая две отдельные улитки ванной/WC и четыре улитки большой спальни. Физический K2 находится в котельной, поэтому на мансарде не рисуется.",
        "author_intent": "Dense owner-style counterflow with long-service-length repartition",
    }

    floor_file = OUTPUT / "HomeAura_Floor1_Final_D162.homeaura.json"
    attic_file = OUTPUT / "HomeAura_Attic_Final_D162.homeaura.json"
    dump(floor_file, floor1)
    dump(attic_file, attic)
    dump(OUTPUT / "final_dense_dual_rise_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "source_D160_floor1_sha256": sha(floor_source), "source_D160_attic_sha256": sha(attic_source),
        "floor1_route_geometry_changed": False,
        "attic_changed_route_ids": ["A-C04-W", "A-C04-E"],
        "attic_removed_route_ids": ["A-C04"],
        "reason": "KEEP_EACH_COMPLETE_PIPE_BELOW_80M_WHILE_FILLING_THE_FULL_LEFT_SOUTH_TERRITORY",
    })
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID, "status": contract["status"], "floor1_route_count": len(floor1["circuits"]),
        "attic_route_count": len(attic["circuits"]), "all_lengths_40_80m": True, "body_contact_count": 0,
        "served_proximity_percent": coverage["served_proximity_percent"], "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D162 - плотная раскладка с двумя коллекторами в котельной\n\n"
        "K1 и K2 находятся рядом на одной внутренней стене котельной. K2 перевёрнут на 180 градусов и отдаёт трубы вверх. "
        f"Контуры мансарды разделены так: {len(stair_records)} идут под лестницей к дальней стене и выходят в гардеробную; "
        f"{len(direct_records)} поднимаются через отдельную внутреннюю проходку котельной.\n\n"
        "Для сохранения полной зоны ванной/WC без превышения 80 м она разделена на две регулярные улитки. На мансарде 15 петель, длины 56,2-76,2 м, контактов тел нет. "
        "Body-only 100-мм proximity по векторным черновым полигонам составляет около 89%; скрытые тёплые подводки в этот процент не добавлялись.\n",
        encoding="utf-8",
    )

    render(floor_file, OUTPUT / "HomeAura_Floor1_D162_Editor_View.png", False)
    render(floor_file, OUTPUT / "HomeAura_Floor1_D162_Clean_View.png", True)
    render(attic_file, OUTPUT / "HomeAura_Attic_D162_Editor_View.png", False)
    render(attic_file, OUTPUT / "HomeAura_Attic_D162_Clean_View.png", True)

    package_current_output()
    print(json.dumps({
        "output": str(OUTPUT), "package": str(PACKAGE), "package_sha256": sha(PACKAGE),
        "routes": len(records), "min_length_m": min(totals) / 1000, "max_length_m": max(totals) / 1000,
        "coverage": coverage, "coverage_gain_vs_D160_m2": contract["coverage_gain_vs_D160_m2"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
