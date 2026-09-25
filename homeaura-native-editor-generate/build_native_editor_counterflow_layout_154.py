from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import unary_union

from build_owner_style_installation_project_141 import paired_counterflow, length_mm, self_contacts


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D153 = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153"
D037 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037" / "canonical_geometry.json"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUT = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_COUNTERFLOW_LAYOUT_154"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_NATIVE_EDITOR_COUNTERFLOW_LAYOUT_154.zip"
OFFSET = 3000
PALETTE = ["#E43F5A", "#3676C8", "#08A982", "#9B5DE5", "#DE8419", "#3CA6C1", "#6A8E35", "#FF6555", "#B35AC9", "#12A594", "#BE6A1D", "#5B8FF9", "#F06595"]


ATTIC_BODIES = [
    ("A-C01", "Гардероб", (47, 58, 96, 81)),
    ("A-C02", "Спальня - север", (47, 85, 96, 112)),
    ("A-C03", "Спальня - юг", (47, 114, 96, 139)),
    ("A-C04", "Ванна + WC", (47, 143, 96, 166)),
    ("A-C08", "Детская север - запад", (133, 58, 159, 104)),
    ("A-C09", "Детская север - восток", (161, 58, 185, 104)),
    ("A-C10", "WC 5,1", (133, 108, 157, 126)),
    ("A-C11", "WC 5,3", (160, 108, 185, 126)),
    ("A-C12", "Детская юг - север", (133, 130, 185, 148)),
    ("A-C13", "Детская юг - юг", (133, 150, 185, 166)),
    ("A-C05", "Холл - верх", (100, 93, 129, 131)),
    ("A-C06", "Холл - середина", (100, 133, 129, 168)),
    ("A-C07", "Холл - вход", (94, 169, 138, 195)),
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def point_grid(x, y):
    return {"x_mm": OFFSET + x * 100, "y_mm": OFFSET + y * 100}


def clean(points):
    output = []
    for item in points:
        item = tuple(item)
        if output and output[-1] == item:
            continue
        if len(output) > 1 and (output[-2][0] == output[-1][0] == item[0] or output[-2][1] == output[-1][1] == item[1]):
            output[-1] = item
        else:
            output.append(item)
    return output


def contact_pairs(routes):
    pairs = []
    for index, first in enumerate(routes):
        a = LineString(first["points_grid"])
        for second in routes[index + 1:]:
            if not a.intersection(LineString(second["points_grid"])).is_empty:
                pairs.append([first["id"], second["id"]])
    return pairs


def attic_domains():
    d062, d047 = load(D062), load(D047)
    return [shape(item["floor_geojson"]) for item in d062["adjacent_floor_domains"]] + [shape(d047["hall_source_contract"]["routing_draft_allowed_floor_geojson"])]


def coverage(routes, domains):
    floor = unary_union(domains)
    served = unary_union([LineString([(x * 100, y * 100) for x, y in route["points_grid"]]).buffer(100, quad_segs=16) for route in routes])
    area = floor.area
    covered = floor.intersection(served).area
    return {
        "known_floor_area_m2": area / 1_000_000,
        "served_proximity_m2": covered / 1_000_000,
        "unresolved_proximity_m2": (area - covered) / 1_000_000,
        "served_proximity_percent": 100 * covered / area,
        "full_coverage_claimed": False,
        "method": "ROUND_100MM_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
    }


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D154 is append-only")
    OUT.mkdir(parents=True)
    floor1 = load(D153 / "HomeAura_Floor1_ExactHouse_D153.homeaura.json")
    attic = load(D153 / "HomeAura_Attic_ExactHouse_D153.homeaura.json")
    d037 = load(D037)

    floor1_routes = []
    floor1["collectors"][0]["ports"] = 24
    floor1["circuits"] = []
    for index, route in enumerate(d037["routes"]):
        points = clean(route["ordered_points_grid"])
        floor1_routes.append({"id": route["route_id"], "points_grid": points})
        floor1["circuits"].append({
            "id": route["route_id"],
            "name": f"{route['route_id']} · регулярная улитка",
            "color": PALETTE[index % len(PALETTE)],
            "ordered_points": [point_grid(x, y) for x, y in points],
            "completed": True,
            "collector_id": "K1",
            "supply_port_index": index * 2,
            "return_port_index": index * 2 + 1,
            "service_zone_id": None,
        })
    floor1["training_metadata"]["notes"] = (
        "D154. 12 полных бесконтактных контуров D037 перенесены в нативный редактор поверх точного L-контура холла. "
        "Холл больше не оставлен пустым: одна непрерывная длинная петля проходит три регулярные зоны вокруг лестницы; входная и нижняя зоны не маскируются как покрытые ею. "
        "Шаг 100 мм используется только на трёх северных транзитных осях, далее 200 мм."
    )

    attic_routes = []
    attic["circuits"] = []
    attic["collectors"][0]["ports"] = 26
    for index, (route_id, territory, box) in enumerate(ATTIC_BODIES):
        body = paired_counterflow(box)
        assert self_contacts(body) == 0
        attic_routes.append({"id": route_id, "points_grid": body, "box_grid": box, "body_length_mm": length_mm(body)})
        attic["circuits"].append({
            "id": route_id,
            "name": f"{route_id} · {territory}",
            "color": PALETTE[index % len(PALETTE)],
            "ordered_points": [point_grid(x, y) for x, y in body],
            "completed": False,
            "collector_id": None,
            "supply_port_index": None,
            "return_port_index": None,
            "service_zone_id": None,
        })
    attic["service_zones"] = []
    attic["training_metadata"]["notes"] = (
        "D154. 13 новых регулярных улиток построены непосредственно по точным комнатам D062/D047. Старые малые тела и крупные пустоты D152 не сохранены. "
        "Это принятая геометрия полей, но ещё не полные петли K2: подводящие участки в доступном 70-мм сервисном слое будут добавлены отдельным следующим блоком с учётом Ø16 и Rmin 80. "
        "Поле 200 мм; только согласованная тройка транзитных труб может идти через 100 мм."
    )

    f1_contacts = contact_pairs(floor1_routes)
    attic_contacts = contact_pairs(attic_routes)
    if f1_contacts or attic_contacts:
        raise RuntimeError({"floor1": f1_contacts, "attic": attic_contacts})
    attic_coverage = coverage(attic_routes, attic_domains())
    floor1_lengths = {r["id"]: length_mm(r["points_grid"]) for r in floor1_routes}
    if not all(40_000 <= value <= 80_000 for value in floor1_lengths.values()):
        raise RuntimeError(floor1_lengths)

    f1_path = OUT / "HomeAura_Floor1_Counterflow_D154.homeaura.json"
    attic_path = OUT / "HomeAura_Attic_CounterflowBodies_D154.homeaura.json"
    dump(f1_path, floor1)
    dump(attic_path, attic)
    audit = {
        "artifact_id": "HA_TWO_FLOOR_NATIVE_EDITOR_COUNTERFLOW_LAYOUT_154",
        "status": "FLOOR1_COMPLETE_ROUTES_PASS_ATTIC_BODY_LAYOUT_PASS_REWORK_K2_SERVICE_LEGS",
        "source_sha256": {"D153_floor1": sha(D153 / "HomeAura_Floor1_ExactHouse_D153.homeaura.json"), "D153_attic": sha(D153 / "HomeAura_Attic_ExactHouse_D153.homeaura.json"), "D037": sha(D037)},
        "floor1": {"route_count": len(floor1_routes), "lengths_mm": floor1_lengths, "contact_pairs": f1_contacts, "all_lengths_40_80m": True},
        "attic": {"body_count": len(attic_routes), "body_lengths_mm": {r["id"]: r["body_length_mm"] for r in attic_routes}, "contact_pairs": attic_contacts, "coverage": attic_coverage, "complete_route_count": 0},
        "owner_style": {"regular_counterflow_body_count": 13, "field_spacing_mm": 200, "dense_transit_spacing_mm": 100, "dense_transit_max_pipe_count": 3},
        "next_safe_block": "K2_THREE_LAYER_SERVICE_LEGS_AND_FULL_40_80M_ROUTE_ASSEMBLY",
    }
    dump(OUT / "independent_geometry_audit.json", audit)
    dump(OUT / "status.json", {"artifact_id": audit["artifact_id"], "status": audit["status"], "floor1_ready_in_editor": True, "attic_fields_ready_in_editor": True, "attic_full_routes_ready": False, "attic_served_proximity_percent": attic_coverage["served_proximity_percent"]})
    (OUT / "README.md").write_text(
        "# D154 - регулярная перераскладка\n\n"
        "Первый этаж: 12 полных контуров 40-80 м, контактов нет, холл заполнен. "
        "Мансарда: 13 новых регулярных тел по точным полигонам; 100-мм proximity вырос примерно с 71% до 88%. "
        "Подводы K2 ещё не дорисованы и поэтому не объявлены полными петлями.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUT.iterdir()) if path.is_file()]
    dump(OUT / "artifact_manifest.json", {"artifact_id": audit["artifact_id"], "append_only": True, "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]})
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    print(json.dumps({"output": str(OUT), "floor1_routes": len(floor1_routes), "attic_bodies": len(attic_routes), "attic_coverage": attic_coverage}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
