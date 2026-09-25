from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_065" / "attic_riser_packing.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069.zip"


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


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D069 is append-only")

    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    positions = source["pipe_positions"]
    centers = [tuple(item["center_mm"]) for item in positions]
    minimum_center = min(math.dist(a, b) for index, a in enumerate(centers) for b in centers[index + 1 :])

    model = {
        "schema": "homeaura-attic-riser-packing-scenario-0.2",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069",
        "status": "ASSUMPTION_BASED_TWENTY_SIX_CANDIDATE_PIPE_PACKING_PASS_REWORK_PHYSICAL_DESIGN",
        "source_D065_artifact_id": source["artifact_id"],
        "source_D065_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D065_disposition": "SUPERSEDED_UNQUALIFIED_CIRCUIT_PIPE_AND_CHASE_NAMING",
        "scenario_only": True,
        "assumed_body_candidate_count": 13,
        "assumed_distinct_vertical_pipe_count": 26,
        "complete_circuit_count": 0,
        "approved_vertical_pipe_count": 0,
        "selected_chase_count": 0,
        "shared_pipe_trunk": False,
        "assumptions_are_product_selection": False,
        "pipe_od_mm_assumption": source["pipe_od_mm_assumption"],
        "provisional_insulated_envelope_od_mm": source["provisional_insulated_envelope_od_mm"],
        "center_pitch_mm_assumption": source["center_pitch_mm"],
        "assumed_chase_clear_bbox_mm": source["chase_clear_internal_bbox_mm"],
        "row_counts": source["row_counts"],
        "scenario_pipe_positions": positions,
        "positions_preserved_from_D065": True,
        "minimum_center_distance_mm": minimum_center,
        "minimum_bare_pipe_clear_gap_mm": source["minimum_bare_pipe_clear_gap_mm"],
        "minimum_provisional_envelope_clear_gap_mm": source["minimum_provisional_insulated_envelope_clear_gap_mm"],
        "minimum_provisional_envelope_to_assumed_boundary_mm": source["minimum_provisional_insulated_envelope_to_chase_wall_mm"],
        "scenario_overlap_count": source["cross_section_overlap_count"],
        "scenario_containment_pass": source["cross_section_containment_pass"],
        "physical_chase_location": "NOT_SELECTED",
        "physical_chase_clear_dimensions": "NOT_MEASURED",
        "bend_radius_and_fanout": "NOT_EVALUATED",
        "vertical_riser_length_mm": None,
        "firestopping": "NOT_EVALUATED",
        "condensation_and_insulation_product": "NOT_SELECTED",
        "hydraulics": "NOT_CALCULATED",
        "commercial_manifold_banks": "NOT_SELECTED",
        "floor_penetration_location": "NOT_SELECTED",
        "physical_R1_interface_status": "NOT_EVALUATED",
        "approved_installation_detail": False,
        "result": "PASS_NUMERICAL_CAPACITY_SCENARIO_REWORK_REAL_CHASE_PRODUCT_BENDS_AND_INTERFACE",
    }
    model["packing_scenario_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_riser_packing_scenario.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT / "source_D065_packing.json").write_bytes(source_bytes)

    scale = 3
    ox, oy = 130, 260
    width, height = model["assumed_chase_clear_bbox_mm"][2:]
    image = Image.new("RGB", (1600, 1050), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 210), fill="#071A21")
    canvas.text((32, 16), "D069 · УСЛОВНЫЙ СЦЕНАРИЙ УПАКОВКИ 26 ТРУБ", font=font(25, True), fill="white")
    canvas.text((32, 60), "400×160 мм — ПРИНЯТОЕ ДЛЯ ПРОВЕРКИ СЕЧЕНИЕ, НЕ ИЗМЕРЕННАЯ ШАХТА", font=font(16, True), fill="#FFCF99")
    canvas.text((32, 99), "13 тел-кандидатов → условно 26 вертикальных труб · готовых полных контуров: 0", font=font(16), fill="#A7EEE7")
    canvas.text((32, 137), "Ø16 / envelope Ø28 / шаг 40 мм — расчётные допущения; физический R1 не подтверждён", font=font(15, True), fill="#FFB2B2")
    canvas.text((32, 174), "Место, проходка, изгибы, крепёж, огнезаделка, изделия и гидравлика: НЕ ОЦЕНЕНЫ", font=font(14), fill="#E8F0F2")
    canvas.rectangle((ox, oy, ox + width * scale, oy + height * scale), fill="#E8F0F2", outline="#23424C", width=5)
    colors = {"SUPPLY": "#D64B4B", "RETURN": "#3978C6"}
    envelope_radius = model["provisional_insulated_envelope_od_mm"] * scale / 2
    pipe_radius = model["pipe_od_mm_assumption"] * scale / 2
    for item in positions:
        x = ox + item["center_mm"][0] * scale
        y = oy + item["center_mm"][1] * scale
        canvas.ellipse((x-envelope_radius, y-envelope_radius, x+envelope_radius, y+envelope_radius), fill="#FFF2B8", outline="#8D5900", width=2)
        canvas.ellipse((x-pipe_radius, y-pipe_radius, x+pipe_radius, y+pipe_radius), fill=colors[item["leg"]], outline="white", width=2)
    canvas.text((130, 815), f"Сценарный минимум между осями: {minimum_center:.0f} мм", font=font(16, True), fill="#23424C")
    canvas.text((130, 854), f"Сценарный зазор envelope Ø28: {model['minimum_provisional_envelope_clear_gap_mm']:.0f} мм", font=font(15), fill="#23424C")
    canvas.text((130, 893), f"Сценарный зазор до условной границы: {model['minimum_provisional_envelope_to_assumed_boundary_mm']:.0f} мм", font=font(15), fill="#23424C")
    canvas.text((130, 940), "PASS только для арифметики поперечного сечения; это не монтажный узел", font=font(16, True), fill="#B00020")
    image.save(OUTPUT / "attic_riser_packing_scenario.png")

    (OUTPUT / "report.md").write_text(
        "# D069 — условный сценарий упаковки стояка\n\n"
        "В условно принятом сечении 400×160 мм арифметически помещаются 26 окружностей с расчётным envelope Ø28 мм при шаге осей 40 мм. "
        "Это сценарий для 13 тел-кандидатов, а не доказательство 13 готовых контуров или существующей шахты.\n\n"
        "Полных контуров, выбранных вертикальных труб и подтверждённых шахт в этом блоке — ноль. "
        "Нужны физическое место R1, измеренное сечение, радиусы изгибов, проходка, огнезаделка, изделие и гидравлический расчёт.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({
            "artifact_id": model["artifact_id"],
            "packing_scenario_digest": model["packing_scenario_digest"],
            "append_only": True,
            "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "scenario_pipes": 26, "complete_circuits": 0, "digest": model["packing_scenario_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
