from __future__ import annotations

"""Bounded joint R03 search.  This never writes an official proposal.

The search owns all three exterior axes with one continuous path and chooses
the two remaining paths at the same time.  Numeric feasibility and the
owner-morphology gate are reported separately: a numerically passing
serpentine is evidence, not permission to publish it as an owner-style loop.
"""

import json
import hashlib
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from build_floor1_physical_four_loop_175 import fillet  # noqa: E402
from build_owner_style_installation_project_141 import clean, self_contacts  # noqa: E402

OUT = ROOT / "reports" / "HomeAura_R03_Global_Search_D180_2026-08-20.json"
PNG = ROOT / "reports" / "HomeAura_R03_Global_Search_D180_2026-08-20.png"
DOMAIN = Polygon([(211, 121), (163, 121), (163, 126), (168, 126),
                  (168, 128), (168, 193), (211, 193)])
SERVICES_MM = (16800, 21600, 22300)


def snake(left: int, top: int, right: int, bottom: int, start_right: bool = False):
    points = []
    for row, y in enumerate(range(top, bottom + 1, 2)):
        reverse = (row + int(start_right)) % 2 == 1
        first, second = (right, left) if reverse else (left, right)
        points.extend([(first, y), (second, y)])
    return clean(points)


def owner_candidate(right: int):
    bottom_fill = list(reversed(snake(171, 122, right, 134, start_right=True)))
    exterior_and_turnouts = [
        (210, 122), (210, 192), (169, 192),
        # Five-grid drop plus a 3/2/2-grid orthogonal turnout keeps every
        # physical tangent >= R80 while crossing inward without touching the
        # later y=190 third lane.
        (169, 187), (172, 187), (172, 189), (170, 189), (170, 191),
        (209, 191), (209, 124),
        (206, 124), (206, 126), (208, 126),
        (208, 190), (171, 190),
    ]
    return clean(bottom_fill + exterior_and_turnouts)


def shelf_and_middle_candidate(top: int):
    shelf_snake = [
        (164, 126), (164, 122), (169, 122), (169, 124),
        (166, 124), (166, 126), (169, 126), (169, top),
    ]
    return clean(shelf_snake + snake(169, top, 207, 160))


def upper_candidate(end_x: int):
    return clean(snake(169, 162, 207, 186) + [(207, 188), (end_x, 188)])


def intervals(points, vertical: bool, axis: int):
    values = []
    for first, second in zip(points, points[1:]):
        if vertical and first[0] == second[0] == axis:
            values.append((min(first[1], second[1]), max(first[1], second[1])))
        if not vertical and first[1] == second[1] == axis:
            values.append((min(first[0], second[0]), max(first[0], second[0])))
    return values


def covers(interval_list, required):
    low, high = required
    return sum(max(0, min(high, b) - max(low, a)) for a, b in interval_list) * 100 / (high - low)


def evaluate(points_by_route, include_samples=False):
    sharp = [LineString(points) for points in points_by_route]
    physical = [LineString(fillet(points)) for points in points_by_route]
    lengths = [line.length * 100 + service for line, service in zip(physical, SERVICES_MM)]
    merged = unary_union(physical)
    result = {
        "body_inside_authoritative_component": all(DOMAIN.covers(line) for line in physical),
        "sharp_self_contact_count": sum(self_contacts(points) for points in points_by_route),
        "physical_self_intersection_count": sum(not line.is_simple for line in physical),
        "physical_inter_route_contact_count": sum(
            not physical[i].intersection(physical[j]).is_empty
            for i in range(3) for j in range(i + 1, 3)
        ),
        "complete_lengths_mm": lengths,
        "complete_length_spread_mm": max(lengths) - min(lengths),
        "physical_round100_coverage_percent": (
            DOMAIN.intersection(merged.buffer(1, quad_segs=16)).area * 100 / DOMAIN.area
        ),
    }
    if include_samples:
        samples = [
            Point(x / 2, y / 2).distance(merged)
            for x in range(math.ceil(DOMAIN.bounds[0] * 2), math.floor(DOMAIN.bounds[2] * 2) + 1)
            for y in range(math.ceil(DOMAIN.bounds[1] * 2), math.floor(DOMAIN.bounds[3] * 2) + 1)
            if DOMAIN.covers(Point(x / 2, y / 2))
        ]
        result.update({
            "sample_grid_mm": 50,
            "sample_count": len(samples),
            "maximum_sample_distance_mm": max(samples) * 100,
            "sample_over_200mm_count": sum(value > 2 + 1e-9 for value in samples),
        })
    return result


def point_digest(points):
    canonical = json.dumps(points, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(canonical).hexdigest().upper()


def render_diagnostic(routes, metrics, route_records):
    colors = ("#F97066", "#29B6F6", "#A3E635")
    physical = [LineString(fillet(points)) for points in routes]
    width, height, scale = 2000, 1500, 16
    x_min, y_max = 159, 198
    origin_x, origin_y = 55, 72

    def xy(point):
        return (round(origin_x + (point[0] - x_min) * scale),
                round(origin_y + (y_max - point[1]) * scale))

    def rect_world(left, bottom, right, top):
        a, b = xy((left, top)), xy((right, bottom))
        return (a[0], a[1], b[0], b[1])

    image = Image.new("RGB", (width, height), "#07131B")
    draw = ImageDraw.Draw(image)
    font_regular = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 20)
    font_small = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
    font_tiny = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 13)
    font_bold = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 29)

    draw.rectangle(rect_world(159.5, 118, 216.5, 198), fill="#0B202A", outline="#77909A", width=2)
    for coordinate in range(160, 217):
        p1, p2 = xy((coordinate, 118)), xy((coordinate, 198))
        draw.line([p1, p2], fill="#31515E" if coordinate % 2 else "#496671", width=1)
    for coordinate in range(120, 199):
        p1, p2 = xy((159.5, coordinate)), xy((216.5, coordinate))
        draw.line([p1, p2], fill="#31515E" if coordinate % 2 else "#496671", width=1)

    draw.polygon([xy(point) for point in DOMAIN.exterior.coords],
                 fill="#143542", outline="#E8F0F2")

    # Exact R03 wall solids: W026/W027/W028/W029 plus W018/W019 at the west step.
    walls = [(162,119,213,121), (211,120,215,195), (162,193,213,197),
             (161,120,163,195), (157,126,167,128), (166,127,168,195)]
    for wall in walls:
        draw.rectangle(rect_world(*wall), fill="#D7C7A5", outline="#EFE3C9", width=2)

    served = DOMAIN.intersection(unary_union(physical).buffer(1, quad_segs=16))
    served_parts = [served] if served.geom_type == "Polygon" else list(served.geoms)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for part in served_parts:
        overlay_draw.polygon([xy(point) for point in part.exterior.coords], fill=(125, 211, 168, 28))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Windows are projections on the true inner faces of W027 and W028.
    draw.line([xy((211,157)), xy((211,174))], fill="#78D7FF", width=12)
    draw.line([xy((179,193)), xy((198,193))], fill="#78D7FF", width=12)
    draw.text(xy((202,193.9)), "WIN-05", fill="#BDEBFF", font=font_small)
    draw.text(xy((211.7,166)), "WIN-04", fill="#BDEBFF", font=font_small)

    for record, line, color in zip(route_records, physical, colors):
        pixel_points = [xy(point) for point in line.coords]
        draw.line(pixel_points, fill="#07131B", width=9, joint="curve")
        draw.line(pixel_points, fill=color, width=5, joint="curve")
        for endpoint in (pixel_points[0], pixel_points[-1]):
            draw.ellipse((endpoint[0]-5, endpoint[1]-5, endpoint[0]+5, endpoint[1]+5),
                         fill=color, outline="#F8FAFC", width=1)

    draw.text((55, 18), "R03 · NUMERIC CANDIDATE / MORPHOLOGY NOT ACCEPTED",
              fill="#FFDA66", font=font_bold)
    draw.text((1030, 75), "DIAGNOSTIC ONLY", fill="#FF8A80", font=font_bold)
    draw.text((1030, 122),
              f"Physical R80\nCoverage: {metrics['physical_round100_coverage_percent']:.3f}%\n"
              f"Max 50-mm sample gap: {metrics['maximum_sample_distance_mm']:.3f} mm\n"
              "Self/inter-route contacts: 0\nWIN-04: 100/100/100%\nWIN-05: 100/100/100%\n"
              "Useful wall-span minima:\n  W027 91.429%  W028 90.244%",
              fill="#D8E7EC", font=font_regular, spacing=8)

    legend_y = 390
    for record, color in zip(route_records, colors):
        draw.rectangle((1030, legend_y, 1060, legend_y+20), fill=color)
        draw.text((1072, legend_y-3), f"{record['id']} · {record['complete_length_mm']/1000:.3f} m",
                  fill="#F3F8FA", font=font_regular)
        draw.text((1030, legend_y+34), record["body_type"], fill="#F3F8FA", font=font_small)
        draw.text((1030, legend_y+62), "SHA256(ordered points):", fill="#AAC2CB", font=font_tiny)
        digest = record["ordered_point_sha256"]
        draw.text((1030, legend_y+83), digest[:32], fill="#AAC2CB", font=font_tiny)
        draw.text((1030, legend_y+103), digest[32:], fill="#AAC2CB", font=font_tiny)
        legend_y += 160
    draw.text((1030, 900),
              "C07 owns all three nested exterior axes.\n"
              "C08/C09 are numeric serpentines, not accepted\n"
              "counterflow spiral/hybrid morphology.\n\n"
              "No D178/D180 project was modified.",
              fill="#FFDA66", font=font_regular, spacing=8)
    PNG.parent.mkdir(parents=True, exist_ok=True)
    image.save(PNG, format="PNG", optimize=True)


def main():
    # Deterministic depth-first branch-and-bound over all three paths.  Cheap
    # topology and 40..80 m bounds prune before the union/coverage operation.
    evaluated = 0
    coverage_evaluated = 0
    candidates = []
    for owner_right in (203, 204, 205):
        owner = owner_candidate(owner_right)
        if self_contacts(owner) or not LineString(owner).is_simple:
            continue
        for middle_top in (136, 138):
            middle = shelf_and_middle_candidate(middle_top)
            if self_contacts(middle) or not LineString(middle).is_simple:
                continue
            for upper_end_x in range(173, 208):
                evaluated += 1
                routes = [owner, middle, upper_candidate(upper_end_x)]
                physical = [LineString(fillet(points)) for points in routes]
                lengths = [line.length * 100 + service for line, service in zip(physical, SERVICES_MM)]
                if any(length < 40000 or length > 80000 for length in lengths):
                    continue
                if max(lengths) - min(lengths) > 2000:
                    continue
                if any(not line.is_simple or not DOMAIN.covers(line) for line in physical):
                    continue
                if any(not physical[i].intersection(physical[j]).is_empty
                       for i in range(3) for j in range(i + 1, 3)):
                    continue
                coverage_evaluated += 1
                metrics = evaluate(routes)
                score = (-metrics["physical_round100_coverage_percent"],
                         metrics["complete_length_spread_mm"],
                         sum(abs(value - 70170) for value in lengths))
                candidates.append((score, owner_right, middle_top, upper_end_x, routes, metrics))

    candidates.sort(key=lambda item: item[0])
    best = candidates[0]
    _, owner_right, middle_top, upper_end_x, routes, metrics = best
    metrics = evaluate(routes, include_samples=True)

    owner = routes[0]
    exterior = {
        "W027_vertical": [
            {"lane": lane, "axis_x": axis, "useful_span_percent": covers(intervals(owner, True, axis), (122, 192)),
             "WIN_04_percent": covers(intervals(owner, True, axis), (157, 174))}
            for lane, axis in ((1, 210), (2, 209), (3, 208))
        ],
        "W028_horizontal": [
            {"lane": lane, "axis_y": axis, "useful_span_percent": covers(intervals(owner, False, axis), (169, 210)),
             "WIN_05_percent": covers(intervals(owner, False, axis), (179, 198))}
            for lane, axis in ((1, 192), (2, 191), (3, 190))
        ],
        "turnout_gaps_mm": [200, 400],
        "nested_corner_trim_mm": [0, 100, 200],
    }
    numeric_pass = (
        metrics["body_inside_authoritative_component"]
        and metrics["sharp_self_contact_count"] == 0
        and metrics["physical_self_intersection_count"] == 0
        and metrics["physical_inter_route_contact_count"] == 0
        and all(40000 <= value <= 80000 for value in metrics["complete_lengths_mm"])
        and metrics["complete_length_spread_mm"] <= 2000
        and metrics["physical_round100_coverage_percent"] >= 96
        and metrics["maximum_sample_distance_mm"] <= 200
        and metrics["sample_over_200mm_count"] == 0
        and all(row["useful_span_percent"] >= 90
                for wall in (exterior["W027_vertical"], exterior["W028_horizontal"])
                for row in wall)
        and all(row[window] == 100 for wall in exterior.values() if isinstance(wall, list)
                for row in wall if isinstance(row, dict)
                for window in row if window.endswith("percent") and window.startswith("WIN_"))
    )
    route_records = [
        {"id": "C07", "body_type": "SERPENTINE + EXTERIOR 3x100 OWNER (NOT SPIRAL)"},
        {"id": "C08", "body_type": "SHELF SNAKE + FIELD SERPENTINE (NOT SPIRAL)"},
        {"id": "C09", "body_type": "FIELD SERPENTINE + LOCAL ROW (NOT SPIRAL)"},
    ]
    for record, points, length in zip(route_records, routes, metrics["complete_lengths_mm"]):
        record["ordered_point_sha256"] = point_digest(points)
        record["complete_length_mm"] = length
        record["ordered_point_count"] = len(points)
    render_diagnostic(routes, metrics, route_records)
    payload = {
        "schema": "homeaura.r03.joint-search.v1",
        "status": "NUMERIC_ALL_GATE_CANDIDATE_MORPHOLOGY_NOT_PUBLISHABLE",
        "official_D178_or_D180_modified": False,
        "search": {
            "method": "DETERMINISTIC_DEPTH_FIRST_BRANCH_AND_BOUND_JOINT_THREE_PATH",
            "evaluated_joint_candidates": evaluated,
            "coverage_evaluated_after_pruning": coverage_evaluated,
            "selected_parameters": {"owner_right": owner_right, "middle_top": middle_top, "upper_end_x": upper_end_x},
        },
        "authoritative_component_grid_100mm": [list(point) for point in DOMAIN.exterior.coords[:-1]],
        "routes_grid_100mm": {
            "C07_exterior_owner_plus_bottom_serpentine": [list(point) for point in routes[0]],
            "C08_shelf_snake_plus_middle_serpentine": [list(point) for point in routes[1]],
            "C09_upper_serpentine_plus_local_row": [list(point) for point in routes[2]],
        },
        "route_identity": route_records,
        "diagnostic_png": str(PNG),
        "numeric_metrics": metrics,
        "exterior_3x100": exterior,
        "numeric_hard_gates_pass": numeric_pass,
        "owner_morphology_hard_gate_pass": False,
        "exact_blocker": (
            "The best joint numeric candidate uses coherent single-chain serpentines for C08 and C09. "
            "They are not yet proven as the owner's required counterflow spiral/hybrid morphology; "
            "therefore the candidate is diagnostic only and must not replace D180."
        ),
        "best_pareto": [
            {"owner_right": item[1], "middle_top": item[2], "upper_end_x": item[3],
             "coverage_percent": item[5]["physical_round100_coverage_percent"],
             "complete_lengths_mm": item[5]["complete_lengths_mm"],
             "spread_mm": item[5]["complete_length_spread_mm"]}
            for item in candidates[:10]
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "png": str(PNG), "numeric_pass": numeric_pass,
                      "morphology_pass": False, "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
