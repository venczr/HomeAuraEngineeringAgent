from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_082 = BASE / "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082" / "attic_manifold_service_zone.json"
SOURCE_085 = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
SOURCE_086 = BASE / "HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086" / "attic_routing_budgets.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088.zip"

PORT_COUNT_PER_HEADER = 12
LOOP_PITCH_MM = 50
HEADER_PITCH_MM = 225
TOP_HEADER_HEIGHT_MM = 650
RETURN_HEADER_HEIGHT_MM = TOP_HEADER_HEIGHT_MM - HEADER_PITCH_MM
WALL_PLANE_X_MM = 9220
OWNER_BEND_RADIUS_MM = 80


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
        raise FileExistsError("D088 is append-only")
    raw_082, service = read(SOURCE_082)
    raw_085, body = read(SOURCE_085)
    raw_086, budgets = read(SOURCE_086)
    x0, y0, x1, y1 = service["service_zone_bbox_building_mm"]
    span = (PORT_COUNT_PER_HEADER - 1) * LOOP_PITCH_MM
    first_y = (y0 + y1 - span) / 2
    last_y = first_y + span
    port_records = []
    for index in range(PORT_COUNT_PER_HEADER):
        y = first_y + index * LOOP_PITCH_MM
        for header, z in (("SUPPLY_HEADER", TOP_HEADER_HEIGHT_MM), ("RETURN_HEADER", RETURN_HEADER_HEIGHT_MM)):
            port_records.append({
                "candidate_port_id": f"K2-P{index + 1:02d}-{'S' if header == 'SUPPLY_HEADER' else 'R'}",
                "station_index": index + 1,
                "header": header,
                "building_xyz_mm": [WALL_PLANE_X_MM, y, z],
                "plan_xy_mm": [WALL_PLANE_X_MM, y],
                "route_id": None,
                "assigned": False,
            })
    xyz = {tuple(item["building_xyz_mm"]) for item in port_records}
    plan = {tuple(item["plan_xy_mm"]) for item in port_records}
    west_face_depth = WALL_PLANE_X_MM - x0
    if len(xyz) != 24 or len(plan) != 12 or first_y < y0 or last_y > y1 or west_face_depth < OWNER_BEND_RADIUS_MM:
        raise RuntimeError({"xyz": len(xyz), "plan": len(plan), "first_y": first_y, "last_y": last_y, "depth": west_face_depth})

    model = {
        "schema": "homeaura-attic-k2-parametric-port-lattice-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088",
        "status": "PARAMETRIC_TWELVE_STATION_K2_PORT_LATTICE_FITS_SERVICE_ZONE_REWORK_PRODUCT_SELECTION_ASSIGNMENT_AND_FANOUT",
        "source_records": [
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_082, service), (raw_085, body), (raw_086, budgets))
        ],
        "manufacturer_class_evidence": {
            "official_source_url": "https://www.uponor.com/en-en/products/manifolds-vario",
            "accessed_date": "2026-08-13",
            "supported_circuit_count_in_class": "UP_TO_12_OR_16_DEPENDING_VARIANT",
            "loop_connection": "G3/4_EUROCONE",
            "primary_connection": "G1",
            "flowmeter_range_l_min": [0, 5],
            "loop_pitch_mm": LOOP_PITCH_MM,
            "header_pitch_mm": HEADER_PITCH_MM,
        },
        "product_selection_status": "NOT_SELECTED_PARAMETRIC_CLASS_ONLY",
        "service_zone_bbox_building_mm": [x0, y0, x1, y1],
        "service_zone_plan_depth_mm": x1 - x0,
        "service_zone_plan_length_mm": y1 - y0,
        "parametric_wall_plane_x_building_mm": WALL_PLANE_X_MM,
        "port_station_count": PORT_COUNT_PER_HEADER,
        "candidate_3d_port_count": len(port_records),
        "unique_3d_coordinate_count": len(xyz),
        "unique_plan_coordinate_count": len(plan),
        "paired_supply_return_share_plan_xy_by_design": True,
        "loop_station_span_mm": span,
        "first_station_y_building_mm": first_y,
        "last_station_y_building_mm": last_y,
        "service_length_margin_each_end_mm": (y1 - y0 - span) / 2,
        "illustrative_vertical_datum": {
            "status": "PRODUCT_CLASS_COMPOSITE_NOT_SELECTED_PRODUCT_INSTALLATION_DATUM",
            "supply_header_z_mm_above_insulation": TOP_HEADER_HEIGHT_MM,
            "return_header_z_mm_above_insulation": RETURN_HEADER_HEIGHT_MM,
            "header_pitch_mm": HEADER_PITCH_MM,
            "supply_height_source": "REHAU_INSTALLATION_GUIDE_EXAMPLE_REFERENCED_IN_D082",
            "header_pitch_source": "UPONOR_OFFICIAL_PRODUCT_CLASS_PAGE",
            "mixed_source_geometry_not_for_FABRICATION": True,
        },
        "owner_pipe_outer_diameter_mm": 16,
        "owner_minimum_bend_radius_mm": OWNER_BEND_RADIUS_MM,
        "available_plan_depth_from_wall_plane_to_service_west_face_mm": west_face_depth,
        "available_depth_exceeds_owner_bend_radius": west_face_depth >= OWNER_BEND_RADIUS_MM,
        "c01_axis_to_service_zone_clearance_mm": body["manifold_outlet_corridor_validation"]["minimum_axis_to_service_zone_clearance_mm"],
        "candidate_ports": port_records,
        "assigned_port_count": 0,
        "route_assignment_published": False,
        "fanout_pipe_geometry_published": False,
        "complete_attic_route_count": 0,
        "physical_product_selected": False,
        "cabinet_and_fixings_selected": False,
        "hydraulic_acceptance": "NOT_EVALUATED_D083_D084_SCREENING_ONLY",
        "result": "PASS_PARAMETRIC_24_PORT_3D_LATTICE_FIT_REWORK_PRODUCT_ASSIGNMENT_FANOUT_AND_HYDRAULICS",
    }
    model["port_lattice_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_port_lattice.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    canvas = Image.new("RGB", (1700, 1150), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 205), fill="#071A21")
    draw.text((34, 17), "D088 · ПАРАМЕТРИЧЕСКАЯ 3D-РЕШЁТКА ПОРТОВ K2", font=font(24, True), fill="white")
    draw.text((34, 62), "12 станций · 24 независимых 3D-точки · шаг контуров 50 мм · рейки 225 мм", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 104), f"Зона 300×1300 мм · станции занимают {span} мм · поля по {model['service_length_margin_each_end_mm']:.0f} мм", font=font(17), fill="#F3D58C")
    draw.text((34, 145), f"До передней грани зоны от условной плоскости рейки: {west_face_depth} мм ≥ R80", font=font(16, True), fill="white")
    draw.text((34, 179), "НЕ ВЫБРАНО ИЗДЕЛИЕ · ПОРТЫ НЕ НАЗНАЧЕНЫ · ТРУБЫ НЕ НАРИСОВАНЫ", font=font(14, True), fill="#FFB2B2")

    panel = (100, 265, 1600, 1010)
    draw.rounded_rectangle(panel, radius=18, fill="#FFFFFF", outline="#9BB3BA", width=3)
    wall_x = 850
    scale_y = 1.65
    center_y_px = (panel[1] + panel[3]) / 2
    z_base = 850
    z_scale = 0.75
    supply_z = z_base - TOP_HEADER_HEIGHT_MM * z_scale
    return_z = z_base - RETURN_HEADER_HEIGHT_MM * z_scale
    y_start_px = center_y_px - span * scale_y / 2
    y_end_px = center_y_px + span * scale_y / 2
    draw.line((wall_x, y_start_px, wall_x, y_end_px), fill="#006A43", width=18)
    draw.line((wall_x + 225, y_start_px, wall_x + 225, y_end_px), fill="#247BA0", width=18)
    for index in range(PORT_COUNT_PER_HEADER):
        yp = y_start_px + index * LOOP_PITCH_MM * scale_y
        draw.ellipse((wall_x - 14, yp - 8, wall_x + 14, yp + 8), fill="#FFD45C", outline="#6A5300", width=2)
        draw.ellipse((wall_x + 225 - 14, yp - 8, wall_x + 225 + 14, yp + 8), fill="#FF9F7A", outline="#7A2100", width=2)
        draw.text((wall_x - 70, yp - 8), f"{index + 1:02d}", font=font(11, True), fill="#143842")
    draw.text((wall_x - 85, y_start_px - 55), "ПОДАЧА", font=font(14, True), fill="#006A43")
    draw.text((wall_x + 150, y_start_px - 55), "ОБРАТКА", font=font(14, True), fill="#247BA0")
    draw.text((180, 330), "СХЕМА РАЗВЁРНУТА ДЛЯ ЧТЕНИЯ", font=font(16, True), fill="#143842")
    draw.text((180, 375), "В плане пары S/R имеют общий XY,", font=font(14), fill="#566B73")
    draw.text((180, 410), "но разнесены по высоте на 225 мм.", font=font(14), fill="#566B73")
    draw.text((180, 500), "24/24 уникальных XYZ", font=font(18, True), fill="#006A43")
    draw.text((180, 545), "0 назначенных контуров", font=font(18, True), fill="#B00020")
    draw.text((180, 590), "0 опубликованных подводок", font=font(18, True), fill="#B00020")
    draw.text((180, 680), "Следующий шаг после выбора K2:", font=font(15, True), fill="#143842")
    draw.text((180, 720), "назначить A-C07 первым,", font=font(15), fill="#566B73")
    draw.text((180, 755), "затем совместно развести 24 линии.", font=font(15), fill="#566B73")
    draw.text((120, 1060), "Показана вместимость класса изделия, а не рабочий чертёж конкретного коллектора.", font=font(15, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_k2_port_lattice_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D088 — параметрическая 3D-решётка портов K2\n\n"
        "В сервисной зоне K2 размещена неназначенная решётка из 12 парных станций. Шаг станций 50 мм, вертикальное расстояние между подающей и обратной рейками 225 мм; это параметры официального класса Uponor Vario. "
        f"Станции занимают {span} мм по длине зоны и оставляют по {model['service_length_margin_each_end_mm']:.0f} мм с каждого конца. Все 24 XYZ-координаты уникальны; в плане подача и обратка одной станции имеют общий XY и различаются по высоте. "
        f"От условной плоскости рейки до передней границы сервисной зоны остаётся {west_face_depth} мм, что больше принятого радиуса R80. "
        "Высотная схема объединяет ориентиры разных официальных продуктовых классов и потому не является чертежом изготовления. Конкретный коллектор, шкаф, крепления, назначение портов, фан-аут и гидравлика остаются REWORK.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "port_lattice_digest": model["port_lattice_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "ports": len(port_records),
        "unique_xyz": len(xyz),
        "station_span_mm": span,
        "end_margin_mm": model["service_length_margin_each_end_mm"],
        "digest": model["port_lattice_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
