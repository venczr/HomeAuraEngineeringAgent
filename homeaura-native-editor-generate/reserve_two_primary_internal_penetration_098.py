from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_079 = BASE / "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079" / "internal_stair_wardrobe_r1_strategy.json"
SOURCE_093 = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
SOURCE_096 = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096" / "attic_primary_pipe_selection.json"
SOURCE_097 = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097" / "attic_primary_bend_fittings.json"
F1_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098.zip"

OPENING_BBOX = [9190.0, 7300.0, 9310.0, 7500.0]
PIPE_AXES = [
    {"primary_id": "PRIMARY_SUPPLY_32", "building_plan_xy_mm": [9250.0, 7350.0]},
    {"primary_id": "PRIMARY_RETURN_32", "building_plan_xy_mm": [9250.0, 7450.0]},
]
PROVISIONAL_ENVELOPE_OD = 70.0
PX_PER_100_MM = 8.503937


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def contained(inner, outer):
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def to_px(value_mm: float) -> float:
    return value_mm / 100 * PX_PER_100_MM


def draw_plan_panel(canvas, image, panel_box, crop_px, raw_offset_mm, title):
    draw = ImageDraw.Draw(canvas, "RGBA")
    x0, y0, x1, y1 = panel_box
    source = image.crop(crop_px).resize((x1-x0, y1-y0))
    canvas.paste(source, (x0, y0))
    sx = (x1-x0)/(crop_px[2]-crop_px[0]); sy = (y1-y0)/(crop_px[3]-crop_px[1])
    def pos(x_mm, y_mm):
        px = to_px(x_mm+raw_offset_mm[0]); py = to_px(y_mm+raw_offset_mm[1])
        return (x0+(px-crop_px[0])*sx, y0+(py-crop_px[1])*sy)
    a = pos(OPENING_BBOX[0], OPENING_BBOX[1]); b = pos(OPENING_BBOX[2], OPENING_BBOX[3])
    draw.rectangle((*a, *b), fill="#FF8A003F", outline="#D84315", width=5)
    radius_px = PROVISIONAL_ENVELOPE_OD/2/100*PX_PER_100_MM*(sx+sy)/2
    for axis, colour in zip(PIPE_AXES, ("#D84315", "#1565C0")):
        cx, cy = pos(*axis["building_plan_xy_mm"])
        draw.ellipse((cx-radius_px,cy-radius_px,cx+radius_px,cy+radius_px), fill=colour, outline="white", width=3)
    draw.rectangle((x0, y0, x1, y0+48), fill="#071A21DD")
    draw.text((x0+15,y0+10),title,font=font(15,True),fill="white")


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D098 is append-only")
    raw079, strategy = read(SOURCE_079)
    raw093, ports = read(SOURCE_093)
    raw096, pipe = read(SOURCE_096)
    raw097, bends = read(SOURCE_097)
    old = strategy["selected_penetration"]["building_bbox_mm"]
    service = [9070.0, 6500.0, 9370.0, 7800.0]
    cabinet = ports["mounting_transform"]["cabinet_plan_bbox_building_mm"]
    dx, dy = strategy["pdf_page_registration"]["attic_to_floor_1_translation_mm"]
    attic_bbox = [OPENING_BBOX[0]-dx,OPENING_BBOX[1]-dy,OPENING_BBOX[2]-dx,OPENING_BBOX[3]-dy]
    radius = PROVISIONAL_ENVELOPE_OD/2
    axis_gap = abs(PIPE_AXES[1]["building_plan_xy_mm"][1]-PIPE_AXES[0]["building_plan_xy_mm"][1])
    x_margin = min(PIPE_AXES[0]["building_plan_xy_mm"][0]-OPENING_BBOX[0],OPENING_BBOX[2]-PIPE_AXES[0]["building_plan_xy_mm"][0])-radius
    y_margin = min(PIPE_AXES[0]["building_plan_xy_mm"][1]-OPENING_BBOX[1],OPENING_BBOX[3]-PIPE_AXES[1]["building_plan_xy_mm"][1])-radius
    model = {
        "schema": "homeaura-two-primary-internal-penetration-reservation-0.1",
        "artifact_id": "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098",
        "status": "TWO_PRIMARY_INTERNAL_SAME_COORDINATE_PENETRATION_RESERVATION_PASS_REWORK_SLAB_SCAN_FIRESTOP_AND_INSULATION_SELECTION",
        "source_records": [
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw079,strategy),(raw093,ports),(raw096,pipe),(raw097,bends))
        ],
        "owner_route_intent": "K1_BOILER_ROOM_FLOOR_RUN_TO_FAR_STAIR_WALL_VERTICAL_TO_ATTIC_WARDROBE_K2",
        "external_wall_used": False,
        "floor_to_floor_height_mm": 3000,
        "primary_main_count": 2,
        "primary_pipe_od_mm": 32,
        "selected_building_plan_opening_candidate": {
            "building_bbox_mm": OPENING_BBOX,
            "clear_size_mm": [OPENING_BBOX[2]-OPENING_BBOX[0],OPENING_BBOX[3]-OPENING_BBOX[1]],
            "floor_1_pdf_bbox_mm": OPENING_BBOX,
            "attic_pdf_bbox_mm": attic_bbox,
            "same_physical_plan_coordinates_on_both_floors": True,
            "inside_D079_maximum_reservation": contained(OPENING_BBOX, old),
            "D079_maximum_reservation_bbox_mm": old,
            "inside_attic_K2_service_zone": contained(OPENING_BBOX, service),
            "attic_K2_service_zone_bbox_mm": service,
            "does_not_cut_registered_common_wall_core": OPENING_BBOX[2] <= strategy["shared_stair_wardrobe_partition"]["registered_common_wall_core_x_building_mm"][0],
            "same_D079_attic_floor_and_tread_checks_inherited_by_containment": True,
        },
        "vertical_primary_axes": PIPE_AXES,
        "provisional_insulated_pipe_envelope": {
            "outer_envelope_diameter_mm": PROVISIONAL_ENVELOPE_OD,
            "basis": "32MM_PIPE_PLUS_PROVISIONAL_INSULATION_AND_RESERVATION_ALLOWANCE",
            "final_insulation_product_selected": False,
            "axis_pitch_mm": axis_gap,
            "clear_gap_between_envelopes_mm": axis_gap-PROVISIONAL_ENVELOPE_OD,
            "minimum_envelope_to_opening_x_edge_mm": x_margin,
            "minimum_envelope_to_opening_y_edge_mm": y_margin,
            "geometric_packing_pass": min(axis_gap-PROVISIONAL_ENVELOPE_OD,x_margin,y_margin) >= 0,
            "firestop_annulus_requirement_included": False,
        },
        "cabinet_relation": {
            "selected_K2_cabinet_plan_bbox_mm": cabinet,
            "both_vertical_axes_beneath_cabinet_plan_bbox": all(cabinet[0] <= p["building_plan_xy_mm"][0] <= cabinet[2] and cabinet[1] <= p["building_plan_xy_mm"][1] <= cabinet[3] for p in PIPE_AXES),
            "cabinet_bottom_aff_mm": 270,
            "primary_upturn_and_connection_space_detail_published": False,
        },
        "primary_turn_method": "FOUR_SELECTED_32X32_PRESS_ELBOWS_D097",
        "slab_opening_cut_authorized": False,
        "slab_rebar_beam_scan_required": True,
        "structural_engineer_or_responsible_designer_release_required": True,
        "sleeve_firestop_acoustic_water_seal_detail": "NOT_DESIGNED",
        "complete_primary_route_geometry_count": 0,
        "construction_drawing_status": "NOT_ISSUED",
        "result": "PASS_TWO_MAIN_COORDINATE_AND_PACKING_RESERVATION_REWORK_SITE_STRUCTURE_AND_PENETRATION_DETAIL",
    }
    model["penetration_reservation_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "two_primary_internal_penetration.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")

    f1 = Image.open(F1_RENDER).convert("RGB"); attic = Image.open(ATTIC_RENDER).convert("RGB")
    canvas = Image.new("RGB",(1800,1360),"#F4F8F8")
    draw = ImageDraw.Draw(canvas,"RGBA")
    draw.rectangle((0,0,1800,225),fill="#071A21")
    draw.text((34,18),"D098 · ДВЕ МАГИСТРАЛИ ЧЕРЕЗ ВНУТРЕННЕЕ ПЕРЕКРЫТИЕ",font=font(25,True),fill="white")
    draw.text((34,67),"Одни и те же координаты на 1 этаже и мансарде · без наружной стены",font=font(18,True),fill="#A7EEE7")
    draw.text((34,112),"Резерв отверстия 120×200 мм · 2 оси Ø32 · шаг 100 мм · условный конверт Ø70",font=font(17),fill="#F3D58C")
    draw.text((34,158),"Это место для сканирования и согласования, не разрешение бурить плиту",font=font(17,True),fill="#FFB2B2")
    crop=(650,490,940,780)
    draw_plan_panel(canvas,f1,(45,290,855,1100),crop,(0,0),"1 ЭТАЖ · КОТЕЛЬНАЯ → ДАЛЬНЯЯ СТЕНА ЛЕСТНИЦЫ")
    draw_plan_panel(canvas,attic,(945,290,1755,1100),crop,(-dx,-dy),"МАНСАРДА · ВЫХОД ПОД K2 В ГАРДЕРОБНОЙ")
    draw.text((75,1155),"Красный круг — подача Ø32 · синий — обратка Ø32 · полупрозрачный оранжевый прямоугольник — резерв проходки.",font=font(15),fill="#143842")
    draw.text((75,1202),f"Запасы конверта: между трубами {axis_gap-PROVISIONAL_ENVELOPE_OD:.0f} мм · до длинной грани {x_margin:.0f} мм · до торца {y_margin:.0f} мм.",font=font(15,True),fill="#143842")
    draw.text((75,1249),"ПЕРЕД БУРЕНИЕМ: разметка по чистому полу, скан арматуры/балок, гильза, огнезаделка и проверка утепления.",font=font(15,True),fill="#B00020")
    canvas.save(OUTPUT / "two_primary_internal_penetration_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D098 — совпадающая внутренняя проходка двух магистралей\n\n"
        "Внутри ранее проверенного резерва D079 выделено уменьшенное отверстие-кандидат 120×200 мм: x=9190…9310, y=7300…7500 мм в общей строительной системе. Эти координаты одинаковы для первого этажа и мансарды. Проходка находится со стороны помещения у дальней стены лестницы, под шкафом K2 в гардеробной и не использует наружную стену.\n\n"
        "Оси подачи и обратки 32×3 расположены в точках (9250;7350) и (9250;7450) мм. Для резервирования принят условный наружный конверт 70 мм на магистраль: между конвертами остаётся 30 мм, до краёв отверстия — минимум 15 мм. Это геометрическая проверка, а не узел огнезаделки.\n\n"
        "Перед бурением обязательны сканирование арматуры/балок, подтверждение конструктора, выбор утепления и разработка гильзы/огнезаделки. Полная трасса магистралей пока не опубликована.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({
        "artifact_id":model["artifact_id"],"penetration_reservation_digest":model["penetration_reservation_digest"],"append_only":True,
        "files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"opening":OPENING_BBOX,"axes":PIPE_AXES,"digest":model["penetration_reservation_digest"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
