from __future__ import annotations

import copy
import json
from pathlib import Path

from build_floor1_boiler_pair_178 import (
    CHANGED_IDS,
    apply_specification,
    boiler_coverage,
    exterior_evidence,
    horizontal_turn_wall_audit,
    route_metrics,
    run_editor,
    transit_wall_audit,
)


ROOT = Path(__file__).resolve().parent.parent
SOURCE = (
    ROOT
    / "homeaura-native-editor"
    / "examples"
    / "proposals"
    / "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
    / "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json"
)
OUTPUT = ROOT / "tmp" / "chatgpt_c05c06_solver_20260820"

C05_BODY = [
    (16400, 9200), (18200, 9200), (18200, 11600), (16400, 11600),
    (16400, 9600), (17800, 9600), (17800, 11200), (16800, 11200),
    (16800, 10000), (17400, 10000), (17400, 10800), (17200, 10800),
    (17200, 10200), (17000, 10200), (17000, 11000), (17600, 11000),
    (17600, 9800), (16600, 9800), (16600, 11400), (18000, 11400),
    (18000, 9400), (16400, 9400),
]

C06_BODY = [
    (20600, 11600), (18400, 11600), (18400, 9200), (20600, 9200),
    (20600, 11200), (18800, 11200), (18800, 9600), (20200, 9600),
    (20200, 10800), (19200, 10800), (19200, 10000), (19800, 10000),
    (19800, 10400), (19600, 10400), (19600, 10200), (19400, 10200),
    (19400, 10600), (20000, 10600), (20000, 9800), (19000, 9800),
    (19000, 11000), (20400, 11000), (20400, 9400), (18600, 9400),
    (18600, 11400), (20600, 11400),
]


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def triples(points: list[tuple[int, int]], z: int = 108) -> list[tuple[int, int, int]]:
    return [(x, y, z) for x, y in points]


def specifications(source: dict, variant: str) -> list[dict]:
    circuits = {item["id"]: item for item in source["circuits"]}
    old_c05 = circuits["F1-D171-C05"]
    old_c06 = circuits["F1-D171-C06"]

    c05_prefix = [
        (point["x_mm"], point["y_mm"], point["z_mm"])
        for point in old_c05["ordered_points"][:11]
    ]
    c06_prefix = [
        (point["x_mm"], point["y_mm"], point["z_mm"])
        for point in old_c06["ordered_points"][:6]
    ]
    c05_body = list(C05_BODY)
    c06_body = list(C06_BODY)

    if variant == "chatgpt_orthogonalized":
        c05_post = [
            (16400, 9200, 135),
            (17000, 9200, 135),
            (17000, 9100, 135),
        ]
        c06_post = [
            (20600, 11200, 70),
            (20600, 9400, 70),
            (17000, 9400, 70),
        ]
    elif variant == "chatgpt_r80_escape":
        c05_post = [
            (15700, 9400, 135),
            (15700, 9700, 135),
            (17000, 9700, 135),
            (17000, 9100, 135),
        ]
        c06_post = [
            (21200, 11400, 70),
            (21200, 9400, 70),
            (17000, 9400, 70),
        ]
    elif variant == "chatgpt_layered_top":
        c05_post = [
            (16400, 9200, 135),
            (16400, 8800, 135),
            (17000, 8800, 135),
            (17000, 9100, 135),
        ]
        c06_post = [
            (20600, 11200, 70),
            (20600, 8800, 70),
            (17000, 8800, 70),
            (17000, 9400, 70),
        ]
    elif variant == "chatgpt_layered_top_notch":
        c05_body[10] = (17400, 10400)
        c05_body[11] = (17200, 10400)
        c05_post = [
            (16400, 9200, 135),
            (16400, 8800, 135),
            (18000, 8800, 135),
            (18000, 9100, 135),
            (17000, 9100, 135),
        ]
        c06_post = [
            (20600, 11200, 70),
            (20600, 8800, 70),
            (17000, 8800, 70),
            (17000, 9400, 70),
        ]
    elif variant == "chatgpt_layered_top_center_s":
        c05_body = (
            c05_body[:10]
            + [
                (17400, 10400),
                (17200, 10400),
                (17200, 10800),
                (17000, 10800),
                (17000, 11000),
            ]
            + c05_body[15:]
        )
        c05_post = [
            (16400, 9200, 135),
            (16400, 8800, 135),
            (18000, 8800, 135),
            (18000, 9100, 135),
            (17000, 9100, 135),
        ]
        c06_post = [
            (20600, 11200, 70),
            (20600, 8800, 70),
            (17000, 8800, 70),
            (17000, 9400, 70),
        ]
    elif variant == "chatgpt_layered_top_center_bridge":
        c05_body = (
            c05_body[:10]
            + [
                (17400, 10400),
                (17200, 10400),
                (17200, 10800),
                (17000, 10800),
                (17000, 10200),
                (17600, 10200),
                (17600, 9800),
            ]
            + c05_body[17:]
        )
        c05_post = [
            (16400, 9200, 135),
            (16400, 8800, 135),
            (18000, 8800, 135),
            (18000, 9100, 135),
            (17000, 9100, 135),
        ]
        c06_post = [
            (20600, 11200, 70),
            (20600, 8800, 70),
            (17000, 8800, 70),
            (17000, 9400, 70),
        ]
    elif variant == "chatgpt_exact":
        c05_post = [(16400, 9200, 135), (17000, 9100, 135)]
        c06_post = [(20600, 11200, 70), (17000, 9400, 70)]
    else:
        raise ValueError(variant)

    c05_body_start = len(c05_prefix)
    c06_body_start = len(c06_prefix)
    c05_points = c05_prefix + triples(c05_body) + c05_post
    c06_points = c06_prefix + triples(c06_body) + c06_post

    return [
        {
            "id": "F1-D171-C05",
            "room_id": "F1-R04",
            "ports": (8, 9),
            "points": c05_points,
            "ranges": [
                (1, 3),
                (6, 8),
                (c05_body_start, c05_body_start + len(c05_body) - 1),
            ],
            "name": "ChatGPT56Sol C05 counterflow scratch",
            "grammar": "EXTERNAL_COUNTERFLOW_SPIRAL_SCRATCH",
        },
        {
            "id": "F1-D171-C06",
            "room_id": "F1-R04",
            "ports": (10, 11),
            "points": c06_points,
            "ranges": [
                (1, 3),
                (c06_body_start, c06_body_start + len(c06_body) - 1),
            ],
            "name": "ChatGPT56Sol C06 counterflow scratch",
            "grammar": "EXTERNAL_COUNTERFLOW_SPIRAL_SCRATCH",
        },
    ]


def is_orthogonal(specification: dict) -> bool:
    return all(
        a[0] == b[0] or a[1] == b[1]
        for a, b in zip(specification["points"], specification["points"][1:])
    )


def native_summary(diagnostics: dict) -> dict:
    result = {}
    for item in diagnostics["circuits"]:
        if item["circuit_id"] not in CHANGED_IDS:
            continue
        result[item["circuit_id"]] = {
            key: item.get(key)
            for key in (
                "topology_pass",
                "engineering_pass",
                "orthogonal_axis_pass",
                "rounded_axis_length_mm",
                "self_intersections",
                "self_surface_clearance_violations",
                "inter_circuit_intersections",
                "inter_circuit_surface_clearance_violations",
                "bend_radius_violation_count",
                "heating_body_wall_intrusions",
                "horizontal_turn_wall_intrusions",
                "unmaterialized_vertical_transition_count",
            )
        }
    return result


def evaluate_variant(source: dict, variant: str) -> dict:
    project = copy.deepcopy(source)
    specs = specifications(source, variant)
    try:
        for specification in specs:
            apply_specification(project, specification)
    except RuntimeError as error:
        result = {
            "variant": variant,
            "source": str(SOURCE),
            "preflight_error": str(error),
            "all_plan_segments_orthogonal": all(is_orthogonal(item) for item in specs),
            "acceptance": {
                "orthogonal": all(is_orthogonal(item) for item in specs),
                "transition_materialization": False,
                "all_numeric_native_gates": False,
            },
        }
        dump(OUTPUT / f"{variant}.summary.json", result)
        return result

    source_by_id = {item["id"]: item for item in source["circuits"]}
    current_by_id = {item["id"]: item for item in project["circuits"]}
    unexpected_changes = [
        circuit_id
        for circuit_id in source_by_id
        if circuit_id not in CHANGED_IDS and source_by_id[circuit_id] != current_by_id[circuit_id]
    ]

    project_path = OUTPUT / f"{variant}.homeaura.json"
    diagnostics_path = OUTPUT / f"{variant}.diagnostics.json"
    dump(project_path, project)
    run_editor(project_path, diagnostics_path, "--export-diagnostics")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))

    metrics = {item["id"]: route_metrics(item) for item in specs}
    coverage = boiler_coverage(specs)
    exterior = exterior_evidence(specs)
    sharp_walls = transit_wall_audit(project, specs)
    turn_walls = horizontal_turn_wall_audit(project, CHANGED_IDS)
    native = native_summary(diagnostics)
    rounded_lengths = {
        circuit_id: item["rounded_physical_axis_length_mm"]
        for circuit_id, item in metrics.items()
    }
    spread = abs(rounded_lengths["F1-D171-C05"] - rounded_lengths["F1-D171-C06"])
    physical = coverage["physical_R80_axis_round100"]

    result = {
        "variant": variant,
        "source": str(SOURCE),
        "only_C05_C06_changed": not unexpected_changes,
        "unexpected_changed_circuit_ids": unexpected_changes,
        "all_plan_segments_orthogonal": all(is_orthogonal(item) for item in specs),
        "metrics": metrics,
        "rounded_lengths_mm": rounded_lengths,
        "pair_spread_mm": spread,
        "coverage": coverage,
        "exterior": exterior,
        "transit_wall_audit": sharp_walls,
        "turn_wall_audit": turn_walls,
        "native": native,
    }
    result["acceptance"] = {
        "orthogonal": result["all_plan_segments_orthogonal"],
        "lengths_40_80m": all(40_000 <= value <= 80_000 for value in rounded_lengths.values()),
        "spread_le_2m": spread <= 2_000,
        "coverage_ge_96pct": physical["served_percent"] >= 96,
        "max_gap_le_200mm": physical["maximum_sample_distance_mm"] <= 200 + 1e-9,
        "over_200_count_zero": physical["sample_over_200mm_count"] == 0,
        "exterior_3x100": exterior["all_three_body_lanes_pass"],
        "transit_walls": sharp_walls["pass"],
        "turn_walls": turn_walls["pass"],
        "native_engineering": all(
            item.get("topology_pass") is True
            and item.get("engineering_pass") is True
            and not item.get("self_intersections")
            and not item.get("self_surface_clearance_violations")
            and not item.get("inter_circuit_intersections")
            and not item.get("inter_circuit_surface_clearance_violations")
            and not item.get("bend_radius_violation_count")
            and not item.get("heating_body_wall_intrusions")
            and not item.get("horizontal_turn_wall_intrusions")
            and not item.get("unmaterialized_vertical_transition_count")
            for item in native.values()
        ),
    }
    result["acceptance"]["all_numeric_native_gates"] = all(result["acceptance"].values())
    dump(OUTPUT / f"{variant}.summary.json", result)

    run_editor(project_path, OUTPUT / f"{variant}.clean.png", "--export-room-png-clean", "F1-R04")
    run_editor(
        project_path,
        OUTPUT / f"{variant}.diagnostic.png",
        "--export-room-png-diagnostics",
        "F1-R04",
    )
    return result


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    exact = evaluate_variant(source, "chatgpt_exact")
    orthogonalized = evaluate_variant(source, "chatgpt_orthogonalized")
    r80_escape = evaluate_variant(source, "chatgpt_r80_escape")
    layered_top = evaluate_variant(source, "chatgpt_layered_top")
    layered_top_notch = evaluate_variant(source, "chatgpt_layered_top_notch")
    layered_top_center_s = evaluate_variant(source, "chatgpt_layered_top_center_s")
    layered_top_center_bridge = evaluate_variant(source, "chatgpt_layered_top_center_bridge")
    combined = {
        "source_response_report": "reports/HomeAura_C05_C06_ChatGPT56Sol_response_2026-08-20.md",
        "official_D185_modified": False,
        "variants": {
            "chatgpt_exact": exact["acceptance"],
            "chatgpt_orthogonalized": orthogonalized["acceptance"],
            "chatgpt_r80_escape": r80_escape["acceptance"],
            "chatgpt_layered_top": layered_top["acceptance"],
            "chatgpt_layered_top_notch": layered_top_notch["acceptance"],
            "chatgpt_layered_top_center_s": layered_top_center_s["acceptance"],
            "chatgpt_layered_top_center_bridge": layered_top_center_bridge["acceptance"],
        },
    }
    dump(OUTPUT / "comparison.json", combined)
    print(json.dumps(combined, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
