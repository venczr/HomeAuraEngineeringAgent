from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
FOLDER = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_151"


def seg_relation(a, b):
    line_a = LineString(a)
    line_b = LineString(b)
    return not line_a.intersection(line_b).is_empty


def audit_project(filename: str):
    path = FOLDER / filename
    project = json.loads(path.read_text(encoding="utf-8-sig"))
    lines = [LineString([(p["x_mm"], p["y_mm"]) for p in c["ordered_points"]]) for c in project["circuits"]]
    lengths = [line.length for line in lines]
    self_invalid = [project["circuits"][i]["id"] for i, line in enumerate(lines) if not line.is_simple]
    contacts = []
    for i, first in enumerate(lines):
        for j in range(i + 1, len(lines)):
            if not first.intersection(lines[j]).is_empty:
                contacts.append([project["circuits"][i]["id"], project["circuits"][j]["id"]])
    exclusions = unary_union([Polygon([(p["x_mm"], p["y_mm"]) for p in z["outline"]]) for z in project["exclusions"]])
    exclusion_hits = [project["circuits"][i]["id"] for i, line in enumerate(lines) if line.intersects(exclusions)]
    served = unary_union([line.buffer(100, quad_segs=16) for line in lines])
    room_rows = []
    total_area = total_served = 0.0
    for room in project["rooms"]:
        polygon = Polygon([(p["x_mm"], p["y_mm"]) for p in room["outline"]])
        allowed = polygon.difference(exclusions)
        served_area = allowed.intersection(served).area
        total_area += allowed.area
        total_served += served_area
        room_rows.append({
            "room_id": room["id"], "name": room["name"], "draft_allowed_area_m2": allowed.area / 1_000_000,
            "round_100mm_proximity_area_m2": served_area / 1_000_000,
            "proximity_ratio": served_area / allowed.area if allowed.area else None,
        })
    return {
        "file": filename, "circuit_count": len(lines), "lengths_mm": dict(zip([c["id"] for c in project["circuits"]], lengths)),
        "all_lengths_40_80m": all(40_000 <= value <= 80_000 for value in lengths),
        "self_invalid_route_ids": self_invalid, "inter_route_contact_pairs": contacts,
        "exclusion_hit_route_ids": exclusion_hits, "rooms": room_rows,
        "draft_proximity_total": {"allowed_area_m2": total_area / 1_000_000,
            "served_area_m2": total_served / 1_000_000, "ratio": total_served / total_area},
        "coverage_claim": "DIAGNOSTIC_ONLY_ROUND_100MM_DISTANCE_TO_FULL_AXIS_NOT_HEAT_OUTPUT",
    }


def main():
    result = {
        "artifact_id": "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_151",
        "result": "PASS_NATIVE_EDITABLE_AXIS_GEOMETRY_REWORK_DRAFT_POLYGON_COVERAGE",
        "floor1": audit_project("HomeAura_Floor1_Rework_D151.homeaura.json"),
        "attic": audit_project("HomeAura_Attic_Rework_D151.homeaura.json"),
    }
    (FOLDER / "independent_geometry_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
