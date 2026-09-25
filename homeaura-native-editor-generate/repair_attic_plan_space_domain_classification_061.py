from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from shapely.geometry import LineString, Point, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
DOMAIN = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_AUDIT_059" / "attic_plan_space_domain_audit.json"
VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
BODY = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_REPAIRED_061"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_REPAIRED_061.zip"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D061 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    domain_bytes = DOMAIN.read_bytes()
    domain = json.loads(domain_bytes.decode("utf-8"))
    vector_bytes = VECTOR.read_bytes()
    vector = json.loads(vector_bytes.decode("utf-8"))
    body_bytes = BODY.read_bytes()
    body = json.loads(body_bytes.decode("utf-8"))
    allowed = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    records = []
    for fragment in source["diagnostic_planar_fragments"]:
        legs = []
        for leg, key in (("SUPPLY", "supply_transit_points_grid"), ("RETURN", "return_transit_points_grid")):
            points = fragment[key]
            line = LineString([(point[0] * 100, point[1] * 100) for point in points])
            endpoint_grid = points[0] if leg == "SUPPLY" else points[-1]
            endpoint = Point(endpoint_grid[0] * 100, endpoint_grid[1] * 100)
            known = line.intersection(allowed).length
            total = line.length
            legs.append({
                "leg": leg,
                "candidate_endpoint_grid": endpoint_grid,
                "candidate_endpoint_selection_rule": "FIRST_SUPPLY_POINT" if leg == "SUPPLY" else "LAST_RETURN_POINT",
                "candidate_interface_endpoint_covered_by_D047": allowed.covers(endpoint),
                "transit_length_mm": total,
                "known_D047_length_mm": known,
                "unknown_adjacent_domain_length_mm": total - known,
                "entire_transit_covered_by_D047": allowed.covers(line),
                "outside_D047_interpretation": "UNKNOWN_ADJACENT_FLOOR_DOMAIN_NOT_PROVEN_INVALID",
            })
        total = sum(item["transit_length_mm"] for item in legs)
        known = sum(item["known_D047_length_mm"] for item in legs)
        records.append({
            "route_id": fragment["route_id"],
            "legs": legs,
            "transit_length_mm": total,
            "known_D047_transit_length_mm": known,
            "unknown_adjacent_domain_transit_length_mm": total - known,
            "known_D047_transit_ratio": known / total if total else 1.0,
            "source_containment_result": "PARTIAL_D047_ONLY_REWORK_FULL_ATTIC_FLOOR_UNION",
        })
    total = sum(item["transit_length_mm"] for item in records)
    known = sum(item["known_D047_transit_length_mm"] for item in records)
    endpoint_rows = [{
        "route_id": item["route_id"],
        "leg": leg["leg"],
        "point_grid": leg["candidate_endpoint_grid"],
        "covered_by_local_D047": leg["candidate_interface_endpoint_covered_by_D047"],
        "classification": "KNOWN_LOCAL_D047" if leg["candidate_interface_endpoint_covered_by_D047"] else "OUTSIDE_LOCAL_D047_UNKNOWN_ADJACENT_DOMAIN",
    } for item in records for leg in item["legs"]]
    if sum(item["covered_by_local_D047"] for item in endpoint_rows) != 1:
        raise RuntimeError("expected exactly one D047-covered candidate endpoint")
    covered = next(item for item in endpoint_rows if item["covered_by_local_D047"])
    if covered["route_id"] != "A-C13" or covered["leg"] != "RETURN" or covered["point_grid"] != [129, 93]:
        raise RuntimeError({"unexpected covered endpoint": covered})
    repaired = {
        "schema": "homeaura-attic-plan-space-domain-repair-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_REPAIRED_061",
        "status": "D058_GEOMETRY_PRESERVED_D059_ENDPOINT_CLASSIFICATION_REPAIRED_REWORK_FULL_ATTIC_DOMAINS_AND_R1_INTERFACE",
        "source_D058_artifact_id": source["artifact_id"],
        "source_D058_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D058_geometry_digest": source["geometry_digest"],
        "source_D059_artifact_id": domain["artifact_id"],
        "source_D059_sha256": hashlib.sha256(domain_bytes).hexdigest().upper(),
        "source_D059_disposition": "SUPERSEDED_ENDPOINT_CLASSIFICATION_BUG_RETURN_USED_FIRST_POINT",
        "source_D047_artifact_id": vector["artifact_id"],
        "source_D047_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "current_D050_body_source": {
            "artifact_id": body["artifact_id"],
            "sha256": hashlib.sha256(body_bytes).hexdigest().upper(),
        },
        "old_D009_lineage_from_inherited_D050_fields": {
            "artifact_id_field_value": source["source_body_artifact_id"],
            "sha256_field_value": source["source_body_artifact_sha256"],
            "classification": "MISPAIRED_INHERITED_LINEAGE_NOT_CURRENT_D050_SOURCE",
        },
        "fragment_geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "current_assigned_R1_gate_count": 0,
        "fragment_domain_records": records,
        "candidate_endpoint_table": endpoint_rows,
        "candidate_endpoint_count": 14,
        "covered_by_local_D047_endpoint_count": 1,
        "unknown_adjacent_domain_endpoint_count": 13,
        "total_transit_length_mm": total,
        "known_D047_transit_length_mm": known,
        "unknown_adjacent_domain_transit_length_mm": total - known,
        "full_attic_floor_union_status": "MISSING",
        "physical_R1_interface_status": "NOT_EVALUATED",
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "result": "PASS_ENDPOINT_AND_PROVENANCE_CLASSIFICATION_REPAIR_REWORK_FULL_ATTIC_POLYGONS_AND_PHYSICAL_R1_INTERFACE",
    }
    repaired["repair_digest"] = digest(repaired)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "source_D058_geometry.json").write_bytes(source_bytes)
    (OUTPUT / "attic_plan_space_domain_repair.json").write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_EVIDENCE_060" / "attic_plan_space_evidence_overlay.png", OUTPUT / "attic_plan_space_evidence_overlay.png")
    shutil.copy2(BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_EVIDENCE_060" / "attic_plan_space_evidence_pipes_only.png", OUTPUT / "attic_plan_space_evidence_pipes_only.png")
    (OUTPUT / "report.md").write_text(
        "# D061 — исправление классификации домена D059\n\n"
        "Геометрия D058 сохранена побайтно. Для SUPPLY проверяется первый endpoint, для RETURN — последний. "
        "В результате ровно одна из 14 кандидатных точек подтверждена локальным D047: A-C13 RETURN [129,93]. Остальные 13 находятся вне локального D047 и классифицированы как UNKNOWN ADJACENT FLOOR DOMAIN, а не как запрещённые точки.\n\n"
        "Текущий источник тел D050 привязан к фактическому SHA файла. Старая несовместимая пара artifact_id/SHA сохранена только как явно ошибочная унаследованная lineage. Новых труб и ворот нет.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": repaired["artifact_id"],
        "repair_digest": repaired["repair_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "covered_endpoint": covered,
        "unknown_endpoint_count": 13,
        "known_D047_transit_mm": known,
        "unknown_domain_transit_mm": total - known,
        "repair_digest": repaired["repair_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
