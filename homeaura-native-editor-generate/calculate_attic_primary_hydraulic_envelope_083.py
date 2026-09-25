from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_081 = BASE / "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081" / "attic_wardrobe_manifold.json"
SOURCE_082 = BASE / "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082" / "attic_manifold_service_zone.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083.zip"

WATER_FACTOR_KW_PER_M3H_K = 1.163
PRINTED_NAMED_AREA_M2 = 151.5
SPECIFIC_LOADS_W_M2 = [40, 60, 80]
DELTA_T_K = [5, 7, 10]
SCREENING_VELOCITIES_M_S = [0.5, 0.7]
CANDIDATE_CLEAR_IDS_MM = [12, 16, 20, 25, 26, 32]
BASE_LOAD_W_M2 = 60
BASE_DELTA_T_K = 7


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


def flow_m3h(power_kw: float, delta_t_k: float) -> float:
    return power_kw / (WATER_FACTOR_KW_PER_M3H_K * delta_t_k)


def velocity(flow: float, inside_diameter_mm: float) -> float:
    area = math.pi * (inside_diameter_mm / 1000) ** 2 / 4
    return (flow / 3600) / area


def required_id(flow: float, screening_velocity: float) -> float:
    return math.sqrt(4 * (flow / 3600) / (math.pi * screening_velocity)) * 1000


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D083 is append-only")
    raw_050, bodies = read(SOURCE_050)
    raw_081, topology = read(SOURCE_081)
    raw_082, service = read(SOURCE_082)

    body_sum_mm = sum(route["body_length_mm"] for route in bodies["body_routes"])
    body_sweep_proxy_m2 = body_sum_mm / 1000 * 0.2
    scenarios = []
    for specific_load in SPECIFIC_LOADS_W_M2:
        for delta_t in DELTA_T_K:
            power_kw = PRINTED_NAMED_AREA_M2 * specific_load / 1000
            flow = flow_m3h(power_kw, delta_t)
            scenarios.append({
                "specific_load_w_m2": specific_load,
                "delta_t_k": delta_t,
                "power_kw": power_kw,
                "primary_flow_m3_h": flow,
                "primary_flow_l_min": flow * 1000 / 60,
                "required_clear_id_mm_at_screening_velocity": {
                    str(value): required_id(flow, value) for value in SCREENING_VELOCITIES_M_S
                },
                "candidate_clear_id_velocity_m_s": {
                    str(value): velocity(flow, value) for value in CANDIDATE_CLEAR_IDS_MM
                },
            })

    base = next(
        item for item in scenarios
        if item["specific_load_w_m2"] == BASE_LOAD_W_M2 and item["delta_t_k"] == BASE_DELTA_T_K
    )
    circuits = topology["attic_circuit_topology"]
    total_lower_bound = sum(item["optimistic_total_lower_bound_mm"] for item in circuits)
    loop_flow_records = []
    for circuit in circuits:
        share = circuit["optimistic_total_lower_bound_mm"] / total_lower_bound
        base_flow = base["primary_flow_l_min"] * share
        worst = max(item["primary_flow_l_min"] for item in scenarios) * share
        loop_flow_records.append({
            "circuit_id": circuit["circuit_id"],
            "length_weight": share,
            "base_screening_flow_l_min": base_flow,
            "envelope_max_screening_flow_l_min": worst,
            "within_documented_0_5_l_min_flowmeter_range_at_envelope_max": worst <= 5,
        })

    sources = [
        {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
        for raw, data in ((raw_050, bodies), (raw_081, topology), (raw_082, service))
    ]
    model = {
        "schema": "homeaura-attic-primary-hydraulic-envelope-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083",
        "status": "HYDRAULIC_SCREENING_ENVELOPE_PASS_REWORK_DESIGN_HEAT_LOSS_PIPE_PRODUCT_PRESSURE_DROP_AND_PUMP",
        "source_records": sources,
        "calculation_scope": "SCREENING_ONLY_NOT_A_DESIGN_HEAT_LOSS_OR_PIPE_SELECTION",
        "named_attic_area_source": "VISIBLE_ROOM_AREA_LABELS_SUM_FROM_OWNER_PDF",
        "named_attic_area_m2": PRINTED_NAMED_AREA_M2,
        "body_length_sum_mm": body_sum_mm,
        "body_length_times_200mm_sweep_proxy_m2": body_sweep_proxy_m2,
        "body_sweep_proxy_is_coverage_or_heat_output": False,
        "water_flow_formula": "Q_m3h=P_kW/(1.163*DELTA_T_K)",
        "water_factor_kw_per_m3h_k": WATER_FACTOR_KW_PER_M3H_K,
        "specific_load_scenarios_w_m2": SPECIFIC_LOADS_W_M2,
        "delta_t_scenarios_k": DELTA_T_K,
        "screening_velocity_values_m_s": SCREENING_VELOCITIES_M_S,
        "screening_velocity_values_are_normative_limits": False,
        "hydraulic_scenarios": scenarios,
        "base_screening_scenario": base,
        "base_screening_primary_clear_id_range_mm": [
            base["required_clear_id_mm_at_screening_velocity"]["0.7"],
            base["required_clear_id_mm_at_screening_velocity"]["0.5"],
        ],
        "loop_flow_allocation_method": "PROPORTIONAL_TO_OPTIMISTIC_COMPLETE_LENGTH_LOWER_BOUND_FOR_SCREENING_ONLY",
        "loop_flow_records": loop_flow_records,
        "all_loop_screening_flows_within_documented_uponor_0_5_l_min_flowmeter_range": all(
            item["within_documented_0_5_l_min_flowmeter_range_at_envelope_max"] for item in loop_flow_records
        ),
        "official_product_reference": {
            "url": "https://www.uponor.com/en-en/products/manifolds-vario",
            "documented_flowmeter_range_l_min": [0, 5],
            "documented_primary_connection": "G1",
            "documented_circuit_count_options": "UP_TO_12_OR_16_DEPENDING_VARIANT",
            "accessed_date": "2026-08-13",
        },
        "primary_pipe_outer_diameter_selected": False,
        "primary_pipe_inside_diameter_selected": False,
        "primary_pipe_material_selected": False,
        "pressure_drop_calculated": False,
        "pump_head_calculated": False,
        "design_heat_loss_available": False,
        "design_delta_t_selected": False,
        "product_roughness_fitting_equivalent_lengths_and_fluid_temperature": "MISSING",
        "recommended_next_selection_boundary": "AFTER_HEAT_LOSS_USE_MANUFACTURER_PIPE_ID_AND_PRESSURE_DROP_DATA_CHECK_CLEAR_ID_APPROX_24_TO_28MM_FOR_BASE_SCREENING_POINT",
        "result": "PASS_SCREENING_FLOW_AND_CLEAR_ID_ENVELOPE_REWORK_FINAL_HYDRAULIC_SELECTION",
    }
    model["hydraulic_envelope_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_primary_hydraulic_envelope.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    canvas = Image.new("RGB", (1700, 1200), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1700, 205), fill="#071A21")
    draw.text((34, 18), "D083 · ГИДРАВЛИЧЕСКИЙ ДИАПАЗОН МАГИСТРАЛЕЙ K1→K2", font=font(25, True), fill="white")
    draw.text((34, 64), "151,5 м² · сценарии 40/60/80 Вт/м² · ΔT 5/7/10 K", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 105), "База: 9,09 кВт · 1,12 м³/ч · 18,6 л/мин", font=font(17), fill="#F3D58C")
    draw.text((34, 146), "Расчётный внутренний диаметр базы: 23,8…28,1 мм при условных 0,7…0,5 м/с", font=font(16, True), fill="white")
    draw.text((34, 181), "Не является подбором трубы: теплопотери, ΔT, материал, потери давления и насос не заданы", font=font(14, True), fill="#FFB2B2")

    x0, y0 = 80, 290
    col_w, row_h = 180, 68
    headers = ["Вт/м²", "ΔT", "кВт", "м³/ч", "л/мин", "ID @0,7", "ID @0,5"]
    for index, header in enumerate(headers):
        draw.rectangle((x0 + index * col_w, y0, x0 + (index + 1) * col_w, y0 + row_h), fill="#DCEAEC", outline="#9BB3BA")
        draw.text((x0 + index * col_w + 14, y0 + 20), header, font=font(14, True), fill="#143842")
    for row, item in enumerate(scenarios, start=1):
        values = [
            f'{item["specific_load_w_m2"]}', f'{item["delta_t_k"]}', f'{item["power_kw"]:.2f}',
            f'{item["primary_flow_m3_h"]:.3f}', f'{item["primary_flow_l_min"]:.1f}',
            f'{item["required_clear_id_mm_at_screening_velocity"]["0.7"]:.1f}',
            f'{item["required_clear_id_mm_at_screening_velocity"]["0.5"]:.1f}',
        ]
        fill = "#FFF4D6" if item is base else ("#FFFFFF" if row % 2 else "#EDF4F5")
        for index, value in enumerate(values):
            draw.rectangle((x0 + index * col_w, y0 + row * row_h, x0 + (index + 1) * col_w, y0 + (row + 1) * row_h), fill=fill, outline="#B7C8CD")
            draw.text((x0 + index * col_w + 14, y0 + row * row_h + 20), value, font=font(14, row == 5), fill="#143842")

    chart_y = 980
    draw.text((80, chart_y), "Скорость в кандидатных чистых внутренних диаметрах — базовый сценарий", font=font(17, True), fill="#143842")
    max_width = 1400
    for index, clear_id in enumerate(CANDIDATE_CLEAR_IDS_MM):
        v = base["candidate_clear_id_velocity_m_s"][str(clear_id)]
        y = chart_y + 50 + index * 31
        draw.text((80, y), f"ID {clear_id:>2} мм", font=font(13, True), fill="#143842")
        width = min(max_width, v / 3.0 * max_width)
        color = "#C62828" if v > 1 else ("#E39B00" if v > 0.7 else "#008A57")
        draw.rectangle((190, y + 2, 190 + width, y + 21), fill=color)
        draw.text((205 + width, y), f"{v:.2f} м/с", font=font(13, True), fill=color)
    canvas.save(OUTPUT / "attic_primary_hydraulic_envelope.png")

    (OUTPUT / "report.md").write_text(
        "# D083 — гидравлический диапазон первичных магистралей\n\n"
        "Построен скрининговый диапазон по видимой сумме площадей мансарды 151,5 м², удельным нагрузкам 40/60/80 Вт/м² и перепадам 5/7/10 K. Это не расчёт теплопотерь.\n\n"
        "Базовая точка 60 Вт/м² и ΔT=7 K даёт 9,09 кВт, 1,117 м³/ч или 18,61 л/мин. При условных скоростях 0,7–0,5 м/с требуемый чистый внутренний диаметр составляет примерно 23,8–28,1 мм. Поэтому Ø16 нельзя принимать как общую пару K1→K2; Ø16 сохраняется для отдельных петель.\n\n"
        "Распределение базового расхода по 12 петлям пропорционально нижней оценке длины остаётся в диапазоне штатных расходомеров 0–5 л/мин даже для верхнего сценария. Финальный выбор требует теплопотерь, принятого ΔT, материала и фактического внутреннего диаметра трубы, местных сопротивлений, температуры теплоносителя, расчёта потерь давления и насоса.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "hydraulic_envelope_digest": model["hydraulic_envelope_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "base_power_kw": base["power_kw"],
        "base_flow_m3_h": base["primary_flow_m3_h"],
        "base_id_range_mm": model["base_screening_primary_clear_id_range_mm"],
        "max_loop_screening_flow_l_min": max(item["envelope_max_screening_flow_l_min"] for item in loop_flow_records),
        "digest": model["hydraulic_envelope_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
