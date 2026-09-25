import hashlib
import json
import shutil
from datetime import date
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_125 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json"
SOURCE_098 = BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration.json"
SOURCE_130 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130" / "floor_primary_coordination_clean_evidence.json"
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_OWNER_REPORT_131"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_OPENINGS_OWNER_REPORT_131.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise SystemExit("append-only target already exists")
    d125 = json.loads(SOURCE_125.read_text(encoding="utf8"))
    d098 = json.loads(SOURCE_098.read_text(encoding="utf8"))
    d130 = json.loads(SOURCE_130.read_text(encoding="utf8"))
    OUTPUT.mkdir(parents=True)
    openings = [
        {
            "opening_id": "W01_WEST_ROOM_TO_CENTRAL_HALL",
            "opening_type": "TRANSVERSE_AAC_WALL_OPENING",
            "planned_wall_axis_thickness_mm": d125["crossings"][0]["wall_axis_thickness_mm"],
            "owner_reported_drilled": True,
            "owner_report_date": str(date.today()),
            "as_built_clear_width_mm": None,
            "as_built_clear_height_mm": None,
            "as_built_axis_height_aff_mm": None,
            "sleeve_or_liner_installed": None,
            "edge_protection_verified": None,
            "wall_damage_or_cracking_absent": None,
            "photo_evidence_paths": [],
            "independently_verified": False,
        },
        {
            "opening_id": "W02_CENTRAL_HALL_TO_BOILER_ROOM",
            "opening_type": "TRANSVERSE_AAC_WALL_OPENING",
            "planned_wall_axis_thickness_mm": d125["crossings"][1]["wall_axis_thickness_mm"],
            "owner_reported_drilled": True,
            "owner_report_date": str(date.today()),
            "as_built_clear_width_mm": None,
            "as_built_clear_height_mm": None,
            "as_built_axis_height_aff_mm": None,
            "sleeve_or_liner_installed": None,
            "edge_protection_verified": None,
            "wall_damage_or_cracking_absent": None,
            "photo_evidence_paths": [],
            "independently_verified": False,
        },
        {
            "opening_id": "P01_INTERNAL_SLAB_AT_STAIR_TO_WARDROBE",
            "opening_type": "FLOOR_SLAB_PENETRATION",
            "planned_coordination_clear_size_mm": d098["selected_building_plan_opening_candidate"]["clear_size_mm"],
            "planned_building_bbox_mm": d098["selected_building_plan_opening_candidate"]["building_bbox_mm"],
            "owner_reported_drilled": True,
            "owner_report_date": str(date.today()),
            "as_built_clear_width_mm": None,
            "as_built_clear_length_mm": None,
            "as_built_building_bbox_mm": None,
            "same_physical_plan_coordinates_both_floor_faces_verified": None,
            "rebar_or_structural_member_damage_absent": None,
            "sleeve_edge_and_closeout_system_installed": None,
            "photo_evidence_paths": [],
            "independently_verified": False,
        },
    ]
    record = {
        "schema": "homeaura-primary-openings-owner-report-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_OPENINGS_OWNER_REPORT_131",
        "status": "OWNER_REPORT_RECEIVED_OPENINGS_DRILLED_REWORK_AS_BUILT_VERIFICATION_AND_PIPE_PULL_RELEASE",
        "source_records": [
            {"artifact_id": d125["artifact_id"], "sha256": sha(SOURCE_125)},
            {"artifact_id": d098["artifact_id"], "sha256": sha(SOURCE_098)},
            {"artifact_id": d130["artifact_id"], "sha256": sha(SOURCE_130)},
        ],
        "owner_statement_verbatim": "отверстия сделаны",
        "interpretation": "W01_W02_AND_P01_ARE_REPORTED_PHYSICALLY_DRILLED_BY_OWNER",
        "owner_report_is_not_instrumental_verification": True,
        "opening_count": len(openings),
        "openings": openings,
        "released_claims": ["OWNER_REPORTED_DRILLED_STATE_ONLY"],
        "not_released_claims": [
            "AS_BUILT_DIMENSIONS",
            "SLEEVE_OR_EDGE_PROTECTION_ACCEPTANCE",
            "STRUCTURAL_OR_REBAR_CONDITION",
            "FIRE_ACOUSTIC_MOISTURE_CLOSEOUT",
            "PIPE_PULL_AUTHORIZATION",
            "PIPE_PRESSURE_TEST_ACCEPTANCE",
            "CONSTRUCTION_CLOSEOUT",
        ],
        "approved_pipe_geometry_count": 0,
        "pipe_pull_authorized": False,
        "construction_closeout_authorized": False,
        "result": "PASS_OWNER_REPORT_CAPTURE_REWORK_FIELD_EVIDENCE_AND_RELEASE_GATE",
    }
    record["owner_report_digest"] = digest(record)
    (OUTPUT / "primary_openings_owner_report.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "report.md").write_text(
        "# D131 - отверстия выполнены со слов владельца\n\n"
        "Зафиксировано сообщение владельца: W01, W02 и P01 физически выполнены. Это снимает статус `НЕ СВЕРЛЕНО`, но не подтверждает размеры, положение, состояние арматуры, гильзы, защиту кромок или пригодность для протяжки. "
        "До инструментального осмотра и заполнения исполнительной карточки протяжка труб и закрытие проходов не выпущены.\n",
        encoding="utf8",
    )
    files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
    manifest = {"artifact_id": record["artifact_id"], "owner_report_digest": record["owner_report_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": record["owner_report_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
