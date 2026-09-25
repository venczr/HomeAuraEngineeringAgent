from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCES = {
    "FLOOR_1_ROUTE_BASELINE": BASE / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json",
    "ATTIC_BODY_BASELINE": BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json",
    "ATTIC_VECTOR_DOMAINS": BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json",
    "RISER_PACKING_SCENARIO": BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069" / "attic_riser_packing_scenario.json",
    "SOURCED_WALL_STRIPS": BASE / "HA_TWO_FLOOR_ATTIC_WALL_STRIPS_070" / "attic_sourced_wall_strip_audit.json",
    "OPENING_EVIDENCE": BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_EVIDENCE_071" / "attic_partition_opening_evidence.json",
}
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PHYSICAL_INPUT_GATE_072"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PHYSICAL_INPUT_GATE_072.zip"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D072 is append-only")
    source_records = []
    source_models = {}
    for role, path in SOURCES.items():
        raw = path.read_bytes()
        source_models[role] = json.loads(raw.decode("utf-8"))
        source_records.append({"role": role, "artifact_id": source_models[role]["artifact_id"], "path": str(path), "sha256": hashlib.sha256(raw).hexdigest().upper()})

    required_inputs = [
        {
            "input_id": "R1_PHYSICAL_EXIT_AND_PENETRATION",
            "provider": "OWNER_SITE_STRUCTURAL",
            "required": ["permitted plan location/face", "opening width and depth", "elevation", "slab/wall construction", "permitted drilling or formed sleeve", "firestop requirement"],
            "reason": "Floor PDFs do not prove a physical riser exit, sleeve or structural penetration.",
        },
        {
            "input_id": "VERTICAL_AND_CONNECTION_DIMENSIONS",
            "provider": "SITE_MEASUREMENT",
            "required": ["finished-floor to finished-floor height", "vertical pipe length", "collector/internal stub lengths", "service access clearances"],
            "reason": "Attic planar fragments are not complete K1-to-K1 circuits and cannot be checked against 40–80 m without vertical and connection lengths.",
        },
        {
            "input_id": "PIPE_AND_BEND_SYSTEM",
            "provider": "ENGINEERING_PRODUCT_SELECTION",
            "required": ["pipe product and OD", "minimum bend radius", "insulation/envelope OD", "support pitch", "installation tolerance"],
            "reason": "D069 proves only an assumed numerical packing scenario using Ø16/Ø28/pitch40.",
        },
        {
            "input_id": "PARTITION_OPENING_AND_THRESHOLD",
            "provider": "OWNER_SITE_SURVEY",
            "required": ["whether the 901.7 mm matched face gap is a usable passage", "threshold ownership", "door leaf/swing", "permitted sleeve positions"],
            "reason": "D071 proves transverse geometric width and four unowned axes, not an installable opening.",
        },
        {
            "input_id": "COMPLETE_ATTIC_FINISH_FLOOR_AND_WALL_REGISTRY",
            "provider": "SURVEY_OR_AUTHORITATIVE_DESIGN",
            "required": ["complete finish-floor polygons", "wall solids", "door/threshold polygons", "survey tolerance"],
            "reason": "D062 is an incomplete vector-draft union; flattened PDF paths do not resolve every threshold or wall domain.",
        },
        {
            "input_id": "HYDRAULIC_AND_HEAT_DESIGN",
            "provider": "MEP_ENGINEERING",
            "required": ["room heat losses", "design supply/return temperatures", "flow per circuit", "pipe pressure loss", "manifold/pump selection and balancing"],
            "reason": "Geometry alone cannot certify thermal output, R1/K1 capacity or hydraulics.",
        },
    ]
    model = {
        "schema": "homeaura-attic-physical-input-gate-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PHYSICAL_INPUT_GATE_072",
        "status": "SAFE_LOCAL_PREPARATION_COMPLETE_BLOCKED_PHYSICAL_R1_SURVEY_STRUCTURE_PRODUCT_AND_HYDRAULICS",
        "sources": source_records,
        "verified_current_state": {
            "floor_1_complete_planar_route_count": len(source_models["FLOOR_1_ROUTE_BASELINE"]["routes"]),
            "attic_regular_body_candidate_count": len(source_models["ATTIC_BODY_BASELINE"]["body_routes"]),
            "attic_complete_circuit_count": source_models["ATTIC_BODY_BASELINE"]["complete_circuit_count"],
            "current_assigned_physical_R1_gate_count": 0,
            "approved_attic_pipe_geometry_count": 0,
            "opening_candidate_width_mm": source_models["OPENING_EVIDENCE"]["opening_clear_width_mm"],
            "unowned_crossing_axis_count": source_models["OPENING_EVIDENCE"]["candidate_axis_count"],
            "packing_scenario_pipe_count": source_models["RISER_PACKING_SCENARIO"]["assumed_distinct_vertical_pipe_count"],
            "selected_physical_chase_count": source_models["RISER_PACKING_SCENARIO"]["selected_chase_count"],
            "longitudinal_wall_rework_leg_count": source_models["SOURCED_WALL_STRIPS"]["longitudinal_rework_leg_count"],
            "attic_floor_union_complete": False,
            "hydraulics_calculated": False,
        },
        "required_external_inputs": required_inputs,
        "required_input_count": len(required_inputs),
        "safe_frozen_geometry": ["FLOOR_1_ROUTE_BASELINE", "ATTIC_BODY_BASELINE"],
        "diagnostic_not_installation_geometry": ["RISER_PACKING_SCENARIO", "SOURCED_WALL_STRIPS", "OPENING_EVIDENCE"],
        "forbidden_without_inputs": [
            "publish attic K1-to-K1 complete circuits",
            "assign physical R1 gates",
            "select or dimension a real chase from D069",
            "route A-C12/A-C13 longitudinally inside a wall",
            "claim full attic coverage or hydraulics",
        ],
        "new_pipe_geometry_count": 0,
        "new_gate_count": 0,
        "geometry_modified": False,
        "result": "BLOCKED_OWNER_SITE_STRUCTURAL_PRODUCT_AND_MEP_INPUTS_NO_FURTHER_CANONICAL_ROUTING_AUTHORIZED_BY_AVAILABLE_SOURCES",
    }
    model["gate_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_physical_input_gate.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    image = Image.new("RGB", (1800, 1500), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 210), fill="#071A21")
    canvas.text((36, 22), "D072 · ГРАНИЦА ДОСТОВЕРНОЙ РАЗВОДКИ МАНСАРДЫ", font=font(30, True), fill="white")
    canvas.text((36, 76), "Без физического R1, обмера проходки и выбранной трубной системы новые полные трассы рисовать нельзя", font=font(18, True), fill="#FFB2B2")
    canvas.text((36, 121), "Сохранено: 12 трасс 1-го этажа · 13 регулярных тел мансарды · новых труб/ворот: 0", font=font(17), fill="#A7EEE7")
    canvas.text((36, 164), "Это точная инженерная граница, а не завершённый монтажный проект", font=font(16, True), fill="#F3D58C")

    y = 250
    for index, item in enumerate(required_inputs, start=1):
        color = "#EAF3F4" if index % 2 else "#F1F6F7"
        canvas.rounded_rectangle((45, y, 1755, y + 165), radius=18, fill=color, outline="#A7BBC1", width=2)
        canvas.text((70, y + 18), f"{index}. {item['input_id']}", font=font(18, True), fill="#143842")
        canvas.text((70, y + 54), f"Источник: {item['provider']}", font=font(14, True), fill="#7B4C00")
        required = " · ".join(item["required"])
        canvas.text((70, y + 88), required, font=font(12), fill="#334D55")
        canvas.text((70, y + 123), item["reason"], font=font(12), fill="#8A1A1A")
        y += 185
    canvas.text((55, 1380), "До получения этих данных: мансардные тела остаются кандидатами, R1 не назначен, полные контуры и гидравлика не приняты.", font=font(16, True), fill="#B00020")
    image.save(OUTPUT / "attic_physical_input_gate.png")

    (OUTPUT / "report.md").write_text(
        "# D072 — точная граница дальнейшей разводки\n\n"
        "Без выдумывания источников выполнена вся безопасная подготовка: сохранены 12 планарных трасс первого этажа, 13 регулярных тел мансарды, векторные черновые области пола, условная проверка упаковки, прослеженные полосы стены и совпавший разрыв 901,7 мм.\n\n"
        "Для перехода к полным контурам мансарды нужны: физическое место и проходка R1; вертикальные размеры; выбранная труба и радиусы; подтверждение прохода/порога; полный обмер полов и стен; теплотехнический и гидравлический расчёт. "
        "До этого новые канонические трубы, ворота R1 и монтажные утверждения не публикуются.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "gate_digest": model["gate_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "required_inputs": len(required_inputs), "new_geometry": 0, "digest": model["gate_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
