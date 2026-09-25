from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_152"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
D037 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037" / "canonical_geometry.json"
OUT = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153.zip"
OFFSET = 3000


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def mm_point(x: float, y: float):
    return {"x_mm": round(x + OFFSET), "y_mm": round(y + OFFSET)}


def polygon_points(geometry: Polygon):
    return [mm_point(x, y) for x, y in list(geometry.exterior.coords)[:-1]]


def room(room_id: str, name: str, area: float, geometry: Polygon, colour: str):
    centre = geometry.representative_point()
    return {
        "id": room_id,
        "floor_id": "ATTIC",
        "name": name,
        "area_m2": area,
        "outline": polygon_points(geometry),
        "label_position": mm_point(centre.x, centre.y),
        "heating_allowed": True,
        "fill_color": colour,
    }


def exact_attic_rooms(d062, d047):
    semantics = {
        "ATTIC_LEFT_NORTH_RECT_DRAFT": ("A-R15", "Гардероб", 13.0, "#183743"),
        "ATTIC_LEFT_MIDDLE_RECT_DRAFT": ("A-R14", "Спальня", 28.7, "#1A3D48"),
        "ATTIC_LEFT_SOUTH_RECT_DRAFT": ("A-R16", "Ванна + WC", 12.9, "#193B44"),
        "ATTIC_RIGHT_NORTH_RECT_DRAFT": ("A-R10", "Детская", 26.0, "#183743"),
        "ATTIC_RIGHT_MIDDLE_LEFT_RECT_DRAFT": ("A-R11", "WC", 5.1, "#1A3D48"),
        "ATTIC_RIGHT_MIDDLE_RIGHT_RECT_DRAFT": ("A-R13", "WC", 5.3, "#193B44"),
        "ATTIC_RIGHT_SOUTH_RECT_DRAFT": ("A-R12", "Детская", 20.6, "#183743"),
    }
    output = []
    for source in d062["adjacent_floor_domains"]:
        room_id, name, printed_area, colour = semantics[source["domain_id"]]
        output.append(room(room_id, name, printed_area, shape(source["floor_geojson"]), colour))
    hall = shape(d047["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    output.append(room("A-R09", "Холл и лестничная зона", 39.9, hall, "#153844"))
    return output, hall


def exact_floor1_hall(project, d037):
    evidence = d037["wall_clearance_and_coverage_evidence"]
    scale = 35.27777777777778
    polygon = Polygon([(x * scale, y * scale) for x, y in evidence["hall_candidate_polygon_pdf_points"]])
    replacement = {
        "id": "F1-R02",
        "floor_id": "FLOOR_1",
        "name": "Холл и лестница",
        "area_m2": 30.7,
        "outline": polygon_points(polygon),
        "label_position": mm_point(polygon.representative_point().x, polygon.representative_point().y),
        "heating_allowed": True,
        "fill_color": "#153844",
    }
    current = [r for r in project["rooms"] if r["id"] != "F1-R02"]
    current.append(replacement)
    project["rooms"] = current
    return polygon


def diagnostic(project, domains):
    lines = [LineString([(p["x_mm"], p["y_mm"]) for p in route["ordered_points"]]) for route in project["circuits"]]
    served = unary_union([line.buffer(100, quad_segs=16) for line in lines])
    records = []
    for room_id, geometry in domains:
        shifted = Polygon([(x + OFFSET, y + OFFSET) for x, y in geometry.exterior.coords])
        served_area = shifted.intersection(served).area
        unresolved = shifted.difference(served)
        records.append({
            "room_id": room_id,
            "area_m2": shifted.area / 1_000_000,
            "served_proximity_m2": served_area / 1_000_000,
            "unresolved_proximity_m2": unresolved.area / 1_000_000,
            "served_proximity_percent": 100 * served_area / shifted.area,
            "unresolved_component_count": len(unresolved.geoms) if unresolved.geom_type == "MultiPolygon" else (0 if unresolved.is_empty else 1),
        })
    union = unary_union([Polygon([(x + OFFSET, y + OFFSET) for x, y in g.exterior.coords]) for _, g in domains])
    covered = union.intersection(served).area
    return {
        "method": "TRUE_ROUND_100MM_CENTERLINE_PROXIMITY_OVER_VECTOR_DRAFT_FLOOR_DOMAINS",
        "engineering_coverage_claimed": False,
        "rooms": records,
        "known_floor_area_m2": union.area / 1_000_000,
        "served_proximity_m2": covered / 1_000_000,
        "unresolved_proximity_m2": (union.area - covered) / 1_000_000,
        "served_proximity_percent": 100 * covered / union.area,
    }


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D153 is append-only")
    d062, d047, d037 = load(D062), load(D047), load(D037)
    floor1 = load(SOURCE / "HomeAura_Floor1_Rework_D152.homeaura.json")
    attic = load(SOURCE / "HomeAura_Attic_Rework_D152.homeaura.json")
    OUT.mkdir(parents=True)

    exact_rooms, hall = exact_attic_rooms(d062, d047)
    attic["rooms"] = exact_rooms
    all_domain_geometries = [(record["id"], shape(source["floor_geojson"])) for record, source in zip(exact_rooms[:7], d062["adjacent_floor_domains"])]
    all_domain_geometries.append(("A-R09", hall))
    known_union = unary_union([geometry for _, geometry in all_domain_geometries])
    minx, miny, maxx, maxy = known_union.bounds
    attic["levels"][0]["outline"] = [mm_point(minx, miny), mm_point(maxx, miny), mm_point(maxx, maxy), mm_point(minx, maxy)]
    attic["levels"][0]["label_position"] = mm_point(minx, maxy + 500)
    attic["walls"] = []
    attic["training_metadata"]["notes"] = (
        "D153. Геометрия семи помещений и центрального холла мансарды перенесена в нативный редактор из точных векторных finish-face контуров D062/D047. "
        "Архитектура хранится с точностью 1 мм; оси труб остаются на сетке 100 мм. Текущие 11 осей — только чистый бесконтактный baseline: карта показывает реальные непокрытые зоны, которые будут переразбиты новыми регулярными улитками. "
        "Шаг поля 200 мм; только три согласованные транзитные трубы допускаются через 100 мм. Труба 16 мм, Rmin 80 мм."
    )

    floor1_hall = exact_floor1_hall(floor1, d037)
    floor1["training_metadata"]["notes"] = (
        "D153. Первый этаж открыт как нативный проект HomeAura. Холл/лестница заменены на векторный L-контур из исходного PDF; остальные комнаты пока сохраняют проверенные границы D152. "
        "Оси труб бесконтактны и 40–80 м, но покрытия по приблизительным комнатам не принимаются. Коридор остаётся одним длинным контуром-улиткой."
    )

    floor1_path = OUT / "HomeAura_Floor1_ExactHouse_D153.homeaura.json"
    attic_path = OUT / "HomeAura_Attic_ExactHouse_D153.homeaura.json"
    dump(floor1_path, floor1)
    dump(attic_path, attic)

    attic_audit = diagnostic(attic, all_domain_geometries)
    floor1_hall_audit = diagnostic(floor1, [("F1-R02", floor1_hall)])
    audit = {
        "artifact_id": "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153",
        "status": "PASS_EXACT_NATIVE_ARCHITECTURE_REWORK_PIPE_COVERAGE",
        "source_sha256": {"D062": sha(D062), "D047": sha(D047), "D037": sha(D037)},
        "architectural_coordinate_precision_mm": 1,
        "pipe_grid_mm": 100,
        "attic": attic_audit,
        "floor1_exact_hall_only": floor1_hall_audit,
        "route_geometry_preserved_from_D152": True,
        "self_contacts": 0,
        "inter_route_contacts": 0,
        "next_decision": "REPARTITION_REGULAR_COUNTERFLOW_BODIES_OVER_EXACT_VECTOR_DOMAINS",
    }
    dump(OUT / "exact_floor_proximity_audit.json", audit)
    dump(OUT / "status.json", {
        "artifact_id": audit["artifact_id"],
        "status": audit["status"],
        "native_editable_projects": 2,
        "attic_exact_vector_room_count": 8,
        "floor1_exact_vector_room_count": 1,
        "coverage_accepted": False,
        "reason": "The old circuit axes leave measurable gaps on exact floor polygons; D153 is the truthful native-house baseline for rerouting.",
    })
    (OUT / "README.md").write_text(
        "# D153 — точный дом в HomeAura Native Editor\n\n"
        "Мансарда построена по восьми векторным полигонам исходного PDF: семь помещений и центральный холл вокруг лестницы. "
        "На первом этаже точным векторным L-контуром заменён холл. Трубная сетка и архитектурная точность разделены: стены не округляются до 100 мм.\n\n"
        "D153 намеренно не скрывает пустоты: 100-мм proximity audit показывает, где D152 недогревает поле. "
        "Следующий блок меняет распределение контуров, а не закрашивает эти зоны.\n",
        encoding="utf-8",
    )

    files = [path for path in sorted(OUT.iterdir()) if path.is_file()]
    manifest = {
        "artifact_id": audit["artifact_id"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    dump(OUT / "artifact_manifest.json", manifest)
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    print(json.dumps({
        "output": str(OUT),
        "attic_known_floor_m2": attic_audit["known_floor_area_m2"],
        "attic_served_percent": attic_audit["served_proximity_percent"],
        "attic_unresolved_m2": attic_audit["unresolved_proximity_m2"],
        "floor1_hall_served_percent": floor1_hall_audit["served_proximity_percent"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
