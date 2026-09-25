from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCES = [
    ("HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079", "internal_stair_wardrobe_r1_strategy.json"),
    ("HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082", "attic_manifold_service_zone.json"),
    ("HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083", "attic_primary_hydraulic_envelope.json"),
    ("HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085", "attic_body_geometry.json"),
    ("HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_EVIDENCE_087", "evidence_validation.json"),
    ("HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088", "attic_k2_port_lattice.json"),
    ("HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089", "attic_k2_station_assignment.json"),
]
OUTPUT = BASE / "HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_090"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_090.zip"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D090 is append-only")
    records = []
    models = {}
    for artifact_id, filename in SOURCES:
        path = BASE / artifact_id / filename
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        records.append({"artifact_id": artifact_id, "file": filename, "sha256": hashlib.sha256(raw).hexdigest().upper()})
        models[artifact_id] = data

    strategy = models["HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079"]
    service = models["HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082"]
    hydraulic = models["HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083"]
    c01 = models["HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085"]
    lattice = models["HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088"]
    assignment = models["HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089"]
    model = {
        "schema": "homeaura-internal-riser-k2-stage-gate-0.1",
        "artifact_id": "HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_090",
        "status": "INTERNAL_RISER_AND_ATTIC_K2_PARAMETRIC_STAGE_COMPLETE_REQUIRES_PRODUCT_HEAT_LOSS_AND_SITE_SCAN_FOR_PRODUCTION_ROUTING",
        "source_records": records,
        "owner_inputs_locked": {
            "vertical_floor_to_floor_height_mm": 3000,
            "wall_material": "AAC_GAS_CONCRETE",
            "loop_pipe_outer_diameter_mm": 16,
            "minimum_bend_radius_mm": 80,
            "preferred_path": "FROM_BOILER_ROOM_ALONG_FLOOR_TO_STAIRS_RISE_ALONG_FAR_INTERNAL_WALL_INTO_ATTIC_WARDROBE",
            "external_wall_transition_rejected": True,
        },
        "accepted_parametric_baseline": {
            "internal_strategy_artifact_id": strategy["artifact_id"],
            "riser_opening_bbox_building_mm": strategy["selected_penetration"]["building_bbox_mm"],
            "attic_K2_service_zone_bbox_building_mm": service["service_zone_bbox_building_mm"],
            "attic_circuit_count": 12,
            "primary_main_count": 2,
            "K2_candidate_station_count": lattice["port_station_count"],
            "K2_candidate_3d_port_count": lattice["candidate_3d_port_count"],
            "K2_station_span_mm": lattice["loop_station_span_mm"],
            "K2_service_end_margin_mm": lattice["service_length_margin_each_end_mm"],
            "C01_reworked_body_length_mm": c01["body_lengths_mm"]["A-C01"],
            "C01_axis_to_service_zone_clearance_mm": c01["manifold_outlet_corridor_validation"]["minimum_axis_to_service_zone_clearance_mm"],
            "station_assignment_candidate_count": assignment["assignment_count"],
            "station_assignment_is_physical_authority": False,
        },
        "hydraulic_screening_baseline": {
            "named_attic_area_m2": hydraulic["named_attic_area_m2"],
            "base_specific_load_w_m2": hydraulic["base_screening_scenario"]["specific_load_w_m2"],
            "base_delta_t_k": hydraulic["base_screening_scenario"]["delta_t_k"],
            "base_power_kw": hydraulic["base_screening_scenario"]["power_kw"],
            "base_primary_flow_m3_h": hydraulic["base_screening_scenario"]["primary_flow_m3_h"],
            "base_primary_clear_id_screening_range_mm": hydraulic["base_screening_primary_clear_id_range_mm"],
            "screening_only": True,
        },
        "safe_frozen_claims": [
            "INTERNAL_NOT_EXTERNAL_WALL_RISER_STRATEGY",
            "SAME_BUILDING_XY_OPENING_REGISTRATION_BETWEEN_FLOORS",
            "3000MM_VERTICAL_HEIGHT",
            "AAC_WALL_CONTEXT",
            "16MM_LOOP_PIPE_AND_R80_OWNER_LIMIT",
            "TWO_PRIMARY_MAINS_TO_ATTIC_K2",
            "TWELVE_ATTIC_CIRCUIT_TOPOLOGY",
            "300X1300MM_K2_SERVICE_ZONE_VECTOR_DRAFT_CONTAINMENT",
            "C01_REGULAR_BODY_WITH_229_8MM_K2_OUTLET_STRIP",
            "PARAMETRIC_TWELVE_STATION_PORT_LATTICE_FITS_SERVICE_ZONE",
            "ALL_OPTIMISTIC_CIRCUIT_LOWER_BOUNDS_WITHIN_40_80M",
        ],
        "not_frozen_and_not_approved": [
            "CONCRETE_K2_MANUFACTURER_ARTICLE_AND_CABINET",
            "REAL_K2_PORT_COORDINATES_AND_PORT_TO_CIRCUIT_ASSIGNMENT",
            "TWENTY_FOUR_ATTIC_FANOUT_PIPE_GEOMETRIES",
            "PRIMARY_MAIN_PIPE_MATERIAL_OD_ID_AND_INSULATION",
            "DESIGN_HEAT_LOSS_AND_SELECTED_DELTA_T",
            "PRESSURE_DROP_BALANCING_AND_PUMP_HEAD",
            "STRUCTURAL_SCAN_AND_FINAL_SLAB_HOLE_OR_SLEEVES",
            "AAC_FIXING_DETAIL_AND_LOAD_SPREADING",
            "FIRESTOP_WATERPROOFING_AND_FINISHED_FLOOR_BUILDUP",
            "COMPLETE_40_80M_ROUTE_VALIDATION",
            "FULL_COVERAGE_AND_EXTERIOR_100MM_BAND",
        ],
        "external_or_owner_action_gate": {
            "required_before_production_routing": True,
            "items": [
                "SELECT_OR_PROVIDE_EXACT_12_CIRCUIT_K2_PRODUCT_AND_CABINET_DATASHEET",
                "PROVIDE_OR_COMPUTE_ROOM_BY_ROOM_DESIGN_HEAT_LOSS_AND_DESIGN_OUTDOOR_TEMPERATURE",
                "SCAN_THE_PROPOSED_SLAB_ZONE_FOR_REINFORCEMENT_UTILITIES_AND_CONFIRM_STRUCTURAL_PENETRATION",
                "CONFIRM_FINISHED_FLOOR_BUILDUP_AND_AVAILABLE_WARDROBE_SERVICE_HEIGHT",
            ],
            "reason": "WITHOUT_THESE_INPUTS_EXACT_PORT_FANOUT_PRIMARY_MAIN_SELECTION_AND_FINAL_OPENING_CANNOT_BE_ENGINEERING_ACCEPTED",
        },
        "next_automatic_stage_after_gate": [
            "BIND_SELECTED_K2_PRODUCT_GEOMETRY_TO_D082_SERVICE_ZONE",
            "ASSIGN_A_C07_FIRST_THEN_SOLVE_ALL_24_R80_FANOUTS_JOINTLY",
            "COMPUTE_COMPLETE_12_CIRCUIT_LENGTHS_AND_ALL_PAIR_CONTACTS",
            "SIZE_PRIMARY_MAINS_AND_PUMP_FROM_DESIGN_HEAT_LOSS",
            "ISSUE_FINAL_STRUCTURAL_OPENING_AND_AAC_FIXING_DETAIL",
        ],
        "complete_route_count": 0,
        "physical_product_selected": False,
        "production_opening_authorized": False,
        "result": "COMPLETE_PARAMETRIC_STAGE_NEEDS_PRODUCT_HEAT_LOSS_AND_SITE_SCAN_FOR_PRODUCTION_STAGE",
    }
    model["stage_gate_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "internal_riser_k2_stage_gate.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "report.md").write_text(
        "# D090 — рубеж этапа внутреннего стояка и K2\n\n"
        "Зафиксирована внутренняя схема: от K1 в котельной по полу к лестнице, подъём 3 м вдоль дальней внутренней стены и выход в гардеробную мансарды. Вместо 26 длинных труб между этажами принята пара первичных магистралей к двенадцатиконтурному K2; контуры мансарды остаются локальными.\n\n"
        "Сервисная зона K2 300×1300 мм помещается в черновой векторной области. C01 перестроен в регулярную улитку 45,8 м и освобождает 229,8 мм перед зоной коллектора. Параметрическая решётка 12 станций с шагом 50 мм помещается; кандидат назначения всех 12 контуров рассчитан, но не является физической привязкой портов.\n\n"
        "Гидравлический скрининг для 151,5 м² даёт базовую точку 9,09 кВт и 1,117 м³/ч при 60 Вт/м² и ΔT=7 K, с ориентировочным чистым ID первичных магистралей 24–28 мм. Это не подбор: теплопотери, ΔT, материал/ID труб, потери давления и насос не рассчитаны.\n\n"
        "Для следующего производственного этапа нужны: конкретная модель K2 и шкафа с чертежом портов; расчёт теплопотерь по помещениям; сканирование плиты в точке проходки; пирог чистого пола и доступная монтажная высота гардеробной. До этого отверстие не сверлить и 24 подводки не считать утверждёнными.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "stage_gate_digest": model["stage_gate_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT), "package": str(PACKAGE), "safe_claim_count": len(model["safe_frozen_claims"]),
        "external_action_count": len(model["external_or_owner_action_gate"]["items"]), "digest": model["stage_gate_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
