"""Show serialized spiral candidates on untouched Test_01 source PDF plans.

Bold purple is the current single-zone room 8 preview. Pale routes are
historical rejected experiments, included to locate the spirals on the plan.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.ufh_bend_geometry import build_rounded_centerline  # noqa: E402
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral  # noqa: E402


DATA = ROOT / "dev" / "ufh_real_plan"
SOURCE = ROOT / "projects" / "Test_01" / "engineering" / "source_documents"
KITCHEN = ROOT / "projects" / "Test_01" / "exports" / "ufh_generator_package" / "kitchen_spiral_search" / "kitchen_spiral_search.json"
OUT = ROOT / "output" / "pdf"

TRANSFORM = {
    "FLOOR_1_PLAN": (35.276963114841126, 0.354536853315949, -0.013838128109455283),
    "ATTIC_PLAN": (35.192264300635422, 0.4970194120433007, -0.36873403255594894),
}


def page_point(point, floor):
    scale, ox, oy = TRANSFORM[floor]
    return ((point[0] - ox) / scale, (point[1] - oy) / scale)


def add_banner(page, subtitle):
    page.draw_rect(pymupdf.Rect(107, 101, 489, 135), color=(0.65, 0.65, 0.65), fill=(1, 1, 1), width=0.5, overlay=True)
    page.insert_text((114, 114), "HOMEAURA TEST_01 - ACTUAL SPIRAL GEOMETRY", fontsize=8.8, color=(0.22, 0.14, 0.37), overlay=True)
    page.insert_text((114, 125), subtitle, fontsize=6.7, color=(0.56, 0.13, 0.13), overlay=True)


def add_line_legend(page, y, color, text):
    page.draw_line((129, y - 2), (157, y - 2), color=color, width=1.5, overlay=True)
    page.insert_text((164, y), text, fontsize=7.5, color=(0.19, 0.19, 0.19), overlay=True)


def floor_one():
    document = pymupdf.open(str(SOURCE / "Test_01_floor_1_plan.pdf"))
    page = document[0]
    add_banner(page, "Only one current single-zone BODY. Pale experiments failed design gates.")
    kitchen = json.loads(KITCHEN.read_text(encoding="utf-8"))
    origin = kitchen["local_origin_mm"]
    kitchen_colors = ((0.88, 0.37, 0.05), (0.80, 0.17, 0.12))
    for route, color in zip(kitchen["routes"], kitchen_colors):
        rounded = build_rounded_centerline(route["route_mm"], bend_radius_mm=80)
        assert rounded.valid
        global_points = [(x + origin[0], y + origin[1]) for x, y in rounded.points]
        page.draw_polyline([page_point(p, "FLOOR_1_PLAN") for p in global_points], color=color, width=0.75, overlay=True)

    lower_report = json.loads((DATA / "test01_room8_lower_zone_body_20260924.json").read_text(encoding="utf-8"))
    lower_main = build_accessible_bifilar_spiral((4369, 7502, 9195, 8702), 200, minimum_bend_radius_mm=80)
    lower_sharp = [lower_main[0], lower_main[1], lower_main[2], (4369, 7142), (6682, 7142),
                   (6682, 7342), (4469, 7342), (4469, 7502), *lower_main[4:]]
    lower_rounded = build_rounded_centerline(lower_sharp, bend_radius_mm=80)
    assert lower_rounded.valid
    assert abs(lower_rounded.length_mm / 1000 - lower_report["materialised_metrics"]["body_length_m"]) < 0.01
    page.draw_polyline([page_point(p, "FLOOR_1_PLAN") for p in lower_rounded.points], color=(0.36, 0.55, 0.58), width=0.75, overlay=True)

    current = json.loads((DATA / "test01_room8_top_zone_shifted_splice_preview_20260924.json").read_text(encoding="utf-8"))
    current_color = (0.55, 0.07, 0.70)
    page.draw_polyline([page_point(p, "FLOOR_1_PLAN") for p in current["rounded_points_mm"]], color=current_color, width=1.65, overlay=True)
    for point in current["terminals_mm"]:
        page.draw_circle(page_point(point, "FLOOR_1_PLAN"), 2.2, color=current_color, fill=(1, 1, 1), width=1.2, overlay=True)

    page.draw_rect(pymupdf.Rect(117, 574, 479, 683), color=(0.67, 0.67, 0.67), fill=(1, 1, 1), width=0.45, overlay=True)
    page.insert_text((128, 588), "SPIRALS ON THIS PLAN - project candidates, not collector-to-collector circuits", fontsize=7.1, color=(0.13, 0.20, 0.31), overlay=True)
    add_line_legend(page, 604, current_color, "Room 8 upper zone: R80 BODY 44.27 m; pipe-band 97.35%")
    add_line_legend(page, 618, (0.36, 0.55, 0.58), "Room 8 lower: new BODY 35.55 m; coverage 87.81% FAIL")
    add_line_legend(page, 632, kitchen_colors[0], "Room 3 kitchen spiral 1: BODY 80.03 m, residual area")
    add_line_legend(page, 646, kitchen_colors[1], "Room 3 kitchen spiral 2: BODY 87.23 m, residual area")
    page.insert_text((129, 663), "All supply/return transit, joint layout and full-circuit length remain UNVERIFIED.", fontsize=6.6, color=(0.52, 0.14, 0.14), overlay=True)
    page.insert_text((129, 675), "The five-spiral L-room control example is synthetic; it is not Test_01.", fontsize=6.6, color=(0.40, 0.32, 0.11), overlay=True)
    destination = OUT / "Test_01_spiral_candidates_floor_1_20260924.pdf"
    document.save(str(destination), garbage=4, deflate=True)
    document.close()
    return destination


def attic():
    document = pymupdf.open(str(SOURCE / "Test_01_attic_plan.pdf"))
    page = document[0]
    add_banner(page, "No spiral BODY has been serialized for an attic room in the current handoff.")
    page.draw_rect(pymupdf.Rect(117, 575, 479, 636), color=(0.67, 0.67, 0.67), fill=(1, 1, 1), width=0.45, overlay=True)
    page.insert_text((129, 591), "ATTIC STATUS", fontsize=8, color=(0.13, 0.20, 0.31), overlay=True)
    page.insert_text((129, 607), "No spiral lines are drawn because no current serialized spiral BODY exists.", fontsize=7, color=(0.19, 0.19, 0.19), overlay=True)
    page.insert_text((129, 621), "This sheet does not certify heating coverage or collector connection.", fontsize=7, color=(0.52, 0.14, 0.14), overlay=True)
    destination = OUT / "Test_01_spiral_candidates_attic_20260924.pdf"
    document.save(str(destination), garbage=4, deflate=True)
    document.close()
    return destination


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print(floor_one())
    print(attic())
