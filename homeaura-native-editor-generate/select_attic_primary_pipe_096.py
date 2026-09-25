from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_080 = BASE / "HA_TWO_FLOOR_INTERNAL_RISER_3D_080" / "internal_riser_3d.json"
SOURCE_083 = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083" / "attic_primary_hydraulic_envelope.json"
SOURCE_092 = BASE / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092" / "attic_k2_product_selection_corrected.json"
SOURCE_095 = BASE / "HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095" / "attic_k2_mounting_datum.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096.zip"

OD_MM = 32.0
WALL_MM = 3.0
ID_MM = OD_MM - 2 * WALL_MM
ROUGHNESS_MM = 0.0004
DENSITY_KG_M3 = 995.0
KINEMATIC_VISCOSITY_M2_S = 0.8e-6
SCREENING_ONE_WAY_LENGTH_M = 8.0


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def hydraulic(flow_m3_h: float):
    diameter = ID_MM / 1000
    flow_m3_s = flow_m3_h / 3600
    area = math.pi * diameter * diameter / 4
    velocity = flow_m3_s / area
    reynolds = velocity * diameter / KINEMATIC_VISCOSITY_M2_S
    friction = 0.25 / math.log10(ROUGHNESS_MM / 1000 / (3.7 * diameter) + 5.74 / reynolds**0.9) ** 2
    pressure_pa_m = friction * DENSITY_KG_M3 * velocity * velocity / (2 * diameter)
    return {
        "flow_m3_h": flow_m3_h,
        "clear_id_mm": ID_MM,
        "velocity_m_s": velocity,
        "reynolds_assumed": reynolds,
        "darcy_friction_factor_swamee_jain": friction,
        "straight_pipe_pressure_gradient_pa_m": pressure_pa_m,
        "one_way_8m_straight_pressure_drop_pa": pressure_pa_m * SCREENING_ONE_WAY_LENGTH_M,
        "supply_return_16m_straight_pressure_drop_pa": pressure_pa_m * SCREENING_ONE_WAY_LENGTH_M * 2,
    }


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D096 is append-only")
    raw_080, riser = read(SOURCE_080)
    raw_083, envelope = read(SOURCE_083)
    raw_092, product = read(SOURCE_092)
    raw_095, mounting = read(SOURCE_095)
    scenario_keys = [(40, 5), (60, 7), (80, 7), (80, 5)]
    indexed = {(item["specific_load_w_m2"], item["delta_t_k"]): item for item in envelope["hydraulic_scenarios"]}
    records = []
    for load, delta_t in scenario_keys:
        source = indexed[(load, delta_t)]
        records.append({
            "specific_load_w_m2": load,
            "delta_t_k": delta_t,
            "screening_power_kw": source["power_kw"],
            **hydraulic(source["primary_flow_m3_h"]),
        })
    base = next(item for item in records if item["specific_load_w_m2"] == 60 and item["delta_t_k"] == 7)
    worst = next(item for item in records if item["specific_load_w_m2"] == 80 and item["delta_t_k"] == 5)
    model = {
        "schema": "homeaura-attic-primary-pipe-selection-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096",
        "status": "TWO_PRIMARY_MAINS_32X3_DESIGN_BASIS_SELECTED_FOR_BASE_SCREENING_PASS_REWORK_HEAT_LOSS_FITTINGS_INSULATION_AND_PUMP",
        "source_records": [
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_080, riser), (raw_083, envelope), (raw_092, product), (raw_095, mounting))
        ],
        "architecture": "K1_BOILER_ROOM_TO_K2_ATTIC_WARDROBE_TWO_PRIMARY_MAINS",
        "selected_design_basis_primary_pipe": {
            "manufacturer": "Uponor",
            "family": "Uni Pipe PLUS white coil",
            "part_number": "1059583",
            "nominal_product_description": "32x3.0 50m",
            "outer_diameter_mm": OD_MM,
            "wall_thickness_mm": WALL_MM,
            "calculated_clear_inside_diameter_mm": ID_MM,
            "oxygen_barrier": True,
            "selection_status": "DESIGN_BASIS_NOT_PURCHASE_AUTHORITY",
            "official_product_url": "https://www.uponor.com/en-gb/s/uponor-uni-pipe-plus-white-32x3-0-50m-1059583",
            "official_product_data_url": "https://www.uponor.com/en-en/product/getproductdatapdf?code=1059583",
            "accessed_date": "2026-08-13",
        },
        "selected_primary_adapter_candidate": {
            "manufacturer": "Uponor",
            "part_number": "1070509",
            "description": "S-Press PLUS adapter male thread 32-R1 MT",
            "manifold_primary_connection": "G1",
            "thread_compatibility_requires_installer_confirmation_and_sealing_detail": True,
            "official_product_url": "https://www.uponor.com/en-en/s/uponor-s-press-plus-adapter-male-thread-32-r1-mt-1070509",
            "selection_status": "CONNECTION_CANDIDATE_NOT_PURCHASE_AUTHORITY",
        },
        "hydraulic_method": {
            "velocity_from_clear_id": True,
            "pressure_gradient_formula": "DARCY_WEISBACH_WITH_SWAMEE_JAIN_FRICTION",
            "assumed_internal_roughness_mm": ROUGHNESS_MM,
            "roughness_source": "UPONOR_UNI_PIPE_PLUS_TECHNICAL_PRODUCT_DATA",
            "assumed_density_kg_m3": DENSITY_KG_M3,
            "assumed_kinematic_viscosity_m2_s": KINEMATIC_VISCOSITY_M2_S,
            "fluid_property_assumptions_not_product_guarantees": True,
            "screening_one_way_straight_length_m": SCREENING_ONE_WAY_LENGTH_M,
            "one_way_length_basis": "ROUNDED_UP_FROM_D080_7111MM_INTERNAL_ROUTE_REFERENCE_TO_ALLOW_LOCAL_K2_LINK_SCREENING",
            "fittings_valves_and_manifold_losses_included": False,
        },
        "screening_records": records,
        "base_screening_result": {
            "power_kw": base["screening_power_kw"],
            "flow_m3_h": base["flow_m3_h"],
            "velocity_m_s": base["velocity_m_s"],
            "straight_pair_pressure_drop_kpa": base["supply_return_16m_straight_pressure_drop_pa"] / 1000,
            "velocity_below_D083_0_7m_s_screening_value": base["velocity_m_s"] < 0.7,
        },
        "worst_screening_result": {
            "power_kw": worst["screening_power_kw"],
            "flow_m3_h": worst["flow_m3_h"],
            "velocity_m_s": worst["velocity_m_s"],
            "straight_pair_pressure_drop_kpa": worst["supply_return_16m_straight_pressure_drop_pa"] / 1000,
            "velocity_below_D083_0_7m_s_screening_value": worst["velocity_m_s"] < 0.7,
        },
        "selected_manifold_max_total_flow_m3_h": 3.6,
        "all_screening_flows_below_selected_manifold_documented_max": all(item["flow_m3_h"] <= 3.6 for item in records),
        "bend_policy": {
            "owner_R80_applies_to_16mm_loop_pipe_not_automatically_to_32mm_primary": True,
            "primary_bends_must_follow_32mm_product_manual_or_use_flow_optimized_fittings": True,
            "hot_air_or_open_flame_bending_prohibited_by_manufacturer": True,
            "primary_bend_geometry_published": False,
        },
        "insulation_product_selected": False,
        "heat_loss_calculation_available": False,
        "design_delta_t_final": False,
        "pump_head_selected": False,
        "balancing_valve_selected": False,
        "complete_primary_route_geometry_count": 0,
        "procurement_authorized": False,
        "result": "PASS_32X3_BASE_SCREENING_DESIGN_BASIS_REWORK_FINAL_THERMAL_HYDRAULICS_AND_ROUTE",
    }
    model["selection_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_primary_pipe_selection.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    canvas = Image.new("RGB", (1700, 1180), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1700, 205), fill="#071A21")
    draw.text((34, 18), "D096 · ДВЕ МАГИСТРАЛИ K1–K2: 32×3 ММ", font=font(23, True), fill="white")
    draw.text((34, 63), "Uponor Uni Pipe PLUS 1059583 · расчётный внутренний Ø26 мм", font=font(16, True), fill="#A7EEE7")
    draw.text((34, 105), f"База 9,09 кВт / ΔT7: {base['flow_m3_h']:.3f} м³/ч · {base['velocity_m_s']:.3f} м/с", font=font(17), fill="#F3D58C")
    draw.text((34, 145), f"Экстремум 12,12 кВт / ΔT5: {worst['flow_m3_h']:.3f} м³/ч · {worst['velocity_m_s']:.3f} м/с", font=font(16, True), fill="white")
    draw.text((34, 179), "РАСЧЁТ ТЕПЛОПОТЕРЬ, ФИТИНГИ, ИЗОЛЯЦИЯ, НАСОС И ПОЛНАЯ ТРАССА ЕЩЁ НЕ УТВЕРЖДЕНЫ", font=font(14, True), fill="#FFB2B2")
    draw.rounded_rectangle((80, 270, 1620, 990), radius=20, fill="#FFFFFF", outline="#9BB3BA", width=3)
    draw.text((125, 315), "ГИДРАВЛИЧЕСКИЙ СКРИНИНГ", font=font(19, True), fill="#143842")
    headers = ["Нагрузка", "ΔT", "Мощность", "Расход", "Скорость Ø26", "Потери прямой пары 16 м"]
    widths = [230, 150, 235, 260, 285, 300]
    x0, y0 = 110, 385
    x = x0
    for h, w in zip(headers, widths):
        draw.rectangle((x, y0, x+w, y0+70), fill="#DCEAEC", outline="#9BB3BA")
        draw.text((x+12, y0+23), h, font=font(13, True), fill="#143842")
        x += w
    for row, item in enumerate(records, start=1):
        y = y0 + row*82
        values = [f"{item['specific_load_w_m2']} Вт/м²", f"{item['delta_t_k']} K", f"{item['screening_power_kw']:.2f} кВт", f"{item['flow_m3_h']:.3f} м³/ч", f"{item['velocity_m_s']:.3f} м/с", f"{item['supply_return_16m_straight_pressure_drop_pa']/1000:.2f} кПа"]
        x = x0
        for index, (value, w) in enumerate(zip(values, widths)):
            fill = "#FFFFFF" if row % 2 else "#EDF4F5"
            draw.rectangle((x, y, x+w, y+70), fill=fill, outline="#B7C8CD")
            colour = "#B00020" if index == 4 and item["velocity_m_s"] > 0.7 else "#143842"
            draw.text((x+12, y+23), value, font=font(13, index in (0,4)), fill=colour)
            x += w
    draw.text((125, 785), "Выбор 32×3 проходит базовый скрининг: 0,584 м/с < условных 0,7 м/с D083.", font=font(16, True), fill="#006A43")
    draw.text((125, 830), "Сценарий 80 Вт/м², ΔT5 даёт 1,09 м/с: без теплопотерь это не финальный диаметр.", font=font(16, True), fill="#B00020")
    draw.text((125, 875), "R80 владельца относится к петле Ø16. Магистраль Ø32 гнуть только по инструкции или фитингами.", font=font(15, True), fill="#143842")
    draw.text((125, 920), "Потери показаны только для прямых 8+8 м; арматура, коллекторы и местные сопротивления не включены.", font=font(15), fill="#566B73")
    draw.text((90, 1080), "Статус: проектная основа для компоновки, не закупочная ведомость и не гидравлический расчёт насоса.", font=font(16, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_primary_pipe_selection_evidence.png")
    (OUTPUT / "report.md").write_text(
        "# D096 — проектная основа двух магистралей K1–K2\n\n"
        "Для подачи и обратки между K1 и K2 принят кандидат Uponor Uni Pipe PLUS 32×3 мм (арт. 1059583), расчётный внутренний диаметр 26 мм. В базовом сценарии 9,09 кВт при ΔT=7 K расход составляет 1,117 м³/ч, скорость 0,584 м/с. При экстремальном скрининге 12,12 кВт и ΔT=5 K скорость возрастает до 1,09 м/с, поэтому окончательное подтверждение диаметра требует расчёта теплопотерь.\n\n"
        "Оценка потерь учитывает только по 8 м прямой трубы на подаче и обратке. Фитинги, клапаны, коллекторы, утепление и насос не включены. Радиус R80 задан владельцем для петлевой трубы Ø16 и автоматически не переносится на магистраль Ø32; её повороты выполняются по инструкции производителя либо пресс-фитингами.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "selection_digest": model["selection_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "id_mm": ID_MM, "base_velocity": base["velocity_m_s"], "worst_velocity": worst["velocity_m_s"], "digest": model["selection_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
