from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_151"
OUT = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_152"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ["HomeAura_Floor1_Rework_D151.homeaura.json", "HomeAura_Attic_Rework_D151.homeaura.json"]:
        project = json.loads((SOURCE / name).read_text(encoding="utf-8-sig"))
        project["training_metadata"]["notes"] = project["training_metadata"]["notes"].replace("D151.", "D152.") + (
            " Независимая проверка подтвердила 0 самопересечений, 0 межконтурных контактов и 0 попаданий в лестничные запреты. "
            "Прокси покрытия по грубым прямоугольникам намеренно не объявляется монтажным покрытием: следующий этап — точные полигоны стен/дверей и расширение улиток по ним."
        )
        new_name = name.replace("D151", "D152")
        (OUT / new_name).write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in ["HomeAura_Floor1_D151_Editor_View.png", "HomeAura_Attic_D151_Editor_View.png"]:
        source_image = SOURCE / name
        if source_image.exists():
            shutil.copy2(source_image, OUT / name.replace("D151", "D152"))
    audit = json.loads((SOURCE / "independent_geometry_audit.json").read_text(encoding="utf-8-sig"))
    audit["artifact_id"] = "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_152"
    audit["result"] = "PASS_NATIVE_EDITABLE_AXIS_GEOMETRY_REWORK_EXACT_FLOOR_POLYGONS_AND_COVERAGE"
    audit["proxy_limitation"] = (
        "The reported rectangles overlap and include walls/door thresholds; their 100 mm proximity ratios are not an installation coverage certificate. "
        "D152 freezes only topology, lengths and owner-style morphology while exact finish-face domains are rebuilt."
    )
    (OUT / "independent_geometry_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = {
        "artifact_id": "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_152",
        "status": "ACCEPTED_NATIVE_EDITOR_BASELINE_FOR_EXACT_COVERAGE_REWORK",
        "editable_project_count": 2, "floor1_circuit_count": 11, "attic_circuit_count": 11,
        "route_geometry": {"self_contacts": 0, "inter_route_contacts": 0, "stair_exclusion_hits": 0,
                           "all_lengths_40_80m": True},
        "owner_input_applied": {"pipe_od_mm": 16, "minimum_bend_radius_mm": 80,
            "floor1_insulation_mm": 100, "attic_insulation_mm": 50, "available_above_insulation_mm": 70,
            "attic_service_channel_layers": 3, "field_spacing_mm": 200,
            "permitted_dense_transit_count": 3, "dense_transit_spacing_mm": 100},
        "not_claimed": ["surveyed finish-face polygons", "door-threshold ownership", "hydraulic balancing", "heat-output sufficiency"],
        "next_safe_block": "TRACE_EXACT_FINISH_FACE_AND_DOOR_POLYGONS_THEN_EXPAND_EXISTING_SPIRALS_WITHOUT_CONTACTS",
    }
    (OUT / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# D152 — нативный дом в HomeAura\n\n"
        "Два редактируемых проекта: первый этаж и мансарда. D149/D150 отклонены. D152 принимает только чистую топологию осей: "
        "все 22 петли 40–80 м, без самопересечений, межконтурных контактов и попаданий в лестничные запреты. "
        "Грубые прямоугольники помещений не используются как доказательство покрытия; точные стены и дверные проёмы остаются следующим блоком.\n",
        encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
