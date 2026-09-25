from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_SUPPORT_STRIP_AUDIT_123"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_SUPPORT_STRIP_AUDIT_123.zip"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120" / "floor_primary_levelling_concept.json",
    BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json",
    BASE / "HA_TWO_FLOOR_FLOOR1_HALL_L_POLYGON_COVERAGE_033" / "hall_l_polygon_coverage.json",
]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D123 is append-only")
    source_records = []
    for path in SOURCES:
        model = json.loads(path.read_text(encoding="utf8"))
        source_records.append({"artifact_id": model.get("artifact_id", model.get("contract_id")), "sha256": sha(path)})

    axis_total = 4570.0
    hall_x0, hall_x1 = 9618.133333333333, 12628.033333333333
    wall_x0, wall_x1 = 12634.0, 12952.0
    axis_x0, axis_x1 = 9230.0, 13200.0
    boiler_x0 = 12952.0
    hall_length = hall_x1 - hall_x0
    wall_length = wall_x1 - wall_x0
    boiler_length = axis_x1 - boiler_x0
    left_unknown = hall_x0 - axis_x0
    seam_unknown = wall_x0 - hall_x1
    vertical_unknown = 600.0
    known_floor = hall_length + boiler_length
    unknown_floor = left_unknown + seam_unknown + vertical_unknown
    assert abs(known_floor + wall_length + unknown_floor - axis_total) < 1e-6

    model = {
        "schema": "homeaura-floor-primary-support-strip-audit-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_SUPPORT_STRIP_AUDIT_123",
        "status": "PARTIAL_SUPPORT_STRIP_VECTOR_DRAFT_PASS_REWORK_WALL_THRESHOLD_AND_STAIR_APPROACH_DOMAIN",
        "source_records": source_records,
        "route_axis_building_mm": [[13200, 8200], [9230, 8200], [9230, 7600]],
        "route_axis_length_mm": axis_total,
        "pipe_route_width_mm": 200,
        "required_support_width_next_to_route_mm": 200,
        "audit_definition": {
            "route_half_width_each_side_mm": 100,
            "north_support_strip_from_axis_y_mm": [-300, -100],
            "south_support_strip_from_axis_y_mm": [100, 300],
            "at_least_one_continuous_200mm_support_strip_required_where_pipe_route_is_in_floor_domain": True,
            "wall_crossing_not_counted_as_floor_support": True,
        },
        "horizontal_axis_partition": [
            {
                "class": "UNKNOWN_WEST_APPROACH_DOMAIN",
                "x_range_mm": [axis_x0, hall_x0],
                "length_mm": left_unknown,
                "support_strip_pass": None,
            },
            {
                "class": "D033_HALL_L_VECTOR_DRAFT",
                "x_range_mm": [hall_x0, hall_x1],
                "length_mm": hall_length,
                "north_200mm_strip_inside_draft_polygon": True,
                "south_200mm_strip_inside_draft_polygon": True,
                "support_strip_pass": True,
            },
            {
                "class": "UNRESOLVED_HALL_TO_WALL_SEAM",
                "x_range_mm": [hall_x1, wall_x0],
                "length_mm": seam_unknown,
                "support_strip_pass": None,
            },
            {
                "class": "D011_HALL_SIDE_WALL_BAND",
                "x_range_mm": [wall_x0, wall_x1],
                "length_mm": wall_length,
                "support_strip_pass": False,
                "reason": "WALL_CROSSING_REQUIRES_SEPARATE_PENETRATION_OR_SLEEVE_DETAIL",
            },
            {
                "class": "D011_BOILER_ROOM_VECTOR_DRAFT",
                "x_range_mm": [boiler_x0, axis_x1],
                "length_mm": boiler_length,
                "north_200mm_strip_inside_draft_rectangle": True,
                "south_200mm_strip_inside_draft_rectangle": False,
                "support_strip_pass": True,
            },
        ],
        "vertical_axis_partition": [
            {
                "class": "UNKNOWN_WEST_STAIR_APPROACH_DOMAIN",
                "line_mm": [[9230, 8200], [9230, 7600]],
                "length_mm": vertical_unknown,
                "support_strip_pass": None,
            }
        ],
        "audit_totals": {
            "known_vector_draft_floor_axis_length_mm": known_floor,
            "known_vector_draft_floor_axis_ratio_percent": known_floor / axis_total * 100,
            "wall_band_axis_length_mm": wall_length,
            "wall_band_axis_ratio_percent": wall_length / axis_total * 100,
            "unknown_or_unresolved_floor_axis_length_mm": unknown_floor,
            "unknown_or_unresolved_floor_axis_ratio_percent": unknown_floor / axis_total * 100,
            "axis_length_reconciliation_mm": known_floor + wall_length + unknown_floor,
            "known_axis_with_at_least_one_200mm_support_strip_mm": known_floor,
            "whole_route_support_strip_pass": False,
        },
        "important_limits": {
            "D033_hall_polygon_status": "VECTOR_L_POLYGON_DRAFT_REQUIRES_THRESHOLD_REVIEW",
            "D011_boiler_room_status": "VECTOR_TRACED_DRAFT_NOT_SURVEY",
            "door_thresholds_and_wall_openings_resolved": False,
            "support_strip_strength_or_insulation_grade_proven": False,
            "planar_geometric_width_does_not_prove_compressive_strength": True,
        },
        "next_safe_inputs": [
            "TRACE_OR_MEASURE_THE_9230_TO_9618_WEST_APPROACH_FLOOR_DOMAIN",
            "TRACE_OR_MEASURE_THE_X9230_Y7600_TO_8200_STAIR_APPROACH_DOMAIN",
            "DETAIL_THE_318MM_HALL_SIDE_WALL_CROSSING_WITH_PROTECTION_OR_SLEEVE",
            "IDENTIFY_EXISTING_INSULATION_AND_LEVELLING_PRODUCT_COMPRESSIVE_GRADE",
            "VERIFY_SUPPORT_STRIP_CONTINUITY_AFTER_DOOR_THRESHOLD_ASSIGNMENT",
        ],
        "approved_pipe_geometry_count": 0,
        "construction_authorized": False,
        "result": "PASS_3257_9MM_DRAFT_SUPPORT_STRIP_REWORK_1312_1MM_WALL_OR_UNKNOWN_AXIS",
    }
    model["support_strip_audit_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "support_strip_audit.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1800, 1050), "#F4F8F8")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 1800, 180), fill="#071B23")
    d.text((42, 18), "D123 · ОПОРНЫЕ ПОЛОСЫ ВДОЛЬ ТРАССЫ", font=font(29, True), fill="white")
    d.text((42, 70), "Доказано по векторному черновику: 3257,9 мм из 4570 мм оси", font=font(20, True), fill="#A8EEE7")
    d.text((42, 122), "Остаток: 318 мм стена + 994,1 мм неизвестная/неразрешённая область", font=font(18, True), fill="#FFB4B4")

    x0, x1, y = 145, 1645, 410
    scale = (x1 - x0) / axis_total
    parts = [
        (left_unknown, "НЕИЗВЕСТНО\n388,1", "#D9A441"),
        (hall_length, "ХОЛЛ D033 · две полосы ≥200\n3009,9 · PASS DRAFT", "#48A979"),
        (seam_unknown, "", "#D9A441"),
        (wall_length, "СТЕНА\n318", "#B8535C"),
        (boiler_length, "КОТЕЛЬНАЯ\n248 · север PASS", "#48A979"),
    ]
    cursor = x0
    for length, label, color in parts:
        width = max(2, length * scale)
        d.rectangle((cursor, y, cursor + width, y + 150), fill=color, outline="#31444C", width=2)
        if width > 65:
            for idx, text_line in enumerate(label.split("\n")):
                bbox = d.textbbox((0, 0), text_line, font=font(14, True))
                d.text((cursor + (width - (bbox[2] - bbox[0])) / 2, y + 50 + idx * 30), text_line, font=font(14, True), fill="white")
        cursor += width
    d.line((x0, y - 30, x1, y - 30), fill="#C00025", width=4)
    d.text((x0, y - 68), "ГОРИЗОНТАЛЬНАЯ ОСЬ 3970 мм", font=font(18, True), fill="#8A1730")

    vx = x0 + 5
    d.line((vx, y + 170, vx, y + 365), fill="#D9A441", width=45)
    d.text((vx + 45, y + 225), "ВЕРТИКАЛЬНЫЙ ПОДХОД К ЛЕСТНИЦЕ 600 мм", font=font(18, True), fill="#805500")
    d.text((vx + 45, y + 270), "область пола и опорные полосы пока НЕ ДОКАЗАНЫ", font=font(17, True), fill="#B00020")

    d.rounded_rectangle((980, 650, 1690, 945), radius=22, fill="white", outline="#9EB0B7", width=3)
    notes = [
        "PASS относится только к геометрической ширине на черновом векторе.",
        "Прочность существующего утеплителя и заполнения не доказана.",
        "Стена не считается опорой пола: нужен отдельный узел пересечения.",
        "994,1 мм пути нельзя принимать до трассировки/замера пола у лестницы.",
        "СТРОИТЕЛЬСТВО: НЕ РАЗРЕШЕНО",
    ]
    yy = 690
    for idx, line in enumerate(notes):
        d.text((1025, yy), line, font=font(16, idx == len(notes) - 1), fill="#B00020" if idx >= 2 else "#153A43")
        yy += 49
    im.save(OUTPUT / "support_strip_audit_evidence.png")

    (OUTPUT / "audit_note.md").write_text(
        "# D123 — аудит опорной полосы\n\n"
        f"Из оси 4570 мм в известных черновых областях пола находится {known_floor:.1f} мм ({known_floor / axis_total * 100:.2f}%). "
        f"В стеновой полосе находится {wall_length:.1f} мм, ещё {unknown_floor:.1f} мм относятся к неизвестному западному/лестничному подходу и шву границ.\n\n"
        "В холле по D033 с обеих сторон 200-мм трассы помещается опорная полоса 200 мм. В котельной подтверждается только северная полоса: южная упирается в границу чернового прямоугольника. "
        "Это геометрическая проверка ширины, не проверка прочности утеплителя или заполнения.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {"artifact_id": model["artifact_id"], "support_strip_audit_digest": model["support_strip_audit_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "known_floor_axis_mm": known_floor,
                      "wall_mm": wall_length, "unknown_mm": unknown_floor, "digest": model["support_strip_audit_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
