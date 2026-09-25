from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from shapely.geometry import LineString, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
DOMAINS = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_PROXIMITY_064"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PLANSPACE_PROXIMITY_064.zip"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D064 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    domain_bytes = DOMAINS.read_bytes()
    domains = json.loads(domain_bytes.decode("utf-8"))
    known = shape(domains["known_floor_union_geojson"])
    buffer100 = known.buffer(100, cap_style=1, join_style=1)
    buffer200 = known.buffer(200, cap_style=1, join_style=1)
    records = []
    for fragment in source["diagnostic_planar_fragments"]:
        legs = []
        for leg, key in (("SUPPLY", "supply_transit_points_grid"), ("RETURN", "return_transit_points_grid")):
            line = LineString([(x * 100, y * 100) for x, y in fragment[key]])
            exact = line.intersection(known).length
            within100 = line.intersection(buffer100).length
            within200 = line.intersection(buffer200).length
            legs.append({
                "leg": leg,
                "length_mm": line.length,
                "inside_known_floor_union_mm": exact,
                "outside_union_within_100mm_proximity_mm": max(0.0, within100 - exact),
                "outside_union_between_100_and_200mm_proximity_mm": max(0.0, within200 - within100),
                "beyond_200mm_from_known_floor_union_mm": max(0.0, line.length - within200),
                "proximity_classification_is_wall_transit_proof": False,
            })
        records.append({"route_id": fragment["route_id"], "legs": legs})
    totals = {
        "total_length_mm": sum(leg["length_mm"] for item in records for leg in item["legs"]),
        "inside_known_floor_union_mm": sum(leg["inside_known_floor_union_mm"] for item in records for leg in item["legs"]),
        "outside_union_within_100mm_proximity_mm": sum(leg["outside_union_within_100mm_proximity_mm"] for item in records for leg in item["legs"]),
        "outside_union_between_100_and_200mm_proximity_mm": sum(leg["outside_union_between_100_and_200mm_proximity_mm"] for item in records for leg in item["legs"]),
        "beyond_200mm_from_known_floor_union_mm": sum(leg["beyond_200mm_from_known_floor_union_mm"] for item in records for leg in item["legs"]),
    }
    if abs(totals["total_length_mm"] - sum(value for key, value in totals.items() if key != "total_length_mm")) > 1e-6:
        raise RuntimeError("proximity partition mismatch")
    model = {
        "schema": "homeaura-attic-plan-space-proximity-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PLANSPACE_PROXIMITY_064",
        "status": "D058_GEOMETRY_PRESERVED_ALL_DIAGNOSTIC_TRANSITS_WITHIN_200MM_OF_KNOWN_FLOOR_REWORK_WALL_THRESHOLD_SEMANTICS",
        "source_D058_artifact_id": source["artifact_id"],
        "source_D058_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D058_geometry_digest": source["geometry_digest"],
        "source_D062_artifact_id": domains["artifact_id"],
        "source_D062_sha256": hashlib.sha256(domain_bytes).hexdigest().upper(),
        "source_D062_contract_digest": domains["contract_digest"],
        "geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "current_assigned_R1_gate_count": 0,
        "distance_measure": "LINE_INTERSECTION_WITH_ROUND_BUFFER_AROUND_KNOWN_FLOOR_UNION",
        "buffer_quad_segs": 16,
        "classification_records": records,
        "totals": totals,
        "all_diagnostic_transit_within_200mm_of_known_floor_union": totals["beyond_200mm_from_known_floor_union_mm"] < 1e-6,
        "wall_transit_classification_status": "NOT_EVALUATED_PROXIMITY_IS_NOT_WALL_SOLID_PROOF",
        "threshold_ownership_status": "NOT_EVALUATED",
        "exterior_boundary_side_status": "NOT_EVALUATED",
        "physical_R1_interface_status": "NOT_EVALUATED",
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "result": "PASS_PROXIMITY_PARTITION_REWORK_WALL_THRESHOLD_EXTERIOR_AND_PHYSICAL_INTERFACE_CLASSIFICATION",
    }
    model["proximity_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_plan_space_proximity.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "source_D058_geometry.json").write_bytes(source_bytes)
    (OUTPUT / "report.md").write_text(
        "# D064 — близость диагностических подводов к известному полу\n\n"
        f"Общая длина диагностических подводов: {totals['total_length_mm']/1000:.1f} м. Внутри известных полигонов: {totals['inside_known_floor_union_mm']/1000:.1f} м; "
        f"снаружи, но не дальше 100 мм: {totals['outside_union_within_100mm_proximity_mm']/1000:.1f} м; на расстоянии 100–200 мм: {totals['outside_union_between_100_and_200mm_proximity_mm']/1000:.1f} м; дальше 200 мм: {totals['beyond_200mm_from_known_floor_union_mm']/1000:.1f} м.\n\n"
        "Это измерение близости, а не доказательство стены, порога или разрешённого прохода. До такой классификации линии остаются диагностическими и не являются утверждёнными трубами.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "proximity_digest": model["proximity_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "totals": totals, "digest": model["proximity_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
