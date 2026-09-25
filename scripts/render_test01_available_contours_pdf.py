"""Draw the currently serialized Test_01 room BODY previews on source PDF copies.

This is a visual inventory. It does not promote old single-room previews to
independent, collector-connected circuits.
"""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dev" / "ufh_real_plan"
SOURCE = ROOT / "projects" / "Test_01" / "engineering" / "source_documents"
OUT = ROOT / "output" / "pdf"

FLOORS = {
    "FLOOR_1_PLAN": {
        "pdf": "Test_01_floor_1_plan.pdf",
        "output": "Test_01_available_contours_floor_1_preview_20260924.pdf",
        "transform": (35.276963114841126, 0.354536853315949, -0.013838128109455283),
        "note": "8 older room BODY routes + 1 newer room 8 upper-zone BODY; no collector connection",
    },
    "ATTIC_PLAN": {
        "pdf": "Test_01_attic_plan.pdf",
        "output": "Test_01_available_contours_attic_preview_20260924.pdf",
        "transform": (35.192264300635422, 0.4970194120433007, -0.36873403255594894),
        "note": "7 older room BODY routes; room 9 has no materialized route",
    },
}

COLORS = [
    (0.81, 0.13, 0.13),
    (0.08, 0.43, 0.72),
    (0.10, 0.58, 0.28),
    (0.89, 0.40, 0.04),
    (0.54, 0.24, 0.67),
    (0.05, 0.59, 0.61),
    (0.68, 0.40, 0.05),
    (0.32, 0.40, 0.62),
]


def page_point(point: list[float], floor: str) -> tuple[float, float]:
    scale, ox, oy = FLOORS[floor]["transform"]
    return ((point[0] - ox) / scale, (point[1] - oy) / scale)


def label_row(page: pymupdf.Page, x: float, y: float, color, label: str, *, dashed=False):
    if color is not None:
        page.draw_line((x, y - 2), (x + 19, y - 2), color=color, width=1.6, dashes="[3 2]" if dashed else None)
    page.insert_text((x + 23, y), label, fontsize=7.2, color=(0.12, 0.12, 0.12))


def render(floor: str, rooms: list[dict], top_candidate: dict) -> dict:
    config = FLOORS[floor]
    document = pymupdf.open(str(SOURCE / config["pdf"]))
    page = document[0]
    room_entries = sorted(
        (r for r in rooms if r.get("floor_source_id") == floor),
        key=lambda r: int(r["label"].split("/")[0].strip()),
    )
    labels = []
    count = 0
    for i, room in enumerate(room_entries):
        number = int(room["label"].split("/")[0].strip())
        routes = room.get("floor_global_route_polylines_mm") or []
        color = (0.55, 0.55, 0.55) if floor == "FLOOR_1_PLAN" and number == 8 else COLORS[i % len(COLORS)]
        for route in routes:
            points = [page_point(point, floor) for point in route]
            if len(points) < 2:
                continue
            page.draw_polyline(points, color=color, width=0.94, stroke_opacity=0.82, overlay=True)
            count += 1
        if routes:
            label = f"{number}: older BODY preview"
            if floor == "FLOOR_1_PLAN" and number == 8:
                label += " (superseded)"
            labels.append((color, label))
        else:
            labels.append((None, f"{number}: NO materialized BODY"))

    if floor == "FLOOR_1_PLAN":
        points = [page_point(point, floor) for point in top_candidate["rounded_points_mm"]]
        page.draw_polyline(points, color=(0.62, 0.08, 0.72), width=1.55, overlay=True)
        for terminal in top_candidate["terminals_mm"]:
            page.draw_circle(page_point(terminal, floor), 2.2, color=(0.62, 0.08, 0.72), fill=(1, 1, 1), width=1.1, overlay=True)
        labels.append(((0.62, 0.08, 0.72), "8: NEW upper-zone BODY only"))

    # The source sheets leave open space above and below the floor plan.
    page.draw_rect(pymupdf.Rect(108, 104, 489, 132), color=(0.6, 0.6, 0.6), fill=(1, 1, 1), width=0.45, overlay=True)
    page.insert_text((115, 115), "HOMEAURA / TEST_01 - AVAILABLE BODY ROUTES", fontsize=8.2, color=(0.11, 0.20, 0.35), overlay=True)
    page.insert_text((115, 125), "PREVIEW ONLY. Routes do not prove separate full circuits, transit or <=90 m.", fontsize=6.7, color=(0.58, 0.12, 0.12), overlay=True)

    page.draw_rect(pymupdf.Rect(118, 575, 475, 672), color=(0.7, 0.7, 0.7), fill=(1, 1, 1), width=0.4, overlay=True)
    page.insert_text((127, 587), config["note"], fontsize=6.9, color=(0.14, 0.19, 0.30), overlay=True)
    page.insert_text((127, 598), "One line = one serialized room BODY; colors distinguish rooms, not supply/return.", fontsize=6.3, color=(0.26, 0.26, 0.26), overlay=True)
    for i, (color, label) in enumerate(labels):
        col, row = divmod(i, 5)
        label_row(page, 128 + 174 * col, 610 + 12 * row, color, label)
    page.insert_text((127, 665), "Source: Test_01 PDF. Route snapshot: 2026-09-21; room 8 upper candidate: 2026-09-24.", fontsize=5.8, color=(0.36, 0.36, 0.36), overlay=True)

    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / config["output"]
    document.save(str(destination), garbage=4, deflate=True)
    document.close()
    return {"floor": floor, "pdf": str(destination), "older_body_routes": count, "new_room8_upper_body": floor == "FLOOR_1_PLAN"}


def main() -> None:
    rooms = json.loads((DATA / "two_floor_summary.json").read_text(encoding="utf-8"))["rooms"]
    top_candidate = json.loads((DATA / "test01_room8_top_zone_shifted_splice_preview_20260924.json").read_text(encoding="utf-8"))
    for floor in FLOORS:
        print(render(floor, rooms, top_candidate))


if __name__ == "__main__":
    main()
