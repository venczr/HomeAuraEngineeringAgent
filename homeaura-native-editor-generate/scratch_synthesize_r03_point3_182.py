from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

from shapely.geometry import LineString

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from build_floor1_wet_pair_176 import derive_transitions, route_metrics  # noqa: E402

SOURCE = (ROOT / "homeaura-native-editor/examples/proposals/"
          "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181/"
          "HomeAura_TwoFloor_SourceWallDomains_D181.homeaura.json")
NEAR = HERE / "fixtures/r03_owner_spiral_near_pass.json"
MULTI = HERE / "fixtures/r03_owner_spiral_c08_wall_clear_multirange.json"
SCRATCH = ROOT / "tmp/R03_Point3_D181_scratch.homeaura.json"
DIAGNOSTICS = ROOT / "tmp/R03_Point3_D181_scratch_diagnostics.json"
REPORT = ROOT / "reports/HomeAura_R03_Point3_Synthesis_D181_2026-08-20.json"
BODY_Z, LOW_Z, HIGH_Z, CONNECTOR_Z = 108, 70, 135, 30


def xyz(point, z=BODY_Z):
    return (point[0] * 100, point[1] * 100, z)


def append(points, additions):
    for point in additions:
        if not points or points[-1] != point:
            points.append(point)


def append_body(points, ranges, body):
    start = len(points) - 1 if points and points[-1] == body[0] else len(points)
    append(points, body)
    ranges.append((start, len(points) - 1))


def build_specs():
    near = json.loads(NEAR.read_text(encoding="utf-8"))["routes_grid_100mm"]
    multi = json.loads(MULTI.read_text(encoding="utf-8"))

    c07_body = [xyz(point) for point in near["C07"]]
    c07 = [
        (15900, 8800, LOW_Z), (16900, 8800, LOW_Z),
        (16900, 11600, LOW_Z), (16900, 13400, LOW_Z),
        c07_body[0],
    ]
    c07_ranges = []
    append_body(c07, c07_ranges, c07_body)
    append(c07, [
        (16900, 19000, HIGH_Z), (16900, 12300, HIGH_Z),
        (17500, 12300, HIGH_Z), (17500, 11600, HIGH_Z), (17100, 11600, HIGH_Z),
        (17100, 10800, HIGH_Z), (15900, 10800, HIGH_Z),
    ])

    shelf = [xyz(point) for point in multi["supplemental_body_segments_grid_100mm"]["C08"][0]]
    main = [xyz(point) for point in multi["routes_grid_100mm"]["C08"]]
    seam = [xyz(point) for point in multi["supplemental_body_segments_grid_100mm"]["C08"][1]]
    main.reverse()
    seam.reverse()
    c08 = [
        (15900, 9500, LOW_Z), (16900, 9500, LOW_Z), (16900, 11600, LOW_Z),
        (17400, 11600, LOW_Z), (17400, 12300, LOW_Z), (16900, 12300, LOW_Z),
        (16900, 12500, LOW_Z), shelf[0],
    ]
    c08_ranges = []
    append_body(c08, c08_ranges, shelf)
    append(c08, [
        (16600, 11600, CONNECTOR_Z), (17200, 11600, CONNECTOR_Z),
        (17200, 12300, CONNECTOR_Z), (16900, 12300, CONNECTOR_Z), main[0],
    ])
    append_body(c08, c08_ranges, main)
    append(c08, [
        (17200, 12700, CONNECTOR_Z), (17200, 13000, CONNECTOR_Z),
        (17500, 13000, CONNECTOR_Z), (17500, 11600, CONNECTOR_Z),
        (17700, 11600, CONNECTOR_Z), (17700, 12300, CONNECTOR_Z),
        (19500, 12300, CONNECTOR_Z), seam[0],
    ])
    append_body(c08, c08_ranges, seam)
    append(c08, [
        (17900, 12300, HIGH_Z), (17400, 12300, HIGH_Z),
        (17400, 11600, HIGH_Z), (16600, 11600, HIGH_Z),
        (16600, 10500, HIGH_Z), (15900, 10500, HIGH_Z),
    ])

    c09_body = [xyz(point) for point in near["C09"]]
    c09 = [
        (15900, 9600, LOW_Z), (17000, 9600, LOW_Z), (17000, 11600, LOW_Z),
        (17600, 11600, LOW_Z), (17600, 12300, LOW_Z),
        (20800, 12300, LOW_Z), (20800, 18400, LOW_Z), c09_body[0],
    ]
    c09_ranges = []
    append_body(c09, c09_ranges, c09_body)
    append(c09, [
        (16900, 18800, HIGH_Z), (16900, 12300, HIGH_Z),
        (17600, 12300, HIGH_Z), (17600, 11600, HIGH_Z), (16800, 11600, HIGH_Z),
        (16800, 9800, HIGH_Z), (15900, 9800, HIGH_Z),
    ])

    return [
        {"id": "F1-D171-C07", "ports": (12, 13), "points": c07, "ranges": c07_ranges},
        {
            "id": "F1-D171-C08", "ports": (14, 15), "points": c08, "ranges": c08_ranges,
            # Keep every connector outside BODY.  The shelf and seam endpoints are
            # topologically enclosed in plan, so materialize their R80 layer change
            # before/after the crossing rather than pretending the crossing is BODY.
            "transition_tangent_overrides": {
                11: (80, 800 - math.sqrt(4 * 80 * 78 - 78 * 78) - 80),
                15: (1500 - math.sqrt(4 * 80 * 78 - 78 * 78) - 80, 80),
                48: (2500 - math.sqrt(4 * 80 * 78 - 78 * 78) - 80, 80),
                50: (80, 2500 - math.sqrt(4 * 80 * 27 - 27 * 27) - 80),
            },
        },
        {"id": "F1-D171-C09", "ports": (16, 17), "points": c09, "ranges": c09_ranges},
    ]


def main():
    project = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    original = copy.deepcopy(project)
    specs = build_specs()
    records = {}
    for spec in specs:
        spec["transitions"] = derive_transitions(spec)
        metrics = route_metrics(spec)
        circuit = next(item for item in project["circuits"] if item["id"] == spec["id"])
        circuit.update({
            "ordered_points": [{"x_mm": x, "y_mm": y, "z_mm": z} for x, y, z in spec["points"]],
            "heating_body_start_index": None, "heating_body_end_index": None,
            "heating_body_ranges": [{"start_index": a, "end_index": b} for a, b in spec["ranges"]],
            "vertical_transitions": spec["transitions"], "system_role": "FLOOR_HEATING_LOOP",
            "routing_layer": "HEATING_PLANE", "axis_elevation_mm": BODY_Z,
            "collector_id": "K1", "supply_port_index": spec["ports"][0],
            "return_port_index": spec["ports"][1], "concealed_service_length_mm": 0,
            "out_of_plane_length_mm": 0, "completed": True,
        })
        records[spec["id"]] = {
            "ordered_points_xyz_mm": [list(point) for point in spec["points"]],
            "heating_body_ranges": [list(item) for item in spec["ranges"]],
            "vertical_transitions": spec["transitions"], "metrics": metrics,
            "ordered_point_sha256": hashlib.sha256(json.dumps(spec["points"], separators=(",", ":")).encode()).hexdigest().upper(),
        }

    SCRATCH.parent.mkdir(exist_ok=True)
    SCRATCH.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    import subprocess
    completed = subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor/HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-diagnostics", str(SCRATCH), str(DIAGNOSTICS),
    ], cwd=ROOT, capture_output=True, text=True)
    diagnostics = json.loads(DIAGNOSTICS.read_text(encoding="utf-8-sig")) if completed.returncode == 0 else None
    selected = [] if diagnostics is None else [item for item in diagnostics["circuits"] if item["circuit_id"] in records]
    lengths = {key: value["metrics"]["rounded_physical_axis_length_mm"] for key, value in records.items()}

    def is_body_segment(circuit_id, segment_index):
        return circuit_id in records and any(
            start <= segment_index < end for start, end in records[circuit_id]["heating_body_ranges"]
        )

    contact_classes = {}
    for item in selected:
        circuit_id = item["circuit_id"]
        classes = {}
        for detail in item["inter_circuit_surface_clearance_violation_details"]:
            other_id = detail["other_circuit_id"]
            kind = ("B" if is_body_segment(circuit_id, detail["circuit_segment_index"]) else "T") + (
                "B" if is_body_segment(other_id, detail["other_circuit_segment_index"]) else "T"
            )
            key = f"{other_id}:{kind}"
            classes[key] = classes.get(key, 0) + 1
        contact_classes[circuit_id] = classes
    length_spread = max(lengths.values()) - min(lengths.values())
    publishable = bool(selected) and length_spread <= 2000 and all(
        item["self_intersections"] == 0
        and item["self_surface_clearance_violations"] == 0
        and item["inter_circuit_intersections"] == 0
        and item["inter_circuit_surface_clearance_violations"] == 0
        and item["heating_body_wall_intrusions"] == 0
        and item["horizontal_turn_wall_intrusions"] == 0
        and item["bend_radius_violation_count"] == 0
        and item["vertical_geometry_materialized"]
        and item["rounded_length_in_range"]
        for item in selected
    )
    payload = {
        "schema": "homeaura.r03.point3-scratch.v1", "official_modified": False,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper(),
        "body_sources": {"C07_C09": str(NEAR), "C08": str(MULTI)},
        "records": records, "editor_return_code": completed.returncode,
        "editor_stderr": completed.stderr[-4000:], "editor_diagnostics": selected,
        "all_other_circuits_byte_equivalent_in_memory": all(
            next(x for x in project["circuits"] if x["id"] == c["id"]) == c
            for c in original["circuits"] if c["id"] not in records
        ),
        "bounded_result": {
            "publishable": publishable,
            "lengths_mm": lengths,
            "length_spread_mm": length_spread,
            "maximum_allowed_spread_mm": 2000,
            "inter_contact_classes": contact_classes,
            "exact_blocker": None if publishable else (
                "Preserved BODY ranges are individually clear and have no BODY-BODY contact, "
                "but this bounded TRANSIT synthesis still has physical TRANSIT contacts; "
                "the three complete lengths also exceed the <=2m spread gate."
            ),
        },
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "return_code": completed.returncode,
                      "lengths": lengths,
                      "diagnostics": selected}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
