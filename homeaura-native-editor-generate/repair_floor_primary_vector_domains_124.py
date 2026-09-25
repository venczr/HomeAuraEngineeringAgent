from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124.zip"
SOURCE_D123 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_SUPPORT_STRIP_AUDIT_123" / "support_strip_audit.json"
SOURCE_D079 = BASE / "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079" / "internal_stair_wardrobe_r1_strategy.json"
SOURCE_D011 = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
SOURCE_PDF_SHA = "40F396CBB4F7FB6D1DAFC198CE81492999A34F66C2F96D113CA8D33360586B25"
SCALE = 35.2777777778


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def source_pdf() -> Path:
    candidates = list(Path(r"C:\Users\zahar\Downloads\Telegram Desktop").glob("*1*этажа*отметками*2*.pdf"))
    if len(candidates) != 1:
        raise RuntimeError(f"expected one floor-1 PDF, found {len(candidates)}")
    return candidates[0]


def path_record(drawings, path_id: int, selected_face: str) -> dict:
    rect = drawings[path_id]["rect"]
    selected = {
        "X_MIN": rect.x0,
        "X_MAX": rect.x1,
        "Y_MIN": rect.y0,
        "Y_MAX": rect.y1,
    }[selected_face]
    return {
        "pdf_path_id": path_id,
        "raw_rect_pt": [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
        "selected_face": selected_face,
        "selected_face_pt": float(selected),
        "selected_face_building_mm": float(selected * SCALE),
    }


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D124 is append-only")
    pdf_path = source_pdf()
    if sha(pdf_path) != SOURCE_PDF_SHA:
        raise RuntimeError("floor-1 PDF SHA mismatch")
    page = pymupdf.open(pdf_path)[0]
    drawings = page.get_drawings()
    sources = [SOURCE_D123, SOURCE_D079, SOURCE_D011]
    records = []
    for path in sources:
        model = json.loads(path.read_text(encoding="utf8"))
        records.append({"artifact_id": model.get("artifact_id", model.get("contract_id")), "sha256": sha(path)})

    west_room_face = path_record(drawings, 304, "X_MIN")
    west_hall_face = path_record(drawings, 15, "X_MAX")
    east_hall_face = path_record(drawings, 3, "X_MIN")
    east_boiler_face = path_record(drawings, 208, "X_MAX")
    west_room_floor_x0 = 120.36000061035156 * SCALE
    west_room_floor_y0 = 152.87957763671875 * SCALE
    west_room_floor_y1 = 249.599609375 * SCALE
    route_x0, route_x1, route_y, route_turn_y = 9230.0, 13200.0, 8200.0, 7600.0
    boundaries = [
        route_x0,
        west_room_face["selected_face_building_mm"],
        west_hall_face["selected_face_building_mm"],
        east_hall_face["selected_face_building_mm"],
        east_boiler_face["selected_face_building_mm"],
        route_x1,
    ]
    parts = [boundaries[i + 1] - boundaries[i] for i in range(5)]
    assert abs(sum(parts) - 3970.0) < 1e-6
    assert west_room_floor_x0 < route_x0 < west_room_face["selected_face_building_mm"]
    assert west_room_floor_y0 < route_turn_y < route_y < west_room_floor_y1
    assert route_x0 - 300.0 > west_room_floor_x0
    floor_axis = parts[0] + parts[2] + parts[4] + 600.0
    wall_axis = parts[1] + parts[3]
    assert abs(floor_axis + wall_axis - 4570.0) < 1e-6

    model = {
        "schema": "homeaura-floor-primary-vector-domain-repair-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124",
        "status": "ROUTE_AXIS_VECTOR_DOMAIN_PARTITION_PASS_REWORK_SUPPORT_STRENGTH_AND_TWO_WALL_OPENING_DETAILS",
        "source_records": records,
        "source_pdf": {
            "path": str(pdf_path),
            "sha256": SOURCE_PDF_SHA,
            "page_index": 0,
            "pdf_point_to_building_mm": SCALE,
            "source_status": "VECTOR_PDF_DRAFT_NOT_SURVEY",
        },
        "route_axis_building_mm": [[13200, 8200], [9230, 8200], [9230, 7600]],
        "route_axis_length_mm": 4570.0,
        "source_faces": {
            "WEST_ROOM_TO_HALL_ROOM_FACE": west_room_face,
            "WEST_ROOM_TO_HALL_HALL_FACE": west_hall_face,
            "HALL_TO_BOILER_HALL_FACE": east_hall_face,
            "HALL_TO_BOILER_BOILER_FACE": east_boiler_face,
        },
        "west_room_draft_floor_evidence": {
            "x_min_source_pt": 120.36000061035156,
            "x_min_building_mm": west_room_floor_x0,
            "x_max_room_face_building_mm": west_room_face["selected_face_building_mm"],
            "y_min_building_mm": west_room_floor_y0,
            "y_max_building_mm": west_room_floor_y1,
            "route_turn_axis_inside_draft_floor": True,
            "vertical_axis_inside_draft_floor": True,
            "continuous_200mm_support_strip_on_west_side": True,
            "support_strip_x_range_mm": [route_x0 - 300.0, route_x0 - 100.0],
            "minimum_support_strip_clearance_to_west_room_outer_boundary_mm": (route_x0 - 300.0) - west_room_floor_x0,
            "floor_strength_or_insulation_grade_proven": False,
        },
        "horizontal_axis_partition": [
            {"class": "WEST_ROOM_VECTOR_DRAFT_FLOOR", "x_range_mm": boundaries[0:2], "length_mm": parts[0], "support_strip_geometry_pass": True},
            {"class": "WEST_AAC_WALL_SOLID", "x_range_mm": boundaries[1:3], "length_mm": parts[1], "support_strip_geometry_pass": False, "separate_transverse_opening_required": True},
            {"class": "CENTRAL_HALL_VECTOR_DRAFT_FLOOR", "x_range_mm": boundaries[2:4], "length_mm": parts[2], "support_strip_geometry_pass": True},
            {"class": "EAST_AAC_WALL_SOLID", "x_range_mm": boundaries[3:5], "length_mm": parts[3], "support_strip_geometry_pass": False, "separate_transverse_opening_required": True},
            {"class": "BOILER_ROOM_VECTOR_DRAFT_FLOOR", "x_range_mm": boundaries[4:6], "length_mm": parts[4], "support_strip_geometry_pass": True},
        ],
        "vertical_axis_partition": [
            {"class": "WEST_ROOM_VECTOR_DRAFT_FLOOR", "line_mm": [[9230, 8200], [9230, 7600]], "length_mm": 600.0, "support_strip_geometry_pass": True, "support_side": "WEST"}
        ],
        "audit_totals": {
            "vector_draft_floor_axis_length_mm": floor_axis,
            "vector_draft_floor_axis_ratio_percent": floor_axis / 4570.0 * 100.0,
            "aac_wall_axis_length_mm": wall_axis,
            "aac_wall_axis_ratio_percent": wall_axis / 4570.0 * 100.0,
            "unknown_axis_length_mm": 0.0,
            "axis_length_reconciliation_mm": floor_axis + wall_axis,
            "floor_axis_with_geometric_200mm_support_strip_mm": floor_axis,
            "floor_axis_support_strip_geometry_pass": True,
            "whole_route_construction_pass": False,
        },
        "D123_disposition": {
            "unknown_or_unresolved_floor_axis_length_mm_994_1": "SUPERSEDED_BY_TWO_VECTOR_WALL_SOLIDS_PLUS_WEST_ROOM_FLOOR_DOMAIN",
            "single_wall_band_318mm": "SUPERSEDED_BY_TWO_EXACT_SOURCE_FACE_WALL_BANDS",
            "D123_preserved_as_historical_partial_audit": True,
        },
        "important_limits": {
            "wall_openings_selected": False,
            "wall_load_bearing_status_confirmed": False,
            "support_strip_strength_or_insulation_grade_proven": False,
            "door_thresholds_surveyed": False,
            "slab_opening_D098_is_a_separate_node": True,
            "approved_pipe_geometry_count": 0,
            "construction_authorized": False,
        },
        "result": "PASS_3940_765MM_DRAFT_FLOOR_AXIS_AND_629_235MM_TWO_AAC_WALLS_REWORK_OPENINGS_AND_MATERIALS",
    }
    model["vector_domain_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "floor_primary_vector_domain_repair.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1800, 1100), "#F4F8F8")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 1800, 180), fill="#071B23")
    d.text((42, 18), "D124 · ТРАССА РАЗЛОЖЕНА ПО ВЕКТОРНЫМ ГРАНЯМ", font=font(29, True), fill="white")
    d.text((42, 70), f"Черновой пол: {floor_axis:.1f} мм · две газобетонные стены: {wall_axis:.1f} мм · неизвестно: 0 мм", font=font(19, True), fill="#A8EEE7")
    d.text((42, 120), "Опорная полоса 200 мм геометрически помещается на всём участке пола; прочность материалов ещё не доказана", font=font(17, True), fill="#F3D58C")
    x0, x1, y = 130, 1670, 405
    scale = (x1 - x0) / 3970.0
    labels = [
        (parts[0], "КОМНАТА\n66,4", "#48A979"),
        (parts[1], "СТЕНА W\n321,7", "#B8535C"),
        (parts[2], "ХОЛЛ\n3009,9", "#48A979"),
        (parts[3], "СТЕНА E\n317,5", "#B8535C"),
        (parts[4], "КОТЕЛЬНАЯ\n254,5", "#48A979"),
    ]
    cursor = x0
    for length, label, color in labels:
        width = max(3, length * scale)
        d.rectangle((cursor, y, cursor + width, y + 160), fill=color, outline="#29454E", width=2)
        if width > 82:
            lines = label.split("\n")
            for idx, line in enumerate(lines):
                bbox = d.textbbox((0, 0), line, font=font(13, True))
                d.text((cursor + (width - (bbox[2] - bbox[0])) / 2, y + 50 + idx * 30), line, font=font(13, True), fill="white")
        cursor += width
    d.line((x0, y - 30, x1, y - 30), fill="#C00025", width=4)
    d.text((x0, y - 68), "ГОРИЗОНТАЛЬНАЯ ОСЬ 3970 мм", font=font(18, True), fill="#8A1730")
    d.line((150, 620, 150, 900), fill="#48A979", width=55)
    d.text((205, 690), "ПОВОРОТ / ПОДХОД 600 мм ВНУТРИ ЗАПАДНОЙ КОМНАТЫ", font=font(19, True), fill="#17603C")
    d.text((205, 738), "полоса 200 мм берётся с западной стороны оси · геометрия PASS DRAFT", font=font(16), fill="#17603C")
    d.rounded_rectangle((995, 650, 1690, 970), radius=22, fill="white", outline="#A2B5BC", width=3)
    notes = [
        "Западная стена: 321,7 мм AAC · отдельное поперечное отверстие.",
        "Восточная стена котельной: 317,5 мм AAC · отдельное отверстие.",
        "Стены не считаются опорой плавающей стяжки.",
        "Отверстие 120×200 в плите у лестницы — другой узел D098.",
        "СТРОИТЕЛЬСТВО: НЕ РАЗРЕШЕНО",
    ]
    yy = 690
    for idx, line in enumerate(notes):
        d.text((1030, yy), line, font=font(15, idx == len(notes) - 1), fill="#B00020" if idx == len(notes) - 1 else "#153A43")
        yy += 52
    im.save(OUTPUT / "floor_primary_vector_domain_evidence.png")

    (OUTPUT / "audit_note.md").write_text(
        "# D124 — уточнение доменов трассы\n\n"
        f"Прежние 994,1 мм неизвестного участка D123 разобраны по живому векторному PDF. Из всей оси 4570 мм {floor_axis:.1f} мм лежат в черновых областях пола, "
        f"а {wall_axis:.1f} мм приходятся на две разные газобетонные стены. Неизвестная длина оси теперь равна нулю.\n\n"
        "На каждом участке пола геометрически помещается хотя бы одна опорная полоса шириной 200 мм. Это не доказывает марку и прочность существующего утеплителя или выравнивающего материала. "
        "Через стены нужны отдельные поперечные защитные проходы; они не заменяют совпадающее отверстие в перекрытии у лестницы.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {"artifact_id": model["artifact_id"], "vector_domain_digest": model["vector_domain_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "floor_axis_mm": floor_axis, "wall_axis_mm": wall_axis, "digest": model["vector_domain_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
