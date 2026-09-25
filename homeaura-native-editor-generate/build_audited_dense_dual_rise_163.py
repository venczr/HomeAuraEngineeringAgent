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
from build_owner_style_installation_project_141 import clean, length_mm  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FINAL_DENSE_DUAL_RISE_162"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_AUDITED_DENSE_DUAL_RISE_163"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_AUDITED_DENSE_DUAL_RISE_163.zip"
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


def replacement(route_id: str, body: list[tuple[int, int]], territory: str, color: str) -> tuple[dict, dict]:
    circuit, record = route_entry(route_id, body, "DIRECT_BOILER_SLAB_TO_RIGHT_HALF", territory)
    circuit["color"] = color
    return circuit, record


def reserve_zone(zone: dict, required_pipes: int, required_width_mm: int) -> dict:
    zone.update({
        "pipe_capacity": None,
        "required_pipe_count": required_pipes,
        "required_plan_width_mm": required_width_mm,
        "pipe_geometry_materialized": False,
        "note": zone.get("note", "") + " Коридор показывает резерв, а не совпадающие оси труб; полосы ещё не назначены.",
    })
    return zone


def package_current_output() -> None:
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
    if "--rerender-and-repackage" in sys.argv:
        floor_file = OUTPUT / "HomeAura_Floor1_Audited_D163.homeaura.json"
        attic_file = OUTPUT / "HomeAura_Attic_Audited_D163.homeaura.json"
        if not floor_file.is_file() or not attic_file.is_file():
            raise FileNotFoundError(OUTPUT)
        render(floor_file, OUTPUT / "HomeAura_Floor1_D163_Editor_View.png", False)
        render(floor_file, OUTPUT / "HomeAura_Floor1_D163_Clean_View.png", True)
        render(attic_file, OUTPUT / "HomeAura_Attic_D163_Editor_View.png", False)
        render(attic_file, OUTPUT / "HomeAura_Attic_D163_Clean_View.png", True)
        package_current_output()
        print(json.dumps({"package": str(PACKAGE), "package_sha256": sha(PACKAGE)}, ensure_ascii=False, indent=2))
        return
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D163 is append-only")
    OUTPUT.mkdir(parents=True)

    floor_source = SOURCE / "HomeAura_Floor1_Final_D162.homeaura.json"
    attic_source = SOURCE / "HomeAura_Attic_Final_D162.homeaura.json"
    contract_source = SOURCE / "final_dense_dual_rise_contract.json"
    floor1, attic, source_contract = load(floor_source), load(attic_source), load(contract_source)

    old_circuits = {item["id"]: copy.deepcopy(item) for item in attic["circuits"]}
    old_records = {item["route_id"]: copy.deepcopy(item) for item in source_contract["routes"]}
    replaced_ids = {"A-C08", "A-C12", "A-C05"}
    circuits = [item for key, item in old_circuits.items() if key not in replaced_ids]
    records = [item for key, item in old_records.items() if key not in replaced_ids]

    additions: list[tuple[dict, dict]] = []
    additions.append(replacement("A-C08-N", dense_counterflow((133, 58, 159, 80)), "Детская восток — север", "#3B82F6"))
    additions.append(replacement("A-C08-S", dense_counterflow((133, 82, 159, 104)), "Детская восток — юг", "#60A5FA"))

    left = list(reversed(dense_counterflow((133, 130, 158, 148))))
    right = [(345 - x, y) for x, y in dense_counterflow((160, 130, 185, 148))]
    additions.append(replacement("A-C12", clean([*left, *right]), "Спальня — двойная регулярная улитка", "#FB923C"))

    c05_body = [tuple(point) for point in old_records["A-C05"]["body_points_grid"]]
    c05_body = [(119 if point in {(117, 105), (117, 103)} else point[0], point[1]) for point in c05_body]
    additions.append(replacement("A-C05", c05_body, "Холл — уплотнённый центр", "#14B8A6"))

    circuits.extend(item[0] for item in additions)
    records.extend(item[1] for item in additions)
    circuit_by_id = {item["id"]: item for item in circuits}
    record_by_id = {item["route_id"]: item for item in records}
    route_order = [
        "A-C01", "A-C02-W", "A-C02-E", "A-C03-W", "A-C03-E", "A-C04-W", "A-C04-E",
        "A-C08-N", "A-C08-S", "A-C09", "A-C10_C11", "A-C12", "A-C13", "A-C05", "A-C06", "A-C07",
    ]
    circuits = [circuit_by_id[item] for item in route_order]
    records = [record_by_id[item] for item in route_order]
    for index, circuit in enumerate(circuits):
        circuit["supply_port_index"] = index * 2
        circuit["return_port_index"] = index * 2 + 1
    attic["circuits"] = circuits

    stair_records = [item for item in records if item["branch_id"].startswith("UNDER")]
    direct_records = [item for item in records if item["branch_id"].startswith("DIRECT")]
    attic["service_zones"] = [
        reserve_zone(make_service_zone("K2-STAIR-WALL-BRANCH-D163", "K2 → под лестницей → дальняя стена → гардероб", stair_records), 14, 1800),
        reserve_zone(make_service_zone("K2-DIRECT-SLAB-BRANCH-D163", "K2 → внутренняя проходка перекрытия → правая половина", direct_records), 18, 2300),
    ]
    for circuit in circuits:
        circuit["service_zone_id"] = "K2-STAIR-WALL-BRANCH-D163" if circuit["id"] in {item["route_id"] for item in stair_records} else "K2-DIRECT-SLAB-BRANCH-D163"

    for project in (floor1, attic):
        project["routing_rules"]["transit_lane_geometry_verified"] = False
        project["routing_rules"]["exterior_edge_zone_applied"] = False
    for collector in floor1["collectors"]:
        if collector["id"] == "K2":
            collector.update({"ports": 32, "rotation_degrees": 180, "pipe_outlet_direction": "UP"})
    attic["collectors"][0].update({"ports": 32, "rotation_degrees": 180, "pipe_outlet_direction": "UP", "visible_on_plan": False, "external_to_plan": True})

    for zone in floor1["service_zones"]:
        if zone["id"] == "K2-STAIR-WALL-FLOOR-D160":
            zone.update({"id": "K2-STAIR-WALL-FLOOR-D163", "pipe_capacity": None, "required_pipe_count": 14, "required_plan_width_mm": 1800, "pipe_geometry_materialized": False})
        elif zone["id"] == "K2-DIRECT-SLAB-D160":
            zone.update({"id": "K2-DIRECT-SLAB-D163", "pipe_capacity": None, "required_pipe_count": 18, "required_plan_width_mm": 2300, "pipe_geometry_materialized": False})
        elif zone["id"] == "K1-K2-SHARED-WALL-CABINET-D162":
            zone.update({"id": "K1-K2-SHARED-WALL-CABINET-D163", "pipe_capacity": 56, "required_pipe_count": 56, "pipe_geometry_materialized": False})
    floor1["service_zones"] = [
        zone for zone in floor1["service_zones"]
        if zone["id"] != "K1-K2-SHARED-WALL-CABINET-D162"
    ]

    hall_room = next(item for item in attic["rooms"] if item["id"] == "A-R09")
    hall_room["area_m2"] = 35.9

    lines: list[tuple[str, LineString]] = []
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
        "scope": "ATTIC_VECTOR_DRAFT_DOMAINS_ONLY",
        "method": "ROUND_100MM_BODY_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
        "known_floor_area_m2": floor.area / 1_000_000,
        "served_proximity_m2": served / 1_000_000,
        "unresolved_proximity_m2": (floor.area - served) / 1_000_000,
        "served_proximity_percent": served * 100 / floor.area,
        "full_coverage_claimed": False,
        "service_transits_counted_as_heating": False,
        "stair_void_is_outside_known_floor_domain": True,
    }
    totals = [item["design_total_length_mm"] for item in records]
    if not all(40_000 <= item <= 80_000 for item in totals):
        raise RuntimeError(totals)

    floor1_lengths = []
    for circuit in floor1["circuits"]:
        points = [(item["x_mm"], item["y_mm"]) for item in circuit["ordered_points"]]
        axis = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:]))
        floor1_lengths.append(axis + circuit.get("concealed_service_length_mm", 0))

    contract = copy.deepcopy(source_contract)
    contract.update({
        "artifact_id": ARTIFACT_ID,
        "status": "SIXTEEN_DENSE_ATTIC_BODIES_PASS_TRANSIT_CORRIDORS_RESERVATION_ONLY_REWORK_LANE_ROUTING_AND_HYDRAULICS",
        "source_D162_floor1_sha256": sha(floor_source),
        "source_D162_attic_sha256": sha(attic_source),
        "source_D162_contract_sha256": sha(contract_source),
        "routes": records,
        "route_count": len(records),
        "attic_all_design_lengths_40_80m": True,
        "all_design_lengths_40_80m": True,
        "minimum_design_length_mm": min(totals),
        "maximum_design_length_mm": max(totals),
        "floor1_length_summary": {"source": "D162_UNCHANGED_D159_GEOMETRY", "count": len(floor1_lengths), "minimum_mm": min(floor1_lengths), "maximum_mm": max(floor1_lengths), "all_40_80m": all(40_000 <= item <= 80_000 for item in floor1_lengths)},
        "body_contact_count": 0,
        "coverage": coverage,
        "coverage_gain_vs_D162_m2": coverage["served_proximity_m2"] - source_contract["coverage"]["served_proximity_m2"],
        "coverage_gain_vs_D162_percentage_points": coverage["served_proximity_percent"] - source_contract["coverage"]["served_proximity_percent"],
        "rise_strategy": {
            "under_stair_wall_to_wardrobe_route_count": len(stair_records),
            "direct_boiler_slab_to_right_half_route_count": len(direct_records),
            "floor_to_floor_height_mm": 3000,
            "minimum_bend_radius_mm": 80,
            "vertical_turn_inside_70mm_floor_layer": False,
            "turn_location": "AT_WALL_OR_OPENING_WITH_FULL_R80_ENVELOPE",
            "plan_axes_are_schematic_reservations_not_pipe_centerlines": True,
            "transit_lane_separation_verified": False,
            "under_stair_required_pipe_count": 14,
            "direct_required_pipe_count": 18,
        },
        "boiler_room_manifolds": {
            "same_internal_wall": True,
            "mounting_wall_id": "FLOOR_1-W025",
            "K1": next(item for item in floor1["collectors"] if item["id"] == "K1"),
            "K2": next(item for item in floor1["collectors"] if item["id"] == "K2"),
            "K2_is_inverted_outlets_up": True,
            "K2_branch_ports_are_contiguous": True,
            "plan_symbol_is_not_installation_elevation": True,
        },
        "routing_rules": {
            **contract["routing_rules"],
            "transit_lane_geometry_verified": False,
            "exterior_edge_zone_applied": False,
            "maximum_three_parallel_transit_pipes_at_100mm_is_design_rule_not_D163_compliance_claim": True,
        },
        "installation_ready": False,
        "next_safe_block": "MATERIALIZE_NONCONTACT_TRANSIT_LANES_WITH_3D_CHASE_AND_HYDRAULIC_BALANCE",
        "D162_audit_fixes": [
            "SOURCE_D162_README_7_PLUS_8_SUPERSEDED_BY_D163_7_PLUS_9",
            "A_R09_NET_POLYGON_AREA_35_9",
            "K2_BRANCH_PORT_GROUPS_CONTIGUOUS",
            "SERVICE_AXES_RECLASSIFIED_AS_RESERVATION_ONLY",
            "FLOOR1_AND_ATTIC_SERVICE_CAPACITY_FIELDS_NO_LONGER_ASSERT_UNPROVEN_PACKING",
            "A_C08_SPLIT_TO_TWO_DENSE_COUNTERFLOWS",
            "A_C12_DUAL_REGULAR_BODY",
            "A_C05_CENTRE_HAIRPIN_TIGHTENED",
        ],
    })

    floor1["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D163: K1/K2 на одной стене; K2 перевёрнут. Жёлтые штрихпунктирные зоны — резерв коридора, не нарисованные поверх друг друга трубы.",
        "author_intent": "Audited dense two-manifold layout with honest service-corridor semantics",
    }
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D163: 16 плотных улиток. Детская восток разделена на две; A-C12 двойная регулярная; физический K2 остаётся в котельной.",
        "author_intent": "Dense owner-style bodies; transit lanes intentionally remain unmaterialized",
    }

    floor_file = OUTPUT / "HomeAura_Floor1_Audited_D163.homeaura.json"
    attic_file = OUTPUT / "HomeAura_Attic_Audited_D163.homeaura.json"
    dump(floor_file, floor1)
    dump(attic_file, attic)
    dump(OUTPUT / "audited_dense_dual_rise_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "source_D162_floor1_sha256": sha(floor_source),
        "source_D162_attic_sha256": sha(attic_source),
        "floor1_heating_route_geometry_changed": False,
        "attic_rebuilt_route_ids": ["A-C08-N", "A-C08-S", "A-C12", "A-C05"],
        "attic_removed_route_ids": ["A-C08"],
        "service_axis_semantics_changed": "SCHEMATIC_RESERVATION_ONLY",
    })
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "floor1_route_count": len(floor1["circuits"]),
        "attic_body_count": len(attic["circuits"]),
        "attic_all_lengths_40_80m": True,
        "body_contact_count": 0,
        "attic_served_proximity_percent": coverage["served_proximity_percent"],
        "transit_lane_geometry_verified": False,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D163 — проверенная плотная раскладка в HomeAura\n\n"
        "K1 и K2 стоят на одной внутренней стене котельной; K2 перевёрнут выходами вверх. На мансарде 16 тел контуров: 7 относятся к пути под лестницей/по дальней стене/в гардеробную, 9 — к прямой внутренней проходке в правую половину.\n\n"
        f"Длины с двумя вертикальными участками по 3 м: {min(totals)/1000:.1f}–{max(totals)/1000:.1f} м. "
        f"Body-only proximity только по черновым векторным доменам мансарды: {coverage['served_proximity_percent']:.1f}%; лестничный проём в знаменатель не входит.\n\n"
        "Важно: жёлтые штрихпунктирные сервисные зоны показывают необходимый резерв. Они больше не выдаются за совпадающие оси реальных труб. Индивидуальные полосы подводки и гидравлическая балансировка остаются отдельным обязательным блоком; installation_ready=false.\n",
        encoding="utf-8",
    )

    render(floor_file, OUTPUT / "HomeAura_Floor1_D163_Editor_View.png", False)
    render(floor_file, OUTPUT / "HomeAura_Floor1_D163_Clean_View.png", True)
    render(attic_file, OUTPUT / "HomeAura_Attic_D163_Editor_View.png", False)
    render(attic_file, OUTPUT / "HomeAura_Attic_D163_Clean_View.png", True)

    package_current_output()
    print(json.dumps({
        "artifact_id": ARTIFACT_ID,
        "route_count": len(records),
        "min_length_m": min(totals) / 1000,
        "max_length_m": max(totals) / 1000,
        "coverage": coverage,
        "package": str(PACKAGE),
        "package_sha256": sha(PACKAGE),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
