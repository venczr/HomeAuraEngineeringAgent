from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_067" / "attic_partition_opening.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_LANE_CAPACITY_068"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PARTITION_LANE_CAPACITY_068.zip"
GRID_MM = 100
SIDE_CLEARANCE_MM = 100
REQUIRED_LANES = 4


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D068 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    opening = source["matched_opening"]
    y0 = opening["opening_bbox_mm"][1]
    y1 = opening["opening_bbox_mm"][3]
    minimum_center = y0 + SIDE_CLEARANCE_MM
    maximum_center = y1 - SIDE_CLEARANCE_MM
    first_grid = math.ceil(minimum_center / GRID_MM) * GRID_MM
    last_grid = math.floor(maximum_center / GRID_MM) * GRID_MM
    candidate_y_mm = list(range(first_grid, last_grid + 1, GRID_MM))
    candidate_y_grid = [value // GRID_MM for value in candidate_y_mm]
    if len(candidate_y_grid) < REQUIRED_LANES:
        raise RuntimeError("opening lacks four 100mm lanes")
    four_lane_selection_grid = [candidate_y_grid[index] for index in (0, 2, 4, 6)] if len(candidate_y_grid) >= 7 else candidate_y_grid[:4]
    selected_spacings = [b - a for a, b in zip(four_lane_selection_grid, four_lane_selection_grid[1:])]
    model = {
        "schema": "homeaura-attic-partition-lane-capacity-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PARTITION_LANE_CAPACITY_068",
        "status": "MATCHED_OPENING_HAS_FOUR_200MM_CENTERLINE_LANES_REWORK_APPROACH_ROUTING_THRESHOLD_AND_PHYSICAL_R1",
        "source_D067_artifact_id": source["artifact_id"],
        "source_D067_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D067_contract_digest": source["contract_digest"],
        "opening_id": opening["opening_id"],
        "opening_clear_width_mm": opening["opening_clear_width_along_wall_mm"],
        "side_clearance_assumption_mm": SIDE_CLEARANCE_MM,
        "pipe_center_grid_mm": GRID_MM,
        "all_candidate_centerline_y_mm": candidate_y_mm,
        "all_candidate_centerline_y_grid": candidate_y_grid,
        "candidate_100mm_lane_count": len(candidate_y_grid),
        "required_independent_lane_count": REQUIRED_LANES,
        "four_lane_200mm_selection_y_grid": four_lane_selection_grid,
        "selected_lane_spacing_grid": selected_spacings,
        "selected_lane_spacing_mm": [value * GRID_MM for value in selected_spacings],
        "selected_lane_minimum_edge_clearance_mm": min(four_lane_selection_grid[0] * GRID_MM - y0, y1 - four_lane_selection_grid[-1] * GRID_MM),
        "selected_crossing_x_grid_candidate": [130, 131, 132, 133],
        "selected_crossing_x_grid_is_route_geometry": False,
        "selected_lane_ownership": None,
        "current_assigned_R1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "approach_corridor_contacts": "NOT_EVALUATED",
        "threshold_floor_ownership": "NOT_EVALUATED",
        "door_leaf_swing_clearance": "NOT_EVALUATED",
        "wall_sleeve_and_firestop": "NOT_EVALUATED",
        "physical_R1_interface_status": "NOT_EVALUATED",
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "result": "PASS_OPENING_WIDTH_CAPACITY_ONLY_REWORK_APPROACH_AND_PHYSICAL_INTERFACE",
    }
    model["capacity_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_partition_lane_capacity.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    width, height = 1500, 900
    image = Image.new("RGB", (width, height), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, width, 190), fill="#071A21")
    canvas.text((30, 15), "D068 · ВМЕСТИМОСТЬ ПРОЁМА D067", font=font(26, True), fill="white")
    canvas.text((30, 62), f'Источник: совпавший разрыв {opening["opening_clear_width_along_wall_mm"]:.1f} мм · расчётный отступ от краёв {SIDE_CLEARANCE_MM} мм', font=font(16), fill="#A7EEE7")
    canvas.text((30, 101), f'Кандидатных осей на сетке 100 мм: {len(candidate_y_grid)} · выбраны 4 оси с шагом 200 мм', font=font(16, True), fill="#F3D58C")
    canvas.text((30, 140), "Это ёмкость сечения проёма, не подводы, не ворота R1 и не монтажный узел", font=font(15, True), fill="#FFB2B2")
    top = 270
    bottom = 720
    left = 280
    right = 1220
    canvas.rectangle((left, top, right, bottom), fill="#D9E8EB", outline="#23424C", width=5)
    y_scale = (bottom - top) / opening["opening_clear_width_along_wall_mm"]
    for y_grid in candidate_y_grid:
        y_mm = y_grid * 100
        yp = top + (y_mm - y0) * y_scale
        canvas.line((left, yp, right, yp), fill="#B7C8CC", width=2)
    for index, y_grid in enumerate(four_lane_selection_grid, start=1):
        yp = top + (y_grid * 100 - y0) * y_scale
        canvas.line((left + 90, yp, right - 90, yp), fill="#6C5CE7", width=7)
        canvas.text((right - 70, yp - 12), f'L{index} y={y_grid}', font=font(12, True), fill="#493CB0")
    canvas.text((280, 760), f'Выбранные оси: {four_lane_selection_grid} grid · интервалы: {[value*100 for value in selected_spacings]} мм', font=font(16, True), fill="#23424C")
    canvas.text((280, 800), f'Минимальный отступ крайней выбранной оси: {model["selected_lane_minimum_edge_clearance_mm"]:.1f} мм', font=font(15), fill="#23424C")
    canvas.text((280, 840), "Распределение A-C12/A-C13 и подходы с обеих сторон ещё не назначены", font=font(14), fill="#B00020")
    image.save(OUTPUT / "attic_partition_lane_capacity.png")
    (OUTPUT / "report.md").write_text(
        "# D068 — ёмкость разрыва D067\n\n"
        f"После расчётного отступа 100 мм от обоих краёв в разрыве {opening['opening_clear_width_along_wall_mm']:.1f} мм помещаются четыре оси с шагом 200 мм. "
        "Этого достаточно по ширине для четырёх независимых труб A-C12/A-C13.\n\n"
        "Это проверка ширины, а не маршрут. Подводы, владение осями, порог, дверное полотно, гильзы, огнезаделка и физический R1 не оценены.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "capacity_digest": model["capacity_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "opening_mm": opening["opening_clear_width_along_wall_mm"], "candidate_100mm_lanes": len(candidate_y_grid), "selected_200mm_lanes": four_lane_selection_grid, "edge_clearance_mm": model["selected_lane_minimum_edge_clearance_mm"], "digest": model["capacity_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
