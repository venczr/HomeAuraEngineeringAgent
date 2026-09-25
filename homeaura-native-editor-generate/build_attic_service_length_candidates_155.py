from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import unary_union

from build_owner_style_installation_project_141 import paired_counterflow, length_mm, self_contacts


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D154 = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_COUNTERFLOW_LAYOUT_154"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUT = PROPOSALS / "HA_TWO_FLOOR_ATTIC_SERVICE_LENGTH_CANDIDATES_155"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_ATTIC_SERVICE_LENGTH_CANDIDATES_155.zip"
OFFSET = 3000
COLLECTOR = (94, 73)
PALETTE = ["#E43F5A", "#3676C8", "#08A982", "#9B5DE5", "#DE8419", "#3CA6C1", "#6A8E35", "#FF6555", "#B35AC9", "#12A594", "#BE6A1D", "#5B8FF9"]


SPECS = [
    ("A-C01", "Гардероб", (47, 58, 96, 81), "IDENTITY"),
    ("A-C02", "Спальня - север", (47, 85, 96, 112), "IDENTITY"),
    ("A-C03", "Спальня - юг", (47, 114, 96, 139), "IDENTITY"),
    ("A-C04", "Ванна + WC", (47, 143, 96, 166), "IDENTITY"),
    ("A-C08", "Детская север - запад", (133, 58, 159, 104), "ROTATE_180"),
    ("A-C09", "Детская север - восток", (161, 58, 185, 104), "ROTATE_180"),
    ("A-C10_C11", "Два WC последовательно", None, "SERIAL"),
    ("A-C12", "Детская юг - север", (133, 130, 185, 148), "ROTATE_180"),
    ("A-C13", "Детская юг - юг", (133, 150, 185, 166), "ROTATE_180"),
    ("A-C05", "Холл - верх", (100, 93, 129, 131), "IDENTITY"),
    ("A-C06", "Холл - середина", (101, 133, 128, 167), "IDENTITY"),
    ("A-C07", "Холл - вход", (95, 170, 137, 193), "MIRROR_Y"),
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def point(x, y):
    return {"x_mm": OFFSET + x * 100, "y_mm": OFFSET + y * 100}


def transform(points, box, name):
    left, top, right, bottom = box
    if name == "IDENTITY":
        return points
    if name == "MIRROR_Y":
        return [(x, top + bottom - y) for x, y in points]
    if name == "ROTATE_180":
        return [(left + right - x, top + bottom - y) for x, y in points]
    raise ValueError(name)


def serial_wc():
    first_box = (133, 108, 157, 126)
    second_box = (160, 108, 185, 126)
    first = paired_counterflow(first_box)
    second = transform(paired_counterflow(second_box), second_box, "ROTATE_180")
    connector = [(first[-1][0], first[-1][1]), (158, first[-1][1]), (158, second[0][1]), second[0]]
    result = first + connector[1:] + second[1:]
    if self_contacts(result):
        raise RuntimeError("WC serial body self-contact")
    return result


def service_path(endpoint):
    x, y = endpoint
    if x <= 98:
        return [COLLECTOR, (98, 73), (98, y), (x, y)]
    trunk_x = 130 if x <= 130 else 132
    return [COLLECTOR, (98, 73), (98, 93), (trunk_x, 93), (trunk_x, y), (x, y)]


def grid_length(points):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:])) * 100


def contact_pairs(routes):
    output = []
    for index, first in enumerate(routes):
        first_line = LineString(first["body_points_grid"])
        for second in routes[index + 1:]:
            if not first_line.intersection(LineString(second["body_points_grid"])).is_empty:
                output.append([first["route_id"], second["route_id"]])
    return output


def coverage(routes):
    d062, d047 = load(D062), load(D047)
    floor = unary_union([shape(item["floor_geojson"]) for item in d062["adjacent_floor_domains"]] + [shape(d047["hall_source_contract"]["routing_draft_allowed_floor_geojson"])])
    served = unary_union([LineString([(x * 100, y * 100) for x, y in item["body_points_grid"]]).buffer(100, quad_segs=16) for item in routes])
    covered = floor.intersection(served).area
    return {"known_floor_area_m2": floor.area / 1_000_000, "served_proximity_m2": covered / 1_000_000,
            "unresolved_proximity_m2": (floor.area - covered) / 1_000_000,
            "served_proximity_percent": 100 * covered / floor.area, "full_coverage_claimed": False}


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D155 is append-only")
    OUT.mkdir(parents=True)
    project = load(D154 / "HomeAura_Attic_CounterflowBodies_D154.homeaura.json")
    routes = []
    service_lines = []
    project["circuits"] = []
    project["collectors"][0]["ports"] = 24
    for index, (route_id, territory, box, orientation) in enumerate(SPECS):
        body = serial_wc() if orientation == "SERIAL" else transform(paired_counterflow(box), box, orientation)
        supply = service_path(body[0])
        return_leg = service_path(body[-1])
        service_length = grid_length(supply) + grid_length(return_leg)
        body_length = length_mm(body)
        total = body_length + service_length
        if not 40_000 <= total <= 80_000:
            raise RuntimeError(f"{route_id}: {body_length}+{service_length}={total}")
        routes.append({
            "route_id": route_id, "territory": territory, "body_points_grid": body,
            "body_length_mm": body_length, "concealed_supply_skeleton_grid": supply,
            "concealed_return_skeleton_grid": return_leg, "concealed_service_length_mm": service_length,
            "design_total_length_mm": total,
            "service_layer_assignment": {"supply_layer": 0, "return_layer": 1},
        })
        service_lines.extend([LineString([(x * 100, y * 100) for x, y in supply]), LineString([(x * 100, y * 100) for x, y in return_leg])])
        project["circuits"].append({
            "id": route_id, "name": f"{route_id} · {territory}", "color": PALETTE[index],
            "ordered_points": [point(x, y) for x, y in body], "completed": True,
            "collector_id": "K2", "supply_port_index": index * 2, "return_port_index": index * 2 + 1,
            "service_zone_id": "K2-SERVICE-SKELETON-D155", "concealed_service_length_mm": service_length,
        })

    pairs = contact_pairs(routes)
    if pairs:
        raise RuntimeError(pairs)
    service_geometry = unary_union(service_lines).buffer(100, cap_style=2, join_style=2)
    if service_geometry.geom_type != "Polygon":
        service_geometry = service_geometry.convex_hull
    project["service_zones"] = [{
        "id": "K2-SERVICE-SKELETON-D155", "floor_id": "ATTIC",
        "name": "K2 · двухуровневая сервисная сеть (оси-кандидаты)",
        "outline": [{"x_mm": round(x + OFFSET), "y_mm": round(y + OFFSET)} for x, y in list(service_geometry.exterior.coords)[:-1]],
        "fill_color": "#164E63",
        "note": "Два уровня в 70 мм: центры 20/50 мм, труба 16 мм. Индивидуальные поперечные смещения и веер 26 труб ещё не материализованы; 90° вертикальный поворот R80 запрещён.",
        "collector_id": "K2", "clear_height_mm": 70, "pipe_capacity": 26,
    }]
    project["training_metadata"]["notes"] = (
        "D155. 12 расчётных петель мансарды: 13 регулярных тел, два WC соединены последовательно. "
        "Длины 40-80 м учитывают тело и два скрытых сервисных плеча по осевому скелету K2. K2 расположен в гардеробной. "
        "Сервисная сеть использует только два уровня в доступных 70 мм; три уровня и поворот R80 на 90° внутри 70 мм не заявляются. "
        "Тонкая пунктирная зона - коридор кандидатов, а не доказанный индивидуальный веер 26 труб."
    )
    project_path = OUT / "HomeAura_Attic_ServiceLengthCandidates_D155.homeaura.json"
    dump(project_path, project)
    result = {
        "artifact_id": "HA_TWO_FLOOR_ATTIC_SERVICE_LENGTH_CANDIDATES_155",
        "status": "BODY_AND_LENGTH_CANDIDATES_PASS_REWORK_INDIVIDUAL_K2_FANOUT",
        "source_D154_sha256": sha(D154 / "HomeAura_Attic_CounterflowBodies_D154.homeaura.json"),
        "pipe_od_mm": 16, "minimum_bend_radius_mm": 80, "available_service_height_mm": 70,
        "service_cross_section": {"baseline_layer_count": 2, "layer_center_heights_mm": [20, 50], "bare_pipe_surface_gap_mm": 14,
            "boundary_clearance_mm": [12, 12], "three_layers_claimed": False,
            "vertical_90_degree_bend_inside_70mm_allowed": False,
            "minimum_shallow_s_offset_run_mm_for_30mm_layer_change": 96},
        "route_count": len(routes), "body_count": 13, "routes": routes,
        "body_contact_pairs": pairs, "all_design_lengths_40_80m": True,
        "coverage": coverage(routes),
        "individual_service_pipe_axes_materialized": False,
        "dense_100mm_three_pipe_group_materialized": False,
        "physical_manifold_selected": False,
        "installation_ready": False,
        "next_safe_block": "MATERIALIZE_24_INDIVIDUAL_K2_SERVICE_AXES_WITH_TWO_LEVEL_AND_R80_S_OFFSETS",
    }
    dump(OUT / "service_length_contract.json", result)
    dump(OUT / "status.json", {"artifact_id": result["artifact_id"], "status": result["status"],
        "all_design_lengths_40_80m": True, "body_contact_count": 0, "individual_service_fanout_ready": False})
    (OUT / "README.md").write_text(
        "# D155 - длины петель и сервисный скелет K2\n\n"
        "Все 12 расчётных петель попадают в 40-80 м с учётом двух сервисных плеч. Два WC соединены последовательно. "
        "В 70 мм принят только двухуровневый вариант. Индивидуальный веер труб пока не выдан за готовую монтажную геометрию.\n",
        encoding="utf-8",
    )
    files = [p for p in sorted(OUT.iterdir()) if p.is_file()]
    dump(OUT / "artifact_manifest.json", {"artifact_id": result["artifact_id"], "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]})
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    print(json.dumps({"output": str(OUT), "routes": len(routes), "lengths_mm": {x["route_id"]: x["design_total_length_mm"] for x in routes}, "coverage": result["coverage"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
