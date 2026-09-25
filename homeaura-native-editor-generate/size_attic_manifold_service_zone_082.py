from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import translate
from shapely.geometry import LineString, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_062 = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
SOURCE_081 = BASE / "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081" / "attic_wardrobe_manifold.json"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
PX_PER_100_MM = 8.503937
SERVICE_BBOX_BUILDING_MM = [9070, 6500, 9370, 7800]
SOURCE_RESERVE_BBOX_BUILDING_MM = [9070, 7200, 9370, 7800]
MAX_OPENING_BBOX_BUILDING_MM = [9150, 7200, 9310, 7600]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(
        str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size
    )


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D082 is append-only")
    raw_050, attic = read(SOURCE_050)
    raw_062, domains = read(SOURCE_062)
    raw_081, source = read(SOURCE_081)
    wardrobe_source = next(
        item for item in domains["adjacent_floor_domains"]
        if item["domain_id"] == "ATTIC_LEFT_NORTH_RECT_DRAFT"
    )
    wardrobe = translate(shape(wardrobe_source["floor_geojson"]), xoff=-DX_MM, yoff=-DY_MM)
    service = box(*SERVICE_BBOX_BUILDING_MM)
    source_reserve = box(*SOURCE_RESERVE_BBOX_BUILDING_MM)
    opening = box(*MAX_OPENING_BBOX_BUILDING_MM)
    body_records = []
    for route in attic["body_routes"]:
        line = LineString([(x - DX_MM, y - DY_MM) for x, y in route["body_points_mm"]])
        body_records.append({
            "route_id": route["route_id"],
            "contact": line.intersects(service),
            "distance_mm": line.distance(service),
        })
    contacts = [item["route_id"] for item in body_records if item["contact"]]
    minimum_clearance = min(item["distance_mm"] for item in body_records)
    service_length = SERVICE_BBOX_BUILDING_MM[3] - SERVICE_BBOX_BUILDING_MM[1]
    service_depth = SERVICE_BBOX_BUILDING_MM[2] - SERVICE_BBOX_BUILDING_MM[0]
    if not wardrobe.covers(service) or contacts:
        raise RuntimeError({"wardrobe_covers": wardrobe.covers(service), "contacts": contacts})

    sources = [
        {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
        for raw, data in ((raw_050, attic), (raw_062, domains), (raw_081, source))
    ]
    model = {
        "schema": "homeaura-attic-manifold-service-zone-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082",
        "status": "TWELVE_CIRCUIT_MANIFOLD_SERVICE_ZONE_PASS_VECTOR_DRAFT_REWORK_PRODUCT_MOUNTING_AND_HYDRAULICS",
        "source_records": sources,
        "supersedes_reservation_artifact_id": source["artifact_id"],
        "superseded_reservation_reason": "D081_600MM_LONG_RESERVATION_SHORTER_THAN_DOCUMENTED_12_PORT_TOTAL_MANIFOLD_DIMENSION_862MM",
        "installation_orientation": "HORIZONTAL_HEADER_RAIL_MOUNTED_ON_VERTICAL_AAC_PARTITION_LONG_AXIS_ALONG_PLAN_Y",
        "service_zone_bbox_building_mm": SERVICE_BBOX_BUILDING_MM,
        "service_zone_bbox_attic_pdf_mm": [
            SERVICE_BBOX_BUILDING_MM[0] + DX_MM,
            SERVICE_BBOX_BUILDING_MM[1] + DY_MM,
            SERVICE_BBOX_BUILDING_MM[2] + DX_MM,
            SERVICE_BBOX_BUILDING_MM[3] + DY_MM,
        ],
        "service_zone_clear_length_mm": service_length,
        "service_zone_clear_depth_mm": service_depth,
        "wardrobe_vector_draft_floor_contains_service_zone": wardrobe.covers(service),
        "existing_body_contact_count": len(contacts),
        "existing_body_contact_route_ids": contacts,
        "minimum_existing_body_centerline_clearance_mm": minimum_clearance,
        "maximum_opening_inside_service_zone": service.covers(opening),
        "source_D081_reservation_inside_revised_service_zone": service.covers(source_reserve),
        "product_class_evidence": {
            "product_selection_status": "FAMILY_CAPABILITY_EVIDENCE_NOT_PURCHASE_SELECTION",
            "uponor_vario_official_url": "https://www.uponor.com/en-en/products/manifolds-vario",
            "uponor_supported_circuit_range": "2_TO_12_OR_2_TO_16_DEPENDING_VARIANT",
            "uponor_loop_pitch_mm": 50,
            "uponor_primary_connection": "G1",
            "uponor_flowmeter_range_l_min": [0, 5],
            "rehau_official_installation_pdf": "https://www.rehau.com/downloads/594742/floor-heating-installation-guide.pdf",
            "rehau_documented_port_count": 12,
            "rehau_12_port_header_length_mm": 740,
            "rehau_12_port_total_dimension_mm": 862,
            "accessed_date": "2026-08-13",
        },
        "documented_12_port_total_dimension_mm": 862,
        "service_length_margin_over_documented_total_mm": service_length - 862,
        "physical_product_selected": False,
        "cabinet_selected": False,
        "aac_fixing_detail": "NOT_DESIGNED_REQUIRES_LOAD_SPREADING_FIXINGS_AND_PRODUCT_INSTRUCTIONS",
        "top_bottom_side_service_clearances": "NOT_ACCEPTED_UNTIL_PRODUCT_SELECTED",
        "manifold_top_header_height_above_insulation_mm": "PRODUCT_DEPENDENT_REHAU_GUIDE_EXAMPLE_650MM",
        "loop_ports_and_primary_connections_published": False,
        "new_pipe_geometry_count": 0,
        "result": "PASS_1300X300_WARDROBE_SERVICE_RESERVATION_REWORK_PRODUCT_FIXING_HYDRAULICS_AND_PORT_GEOMETRY",
    }
    model["service_zone_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_manifold_service_zone.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    source_image = Image.open(ATTIC_RENDER).convert("RGB")
    canvas = source_image.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 225), fill="#071A21")
    draw.text((28, 14), "D082 · СЕРВИСНАЯ ЗОНА K2 В ГАРДЕРОБНОЙ", font=font(25, True), fill="white")
    draw.text((28, 55), "300×1300 мм вдоль внутренней стены · 12 портов · без пересечения тел", font=font(16, True), fill="#A7EEE7")
    draw.text((28, 91), "Документированный ориентир: рейка 740 мм / общий габарит 862 мм", font=font(16), fill="#F3D58C")
    draw.text((28, 127), f"Запас по длине: {service_length - 862} мм · до ближайшей оси тела: {minimum_clearance:.1f} мм", font=font(15, True), fill="white")
    draw.text((28, 164), "Класс изделия подтверждён · конкретный коллектор, шкаф, крепёж и гидравлика ещё не выбраны", font=font(15, True), fill="#FFB2B2")
    draw.text((28, 196), "Зона полностью лежит в векторном черновом полу; границы не являются обмером.", font=font(13), fill="#C4D6DB")

    def px_building(x, y):
        return ((x + DX_MM) / 100 * PX_PER_100_MM, (y + DY_MM) / 100 * PX_PER_100_MM)

    x0, y0 = px_building(SERVICE_BBOX_BUILDING_MM[0], SERVICE_BBOX_BUILDING_MM[1])
    x1, y1 = px_building(SERVICE_BBOX_BUILDING_MM[2], SERVICE_BBOX_BUILDING_MM[3])
    draw.rectangle((x0, y0, x1, y1), fill="#00A66A55", outline="#006A43", width=5)
    rail_x = (x0 + x1) / 2
    rail_y0 = y0 + (y1 - y0 - 862 / 100 * PX_PER_100_MM) / 2
    rail_y1 = rail_y0 + 862 / 100 * PX_PER_100_MM
    draw.line((rail_x, rail_y0, rail_x, rail_y1), fill="#006A43", width=12)
    for index in range(12):
        y = rail_y0 + (index + 0.5) * (rail_y1 - rail_y0) / 12
        draw.ellipse((rail_x - 10, y - 5, rail_x + 10, y + 5), fill="#FFD45C", outline="#6A5300")
    draw.text((x0 - 20, y0 - 40), "K2 · 12 КОНТУРОВ", font=font(15, True), fill="#006A43", stroke_width=2, stroke_fill="white")

    hx0, hy0 = px_building(MAX_OPENING_BBOX_BUILDING_MM[0], MAX_OPENING_BBOX_BUILDING_MM[1])
    hx1, hy1 = px_building(MAX_OPENING_BBOX_BUILDING_MM[2], MAX_OPENING_BBOX_BUILDING_MM[3])
    draw.rectangle((hx0, hy0, hx1, hy1), fill="#FF6D0055", outline="#D84315", width=3)
    draw.text((hx0 - 120, hy1 + 10), "макс. резерв отверстия", font=font(12, True), fill="#D84315", stroke_width=2, stroke_fill="white")
    canvas.save(OUTPUT / "attic_manifold_service_zone_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D082 — монтажная сервисная зона K2\n\n"
        "Резерв D081 длиной 600 мм был недостаточен для реального 12-контурного коллектора. В официальных данных Uponor подтверждены варианты на 12 и более контуров, шаг портов 50 мм, первичное подключение G1 и расходомеры 0–5 л/мин. В монтажном руководстве REHAU для 12 портов приведены длина рейки 740 мм и общий габарит 862 мм.\n\n"
        "Новая сервисная зона имеет 300×1300 мм и расположена вдоль внутренней стены гардеробной. Она целиком находится в черновом векторном полу, включает максимальный резерв отверстия и не пересекает ни одного тела. Запас над документированным габаритом составляет 438 мм; до ближайшей оси A-C01 около 29,8 мм.\n\n"
        "Это подтверждение вместимости класса изделия, а не выбор конкретной марки. Шкаф, крепление к газобетону, сервисные зазоры, порты и гидравлика остаются REWORK.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "service_zone_digest": model["service_zone_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "service_bbox": SERVICE_BBOX_BUILDING_MM,
        "length_margin_mm": model["service_length_margin_over_documented_total_mm"],
        "body_contacts": contacts,
        "body_clearance_mm": minimum_clearance,
        "digest": model["service_zone_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
