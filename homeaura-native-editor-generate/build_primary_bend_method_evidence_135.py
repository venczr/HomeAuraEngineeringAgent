import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_125 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json"
SOURCE_134 = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134" / "primary_openings_acceptance_criteria.json"
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise SystemExit("append-only target already exists")
    d125 = json.loads(SOURCE_125.read_text(encoding="utf8"))
    d134 = json.loads(SOURCE_134.read_text(encoding="utf8"))
    pipe = d125["primary_pipe"]
    assert pipe["bare_pipe_od_mm"] == 32

    record = {
        "schema": "homeaura-primary-bend-method-evidence-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135",
        "status": "OFFICIAL_32X3_R80_TOOL_METHOD_EVIDENCE_PASS_REWORK_INSULATION_COMPATIBILITY_AND_FIELD_RELEASE",
        "source_records": [
            {"artifact_id": d125["artifact_id"], "sha256": sha(SOURCE_125)},
            {"artifact_id": d134["artifact_id"], "sha256": sha(SOURCE_134)},
        ],
        "official_sources": [
            {
                "publisher": "Uponor",
                "document": "MLC tap water and heating - Technical information",
                "url": "https://www.uponor.com/getmedia/8677118b-0315-4f8b-a3f4-daf9bb2d346f/mlc-ukpdf?sitename=Estonia",
                "relevant_pages": [88, 89],
                "facts_used": [
                    "32X3_UNI_PIPE_PLUS_MIN_RADIUS_HAND_160MM",
                    "32X3_UNI_PIPE_PLUS_MIN_RADIUS_INTERNAL_SPRING_96MM",
                    "32X3_UNI_PIPE_PLUS_MIN_RADIUS_BENDING_TOOL_80MM",
                    "HOT_BENDING_PROHIBITED",
                    "REPEATED_BENDING_AT_SAME_POINT_PROHIBITED",
                    "DO_NOT_BEND_PIPE_OVER_CEILING_OR_WALL_OPENING_EDGES",
                ],
            },
            {
                "publisher": "Uponor",
                "document": "Uni Pipe PLUS bending segment R80 32",
                "url": "https://www.uponor.com/fi-fi/s/uponor-uni-pipe-plus-taivutuslesti-r80-32-1120411",
                "part_number": "1120411",
                "facts_used": ["OFFICIAL_R80_SEGMENT_EXISTS_FOR_SIZE_32"],
            },
            {
                "publisher": "Uponor",
                "document": "Uni Pipe PLUS bending tool 16-32",
                "url": "https://www.uponor.com/en-en/product/getproductdatapdf?code=1071925",
                "part_number": "1071925",
                "facts_used": ["TOOL_PRODUCES_EVENLY_FORMED_BENDS_UP_TO_OD32"],
            },
        ],
        "pipe_design_basis": {
            "pipe_family": "UPONOR_UNI_PIPE_PLUS",
            "size": "32X3",
            "bare_pipe_od_mm": pipe["bare_pipe_od_mm"],
            "comparison_insulated_od_mm": pipe["comparison_insulated_od_mm"],
            "coordination_envelope_od_mm": pipe["provisional_coordination_envelope_od_mm"],
            "continuous_pipe_required": pipe["continuous_factory_insulated_pipe_required"],
            "actual_product_code_selected": False,
        },
        "official_minimum_bending_radii_mm": {
            "without_tool_by_hand": 160,
            "internal_bending_spring": 96,
            "external_bending_spring": None,
            "uponor_bending_tool": 80,
        },
        "owner_directed_radius_mm": 80,
        "owner_directed_radius_matches_official_tool_table": True,
        "r80_is_not_released_for_hand_bending": True,
        "r80_is_not_released_for_hot_bending": True,
        "selected_allowed_method_candidate": "UPONOR_BENDING_TOOL_WITH_R80_SEGMENT_FOR_SIZE_32",
        "selected_tool_part_number_candidate": "1071925",
        "selected_segment_part_number_candidate": "1120411",
        "tool_and_segment_procured_and_field_verified": False,
        "factory_insulation_can_remain_installed_during_tool_bending_verified": False,
        "insulation_removal_and_reinstatement_method_selected": False,
        "radius_definition_from_source_diagram_requires_installer_tool_instruction_confirmation": True,
        "method_constraints": [
            "NO_HOT_BENDING",
            "NO_REPEATED_BENDING_AT_SAME_POINT",
            "NO_BENDING_OVER_WALL_OR_SLAB_OPENING_EDGE",
            "REPLACE_KINKED_OR_DAMAGED_PIPE_OR_USE_ACCESSIBLE_APPROVED_REPAIR",
            "FOLLOW_TOOL_OPERATING_INSTRUCTIONS",
            "KEEP_ALL_JOINTS_OUTSIDE_HIDDEN_WALL_SLAB_AND_FLOOR_ZONES",
        ],
        "field_acceptance_inputs": [
            {"input_id": "ACTUAL_PIPE_PRODUCT_CODE", "value": None, "verified": False},
            {"input_id": "TOOL_1071925_PRESENT", "value": None, "verified": False},
            {"input_id": "R80_SEGMENT_1120411_PRESENT", "value": None, "verified": False},
            {"input_id": "FACTORY_INSULATION_BEND_METHOD", "value": None, "verified": False},
            {"input_id": "ACCESSIBLE_BEND_LOCATION_AND_TANGENT_LENGTHS", "value": None, "verified": False},
            {"input_id": "POST_BEND_PIPE_AND_INSULATION_INSPECTION", "value": None, "verified": False},
        ],
        "D134_gate_G04_can_pass": False,
        "new_route_coordinate_count": 0,
        "approved_bend_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "pipe_bending_authorized": False,
        "pipe_pull_authorized": False,
        "construction_authorized": False,
        "result": "PASS_OFFICIAL_R80_TOOL_EVIDENCE_REWORK_PRODUCT_INSULATION_TOOL_AND_AS_BUILT_CONFIRMATION",
    }
    record["bend_method_evidence_digest"] = digest(record)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "primary_bend_method_evidence.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8"
    )
    (OUTPUT / "method_note.md").write_text(
        "# D135 — официальный метод радиуса 80 мм для 32×3\n\n"
        "В официальной таблице Uponor для Uni Pipe PLUS 32×3 минимальный радиус составляет 160 мм при ручной гибке, "
        "96 мм с внутренней пружиной и 80 мм со штатным гибочным инструментом. Для размера 32 опубликован сегмент R80, "
        "артикул 1120411; сам инструмент 16–32 имеет артикул 1071925.\n\n"
        "Горячая гибка, повторная гибка в одной точке и перегиб через кромку стены/перекрытия запрещены. "
        "D135 не разрешает гибку: ещё нужно подтвердить фактический артикул трубы, наличие инструмента и способ работы с заводской изоляцией.\n",
        encoding="utf8",
    )
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "artifact_id": record["artifact_id"],
        "bend_method_evidence_digest": record["bend_method_evidence_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": record["bend_method_evidence_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
