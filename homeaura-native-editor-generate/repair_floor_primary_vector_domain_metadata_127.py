import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SOURCE = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124" / "floor_primary_vector_domain_repair.json"
OUTPUT = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_METADATA_REPAIR_127"
PACKAGE = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_METADATA_REPAIR_127.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise SystemExit("append-only target already exists")
    OUTPUT.mkdir(parents=True)
    source = json.loads(SOURCE.read_text(encoding="utf8"))
    totals = source["audit_totals"]
    floor_mm = totals["vector_draft_floor_axis_length_mm"]
    wall_mm = totals["aac_wall_axis_length_mm"]
    axis_mm = totals["axis_length_reconciliation_mm"]
    assert abs(floor_mm - 3930.7657623286996) < 1e-9
    assert abs(wall_mm - 639.2342376713004) < 1e-9
    assert abs(floor_mm + wall_mm - axis_mm) < 1e-9
    record = {
        "schema": "homeaura-floor-primary-vector-domain-metadata-repair-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_METADATA_REPAIR_127",
        "status": "METADATA_REPAIR_PASS_D124_GEOMETRY_UNCHANGED",
        "source_artifact_id": source["artifact_id"],
        "source_sha256": sha(SOURCE),
        "source_vector_domain_digest": source["vector_domain_digest"],
        "geometry_changed": False,
        "source_route_axis_building_mm": source["route_axis_building_mm"],
        "authoritative_totals": {
            "vector_draft_floor_axis_length_mm": floor_mm,
            "aac_wall_axis_length_mm": wall_mm,
            "unknown_axis_length_mm": totals["unknown_axis_length_mm"],
            "axis_length_reconciliation_mm": axis_mm,
        },
        "superseded_source_result": source["result"],
        "corrected_result": "PASS_3930_766MM_DRAFT_FLOOR_AXIS_AND_639_234MM_TWO_AAC_WALLS_REWORK_OPENINGS_AND_MATERIALS",
        "source_typographical_errors": {
            "floor_axis_token_mm": {"published": 3940.765, "correct": round(floor_mm, 3)},
            "aac_wall_axis_token_mm": {"published": 629.235, "correct": round(wall_mm, 3)},
        },
        "construction_authorized": False,
    }
    record["repair_digest"] = digest(record)
    (OUTPUT / "floor_primary_vector_domain_metadata_repair.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "audit_note.md").write_text(
        "# D127 — исправление метаданных D124\n\n"
        "Геометрия D124 не менялась. Исправлена только опечатка в строковом поле `result`: "
        "фактически 3 930,766 мм оси проходит по черновым областям пола, 639,234 мм — через две газобетонные стены, неизвестная часть равна нулю.\n\n"
        "Статус строительства остаётся REWORK: размеры проходов, материалы пола и выпуск плиты не утверждены.\n",
        encoding="utf8",
    )
    files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
    manifest = {
        "artifact_id": record["artifact_id"],
        "repair_digest": record["repair_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": record["repair_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
