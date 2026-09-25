from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125.zip"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124" / "floor_primary_vector_domain_repair.json",
    BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120" / "floor_primary_levelling_concept.json",
    BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097" / "attic_primary_bend_fittings.json",
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
        raise FileExistsError("D125 is append-only")
    source_models = [json.loads(p.read_text(encoding="utf8")) for p in SOURCES]
    records = [{"artifact_id": m["artifact_id"], "sha256": sha(p)} for p, m in zip(SOURCES, source_models)]
    d124, d098, d120, d097 = source_models
    floor_parts = d124["horizontal_axis_partition"]
    wall_parts = [item for item in floor_parts if item["class"].endswith("AAC_WALL_SOLID")]
    if len(wall_parts) != 2:
        raise RuntimeError("expected two AAC wall crossings")

    model = {
        "schema": "homeaura-floor-primary-aac-crossing-concept-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125",
        "status": "TWO_TRANSVERSE_AAC_CROSSING_CONCEPT_PASS_REWORK_OPENING_SIZE_WALL_STATUS_AND_INSTALLER_DETAIL",
        "source_records": records,
        "route_architecture": "TWO_FACTORY_INSULATED_PRIMARY_32X3_MAINS_K1_TO_STAIR_RISER",
        "primary_pipe": {
            "bare_pipe_od_mm": 32,
            "comparison_factory_insulation_mm": 15,
            "comparison_insulated_od_mm": 62,
            "provisional_coordination_envelope_od_mm": 70,
            "axis_pitch_mm": 100,
            "hidden_press_fitting_count": 0,
            "continuous_factory_insulated_pipe_required": True,
        },
        "crossings": [
            {
                "crossing_id": "W01_WEST_ROOM_TO_CENTRAL_HALL",
                "wall_material": "AAC_GAS_CONCRETE",
                "wall_axis_thickness_mm": wall_parts[0]["length_mm"],
                "wall_x_range_building_mm": wall_parts[0]["x_range_mm"],
                "route_crossing_axis_y_mm": 8200,
                "orientation": "TRANSVERSE_APPROXIMATELY_PERPENDICULAR_TO_WALL",
                "opening_or_sleeve_size_selected": False,
                "wall_load_bearing_status_confirmed": False,
                "construction_authorized": False,
            },
            {
                "crossing_id": "W02_CENTRAL_HALL_TO_BOILER_ROOM",
                "wall_material": "AAC_GAS_CONCRETE",
                "wall_axis_thickness_mm": wall_parts[1]["length_mm"],
                "wall_x_range_building_mm": wall_parts[1]["x_range_mm"],
                "route_crossing_axis_y_mm": 8200,
                "orientation": "TRANSVERSE_APPROXIMATELY_PERPENDICULAR_TO_WALL",
                "opening_or_sleeve_size_selected": False,
                "wall_load_bearing_status_confirmed": False,
                "construction_authorized": False,
            },
        ],
        "common_detail_requirements": {
            "wall_crossing_allowed_by_owner": True,
            "one_protective_sleeve_or_tested_common_system_per_primary": True,
            "pipe_or_factory_jacket_may_touch_raw_AAC_edge": False,
            "pipe_may_be_bent_over_wall_edge": False,
            "thermal_movement_must_not_be_obstructed": True,
            "sleeve_internal_surface_smooth_and_edges_rounded_or_protected": True,
            "annulus_and_finish_must_be_compatible_with_pipe_and_factory_jacket": True,
            "expanding_foam_may_contact_MLC_or_factory_jacket": False,
            "fire_smoke_air_acoustic_closeout_selected": False,
            "opening_size_must_be_set_after_sleeve_system_and_annulus_requirements": True,
            "wall_opening_structural_release_required_if_wall_is_load_bearing_or_status_unknown": True,
            "wall_chase_is_not_used": True,
            "floor_levelling_layer_stops_and_restarts_at_wall_faces": True,
            "wall_solid_is_not_counted_as_screed_support_strip": True,
        },
        "official_sources": [
            {
                "publisher": "UPONOR",
                "title": "MLC Press-fit Technical Guide",
                "url": "https://www.uponor.com/getmedia/3607d4dd-f6aa-46f8-99d3-88137e19c478/mlc-plumbing-tech-guidepdf?sitename=UK",
                "pages": [10, 61, 62, 63],
                "requirements_used": [
                    "WALL_AND_CEILING_OPENINGS_MUST_ADDRESS_FIRE_SOUND_THERMAL_AND_EXPANSION_REQUIREMENTS",
                    "PIPE_MAY_NOT_BE_BENT_OVER_OPENING_EDGES",
                    "HOT_BENDING_PROHIBITED",
                    "THERMAL_MOVEMENT_MUST_NOT_BE_OBSTRUCTED",
                ],
                "accessed_date": "2026-08-13",
            },
            {
                "publisher": "UPONOR_UK",
                "title": "Multi-layer Composite Pipes FAQ",
                "url": "https://www.uponor.com/en-gb/services/services-for-installers/uk-support/mlcp-faq",
                "requirements_used": [
                    "PROTECT_MLC_THROUGH_WALL_WITH_SLEEVE_WHERE_MOVEMENT_OR_DAMAGE_IS_POSSIBLE",
                    "EXPANDING_FOAM_MUST_NOT_CONTACT_MLC_DIRECTLY",
                ],
                "accessed_date": "2026-08-13",
            },
            {
                "publisher": "H_PLUS_H",
                "title": "Designing and Building with Aircrete",
                "url": "https://www.hhcelcon.co.uk/media/1550/Designing%20%26%20Building%20with%20Aircrete%202020%20Web%20Version_2025.pdf",
                "page": 26,
                "requirements_used": [
                    "SERVICE_HOLES_AND_CHASES_REQUIRE_AIRCRETE_SPECIFIC_DETAIL",
                    "VERTICAL_CHASE_LIMIT_ONE_THIRD_WALL_THICKNESS",
                    "HORIZONTAL_CHASE_LIMIT_ONE_SIXTH_WALL_THICKNESS",
                    "BACK_TO_BACK_CHASING_REQUIRES_DESIGNER_APPROVAL",
                ],
                "design_disposition": "NO_HORIZONTAL_CHASE__TRANSVERSE_OPENINGS_ONLY",
                "accessed_date": "2026-08-13",
            },
        ],
        "separate_slab_penetration_node": {
            "artifact_id": d098["artifact_id"],
            "building_bbox_mm": d098["selected_building_plan_opening_candidate"]["building_bbox_mm"],
            "coordination_clear_size_mm": d098["selected_building_plan_opening_candidate"]["clear_size_mm"],
            "same_physical_plan_coordinates_on_both_floors": True,
            "slab_scan_and_responsible_designer_release_required": True,
            "approved_opening_count": 0,
            "not_same_as_W01_or_W02": True,
        },
        "primary_direction_change_policy": {
            "fitting_family": d097["selected_direction_change_fitting"]["family"],
            "part_number": d097["selected_direction_change_fitting"]["part_number"],
            "accessible_boxes_only": True,
            "wall_crossings_are_straight_no_fitting_inside_wall": True,
        },
        "not_selected": [
            "W01_OPENING_SIZE_AND_SLEEVE_PRODUCT",
            "W02_OPENING_SIZE_AND_SLEEVE_PRODUCT",
            "AAC_WALL_LOAD_BEARING_STATUS",
            "FIRE_SMOKE_ACOUSTIC_CLOSEOUT_SYSTEM",
            "DIRECT_CONTACT_COMPATIBILITY_WITH_FACTORY_JACKET",
            "EXACT_VERTICAL_DATUM_OF_WALL_OPENINGS",
            "D098_SLAB_SCAN_AND_OPENING_RELEASE",
        ],
        "approved_wall_opening_count": 0,
        "approved_slab_opening_count": 0,
        "approved_pipe_geometry_count": 0,
        "construction_authorized": False,
        "result": "PASS_TWO_AAC_CROSSING_METHODS_REWORK_SLEEVES_OPENING_SIZE_WALL_STATUS_AND_CLOSEOUT",
    }
    model["aac_crossing_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "floor_primary_aac_crossings.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1800, 1200), "#F4F8F8")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 1800, 180), fill="#071B23")
    d.text((42, 18), "D125 · ДВА ПРОХОДА ЧЕРЕЗ ГАЗОБЕТОН", font=font(29, True), fill="white")
    d.text((42, 72), "W01: комната ↔ холл · W02: холл ↔ котельная · только поперечные проходы, не штробы", font=font(18, True), fill="#A8EEE7")
    d.text((42, 121), "Размеры отверстий и гильз ещё не назначены: нужна марка стены, гильз и заделки", font=font(17, True), fill="#FFB4B4")
    for idx, wall in enumerate(model["crossings"]):
        x = 130 + idx * 790
        d.rounded_rectangle((x, 255, x + 650, 720), radius=22, fill="white", outline="#9EB0B7", width=3)
        d.text((x + 30, 280), wall["crossing_id"], font=font(18, True), fill="#143842")
        d.rectangle((x + 260, 360, x + 390, 610), fill="#E4C49A", outline="#8C5A28", width=3)
        d.text((x + 267, 620), f'{wall["wall_axis_thickness_mm"]:.1f} мм AAC', font=font(13, True), fill="#8C5A28")
        for cy, color, label in ((430, "#C83434", "ПОДАЧА Ø62"), (540, "#2477B3", "ОБРАТКА Ø62")):
            d.line((x + 65, cy, x + 585, cy), fill=color, width=14)
            d.rectangle((x + 240, cy - 34, x + 410, cy + 34), outline="#6F33A8", width=5)
            d.text((x + 35, cy - 38), label, font=font(13, True), fill=color)
        d.text((x + 35, 670), "Фиолетовый контур = защитная гильза / испытанная система", font=font(13), fill="#6F33A8")
    d.rounded_rectangle((130, 785, 1670, 1110), radius=22, fill="white", outline="#9EB0B7", width=3)
    requirements = [
        "Труба проходит стену прямо; изгиб через кромку запрещён.",
        "Гильза гладкая, края защищены; тепловое перемещение трубы не зажимается.",
        "Монтажная пена не соприкасается с MLC/оболочкой напрямую; заделка выбирается как система.",
        "Для несущей или пока не классифицированной стены размер отверстия выпускает ответственный проектировщик.",
        "Проход в стене не заменяет отверстие 120×200 в плите у лестницы — это отдельный совпадающий межэтажный узел.",
        "ПРОХОДЫ W01/W02: К МОНТАЖУ НЕ ВЫПУЩЕНЫ",
    ]
    yy = 825
    for idx, line in enumerate(requirements):
        d.ellipse((160, yy + 5, 174, yy + 19), fill="#B00020" if idx == len(requirements) - 1 else "#00A37A")
        d.text((190, yy), line, font=font(15, idx == len(requirements) - 1), fill="#B00020" if idx == len(requirements) - 1 else "#143842")
        yy += 45
    im.save(OUTPUT / "floor_primary_aac_crossings_evidence.png")

    (OUTPUT / "method_note.md").write_text(
        "# D125 — два стеновых прохода магистралей\n\n"
        "Маршрут пересекает две разные внутренние газобетонные стены: между западной комнатой и холлом, затем между холлом и котельной. В каждой стене принимается только короткий поперечный проход двух непрерывных предизолированных магистралей; горизонтальная штроба вдоль стены не используется.\n\n"
        "Uponor требует защищать MLC при проходе стены, не гнуть трубу через кромку и не препятствовать температурному перемещению. Гильзу, размер отверстия и заделку нельзя назначить только по наружному Ø62: нужны фактическая стена, требуемые пожарные/акустические свойства и совместимость с заводской оболочкой. Поэтому W01/W02 остаются координационными узлами, а отверстие D098 120×200 в перекрытии у лестницы остаётся отдельной процедурой сканирования и выпуска.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {"artifact_id": model["artifact_id"], "aac_crossing_digest": model["aac_crossing_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "crossing_count": 2, "digest": model["aac_crossing_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
