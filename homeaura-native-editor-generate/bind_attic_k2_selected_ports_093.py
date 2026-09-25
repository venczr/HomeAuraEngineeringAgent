from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_089 = BASE / "HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089" / "attic_k2_station_assignment.json"
SOURCE_092 = BASE / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092" / "attic_k2_product_selection_corrected.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093.zip"

WALL_X_MM = 9370.0
CABINET_Y0_MM = 6625.0
CABINET_LENGTH_MM = 1050.0
MANIFOLD_LENGTH_MM = 714.0
MANIFOLD_Y0_MM = CABINET_Y0_MM + (CABINET_LENGTH_MM - MANIFOLD_LENGTH_MM) / 2
FIRST_LOOP_OFFSET_MM = 77.0
LAST_END_OFFSET_MM = 87.0
LOOP_PITCH_MM = 50.0
SUPPLY_WALL_OFFSET_MM = 30.0
RETURN_WALL_OFFSET_MM = 50.0
HEADER_PITCH_MM = 215.0
DRAWING_B1_MM = 217.0
CABINET_FRONT_X_MM = 9235.0
BEND_RADIUS_MM = 80.0


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


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
        raise FileExistsError("D093 is append-only")
    raw_089, assignment = read(SOURCE_089)
    raw_092, selection = read(SOURCE_092)
    expected_length = FIRST_LOOP_OFFSET_MM + 11 * LOOP_PITCH_MM + LAST_END_OFFSET_MM
    if expected_length != MANIFOLD_LENGTH_MM:
        raise RuntimeError({"length_reconciliation": expected_length})
    assignments = {item["candidate_station_index"]: item for item in assignment["assignments"]}
    ports = []
    for station in range(1, 13):
        y = MANIFOLD_Y0_MM + FIRST_LOOP_OFFSET_MM + (station - 1) * LOOP_PITCH_MM
        owner = assignments[station]
        ports.extend([
            {
                "physical_port_id": f"K2-1140843-P{station:02d}-S",
                "station_index": station,
                "leg": "SUPPLY",
                "route_id": owner["circuit_id"],
                "building_plan_xy_mm": [WALL_X_MM - SUPPLY_WALL_OFFSET_MM, y],
                "wall_offset_mm": SUPPLY_WALL_OFFSET_MM,
                "mounting_height_z_mm": None,
            },
            {
                "physical_port_id": f"K2-1140843-P{station:02d}-R",
                "station_index": station,
                "leg": "RETURN",
                "route_id": owner["circuit_id"],
                "building_plan_xy_mm": [WALL_X_MM - RETURN_WALL_OFFSET_MM, y],
                "wall_offset_mm": RETURN_WALL_OFFSET_MM,
                "mounting_height_z_mm": None,
            },
        ])
    coordinates = {tuple(item["building_plan_xy_mm"]) for item in ports}
    ids = {item["physical_port_id"] for item in ports}
    route_legs = {(item["route_id"], item["leg"]) for item in ports}
    if len(coordinates) != 24 or len(ids) != 24 or len(route_legs) != 24:
        raise RuntimeError({"coordinates": len(coordinates), "ids": len(ids), "legs": len(route_legs)})

    model = {
        "schema": "homeaura-attic-k2-selected-product-plan-ports-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093",
        "status": "SELECTED_K2_1140843_PLAN_PORT_COORDINATES_AND_CANDIDATE_OWNERSHIP_PASS_REWORK_MOUNTING_HEIGHT_FANOUT_AND_HYDRAULICS",
        "source_records": [
            {"artifact_id": assignment["artifact_id"], "sha256": hashlib.sha256(raw_089).hexdigest().upper()},
            {"artifact_id": selection["artifact_id"], "sha256": hashlib.sha256(raw_092).hexdigest().upper()},
        ],
        "selected_manifold_part_number": "1140843",
        "selected_cabinet_part_number": "1136219",
        "manufacturer_drawing_source": {
            "product_url": "https://www.uponor.com/en-en/s/uponor-vario-s-manifold-fm-12xg3-4-euro-g1-1140843",
            "product_data_pdf": "https://prod.uponor.com/en-en/product/getproductdatapdf?code=1140843",
            "z_drawing_url": "https://brandportal.uponor.com/transform/512cc194-504e-4131-bbe0-aae24e92a25f/1140843_ZMD?format=png",
            "accessed_date": "2026-08-13",
            "drawing_dimensions_mm": {
                "overall_length_l": MANIFOLD_LENGTH_MM,
                "first_loop_offset_l1": FIRST_LOOP_OFFSET_MM,
                "last_end_offset_l2": LAST_END_OFFSET_MM,
                "loop_pitch_b": LOOP_PITCH_MM,
                "header_pitch_specification": HEADER_PITCH_MM,
                "drawing_measurement_b1": DRAWING_B1_MM,
                "supply_wall_offset_h1": SUPPLY_WALL_OFFSET_MM,
                "return_wall_offset_h2": RETURN_WALL_OFFSET_MM,
            },
            "length_reconciliation_mm": expected_length,
        },
        "mounting_transform": {
            "cabinet_plan_bbox_building_mm": [9235.0, CABINET_Y0_MM, 9370.0, CABINET_Y0_MM + CABINET_LENGTH_MM],
            "wall_plane_x_building_mm": WALL_X_MM,
            "manifold_length_centered_in_cabinet": True,
            "manifold_start_y_building_mm": MANIFOLD_Y0_MM,
            "manifold_end_y_building_mm": MANIFOLD_Y0_MM + MANIFOLD_LENGTH_MM,
            "cabinet_end_margin_each_side_mm": (CABINET_LENGTH_MM - MANIFOLD_LENGTH_MM) / 2,
            "absolute_mounting_height_z_mm": "NOT_SELECTED_FINISHED_FLOOR_BUILDUP_AND_SERVICE_HEIGHT_REQUIRED",
        },
        "cabinet_plan_clearance_screening": {
            "cabinet_front_x_building_mm": CABINET_FRONT_X_MM,
            "supply_port_to_cabinet_front_mm": WALL_X_MM - SUPPLY_WALL_OFFSET_MM - CABINET_FRONT_X_MM,
            "return_port_to_cabinet_front_mm": WALL_X_MM - RETURN_WALL_OFFSET_MM - CABINET_FRONT_X_MM,
            "minimum_plan_clearance_mm": WALL_X_MM - RETURN_WALL_OFFSET_MM - CABINET_FRONT_X_MM,
            "design_bend_radius_mm": BEND_RADIUS_MM,
            "minimum_plan_clearance_at_least_r80": WALL_X_MM - RETURN_WALL_OFFSET_MM - CABINET_FRONT_X_MM >= BEND_RADIUS_MM,
            "minimum_plan_margin_over_r80_mm": WALL_X_MM - RETURN_WALL_OFFSET_MM - CABINET_FRONT_X_MM - BEND_RADIUS_MM,
            "scope": "PLAN_X_CLEARANCE_ONLY_NOT_A_3D_BEND_ENVELOPE",
        },
        "port_count": len(ports),
        "unique_plan_coordinate_count": len(coordinates),
        "unique_port_id_count": len(ids),
        "unique_route_leg_ownership_count": len(route_legs),
        "physical_plan_ports": ports,
        "assignment_source_status": "D089_OPTIMIZED_CANDIDATE_OWNERSHIP_BOUND_TO_SELECTED_PRODUCT_STATION_ORDER_NOT_INSTALLATION_APPROVAL",
        "plan_port_coordinates_bound_to_selected_product": True,
        "mounting_height_bound": False,
        "fanout_pipe_geometry_count": 0,
        "complete_route_count": 0,
        "procurement_authorized": False,
        "hydraulic_acceptance": "NOT_EVALUATED",
        "result": "PASS_24_SELECTED_PRODUCT_PLAN_PORTS_REWORK_HEIGHT_R80_FANOUT_COMPLETE_ROUTES_AND_HYDRAULICS",
    }
    model["port_binding_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_selected_ports.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    canvas = Image.new("RGB", (1700, 1150), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 205), fill="#071A21")
    draw.text((34, 18), "D093 · ПЛАНОВЫЕ ПОРТЫ ВЫБРАННОГО K2 1140843", font=font(23, True), fill="white")
    draw.text((34, 63), "24 уникальные XY-точки · 12 станций · 77 + 11×50 + 87 = 714 мм", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 105), "Подача 30 мм от стены · обратка 50 мм · шаг реек 215 мм (спецификация)", font=font(17), fill="#F3D58C")
    draw.text((34, 145), "Назначение D089 привязано к станциям выбранного изделия", font=font(16, True), fill="white")
    draw.text((34, 179), "АБСОЛЮТНАЯ ВЫСОТА / R80-ФАН-АУТ / ГИДРАВЛИКА ЕЩЁ НЕ УТВЕРЖДЕНЫ", font=font(14, True), fill="#FFB2B2")

    draw.rounded_rectangle((90, 270, 1610, 950), radius=18, fill="#FFFFFF", outline="#9BB3BA", width=3)
    xwall = 1320
    ystart = 360
    scale = 1.0
    draw.line((xwall, 320, xwall, 890), fill="#6C7A80", width=6)
    draw.text((xwall - 55, 285), "СТЕНА", font=font(13, True), fill="#566B73")
    draw.line((350, ystart, 350 + MANIFOLD_LENGTH_MM * scale, ystart), fill="#006A43", width=14)
    draw.line((350, ystart + 250, 350 + MANIFOLD_LENGTH_MM * scale, ystart + 250), fill="#247BA0", width=14)
    for station in range(1, 13):
        x = 350 + (FIRST_LOOP_OFFSET_MM + (station - 1) * LOOP_PITCH_MM) * scale
        draw.ellipse((x - 7, ystart - 15, x + 7, ystart + 15), fill="#FFD45C", outline="#6A5300")
        draw.ellipse((x - 7, ystart + 235, x + 7, ystart + 265), fill="#FF9F7A", outline="#7A2100")
        draw.text((x - 9, ystart + 35), f"{station:02d}", font=font(10, True), fill="#143842")
    draw.text((340, ystart - 70), "ПОДАЮЩАЯ РЕЙКА", font=font(14, True), fill="#006A43")
    draw.text((340, ystart + 290), "ОБРАТНАЯ РЕЙКА", font=font(14, True), fill="#247BA0")
    draw.text((350, 750), "ФАКТИЧЕСКАЯ РАЗМЕРНАЯ ЦЕПОЧКА", font=font(16, True), fill="#143842")
    draw.text((350, 792), "l1=77 · 11 шагов b=50 · l2=87 · общая l=714 мм", font=font(15), fill="#143842")
    draw.text((350, 834), "h1=30 · h2=50 · шаг реек 215 · размер b1=217 мм", font=font(15, True), fill="#006A43")
    draw.text((130, 990), "До фасада шкафа: подача 105 мм · обратка 85 мм · R80: плановый запас 5 мм", font=font(15, True), fill="#006A43")
    draw.text((130, 1030), "Плановые XY определены. Z появится после фиксации чистого пола и высоты шкафа.", font=font(15, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_k2_selected_ports_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D093 — плановые порты выбранного коллектора K2\n\n"
        "Размерный чертёж Uponor 1140843 позволил заменить условную геометрию D088 реальными плановыми смещениями: 77 мм до первого отвода, 50 мм между 12 отводами и 87 мм после последнего, что точно даёт общую длину 714 мм. Подающая рейка вынесена на 30 мм от стены, обратная на 50 мм. Спецификация указывает шаг реек 215 мм; отдельный размер b1 на чертеже равен 217 мм, поэтому эти значения не смешиваются.\n\n"
        "Коллектор центрирован в шкафу 1050 мм, оставляя по 168 мм с торцов. Двенадцать кандидатных назначений D089 привязаны к станциям выбранного изделия; получены 24 уникальные плановые XY-точки. Абсолютная высота Z, геометрия R80-фан-аута, полные маршруты и гидравлика пока не утверждены.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "port_binding_digest": model["port_binding_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT), "package": str(PACKAGE), "ports": len(ports), "unique_coords": len(coordinates),
        "manifold_y": [MANIFOLD_Y0_MM, MANIFOLD_Y0_MM + MANIFOLD_LENGTH_MM], "digest": model["port_binding_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
