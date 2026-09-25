from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_051"
HISTORICAL_BODY = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052.zip"
TOLERANCE_MM = 1e-6


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D052 is append-only")
    source_bytes = (SOURCE / "attic_r1_contract.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    historical_bytes = HISTORICAL_BODY.read_bytes()
    historical = json.loads(historical_bytes.decode("utf-8"))
    model = deepcopy(source)

    # Preserve the accepted current mapping and route geometry; only repair
    # provenance and numerical-comparison metadata.
    current_mapping_bytes = json.dumps(source["planned_R1_gate_mapping"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    current_fragments_bytes = json.dumps(source["attic_plane_route_fragments"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    current_bodies_bytes = json.dumps([route["body_points_grid"] for route in source["body_routes"]], ensure_ascii=False, separators=(",", ":")).encode()
    historical_mapping = deepcopy(historical["planned_R1_gate_mapping"])
    model.update(
        schema="homeaura-attic-r1-contract-0.2",
        artifact_id="HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052",
        status="AUTHORITATIVE_R1_MAPPING_AND_TWO_FRAGMENTS_PASS_PROVENANCE_REPAIRED_REWORK_REMAINING_ROUTES",
        immediate_parent_artifact_id=source["artifact_id"],
        immediate_parent_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        preferred_body_parent_artifact_id=historical["artifact_id"],
        preferred_body_parent_sha256=hashlib.sha256(historical_bytes).hexdigest().upper(),
        source_planned_R1_gate_mapping=historical_mapping,
        source_planned_R1_gate_mapping_status="EXACT_D050_HISTORICAL_MAPPING_SUPERSEDED_FOR_A-C08_A-C09_ONLY",
        current_planned_R1_gate_mapping_status="AUTHORITATIVE",
        current_mapping_preserved_from_D051=True,
        attic_plane_route_fragments_preserved_from_D051=True,
        body_points_preserved_from_D051=True,
        boundary_clearance_numeric_contract={
            "required_minimum_mm": 100.0,
            "comparison_tolerance_mm": TOLERANCE_MM,
            "pass_formula": "MEASURED_MM + TOLERANCE_MM >= REQUIRED_MINIMUM_MM",
            "measured_minimum_mm": model["draft_boundary_clearance_validation"]["minimum_clearance_mm"],
            "comparison_pass": model["draft_boundary_clearance_validation"]["minimum_clearance_mm"] + TOLERANCE_MM >= 100.0,
            "exact_design_intent_mm": 100.0,
            "margin_status": "ZERO_DESIGN_MARGIN_VECTOR_DRAFT_NOT_SURVEYED",
        },
        result="PASS_AUTHORITATIVE_R1_CONTRACT_PROVENANCE_REPAIRED_REWORK_REMAINING_ELEVEN",
    )
    model["draft_boundary_clearance_validation"]["comparison_tolerance_mm"] = TOLERANCE_MM
    model["draft_boundary_clearance_validation"]["pass_formula"] = "MEASURED_MM + TOLERANCE_MM >= REQUIRED_MINIMUM_MM"
    model["draft_boundary_clearance_validation"]["zero_design_margin"] = True
    if json.dumps(model["planned_R1_gate_mapping"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() != current_mapping_bytes:
        raise RuntimeError("current mapping changed")
    if json.dumps(model["attic_plane_route_fragments"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() != current_fragments_bytes:
        raise RuntimeError("fragments changed")
    if json.dumps([route["body_points_grid"] for route in model["body_routes"]], ensure_ascii=False, separators=(",", ":")).encode() != current_bodies_bytes:
        raise RuntimeError("body points changed")
    historical_by_key = {(item["route_id"], item["leg"]): item["gate_point_grid"] for item in historical_mapping}
    current_by_key = {(item["route_id"], item["leg"]): item["gate_point_grid"] for item in model["planned_R1_gate_mapping"]}
    if historical_by_key[("A-C08", "SUPPLY")] != [132, 57] or historical_by_key[("A-C09", "SUPPLY")] != [132, 59]:
        raise RuntimeError("historical mapping is not D050")
    if current_by_key[("A-C09", "SUPPLY")] != [132, 57] or current_by_key[("A-C08", "SUPPLY")] != [132, 59]:
        raise RuntimeError("current mapping changed")
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "current_mapping_preserved": True,
        "fragments_preserved": True,
        "body_points_preserved": True,
        "historical_mapping_exact_D050": model["source_planned_R1_gate_mapping"] == historical["planned_R1_gate_mapping"],
        "historical_A-C08_pair_grid": [historical_by_key[("A-C08", "SUPPLY")], historical_by_key[("A-C08", "RETURN")]],
        "historical_A-C09_pair_grid": [historical_by_key[("A-C09", "SUPPLY")], historical_by_key[("A-C09", "RETURN")]],
        "current_A-C09_pair_grid": [current_by_key[("A-C09", "SUPPLY")], current_by_key[("A-C09", "RETURN")]],
        "current_A-C08_pair_grid": [current_by_key[("A-C08", "SUPPLY")], current_by_key[("A-C08", "RETURN")]],
        "clearance_comparison_tolerance_mm": TOLERANCE_MM,
        "clearance_comparison_pass": model["boundary_clearance_numeric_contract"]["comparison_pass"],
        "complete_circuit_count": 0,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_r1_contract.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    for source_name, target_name in (("attic_r1_contract_overlay.png", "attic_r1_contract_repaired_overlay.png"), ("attic_r1_contract_pipes_only.png", "attic_r1_contract_repaired_pipes_only.png")):
        image = Image.open(SOURCE / source_name).convert("RGB")
        canvas = ImageDraw.Draw(image, "RGBA")
        canvas.rectangle((0, 0, image.width, 170), fill="#071A21")
        canvas.text((28, 10), "D052 · МАНСАРДА · КОНТРАКТ R1 С ИСПРАВЛЕННОЙ ИСТОРИЕЙ", font=font(23, True), fill="white")
        canvas.text((28, 49), "Текущая разводка D051 не изменена · A-C09=57/58 · A-C08=59/60", font=font(15), fill="#A7EEE7")
        canvas.text((28, 81), "Историческая D050 восстановлена точно: A-C08=57/58 · A-C09=59/60", font=font(15, True), fill="#F3D58C")
        canvas.text((28, 113), "Отступ 100 мм: допуск сравнения 0,000001 мм · проектный запас 0 · источник не обмер", font=font(14), fill="#FFB2B2")
        canvas.text((28, 141), "ЛИНИИ/ТЕЛА НЕ ИЗМЕНЕНЫ · 2 ФРАГМЕНТА PASS · 11 ОСТАЛЬНЫХ REWORK", font=font(14, True), fill="#FFB2B2")
        image.save(OUTPUT / target_name)
    (OUTPUT / "report.md").write_text(
        "# D052 — исправление истории контракта R1\n\n"
        "Ни одна точка трубы, тело или планарный фрагмент D051 не изменены. Историческая таблица восстановлена точно из D050: A-C08 использовал 57/58, A-C09 — 59/60. "
        "Актуальная таблица остаётся принятой геометрией D051: A-C09 57/58, A-C08 59/60. Числовой тест чернового 100-мм осевого отступа теперь явно использует допуск 0,000001 мм и отмечает нулевой проектный запас. "
        "Это не обмер и не поверхностный зазор трубы. Полных коллекторных контуров по-прежнему 0.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "historical_mapping_exact_D050": validation["historical_mapping_exact_D050"],
        "current_mapping_preserved": True,
        "fragments_preserved": True,
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
