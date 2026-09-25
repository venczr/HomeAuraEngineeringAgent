from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCES=[
    ("HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_099","internal_riser_k2_stage_gate.json"),
    ("HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100","owner_floor_build_up.json"),
    ("HA_TWO_FLOOR_PRIMARY_WALL_SERVICE_BOX_101","primary_wall_service_box.json"),
]
OUTPUT=BASE/"HA_TWO_FLOOR_FLOOR_BUILDUP_STAGE_GATE_102"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_FLOOR_BUILDUP_STAGE_GATE_102.zip"


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value:object)->str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists(): raise FileExistsError("D102 is append-only")
    records=[]; models={}
    for aid,name in SOURCES:
        path=BASE/aid/name; raw=path.read_bytes(); data=json.loads(raw.decode("utf-8"))
        records.append({"artifact_id":aid,"file":name,"sha256":hashlib.sha256(raw).hexdigest().upper()}); models[aid]=data
    buildup=models[SOURCES[1][0]]; box=models[SOURCES[2][0]]
    model={
        "schema":"homeaura-floor-build-up-stage-gate-0.1",
        "artifact_id":"HA_TWO_FLOOR_FLOOR_BUILDUP_STAGE_GATE_102",
        "status":"FLOOR_BUILDUPS_INTEGRATED_PRIMARY_ROUTE_POLICY_UPDATED_PASS_REWORK_LAYER_SPEC_AND_SITE_SCAN",
        "source_records":records,
        "accepted_owner_build_up":{
            "floor_1_installed_insulation_mm":100,
            "floor_1_remaining_to_finished_floor_mm":70,
            "floor_1_total_slab_to_finished_floor_mm":170,
            "attic_installed_insulation_mm":50,
            "attic_remaining_to_finished_floor_mm":70,
            "attic_total_slab_to_finished_floor_mm":120,
        },
        "accepted_routing_consequences":[
            "LOOP_16MM_REMAINS_IN_70MM_FLOOR_BUILD_UP_SUBJECT_TO_FINAL_LAYER_SPEC",
            "PRIMARY_32MM_MAINS_NOT_BURIED_IN_70MM_REMAINING_BUILD_UP",
            "PRIMARY_MAINS_RUN_IN_ACCESSIBLE_INTERNAL_WALL_SERVICE_BOX",
            "D098_PENETRATION_PLAN_COORDINATES_UNCHANGED",
            "K2_CABINET_PROJECT_DATUM_REBASED_TO_ATTIC_STRUCTURAL_SLAB",
        ],
        "primary_service_box_reservation":{
            "clear_section_mm":[200,120],
            "primary_axis_heights_above_finished_floor_mm":[50,150],
            "provisional_envelope_od_mm":70,
            "clear_inter_envelope_gap_mm":30,
            "minimum_clear_edge_margin_mm":15,
            "removable_cover_required":True,
            "selected_product":False,
        },
        "K2_updated_vertical_datum":{
            "attic_structural_slab_to_finished_floor_mm":120,
            "cabinet_bottom_above_finished_floor_mm":270,
            "cabinet_top_above_finished_floor_mm":1000,
            "cabinet_bottom_above_structural_slab_mm":390,
            "cabinet_top_above_structural_slab_mm":1120,
        },
        "three_metre_height_working_interpretation":{
            "owner_value_mm":3000,
            "working_reference":"FINISHED_FLOOR_TO_FINISHED_FLOOR_PENDING_SITE_MEASUREMENT",
            "implied_structural_slab_top_separation_mm":3050,
            "calculation":"3000_PLUS_FLOOR1_BUILDUP_170_MINUS_ATTIC_BUILDUP_120",
            "final_vertical_route_length_released":False,
        },
        "site_or_layer_inputs_still_required":[
            "SEPARATE_THE_70MM_INTO_PIPE_FIXING_SCREED_ADHESIVE_AND_FINISH_LAYERS",
            "CONFIRM_3000MM_HEIGHT_DATUM_BY_MEASUREMENT",
            "SELECT_SERVICE_BOX_AND_VERIFY_DOORS_STAIRS_PRESS_TOOL_ACCESS_AND_AAC_FIXINGS",
            "SCAN_AND_STRUCTURALLY_RELEASE_D098_PENETRATION",
        ],
        "floor_layer_construction_approved":False,
        "primary_service_box_construction_approved":False,
        "complete_primary_route_count":0,
        "construction_issue_count":0,
        "result":"COMPLETE_BUILDUP_INTEGRATION_AND_ROUTE_POLICY_NEEDS_FINAL_LAYER_COMPOSITION_AND_SITE_RELEASE",
    }
    model["stage_gate_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"floor_build_up_stage_gate.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUTPUT/"report.md").write_text(
        "# D102 — пироги пола включены в проект\n\n"
        "На первом этаже зафиксировано 100 мм уже уложенного утеплителя и 70 мм до чистого пола; на мансарде — 50 и 70 мм. Предварительная полная высота пирога от плиты составляет 170 и 120 мм.\n\n"
        "Петли Ø16 остаются в 70-мм верхнем слое, но состав крепления, стяжки, клея и покрытия ещё требуется определить. Магистрали Ø32 не замоноличиваются: для них зарезервирован доступный пристенный короб чистым сечением 200×120 мм с осями на высотах 50 и 150 мм от чистого пола.\n\n"
        "Отметки шкафа K2 относительно мансардной плиты: низ 390 мм, верх 1120 мм. Если прежние 3000 мм относятся к чистым полам, разность верхов несущих плит составит 3050 мм; это нужно проверить натурным замером. Плановое место проходки D098 не меняется.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({
        "artifact_id":model["artifact_id"],"stage_gate_digest":model["stage_gate_digest"],"append_only":True,
        "files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"digest":model["stage_gate_digest"]},ensure_ascii=False))


if __name__=="__main__": main()
