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
SOURCE_078 = BASE / "HA_TWO_FLOOR_WALL_REGISTERED_R1_LOCATION_078" / "wall_registered_r1_location.json"
F1_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079.zip"

PT_TO_MM = 35.2777777778
PX_PER_100_MM = 8.503937
F1_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")
ATTIC_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")

# Attic plan -> floor-1/building datum, proven in D078 by two exterior shell faces.
REGISTRATION_DX_PT = 10.20
REGISTRATION_DY_PT = 8.64
REGISTRATION_DX_MM = REGISTRATION_DX_PT * PT_TO_MM
REGISTRATION_DY_MM = REGISTRATION_DY_PT * PT_TO_MM

# Clear slab penetration is entirely on the room/wardrobe side of the common
# stair partition. It is outside the gas-concrete wall solid on both plans.
HOLE_BUILDING_BBOX_MM = [9150, 7200, 9310, 7600]

# Reservation only: no pipe centerlines are published in D079.
F1_SERVICE_CORRIDOR_AXIS_MM = [(13200, 8200), (9230, 8200), (9230, 7600)]
F1_SERVICE_CORRIDOR_HALF_WIDTH_MM = 200
ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM = [8770, 6400, 9370, 7800]


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


def route_contact_records(routes, key, geometry):
    contacts = []
    distances = []
    for route in routes:
        line = LineString(route[key])
        intersection = line.intersection(geometry)
        if intersection.is_empty:
            distances.append({"route_id": route["route_id"], "distance_mm": line.distance(geometry)})
        else:
            contacts.append({
                "route_id": route["route_id"],
                "intersection_length_mm": intersection.length,
                "intersection_geojson_type": intersection.geom_type,
                "required_action": "LOCAL_REROUTE_AROUND_INTERNAL_RISER_RESERVATION",
            })
    return contacts, distances


def aligned_attic_line(points):
    return LineString([(x - REGISTRATION_DX_MM, y - REGISTRATION_DY_MM) for x, y in points])


def to_px_mm(point):
    return round(point[0] / 100 * PX_PER_100_MM), round(point[1] / 100 * PX_PER_100_MM)


def draw_registered_geometry(
    draw: ImageDraw.ImageDraw,
    panel_x: int,
    panel_y: int,
    crop_box: tuple[int, int, int, int],
    panel_size: tuple[int, int],
    points_mm,
    fill,
    outline,
    width: int = 4,
):
    sx = panel_size[0] / (crop_box[2] - crop_box[0])
    sy = panel_size[1] / (crop_box[3] - crop_box[1])
    pixels = []
    for x_mm, y_mm in points_mm:
        px, py = to_px_mm((x_mm, y_mm))
        pixels.append((panel_x + (px - crop_box[0]) * sx, panel_y + (py - crop_box[1]) * sy))
    if fill is not None:
        draw.polygon(pixels, fill=fill)
    draw.line(pixels + ([pixels[0]] if len(pixels) > 2 else []), fill=outline, width=width, joint="curve")


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D079 is append-only")

    raw_011, vector = read(SOURCE_011)
    raw_f1, floor1 = read(SOURCE_F1)
    raw_a, attic = read(SOURCE_A)
    raw_058, diagnostic = read(SOURCE_058)
    raw_062, domains = read(SOURCE_062)
    raw_069, packing = read(SOURCE_069)
    raw_074, owner = read(SOURCE_074)
    raw_078, old = read(SOURCE_078)

    f1_room_face = path_record(F1_PDF, 304)
    f1_stair_face = path_record(F1_PDF, 15)
    attic_wardrobe_face = path_record(ATTIC_PDF, 141)
    attic_stair_face = path_record(ATTIC_PDF, 597)

    f1_room_finish_x = f1_room_face["raw_rect_pt"][2] * PT_TO_MM
    f1_stair_finish_x = f1_stair_face["raw_rect_pt"][0] * PT_TO_MM
    attic_wardrobe_finish_x = attic_wardrobe_face["raw_rect_pt"][0] * PT_TO_MM - REGISTRATION_DX_MM
    attic_stair_finish_x = attic_stair_face["raw_rect_pt"][2] * PT_TO_MM - REGISTRATION_DX_MM
    common_core_x0 = max(f1_room_finish_x, attic_wardrobe_finish_x)
    common_core_x1 = min(f1_stair_finish_x, attic_stair_finish_x)
    if common_core_x1 <= common_core_x0:
        raise ValueError("Registered stair/wardrobe wall solids do not overlap")

    hole = box(*HOLE_BUILDING_BBOX_MM)
    attic_hole_raw = translate(hole, xoff=REGISTRATION_DX_MM, yoff=REGISTRATION_DY_MM)
    corridor_axis = LineString(F1_SERVICE_CORRIDOR_AXIS_MM)
    corridor = corridor_axis.buffer(F1_SERVICE_CORRIDOR_HALF_WIDTH_MM, cap_style=2, join_style=2)
    fanout = box(*ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM)

    attic_left_north = next(
        item for item in domains["adjacent_floor_domains"]
        if item["domain_id"] == "ATTIC_LEFT_NORTH_RECT_DRAFT"
    )
    wardrobe_registered = translate(
        shape(attic_left_north["floor_geojson"]),
        xoff=-REGISTRATION_DX_MM,
        yoff=-REGISTRATION_DY_MM,
    )
    source_void = vector["vector_traced_geometry"]["attic_structural_stair_void"]
    attic_void_registered = translate(
        box(*(value * 100 for value in source_void["conservative_blocked_box_grid"])),
        xoff=-REGISTRATION_DX_MM,
        yoff=-REGISTRATION_DY_MM,
    )
    f1_treads = box(*(
        value * 100
        for value in vector["vector_traced_geometry"]["floor_1_first_three_treads"]["conservative_blocked_box_grid"]
    ))

    f1_hole_contacts, f1_hole_distances = route_contact_records(
        floor1["routes"], "ordered_points_mm", hole
    )
    f1_corridor_contacts, _ = route_contact_records(
        floor1["routes"], "ordered_points_mm", corridor
    )

    attic_body_contacts = []
    attic_body_distances = []
    fanout_body_contacts = []
    for route in attic["body_routes"]:
        line = aligned_attic_line(route["body_points_mm"])
        if line.intersects(hole):
            attic_body_contacts.append(route["route_id"])
        if line.intersects(fanout):
            fanout_body_contacts.append(route["route_id"])
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
        {
            "artifact_id": data.get("artifact_id", data.get("contract_id")),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        }
        for raw, data in (
            (raw_011, vector), (raw_f1, floor1), (raw_a, attic), (raw_058, diagnostic),
            (raw_062, domains), (raw_069, packing), (raw_074, owner), (raw_078, old),
        )
    ]

    model = {
        "schema": "homeaura-internal-stair-wardrobe-r1-strategy-0.1",
        "artifact_id": "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079",
        "status": "OWNER_SELECTED_INTERNAL_BOILER_TO_STAIR_TO_WARDROBE_STRATEGY_PASS_REWORK_PIPE_FANOUT_AND_STRUCTURAL_DETAIL",
        "source_records": source_records,
        "supersedes_artifact_id": old["artifact_id"],
        "superseded_artifact_disposition": "REJECTED_BY_OWNER_EXTERNAL_WALL_RISER_NOT_DESIRED",
        "owner_selected_topology": [
            "K1_IN_BOILER_ROOM",
            "FLOOR_LEVEL_SERVICE_RUN_FROM_BOILER_TO_STAIR",
            "VERTICAL_RISE_AT_FAR_STAIR_WALL",
            "SLAB_PENETRATION_ON_WARDROBE_SIDE",
            "ATTIC_FANOUT_INSIDE_WARDROBE",
        ],
        "coordinate_system": "BUILDING_PLAN_MM_DATUM_FLOOR_1_PDF_AFTER_EXTERIOR_SHELL_REGISTRATION",
        "pdf_page_registration": {
            "attic_to_floor_1_translation_pt": [-REGISTRATION_DX_PT, -REGISTRATION_DY_PT],
            "attic_to_floor_1_translation_mm": [-REGISTRATION_DX_MM, -REGISTRATION_DY_MM],
            "scale_rotation_or_shear": "NONE",
            "source_artifact_id": old["artifact_id"],
        },
        "shared_stair_wardrobe_partition": {
            "wall_id": "INTERNAL_FAR_STAIR_WALL_TO_ATTIC_WARDROBE",
            "floor_1_room_side_face_source": f1_room_face,
            "floor_1_stair_side_face_source": f1_stair_face,
            "attic_wardrobe_side_face_source": attic_wardrobe_face,
            "attic_stair_side_face_source": attic_stair_face,
            "floor_1_wall_solid_x_building_mm": [f1_room_finish_x, f1_stair_finish_x],
            "attic_wall_solid_x_registered_building_mm": [attic_wardrobe_finish_x, attic_stair_finish_x],
            "registered_common_wall_core_x_building_mm": [common_core_x0, common_core_x1],
            "registered_common_wall_core_width_mm": common_core_x1 - common_core_x0,
            "wall_solids_overlap_on_both_floor_plans": True,
            "wall_material": owner["owner_inputs"]["wall_material"],
        },
        "selected_penetration": {
            "description": "CLEAR_SLAB_OPENING_INSIDE_WARDROBE_SIDE_ALONG_COMMON_STAIR_PARTITION",
            "building_bbox_mm": HOLE_BUILDING_BBOX_MM,
            "floor_1_pdf_bbox_mm": HOLE_BUILDING_BBOX_MM,
            "attic_pdf_bbox_mm": list(attic_hole_raw.bounds),
            "same_physical_plan_bbox_on_both_floors": True,
            "clear_size_mm": [width, length],
            "orientation": "LONG_SIDE_PARALLEL_TO_SHARED_PARTITION_Y_AXIS",
            "floor_1_room_finish_face_clearance_mm": f1_room_finish_x - HOLE_BUILDING_BBOX_MM[2],
            "attic_wardrobe_finish_face_clearance_mm": attic_wardrobe_finish_x - HOLE_BUILDING_BBOX_MM[2],
            "does_not_cut_registered_common_wall_core": hole.bounds[2] <= common_core_x0,
            "attic_wardrobe_draft_floor_contains_opening": wardrobe_registered.covers(hole),
            "attic_conservative_stair_void_contact": hole.intersects(attic_void_registered),
            "attic_conservative_stair_void_clearance_mm": hole.distance(attic_void_registered),
            "structural_slab_scan_and_opening_approval": "REQUIRED_BEFORE_CONSTRUCTION",
        },
        "floor_1_service_corridor_reservation": {
            "axis_building_mm": F1_SERVICE_CORRIDOR_AXIS_MM,
            "reserved_half_width_mm": F1_SERVICE_CORRIDOR_HALF_WIDTH_MM,
            "routing_role": "K1_TO_STAIR_FAR_WALL_BUNDLE_RESERVATION_ONLY",
            "first_three_treads_contact": corridor.intersects(f1_treads),
            "existing_route_contact_count": len(f1_corridor_contacts),
            "existing_route_contacts": f1_corridor_contacts,
            "pipe_centerlines_published": False,
        },
        "attic_wardrobe_fanout_reservation": {
            "building_bbox_mm": ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM,
            "attic_pdf_bbox_mm": list(translate(fanout, xoff=REGISTRATION_DX_MM, yoff=REGISTRATION_DY_MM).bounds),
            "wardrobe_draft_floor_contains_reservation": wardrobe_registered.covers(fanout),
            "existing_attic_body_contact_count": len(fanout_body_contacts),
            "existing_attic_body_contact_route_ids": fanout_body_contacts,
            "requires_local_body_rework": bool(fanout_body_contacts),
            "second_collector_claimed": False,
            "role": "PIPE_FANOUT_AND_DIRECTION_CHANGE_ZONE_NOT_A_SECOND_MANIFOLD",
        },
        "floor_to_floor_height_mm": owner["owner_inputs"]["floor_to_floor_height_mm"],
        "pipe_od_mm": owner["owner_inputs"]["pipe_outer_diameter_mm"],
        "design_centerline_bend_radius_mm": owner["owner_inputs"]["design_minimum_bend_radius_mm"],
        "heated_radius_reduction_credited": False,
        "minimum_reserved_single_bend_tangent_mm": owner["owner_inputs"]["design_minimum_bend_radius_mm"],
        "recommended_local_turning_zone_depth_mm": 200,
        "twenty_six_pipe_bend_fanout_3d_validation": "NOT_EVALUATED",
        "candidate_vertical_pipe_count": len(centers),
        "candidate_vertical_pipe_centers": centers,
        "straight_penetration_packing_scenario_fits": True,
        "packing_minimum_center_distance_mm": packing["minimum_center_distance_mm"],
        "packing_minimum_provisional_envelope_gap_mm": packing["minimum_provisional_envelope_clear_gap_mm"],
        "floor_1_penetration_route_contact_count": len(f1_hole_contacts),
        "floor_1_penetration_route_contacts": f1_hole_contacts,
        "floor_1_minimum_noncontact_route_clearance_mm": min(item["distance_mm"] for item in f1_hole_distances),
        "attic_body_contact_count": len(attic_body_contacts),
        "attic_body_contact_route_ids": attic_body_contacts,
        "attic_minimum_body_clearance_mm": min(item["distance_mm"] for item in attic_body_distances),
        "diagnostic_attic_fragment_contact_count": len(fragment_contacts),
        "diagnostic_attic_fragment_contact_route_ids": fragment_contacts,
        "diagnostic_attic_fragment_minimum_clearance_mm": min(item["distance_mm"] for item in fragment_distances),
        "selected_r1_plan_location": True,
        "selected_internal_route_strategy": True,
        "physical_route_geometry_published": False,
        "current_assigned_r1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "complete_attic_circuit_count": 0,
        "slab_rebar_beam_scan": "REQUIRED",
        "aac_wall_chases_and_transverse_openings": "OWNER_ALLOWED_MATERIAL_RECORDED_DETAIL_NOT_DESIGNED",
        "sleeves_firestop_edge_reinforcement_and_acoustic_sealing": "NOT_DESIGNED",
        "result": "PASS_INTERNAL_RISER_LOCATION_AND_ROUTE_STRATEGY_REWORK_F1_C01_LOCAL_ROUTE_ATTIC_A_C01_FANOUT_AND_FULL_26_PIPE_ROUTING",
    }
    model["strategy_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "internal_stair_wardrobe_r1_strategy.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    f1_image = Image.open(F1_RENDER).convert("RGB")
    attic_image = Image.open(ATTIC_RENDER).convert("RGB")
    canvas_image = Image.new("RGB", (1800, 1420), "#F4F8F8")
    draw = ImageDraw.Draw(canvas_image, "RGBA")
    draw.rectangle((0, 0, 1800, 245), fill="#071A21")
    draw.text((34, 18), "D079 · ВНУТРЕННИЙ СТОЯК: КОТЕЛЬНАЯ → ЛЕСТНИЦА → ГАРДЕРОБНАЯ", font=font(26, True), fill="white")
    draw.text((34, 67), "Наружная стена отклонена владельцем · отверстие 400×160 мм у дальней стены лестницы", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 110), "Высота 3 000 мм · труба Ø16 · расчётный R80 без уменьшения при прогреве", font=font(17), fill="#F3D58C")
    draw.text((34, 153), "Оранжевое — отверстие · жёлтое — резерв короба/транзита · зелёное — зона развода в гардеробной", font=font(15), fill="white")
    draw.text((34, 197), "Это выбранная трассировочная схема; 26 отдельных труб и узлы изгиба ещё не опубликованы.", font=font(15, True), fill="#FFB2B2")

    crop_box = (600, 400, 1450, 1050)
    panel_size = (820, 720)
    panel_y = 315
    for panel_x, image, title in (
        (40, f1_image, "1 ЭТАЖ · ОТ КОТЕЛЬНОЙ К ДАЛЬНЕЙ СТЕНЕ ЛЕСТНИЦЫ"),
        (940, attic_image, "МАНСАРДА · ВЫХОД И РАЗВОД В ГАРДЕРОБНОЙ"),
    ):
        crop = image.crop(crop_box).resize(panel_size)
        canvas_image.paste(crop, (panel_x, panel_y))
        draw.text((panel_x, 265), title, font=font(18, True), fill="#143842")

    wall_y0, wall_y1 = 6500, 8000
    f1_wall = [(f1_room_finish_x, wall_y0), (f1_stair_finish_x, wall_y0), (f1_stair_finish_x, wall_y1), (f1_room_finish_x, wall_y1)]
    attic_wall_raw = [
        (attic_wardrobe_finish_x + REGISTRATION_DX_MM, wall_y0 + REGISTRATION_DY_MM),
        (attic_stair_finish_x + REGISTRATION_DX_MM, wall_y0 + REGISTRATION_DY_MM),
        (attic_stair_finish_x + REGISTRATION_DX_MM, wall_y1 + REGISTRATION_DY_MM),
        (attic_wardrobe_finish_x + REGISTRATION_DX_MM, wall_y1 + REGISTRATION_DY_MM),
    ]
    draw_registered_geometry(draw, 40, panel_y, crop_box, panel_size, f1_wall, "#7257A844", "#5E35B1", 3)
    draw_registered_geometry(draw, 940, panel_y, crop_box, panel_size, attic_wall_raw, "#7257A844", "#5E35B1", 3)

    draw_registered_geometry(
        draw, 40, panel_y, crop_box, panel_size, F1_SERVICE_CORRIDOR_AXIS_MM,
        None, "#E9A400AA", 18,
    )
    f1_hole_points = [
        (HOLE_BUILDING_BBOX_MM[0], HOLE_BUILDING_BBOX_MM[1]),
        (HOLE_BUILDING_BBOX_MM[2], HOLE_BUILDING_BBOX_MM[1]),
        (HOLE_BUILDING_BBOX_MM[2], HOLE_BUILDING_BBOX_MM[3]),
        (HOLE_BUILDING_BBOX_MM[0], HOLE_BUILDING_BBOX_MM[3]),
    ]
    draw_registered_geometry(draw, 40, panel_y, crop_box, panel_size, f1_hole_points, "#FF6D0066", "#D84315", 5)

    attic_hole_points = [(x + REGISTRATION_DX_MM, y + REGISTRATION_DY_MM) for x, y in f1_hole_points]
    fanout_raw = [
        (ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[0] + REGISTRATION_DX_MM, ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[1] + REGISTRATION_DY_MM),
        (ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[2] + REGISTRATION_DX_MM, ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[1] + REGISTRATION_DY_MM),
        (ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[2] + REGISTRATION_DX_MM, ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[3] + REGISTRATION_DY_MM),
        (ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[0] + REGISTRATION_DX_MM, ATTIC_WARDROBE_FANOUT_BBOX_BUILDING_MM[3] + REGISTRATION_DY_MM),
    ]
    draw_registered_geometry(draw, 940, panel_y, crop_box, panel_size, fanout_raw, "#00A66A44", "#008F5A", 4)
    draw_registered_geometry(draw, 940, panel_y, crop_box, panel_size, attic_hole_points, "#FF6D0066", "#D84315", 5)

    draw.text((58, 1070), "Совпадающая перегородка", font=font(14, True), fill="#5E35B1")
    draw.text((58, 1105), "Отверстие со стороны помещения: не режет газобетонную полосу и не попадает в лестничный проём.", font=font(15), fill="#143842")
    draw.text((58, 1148), "Первый этаж: требуется локально переложить F1-C01 и все транзиты, вошедшие в жёлтый резерв.", font=font(15, True), fill="#B00020")
    draw.text((58, 1191), "Мансарда: отверстие не касается существующих тел; для зоны развода перестраивается A-C01.", font=font(15, True), fill="#B00020")
    draw.text((58, 1242), "Перед бурением: просканировать плиту/балки; предусмотреть гильзу, противопожарную и акустическую заделку.", font=font(15), fill="#566B73")
    draw.text((58, 1290), "R80 принят как жёсткий расчётный минимум. Уменьшение радиуса при прогреве в запас не засчитано.", font=font(15), fill="#566B73")
    draw.text((58, 1345), "СТАТУС: МЕСТО И СХЕМА ВЫБРАНЫ · ПОЛНАЯ РАЗВОДКА 26 ТРУБ И 3D-ФАНАУТ — СЛЕДУЮЩИЙ БЛОК", font=font(15, True), fill="#143842")
    canvas_image.save(OUTPUT / "internal_stair_wardrobe_r1_two_floor.png")

    (OUTPUT / "report.md").write_text(
        "# D079 — внутренний стояк через лестницу в гардеробную\n\n"
        "Вариант D078 у наружной стены отклонён по решению владельца. Принята внутренняя схема: от K1 в котельной трубы идут в зарезервированном напольном/пристенном сервисном коридоре к лестнице, поднимаются у дальней стены и выходят в гардеробной мансарды.\n\n"
        "Планы этажей зарегистрированы в одной строительной системе. Полосы одной и той же перегородки перекрываются на 220,1 мм. Чистое отверстие 400×160 мм выбрано в bbox x=9 150…9 310, y=7 200…7 600 мм — со стороны помещения, без резки полосы газобетона. На первом этаже оно находится в 7,6 мм от чистовой грани перегородки, на мансарде в 66,8 мм от грани гардеробной. От консервативного лестничного проёма остаётся 230,2 мм.\n\n"
        "Отверстие не касается мансардных тел или диагностических фрагментов. На первом этаже требуется локально перестроить F1-C01; сервисный коридор затрагивает дополнительные существующие транзиты и поэтому пока является резервом, а не опубликованными трубами. В гардеробной выделена зона развода, для которой потребуется перестроить A-C01.\n\n"
        "Исходные физические параметры зафиксированы: высота 3 000 мм, труба Ø16 мм, расчётный радиус оси R80. Уменьшение радиуса после прогрева не используется. Прямая упаковка 26 труб в отверстии воспроизводит прежний сценарий, но одновременные изгибы и 3D-фанаут ещё должны быть построены и проверены. Перед бурением обязательны сканирование плиты/балок, рабочая гильза и узлы заделки.\n",
        encoding="utf-8",
    )

    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "strategy_digest": model["strategy_digest"],
        "append_only": True,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in files
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "hole_building_bbox_mm": HOLE_BUILDING_BBOX_MM,
        "common_wall_core_width_mm": common_core_x1 - common_core_x0,
        "floor_1_wall_clearance_mm": model["selected_penetration"]["floor_1_room_finish_face_clearance_mm"],
        "attic_wall_clearance_mm": model["selected_penetration"]["attic_wardrobe_finish_face_clearance_mm"],
        "attic_void_clearance_mm": model["selected_penetration"]["attic_conservative_stair_void_clearance_mm"],
        "f1_hole_contacts": f1_hole_contacts,
        "f1_corridor_contacts": [item["route_id"] for item in f1_corridor_contacts],
        "fanout_body_contacts": fanout_body_contacts,
        "strategy_digest": model["strategy_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
