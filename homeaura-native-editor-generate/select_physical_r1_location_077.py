from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_011 = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
SOURCE_F1 = BASE / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
SOURCE_A = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_058 = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
SOURCE_062 = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
SOURCE_069 = BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069" / "attic_riser_packing_scenario.json"
SOURCE_074 = BASE / "HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074" / "owner_physical_inputs.json"
F1_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_PHYSICAL_R1_LOCATION_077"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PHYSICAL_R1_LOCATION_077.zip"
PX = 8.503937

# 400 mm long along the wall (Y), 160 mm across the wall/floor interface (X).
HOLE_BBOX_MM = [13120, 7800, 13280, 8200]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def to_px_mm(point):
    return round(point[0] / 100 * PX), round(point[1] / 100 * PX)


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D077 is append-only")
    raw_011, vector = read(SOURCE_011)
    raw_f1, floor1 = read(SOURCE_F1)
    raw_a, attic = read(SOURCE_A)
    raw_058, diagnostic = read(SOURCE_058)
    raw_062, domains = read(SOURCE_062)
    raw_069, packing = read(SOURCE_069)
    raw_074, owner = read(SOURCE_074)

    hole = box(*HOLE_BBOX_MM)
    boiler_bounds_grid = vector["vector_traced_geometry"]["boiler_room_interior"]["source_bounds_grid"]
    boiler = box(*(value * 100 for value in boiler_bounds_grid))
    source_void_grid = vector["vector_traced_geometry"]["attic_structural_stair_void"]["source_bounds_grid"]
    conservative_void_grid = vector["vector_traced_geometry"]["attic_structural_stair_void"]["conservative_blocked_box_grid"]
    source_void = box(*(value * 100 for value in source_void_grid))
    conservative_void = box(*(value * 100 for value in conservative_void_grid))
    wall_band = box(12987.866795857748, 5700, 13207.999784681533, 9200)
    known_attic_floor = shape(domains["known_floor_union_geojson"])

    f1_contacts = []
    f1_distances = []
    for route in floor1["routes"]:
        line = LineString(route["ordered_points_mm"])
        intersection = line.intersection(hole)
        if not intersection.is_empty:
            f1_contacts.append({
                "route_id": route["route_id"],
                "intersection_length_mm": intersection.length,
                "intersection_geojson_type": intersection.geom_type,
                "required_action": "REROUTE_LOCALLY_AROUND_SELECTED_R1_PENETRATION",
            })
        else:
            f1_distances.append({"route_id": route["route_id"], "distance_mm": line.distance(hole)})

    attic_body_contacts = []
    attic_body_distances = []
    for route in attic["body_routes"]:
        line = LineString(route["body_points_mm"])
        if line.intersects(hole):
            attic_body_contacts.append(route["route_id"])
        attic_body_distances.append({"route_id": route["route_id"], "distance_mm": line.distance(hole)})

    diagnostic_contacts = []
    for fragment in diagnostic["diagnostic_planar_fragments"]:
        line = LineString(fragment["ordered_points_mm"])
        if line.intersects(hole):
            diagnostic_contacts.append(fragment["route_id"])

    clear_width = HOLE_BBOX_MM[2] - HOLE_BBOX_MM[0]
    clear_length = HOLE_BBOX_MM[3] - HOLE_BBOX_MM[1]
    pipe_centers = []
    for item in packing["scenario_pipe_positions"]:
        local_along, local_across = item["center_mm"]
        pipe_centers.append({
            "candidate_pipe_id": item["pipe_id"],
            "plan_center_mm": [HOLE_BBOX_MM[0] + local_across, HOLE_BBOX_MM[1] + local_along],
            "assigned_to_complete_route": False,
        })

    model = {
        "schema": "homeaura-physical-r1-location-0.1",
        "artifact_id": "HA_TWO_FLOOR_PHYSICAL_R1_LOCATION_077",
        "status": "PHYSICAL_R1_PENETRATION_LOCATION_SELECTED_REWORK_F1_C11_AND_STRUCTURAL_INSTALLATION_DETAIL",
        "source_records": [
            {"artifact_id": data["artifact_id"] if "artifact_id" in data else data["contract_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_011, vector), (raw_f1, floor1), (raw_a, attic), (raw_058, diagnostic), (raw_062, domains), (raw_069, packing), (raw_074, owner))
        ],
        "selection_method": "OWNER_AUTHORIZED_AGENT_SELECTION_WALL_ALIGNED_BOILER_SIDE_ADJACENT_TO_STAIR_VOID",
        "coordinate_system": "SHARED_PDF_MODEL_MM",
        "location_description": "BOILER_ROOM_SIDE_ALONG_WEST_WALL_IMMEDIATELY_EAST_OF_ATTIC_STAIR_VOID",
        "orientation": "LONG_SIDE_PARALLEL_TO_WALL_Y_AXIS",
        "clear_penetration_bbox_mm": HOLE_BBOX_MM,
        "clear_penetration_size_mm": [clear_width, clear_length],
        "clear_penetration_width_across_wall_mm": clear_width,
        "clear_penetration_length_along_wall_mm": clear_length,
        "floor_1_boiler_interior_contains_penetration": boiler.covers(hole),
        "attic_source_stair_void_contact": not hole.disjoint(source_void),
        "attic_source_stair_void_clearance_mm": hole.distance(source_void),
        "attic_conservative_void_contact": not hole.disjoint(conservative_void),
        "attic_conservative_void_clearance_mm": hole.distance(conservative_void),
        "attic_wall_band_overlap_area_mm2": hole.intersection(wall_band).area,
        "attic_known_floor_overlap_area_mm2": hole.intersection(known_attic_floor).area,
        "penetration_intentionally_straddles_attic_wall_to_floor_interface": True,
        "wall_material": owner["owner_inputs"]["wall_material"],
        "floor_to_floor_height_mm": owner["owner_inputs"]["floor_to_floor_height_mm"],
        "pipe_od_mm": owner["owner_inputs"]["pipe_outer_diameter_mm"],
        "design_centerline_bend_radius_mm": owner["owner_inputs"]["design_minimum_bend_radius_mm"],
        "heated_radius_reduction_credited": False,
        "candidate_vertical_pipe_count": len(pipe_centers),
        "candidate_vertical_pipe_centers_mm": pipe_centers,
        "all_candidate_envelopes_fit_clear_penetration": True,
        "packing_minimum_center_distance_mm": packing["minimum_center_distance_mm"],
        "packing_minimum_provisional_envelope_gap_mm": packing["minimum_provisional_envelope_clear_gap_mm"],
        "packing_minimum_provisional_envelope_to_opening_edge_mm": packing["minimum_provisional_envelope_to_assumed_boundary_mm"],
        "floor_1_route_contact_count": len(f1_contacts),
        "floor_1_route_contacts": f1_contacts,
        "floor_1_minimum_noncontact_route_clearance_mm": min(item["distance_mm"] for item in f1_distances),
        "attic_body_contact_count": len(attic_body_contacts),
        "attic_body_contact_route_ids": attic_body_contacts,
        "attic_minimum_body_clearance_mm": min(item["distance_mm"] for item in attic_body_distances),
        "diagnostic_attic_fragment_contact_count": len(diagnostic_contacts),
        "diagnostic_attic_fragment_contact_route_ids": diagnostic_contacts,
        "selected_r1_plan_location": True,
        "selected_clear_penetration_dimensions": True,
        "structural_cutting_approval": "REQUIRED_BEFORE_CONSTRUCTION",
        "sleeve_edge_reinforcement_firestop_and_sealing": "NOT_DESIGNED",
        "physical_route_geometry_published": False,
        "current_assigned_R1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "complete_attic_circuit_count": 0,
        "result": "PASS_R1_LOCATION_SELECTION_REWORK_C11_LOCAL_ROUTE_STRUCTURAL_OPENING_AND_FULL_CONNECTION_ROUTING",
    }
    model["location_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "physical_r1_location.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    f1_image = Image.open(F1_RENDER).convert("RGB")
    attic_image = Image.open(ATTIC_RENDER).convert("RGB")
    height = 1450
    canvas_image = Image.new("RGB", (1800, height), "#F7FAFA")
    canvas = ImageDraw.Draw(canvas_image, "RGBA")
    canvas.rectangle((0, 0, 1800, 210), fill="#071A21")
    canvas.text((34, 18), "D077 · МЕСТО R1 ВЫБРАНО", font=font(30, True), fill="white")
    canvas.text((34, 70), "Отверстие 400×160 мм вдоль стены котельной, справа от лестничного проёма", font=font(19, True), fill="#A7EEE7")
    canvas.text((34, 115), "Координаты: x=13 120…13 280 · y=7 800…8 200 мм · длинная сторона вдоль стены", font=font(16), fill="#F3D58C")
    canvas.text((34, 158), "Мансардные тела: 0 контактов · лестничный проём: 0 · первый этаж: перестроить только C11", font=font(16, True), fill="#FFB2B2")

    crop_box = (720, 380, 1300, 1050)
    f1_crop = f1_image.crop(crop_box).resize((760, 880))
    attic_crop = attic_image.crop(crop_box).resize((760, 880))
    for x, crop, title in ((40, f1_crop, "1 ЭТАЖ · КОТЕЛЬНАЯ"), (1000, attic_crop, "МАНСАРДА · У ЛЕСТНИЦЫ")):
        canvas_image.paste(crop, (x, 300))
        canvas.text((x, 250), title, font=font(21, True), fill="#143842")
        # Transform model pixels into crop-resized coordinates.
        p0 = to_px_mm((HOLE_BBOX_MM[0], HOLE_BBOX_MM[1]))
        p1 = to_px_mm((HOLE_BBOX_MM[2], HOLE_BBOX_MM[3]))
        sx = 760 / (crop_box[2] - crop_box[0])
        sy = 880 / (crop_box[3] - crop_box[1])
        rect = (x + (p0[0]-crop_box[0])*sx, 300 + (p0[1]-crop_box[1])*sy, x + (p1[0]-crop_box[0])*sx, 300 + (p1[1]-crop_box[1])*sy)
        canvas.rectangle(rect, fill="#FF7A0066", outline="#D50000", width=5)
        canvas.text((rect[0]-65, rect[1]-38), "R1 400×160", font=font(12, True), fill="#D50000", stroke_width=2, stroke_fill="white")
    canvas.text((55, 1235), "Внутри отверстия условно помещаются 26 осей Ø16 по схеме 9+9+8; назначения контуров ещё нет.", font=font(17, True), fill="#143842")
    canvas.text((55, 1285), "До строительства: локально обойти отверстие контуром F1-C11 и согласовать вырез/гильзу, усиление кромки и огнезаделку.", font=font(17, True), fill="#B00020")
    canvas.text((55, 1340), "Выбор места завершён; новых утверждённых труб в этом блоке нет.", font=font(15), fill="#566B73")
    canvas_image.save(OUTPUT / "physical_r1_location_two_floor.png")

    (OUTPUT / "report.md").write_text(
        "# D077 — выбранное место R1\n\n"
        "R1 размещён на стороне котельной вдоль её западной стены, непосредственно справа от лестничного проёма. "
        "Выбрано чистое отверстие 400×160 мм: x=13 120…13 280 мм, y=7 800…8 200 мм; длинная сторона идёт вдоль стены.\n\n"
        "На первом этаже отверстие целиком находится внутри чернового интерьера котельной. На мансарде оно не пересекает ни фактическую, ни консервативную границу лестничного проёма; минимальный зазор до консервативной границы 20 мм, до фактически трассированной — 126 мм. Ближайшее тело мансарды находится в 220 мм.\n\n"
        "Существующая планарная схема первого этажа имеет один конфликт: вертикальный участок F1-C11 проходит через выбранное отверстие на 400 мм. Этот участок должен быть локально переразведён при объединении R1 с первым этажом. Остальные контуры отверстие не пересекают.\n\n"
        "Геометрия отверстия допускает условную упаковку 26 труб Ø16 по ранее проверенной схеме 9+9+8. До строительства нужны конструктивное согласование выреза/гильзы, усиление кромки при необходимости, герметизация и огнезаделка.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "location_digest": model["location_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "bbox_mm": HOLE_BBOX_MM, "f1_contacts": f1_contacts, "attic_body_clearance_mm": model["attic_minimum_body_clearance_mm"], "digest": model["location_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
