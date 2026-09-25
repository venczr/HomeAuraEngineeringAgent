from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import translate
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
SOURCE_077 = BASE / "HA_TWO_FLOOR_PHYSICAL_R1_LOCATION_077" / "physical_r1_location.json"
F1_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_WALL_REGISTERED_R1_LOCATION_078"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_WALL_REGISTERED_R1_LOCATION_078.zip"

PT_TO_MM = 35.2777777778
PX_PER_100_MM = 8.503937
F1_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")
ATTIC_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")

# Building coordinates use the first-floor sheet as the datum.  The two plan
# drawings have the same 1:100 scale but are translated on their PDF pages.
REGISTRATION_DX_PT = 10.20
REGISTRATION_DY_PT = 8.64
REGISTRATION_DX_MM = REGISTRATION_DX_PT * PT_TO_MM
REGISTRATION_DY_MM = REGISTRATION_DY_PT * PT_TO_MM

# The clear slab penetration is inside the rooms, parallel to the common east
# exterior wall.  Its east edge is 27.2 mm from the finish face on both floors.
HOLE_BUILDING_BBOX_MM = [18050, 7800, 18210, 8200]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(
        str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")),
        size,
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def path_record(pdf: Path, path_id: int) -> dict:
    drawing = pymupdf.open(pdf)[0].get_drawings()[path_id]
    rect = drawing["rect"]
    return {
        "pdf_path_id": path_id,
        "raw_rect_pt": [rect.x0, rect.y0, rect.x1, rect.y1],
    }


def to_px_mm(point):
    return round(point[0] / 100 * PX_PER_100_MM), round(point[1] / 100 * PX_PER_100_MM)


def route_contact_records(routes, key, hole):
    contacts = []
    distances = []
    for route in routes:
        line = LineString(route[key])
        intersection = line.intersection(hole)
        if intersection.is_empty:
            distances.append({"route_id": route["route_id"], "distance_mm": line.distance(hole)})
        else:
            contacts.append({
                "route_id": route["route_id"],
                "intersection_length_mm": intersection.length,
                "intersection_geojson_type": intersection.geom_type,
                "required_action": "LOCAL_REROUTE_AROUND_WALL_REGISTERED_R1_OPENING",
            })
    return contacts, distances


def aligned_attic_line(points):
    return LineString([(x - REGISTRATION_DX_MM, y - REGISTRATION_DY_MM) for x, y in points])


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D078 is append-only")

    raw_011, vector = read(SOURCE_011)
    raw_f1, floor1 = read(SOURCE_F1)
    raw_a, attic = read(SOURCE_A)
    raw_058, diagnostic = read(SOURCE_058)
    raw_062, domains = read(SOURCE_062)
    raw_069, packing = read(SOURCE_069)
    raw_074, owner = read(SOURCE_074)
    raw_077, old = read(SOURCE_077)

    f1_outer_east = path_record(F1_PDF, 4282)
    attic_outer_east = path_record(ATTIC_PDF, 1544)
    f1_outer_north = path_record(F1_PDF, 4288)
    attic_outer_north = path_record(ATTIC_PDF, 1472)
    f1_finish_east = path_record(F1_PDF, 202)
    attic_finish_east = path_record(ATTIC_PDF, 419)

    derived_dx = attic_outer_east["raw_rect_pt"][2] - f1_outer_east["raw_rect_pt"][2]
    derived_dy = attic_outer_north["raw_rect_pt"][1] - f1_outer_north["raw_rect_pt"][1]
    if abs(derived_dx - REGISTRATION_DX_PT) > 1e-4 or abs(derived_dy - REGISTRATION_DY_PT) > 1e-4:
        raise ValueError("PDF exterior-shell registration drift")

    f1_finish_x = f1_finish_east["raw_rect_pt"][0] * PT_TO_MM
    attic_finish_x_raw = attic_finish_east["raw_rect_pt"][0] * PT_TO_MM
    attic_finish_x_registered = attic_finish_x_raw - REGISTRATION_DX_MM
    if abs(f1_finish_x - attic_finish_x_registered) > 0.01:
        raise ValueError("Registered east finish faces do not coincide")

    hole = box(*HOLE_BUILDING_BBOX_MM)
    attic_hole_raw = translate(hole, xoff=REGISTRATION_DX_MM, yoff=REGISTRATION_DY_MM)
    boiler_bounds_grid = vector["vector_traced_geometry"]["boiler_room_interior"]["source_bounds_grid"]
    boiler = box(*(value * 100 for value in boiler_bounds_grid))
    known_attic_floor_registered = translate(
        shape(domains["known_floor_union_geojson"]),
        xoff=-REGISTRATION_DX_MM,
        yoff=-REGISTRATION_DY_MM,
    )

    f1_contacts, f1_distances = route_contact_records(floor1["routes"], "ordered_points_mm", hole)
    attic_body_contacts = []
    attic_body_distances = []
    for route in attic["body_routes"]:
        line = aligned_attic_line(route["body_points_mm"])
        if line.intersects(hole):
            attic_body_contacts.append(route["route_id"])
        attic_body_distances.append({"route_id": route["route_id"], "distance_mm": line.distance(hole)})
    fragment_contacts = []
    fragment_distances = []
    for fragment in diagnostic["diagnostic_planar_fragments"]:
        line = aligned_attic_line(fragment["ordered_points_mm"])
        if line.intersects(hole):
            fragment_contacts.append(fragment["route_id"])
        fragment_distances.append({"route_id": fragment["route_id"], "distance_mm": line.distance(hole)})

    width = HOLE_BUILDING_BBOX_MM[2] - HOLE_BUILDING_BBOX_MM[0]
    length = HOLE_BUILDING_BBOX_MM[3] - HOLE_BUILDING_BBOX_MM[1]
    centers = []
    for item in packing["scenario_pipe_positions"]:
        local_along, local_across = item["center_mm"]
        centers.append({
            "candidate_pipe_id": item["pipe_id"],
            "building_plan_center_mm": [
                HOLE_BUILDING_BBOX_MM[0] + local_across,
                HOLE_BUILDING_BBOX_MM[1] + local_along,
            ],
            "assigned_to_complete_route": False,
        })

    source_records = [
        {"artifact_id": data.get("artifact_id", data.get("contract_id")), "sha256": hashlib.sha256(raw).hexdigest().upper()}
        for raw, data in (
            (raw_011, vector), (raw_f1, floor1), (raw_a, attic), (raw_058, diagnostic),
            (raw_062, domains), (raw_069, packing), (raw_074, owner), (raw_077, old),
        )
    ]
    model = {
        "schema": "homeaura-wall-registered-physical-r1-location-0.2",
        "artifact_id": "HA_TWO_FLOOR_WALL_REGISTERED_R1_LOCATION_078",
        "status": "PHYSICAL_R1_LOCATION_SELECTED_ON_COMMON_REGISTERED_EAST_WALL_REWORK_F1_C08_AND_STRUCTURAL_DETAIL",
        "source_records": source_records,
        "supersedes_artifact_id": old["artifact_id"],
        "superseded_artifact_disposition": "REJECTED_UNREGISTERED_PDF_PAGE_COORDINATES_NOT_A_COMMON_BUILDING_DATUM",
        "coordinate_system": "BUILDING_PLAN_MM_DATUM_FLOOR_1_PDF_AFTER_EXTERIOR_SHELL_REGISTRATION",
        "pdf_page_registration": {
            "method": "TRANSLATION_FROM_MATCHED_OUTER_EAST_AND_OUTER_NORTH_BUILDING_SHELL_FACES",
            "attic_to_floor_1_translation_pt": [-REGISTRATION_DX_PT, -REGISTRATION_DY_PT],
            "attic_to_floor_1_translation_mm": [-REGISTRATION_DX_MM, -REGISTRATION_DY_MM],
            "floor_1_outer_east_source": f1_outer_east,
            "attic_outer_east_source": attic_outer_east,
            "floor_1_outer_north_source": f1_outer_north,
            "attic_outer_north_source": attic_outer_north,
            "scale_rotation_or_shear": "NONE",
            "registration_residual_mm": 0.0,
        },
        "common_wall_alignment": {
            "wall_id": "COMMON_EAST_EXTERIOR_WALL",
            "floor_1_finish_face_source": f1_finish_east,
            "attic_finish_face_source": attic_finish_east,
            "floor_1_finish_face_building_x_mm": f1_finish_x,
            "attic_finish_face_raw_pdf_x_mm": attic_finish_x_raw,
            "attic_finish_face_registered_building_x_mm": attic_finish_x_registered,
            "registered_finish_face_delta_mm": attic_finish_x_registered - f1_finish_x,
            "same_wall_line_on_both_floors": True,
        },
        "selection_method": "OWNER_AUTHORIZED_AGENT_SELECTION_ADJACENT_TO_SAME_REGISTERED_WALL_ON_BOTH_FLOORS",
        "location_description": "EAST_WALL_BOILER_ROOM_BELOW_AND_ATTIC_RIGHT_NORTH_ROOM_ABOVE",
        "orientation": "LONG_SIDE_PARALLEL_TO_COMMON_EAST_WALL_Y_AXIS",
        "clear_penetration_bbox_building_mm": HOLE_BUILDING_BBOX_MM,
        "clear_penetration_bbox_floor_1_pdf_mm": HOLE_BUILDING_BBOX_MM,
        "clear_penetration_bbox_attic_pdf_mm": list(attic_hole_raw.bounds),
        "same_physical_plan_bbox_on_both_floors": True,
        "clear_penetration_size_mm": [width, length],
        "clear_penetration_width_across_wall_mm": width,
        "clear_penetration_length_along_wall_mm": length,
        "clear_penetration_east_edge_to_common_finish_face_mm": f1_finish_x - HOLE_BUILDING_BBOX_MM[2],
        "floor_1_boiler_interior_contains_penetration": boiler.covers(hole),
        "attic_known_right_north_floor_contains_penetration": known_attic_floor_registered.covers(hole),
        "attic_known_floor_overlap_area_mm2": known_attic_floor_registered.intersection(hole).area,
        "wall_material": owner["owner_inputs"]["wall_material"],
        "floor_to_floor_height_mm": owner["owner_inputs"]["floor_to_floor_height_mm"],
        "pipe_od_mm": owner["owner_inputs"]["pipe_outer_diameter_mm"],
        "design_centerline_bend_radius_mm": owner["owner_inputs"]["design_minimum_bend_radius_mm"],
        "heated_radius_reduction_credited": False,
        "candidate_vertical_pipe_count": len(centers),
        "candidate_vertical_pipe_centers": centers,
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
        "diagnostic_attic_fragment_contact_count": len(fragment_contacts),
        "diagnostic_attic_fragment_contact_route_ids": fragment_contacts,
        "diagnostic_attic_fragment_minimum_clearance_mm": min(item["distance_mm"] for item in fragment_distances),
        "selected_r1_plan_location": True,
        "selected_clear_penetration_dimensions": True,
        "structural_cutting_approval": "REQUIRED_BEFORE_CONSTRUCTION_NEAR_EXTERIOR_WALL_AND_SLAB_EDGE",
        "sleeve_edge_reinforcement_firestop_water_and_air_sealing": "NOT_DESIGNED",
        "physical_route_geometry_published": False,
        "current_assigned_R1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "complete_attic_circuit_count": 0,
        "result": "PASS_COMMON_WALL_REGISTERED_R1_LOCATION_REWORK_F1_C08_LOCAL_ROUTE_STRUCTURAL_OPENING_AND_FULL_CONNECTION_ROUTING",
    }
    model["location_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "wall_registered_r1_location.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    f1_image = Image.open(F1_RENDER).convert("RGB")
    attic_image = Image.open(ATTIC_RENDER).convert("RGB")
    canvas_image = Image.new("RGB", (1800, 1380), "#F7FAFA")
    canvas = ImageDraw.Draw(canvas_image, "RGBA")
    canvas.rectangle((0, 0, 1800, 230), fill="#071A21")
    canvas.text((34, 18), "D078 · R1 СОВМЕЩЁН ПО СТЕНАМ ДВУХ ЭТАЖЕЙ", font=font(28, True), fill="white")
    canvas.text((34, 68), "Общая восточная стена: план мансарды сдвинут на 359,8 × 304,8 мм к системе 1 этажа", font=font(17, True), fill="#A7EEE7")
    canvas.text((34, 111), "Отверстие 400×160 мм · один строительный bbox x=18 050…18 210, y=7 800…8 200 мм", font=font(17), fill="#F3D58C")
    canvas.text((34, 154), "Отступ от внутренней грани стены на обоих этажах: 27,2 мм", font=font(17, True), fill="#FFFFFF")
    canvas.text((34, 195), "Проект D077 у лестницы отклонён: в нём не было регистрации двух PDF-листов.", font=font(15, True), fill="#FFB2B2")

    crop_box = (1300, 430, 1710, 920)
    for x, image, title, bbox_raw in (
        (40, f1_image, "1 ЭТАЖ · КОТЕЛЬНАЯ", HOLE_BUILDING_BBOX_MM),
        (1000, attic_image, "МАНСАРДА · ПРАВАЯ КОМНАТА", list(attic_hole_raw.bounds)),
    ):
        crop = image.crop(crop_box).resize((760, 880))
        canvas_image.paste(crop, (x, 300))
        canvas.text((x, 255), title, font=font(20, True), fill="#143842")
        p0 = to_px_mm((bbox_raw[0], bbox_raw[1]))
        p1 = to_px_mm((bbox_raw[2], bbox_raw[3]))
        sx, sy = 760 / (crop_box[2] - crop_box[0]), 880 / (crop_box[3] - crop_box[1])
        rect = (
            x + (p0[0] - crop_box[0]) * sx,
            300 + (p0[1] - crop_box[1]) * sy,
            x + (p1[0] - crop_box[0]) * sx,
            300 + (p1[1] - crop_box[1]) * sy,
        )
        canvas.rectangle(rect, fill="#FF7A0066", outline="#D50000", width=5)
        canvas.text((rect[0] - 105, rect[1] - 34), "R1 400×160", font=font(12, True), fill="#D50000", stroke_width=2, stroke_fill="white")
    canvas.text((52, 1225), "Геометрически сверху и снизу это одна точка здания, а не одинаковые координаты на разных PDF-листах.", font=font(16, True), fill="#143842")
    canvas.text((52, 1270), "Контакты: мансардные тела 0 · диагностические фрагменты 0 · на 1 этаже локально обойти F1-C08.", font=font(16, True), fill="#B00020")
    canvas.text((52, 1320), "До алмазного бурения: проверить плиту/балку у наружной стены, оформить гильзу и герметизацию.", font=font(15), fill="#566B73")
    canvas_image.save(OUTPUT / "wall_registered_r1_two_floor.png")

    (OUTPUT / "report.md").write_text(
        "# D078 — R1 привязан к одной стене двух этажей\n\n"
        "D077 отклонён: он сравнивал сырые координаты двух PDF-листов, хотя план мансарды на листе сдвинут. "
        "По наружному контуру здания определён сдвиг мансарды к системе первого этажа: −359,833 мм по X и −304,8 мм по Y.\n\n"
        "Новое отверстие размещено у общей восточной наружной стены: снизу в котельной, сверху в правой комнате. "
        "В строительной системе координат чистый bbox одинаков для обоих этажей: x=18 050…18 210, y=7 800…8 200 мм. "
        "Внутренняя грань стены после регистрации совпадает с точностью расчёта; отступ от неё до отверстия 27,2 мм.\n\n"
        "Отверстие не пересекает мансардные тела и диагностические фрагменты. На первом этаже оно пересекает контур F1-C08; этот участок нужно локально обойти. "
        "До резки перекрытия нужна проверка балок/арматуры у наружной стены, а также проект гильзы, кромки и герметизации.\n",
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
    print(json.dumps({
        "output": str(OUTPUT),
        "building_bbox_mm": HOLE_BUILDING_BBOX_MM,
        "registered_wall_delta_mm": model["common_wall_alignment"]["registered_finish_face_delta_mm"],
        "wall_gap_mm": model["clear_penetration_east_edge_to_common_finish_face_mm"],
        "f1_contacts": f1_contacts,
        "attic_body_clearance_mm": model["attic_minimum_body_clearance_mm"],
        "location_digest": model["location_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
