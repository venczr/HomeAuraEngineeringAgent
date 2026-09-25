"""Source-vector door opening extraction for the Test_01 PDF plans.

The PDF plans are the authority for the location of drawn doors.  This module
only recognises the repeated vector pattern used by the plans: two parallel
thin wall bands, a gap between their endpoints, jambs at the gap endpoints,
and a long leaf line inside the gap.  A wall gap by itself is deliberately
not promoted to a door.

The result is suitable for geometry-only transit previews.  It does not
assert that a floor penetration, fire separation, corridor lane or manifold
has been approved.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pymupdf
from shapely.geometry import LineString, Polygon


@dataclass(frozen=True)
class DoorOpening:
    opening_id: str
    document_id: str
    orientation: str
    opening_drawing_units: tuple[tuple[float, float], tuple[float, float]]
    opening_mm: tuple[tuple[int, int], tuple[int, int]]
    width_mm: int
    adjacent_room_ids: tuple[str, ...]
    vector_evidence: tuple[str, ...]
    geometry_status: str = "DOOR_GEOMETRY_DETECTED"
    passage_status: str = "SOURCE_PDF_VECTOR_CONFIRMED"
    transit_preview_allowed: bool = True
    manifold_connected: str = "UNVERIFIED"

    def as_dict(self) -> dict[str, object]:
        return {
            "opening_id": self.opening_id,
            "document_id": self.document_id,
            "orientation": self.orientation,
            "opening_drawing_units": [[round(x, 3), round(y, 3)] for x, y in self.opening_drawing_units],
            "opening_mm": [list(p) for p in self.opening_mm],
            "width_mm": self.width_mm,
            "adjacent_room_ids": list(self.adjacent_room_ids),
            "vector_evidence": list(self.vector_evidence),
            "geometry_status": self.geometry_status,
            "passage_status": self.passage_status,
            "transit_preview_allowed": self.transit_preview_allowed,
            "manifold_connected": self.manifold_connected,
        }


def _thin_rectangles(page: pymupdf.Page) -> tuple[tuple[float, float, float, float], ...]:
    """Return unique axis-aligned wall/detail rectangles."""
    found: set[tuple[float, float, float, float]] = set()
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] != "re":
                continue
            rect = item[1]
            if rect.width <= 1.5 or rect.height <= 1.5:
                found.add(tuple(round(float(v), 3) for v in (rect.x0, rect.y0, rect.x1, rect.y1)))
    return tuple(found)


def _door_candidates(rects: Sequence[tuple[float, float, float, float]]) -> list[tuple[str, float, float, float, float]]:
    """Find door symbols and return orientation, axis pair and opening span."""
    horizontal = [r for r in rects if r[3] - r[1] <= 1.5 and r[2] - r[0] >= 5]
    vertical = [r for r in rects if r[2] - r[0] <= 1.5 and r[3] - r[1] >= 3]
    # The drawing export repeats wall bands several times.  Keep the two
    # threshold sides and the width, rather than every repeated primitive.
    candidates: dict[tuple[str, float, float, float, float], tuple[str, float, float, float, float]] = {}

    def add_horizontal(a, b) -> None:
        ya, yb = (a[1] + a[3]) / 2, (b[1] + b[3]) / 2
        if abs(ya - yb) < 4 or abs(ya - yb) > 8:
            return
        if a[2] <= b[0]: left, right = a, b
        elif b[2] <= a[0]: left, right = b, a
        else: return
        gap = right[0] - left[2]
        if not 15 <= gap <= 35:
            return
        lo, hi = sorted((ya, yb))
        jambs = 0
        for rect in vertical:
            cx = (rect[0] + rect[2]) / 2
            if abs(cx - left[2]) <= 1 and rect[1] <= lo + 1 and rect[3] >= hi - 1:
                jambs += 1
            if abs(cx - right[0]) <= 1 and rect[1] <= lo + 1 and rect[3] >= hi - 1:
                jambs += 1
        leaf = any(
            left[2] - 1 <= (r[0] + r[2]) / 2 <= right[0] + 1
            and r[1] < lo - 5 and r[3] > hi + 5 for r in vertical
        )
        if jambs >= 2 and leaf:
            key = ("HORIZONTAL", round(left[2], 2), round(right[0], 2), round(lo, 1), round(hi, 1))
            candidates.setdefault(key, ("HORIZONTAL", round(lo, 2), round(hi, 2), round(left[2], 2), round(right[0], 2)))

    def add_vertical(a, b) -> None:
        xa, xb = (a[0] + a[2]) / 2, (b[0] + b[2]) / 2
        if abs(xa - xb) < 4 or abs(xa - xb) > 8:
            return
        if a[3] <= b[1]: top, bottom = a, b
        elif b[3] <= a[1]: top, bottom = b, a
        else: return
        gap = bottom[1] - top[3]
        if not 15 <= gap <= 35:
            return
        lo, hi = sorted((xa, xb))
        jambs = 0
        for rect in horizontal:
            cy = (rect[1] + rect[3]) / 2
            if abs(cy - top[3]) <= 1 and rect[0] <= lo + 1 and rect[2] >= hi - 1:
                jambs += 1
            if abs(cy - bottom[1]) <= 1 and rect[0] <= lo + 1 and rect[2] >= hi - 1:
                jambs += 1
        leaf = any(
            top[3] - 1 <= (r[1] + r[3]) / 2 <= bottom[1] + 1
            and r[0] < lo - 5 and r[2] > hi + 5 for r in horizontal
        )
        if jambs >= 2 and leaf:
            key = ("VERTICAL", round(top[3], 2), round(bottom[1], 2), round(lo, 1), round(hi, 1))
            candidates.setdefault(key, ("VERTICAL", round(lo, 2), round(hi, 2), round(top[3], 2), round(bottom[1], 2)))

    for i, a in enumerate(horizontal):
        for b in horizontal[i + 1:]: add_horizontal(a, b)
    for i, a in enumerate(vertical):
        for b in vertical[i + 1:]: add_vertical(a, b)
    return sorted(candidates.values())


def extract_pdf_door_openings(
    pdf_path: str | Path,
    document_id: str,
    *,
    scale_mm_per_drawing_unit: float,
    rooms: Iterable[tuple[str, Iterable[tuple[float, float]]]] = (),
) -> tuple[DoorOpening, ...]:
    """Extract source-vector doors and bind only geometrically adjacent rooms."""
    with pymupdf.open(str(pdf_path)) as document:
        page = document[0]
        rects = _thin_rectangles(page)
    room_polys = [(rid, Polygon(list(points))) for rid, points in rooms]
    result: list[DoorOpening] = []
    seen: set[tuple[str, int, int, int, int]] = set()
    for index, (orientation, a, b, c, d) in enumerate(_door_candidates(rects), 1):
        if orientation == "HORIZONTAL":
            # The lower/upper axis nearest a room is the threshold candidate.
            p1, p2 = (c, a), (d, a)
            p_alt = LineString([(c, b), (d, b)])
            axis = a if any(poly.boundary.distance(LineString([p1, p2])) <= 1.5 for _, poly in room_polys) else b
            p1, p2 = (c, axis), (d, axis)
            side_segments = (LineString([(c, a), (d, a)]), LineString([(c, b), (d, b)]))
        else:
            p1, p2 = (a, c), (a, d)
            p_alt = LineString([(b, c), (b, d)])
            axis = c if any(poly.boundary.distance(LineString([p1, p2])) <= 1.5 for _, poly in room_polys) else d
            p1, p2 = (axis, a), (axis, b)
            side_segments = (LineString([(a, c), (a, d)]), LineString([(b, c), (b, d)]))
        key = (orientation, round(p1[0]), round(p1[1]), round(p2[0]), round(p2[1]))
        if key in seen: continue
        seen.add(key)
        segment = LineString([p1, p2])
        # Bind both sides of the threshold.  Using only the selected side
        # previously attached room 12's door to WC 13 because the lower wall
        # band happened to be the first source primitive encountered.
        adjacent = tuple(rid for rid, poly in room_polys if any(poly.boundary.distance(side) <= 1.5 for side in side_segments))
        width = int(round(segment.length * scale_mm_per_drawing_unit))
        mm = tuple(tuple(int(round(v * scale_mm_per_drawing_unit)) for v in p) for p in (p1, p2))
        source_door = width >= 600
        result.append(DoorOpening(
            opening_id=f"{document_id}-DOOR-{index:03d}", document_id=document_id,
            orientation=orientation, opening_drawing_units=(p1, p2), opening_mm=mm,
            width_mm=width, adjacent_room_ids=adjacent,
            vector_evidence=("PARALLEL_WALL_BANDS", "TWO_JAMBS", "DOOR_LEAF_VECTOR") if source_door else ("PARALLEL_WALL_BANDS", "TWO_JAMBS", "LEAF_OR_DETAIL_VECTOR", "WIDTH_BELOW_DOOR_PREVIEW_THRESHOLD"),
            passage_status="SOURCE_PDF_VECTOR_CONFIRMED" if source_door else "UNKNOWN_OPENING_SYMBOL",
            transit_preview_allowed=source_door,
        ))
    return tuple(result)


__all__ = ["DoorOpening", "extract_pdf_door_openings"]
