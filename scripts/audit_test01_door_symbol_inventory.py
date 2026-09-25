"""Read-only audit: what source-vector door evidence does each room carry?

The canonical door extractor (``agent/pdf_door_openings.py``) recognises the
repeated plan symbol only when two parallel thin wall bands, a 15-35
drawing-unit gap, two jambs and a leaf line are all present.  Rooms without
such a symbol are left without a door.  Before any corridor or transit claim
this audit records, per room, what the source vectors actually contain:

* the thin wall bands whose centre lies inside the room bounding box;
* the *consecutive* gaps on each collinear wall line (a correct gap is the
  free span between the end of one wall segment and the start of the next
  segment on the same line, never an arbitrary pair of bands);
* whether the canonical extractor produced a door symbol for the room.

Nothing here is promoted to a door.  The script changes no routing, no
manifold status and no authority flag.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf

from agent.pdf_door_openings import _door_candidates, _thin_rectangles
from agent.test01_drawing_understanding import reconstruct_test01_room_candidates


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "Test_01"
OUT = ROOT / "dev" / "ufh_real_plan"

FLOORS = (
    ("FLOOR_1_PLAN", "Test_01_floor_1_plan.pdf"),
    ("ATTIC_PLAN", "Test_01_attic_plan.pdf"),
)

MINIMUM_GAP_DRAWING_UNITS = 5.0
MAXIMUM_GAP_DRAWING_UNITS = 45.0


def _room_rows(drawing, floor: str):
    rows = []
    for room in drawing.building_rooms:
        if room.floor_source_id != floor:
            continue
        hypothesis = next(
            h for h in drawing.understanding.hypotheses
            if h.hypothesis_id == room.room_hypothesis_id
        )
        rows.append((
            room.room_hypothesis_id,
            room.label_text,
            [(float(p.x), float(p.y)) for p in hypothesis.geometry.points],
        ))
    return rows


def _wall_bands(rects):
    """Split the thin rectangles into horizontal and vertical wall bands."""
    horizontal = [r for r in rects if r[3] - r[1] <= 1.5 and r[2] - r[0] >= 5]
    vertical = [r for r in rects if r[2] - r[0] <= 1.5 and r[3] - r[1] >= 3]
    return horizontal, vertical


def _line_segments(page):
    """Return the stroked line primitives as axis-aligned segments.

    The canonical extractor reads rectangle primitives only.  Rooms whose
    walls are drawn as strokes therefore carry no rectangle-based evidence at
    all, so this pass records the stroked geometry separately.
    """
    horizontal: dict[float, list[list[float]]] = {}
    vertical: dict[float, list[list[float]]] = {}
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) <= 0.5 and abs(p1.x - p2.x) >= 3:
                line = round(p1.y * 2) / 2
                horizontal.setdefault(line, []).append(
                    sorted([float(p1.x), float(p2.x)]))
            elif abs(p1.x - p2.x) <= 0.5 and abs(p1.y - p2.y) >= 3:
                line = round(p1.x * 2) / 2
                vertical.setdefault(line, []).append(
                    sorted([float(p1.y), float(p2.y)]))
    return horizontal, vertical


def _wall_line_gaps(bands, orientation):
    """Return the consecutive gaps on every collinear wall line.

    Bands are grouped by their wall line (constant y for horizontal bands,
    constant x for vertical bands), merged where they touch, and then walked
    in order.  Only the free span between two *neighbouring* segments is a gap;
    pairing arbitrary bands produced overlapping pairs and fabricated openings.
    """
    lines: dict[float, list[list[float]]] = {}
    for rect in bands:
        if orientation == "HORIZONTAL":
            line = round(rect[1] * 2) / 2
            span = [rect[0], rect[2]]
        else:
            line = round(rect[0] * 2) / 2
            span = [rect[1], rect[3]]
        lines.setdefault(line, []).append(span)
    return _gaps_from_lines(lines, orientation)


def _gaps_from_lines(lines, orientation):
    """Merge collinear spans and return the free span between neighbours."""
    gaps = []
    for line, spans in lines.items():
        spans.sort()
        merged: list[list[float]] = []
        for start, end in spans:
            if merged and start <= merged[-1][1] + 0.01:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        for index in range(1, len(merged)):
            span = merged[index][0] - merged[index - 1][1]
            if not MINIMUM_GAP_DRAWING_UNITS <= span <= MAXIMUM_GAP_DRAWING_UNITS:
                continue
            centre = (merged[index - 1][1] + merged[index][0]) / 2
            gaps.append({
                "orientation": orientation,
                "band_axis_drawing_units": round(line, 3),
                "centre_drawing_units": (
                    [round(centre, 3), round(line, 3)] if orientation == "HORIZONTAL"
                    else [round(line, 3), round(centre, 3)]
                ),
                "span_drawing_units": round(span, 3),
                "left_wall_segment_drawing_units": [
                    round(merged[index - 1][0], 3), round(merged[index - 1][1], 3)],
                "right_wall_segment_drawing_units": [
                    round(merged[index][0], 3), round(merged[index][1], 3)],
            })
    return gaps


def _gap_evidence(gap, scale):
    """Classify a wall gap for later confirmation; never promote it to a door."""
    width_mm = int(round(gap["span_drawing_units"] * scale))
    if width_mm < 600:
        classification = "GAP_NARROWER_THAN_DOOR_PREVIEW_THRESHOLD"
    elif width_mm > 1200:
        classification = "GAP_WIDER_THAN_SINGLE_DOOR_PREVIEW_RANGE"
    else:
        classification = "GAP_WIDTH_CONSISTENT_WITH_DOOR_PREVIEW_RANGE"
    return {
        "orientation": gap["orientation"],
        "band_axis_drawing_units": gap["band_axis_drawing_units"],
        "centre_drawing_units": gap["centre_drawing_units"],
        "span_drawing_units": gap["span_drawing_units"],
        "width_mm": width_mm,
        "wall_segments_drawing_units": [
            gap["left_wall_segment_drawing_units"],
            gap["right_wall_segment_drawing_units"],
        ],
        "classification": classification,
    }


def _in_bbox(centre, bbox, margin=2.0):
    return (
        bbox[0] - margin <= centre[0] <= bbox[2] + margin
        and bbox[1] - margin <= centre[1] <= bbox[3] + margin
    )


def main() -> None:
    drawing = reconstruct_test01_room_candidates(PROJECT)
    payload = {"method": "SOURCE_PDF_VECTOR_DOOR_INVENTORY_AUDIT", "documents": []}
    for floor, filename in FLOORS:
        scale = float(next(
            s.scale_m_per_drawing_unit for s in drawing.scale_candidates
            if s.frame.frame_id.startswith(floor)
        )) * 1000
        pdf_path = PROJECT / "engineering" / "source_documents" / filename
        with pymupdf.open(str(pdf_path)) as document:
            rects = _thin_rectangles(document[0])
        detected = _door_candidates(rects)
        horizontal, vertical = _wall_bands(rects)
        gaps = _wall_line_gaps(horizontal, "HORIZONTAL") + _wall_line_gaps(vertical, "VERTICAL")
        with pymupdf.open(str(pdf_path)) as page_document:
            stroked_horizontal, stroked_vertical = _line_segments(page_document[0])
        stroked_gaps = (
            _gaps_from_lines(stroked_horizontal, "HORIZONTAL")
            + _gaps_from_lines(stroked_vertical, "VERTICAL")
        )

        rows = []
        for room_id, label, points in _room_rows(drawing, floor):
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            bbox = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
            own = [gap for gap in gaps if _in_bbox(gap["centre_drawing_units"], bbox)]
            own_evidence = [_gap_evidence(gap, scale) for gap in own]
            # The canonical symbols are filtered by the room bounding box in the
            # gap direction only; a wide opening is visible from both sides.
            symbol_matches = []
            for cand in detected:
                if cand[0] == "HORIZONTAL":
                    hit = (
                        bbox[0] - 2 <= cand[3] <= bbox[2] + 2
                        or bbox[0] - 2 <= cand[4] <= bbox[2] + 2
                    )
                else:
                    hit = (
                        bbox[1] - 2 <= cand[3] <= bbox[3] + 2
                        or bbox[1] - 2 <= cand[4] <= bbox[3] + 2
                    )
                if hit:
                    symbol_matches.append({
                        "orientation": cand[0],
                        "axis_pair_drawing_units": [round(cand[1], 2), round(cand[2], 2)],
                        "gap_span_drawing_units": [round(cand[3], 2), round(cand[4], 2)],
                    })
            door_width_consistent = [
                item for item in own_evidence
                if item["classification"] == "GAP_WIDTH_CONSISTENT_WITH_DOOR_PREVIEW_RANGE"
            ]
            if symbol_matches:
                status = "DOOR_SYMBOL_PRESENT"
            elif door_width_consistent:
                status = "WALL_GAP_ONLY_DOOR_WIDTH_UNCONFIRMED"
            elif own:
                status = "WALL_GAP_ONLY_NO_DOOR_WIDTH"
            else:
                status = "NO_GAP_AND_NO_DOOR_SYMBOL"
            rows.append({
                "room_hypothesis_id": room_id,
                "label": label,
                "floor": floor,
                "bbox_drawing_units": bbox,
                "bbox_width_mm": int(round((bbox[2] - bbox[0]) * scale)),
                "bbox_height_mm": int(round((bbox[3] - bbox[1]) * scale)),
                "thin_wall_band_count_in_bbox": sum(
                    1 for r in horizontal + vertical
                    if bbox[0] <= (r[0] + r[2]) / 2 <= bbox[2]
                    and bbox[1] <= (r[1] + r[3]) / 2 <= bbox[3]
                ),
                "wall_gap_candidates_in_bbox": own,
                "wall_gap_candidate_count": len(own),
                "wall_gap_evidence": own_evidence,
                "wall_gap_classifications": sorted({item["classification"] for item in own_evidence}),
                "detected_door_symbol_matches": symbol_matches,
                "detected_door_symbol_count": len(symbol_matches),
                "inventory_status": status,
                "stroked_wall_gap_candidates_in_bbox": [
                    gap for gap in stroked_gaps if _in_bbox(gap["centre_drawing_units"], bbox)
                ],
                "stroked_wall_gap_evidence": [
                    _gap_evidence(gap, scale)
                    for gap in stroked_gaps if _in_bbox(gap["centre_drawing_units"], bbox)
                ],
            })
        payload["documents"].append({
            "document_id": floor,
            "source_pdf": str(pdf_path.relative_to(ROOT)),
            "scale_mm_per_drawing_unit": scale,
            "thin_wall_band_counts": {"horizontal": len(horizontal), "vertical": len(vertical)},
            "wall_line_gap_count": len(gaps),
            "canonical_detected_door_symbol_count": len(detected),
            "rooms": rows,
        })
    payload["caveat"] = (
        "Symbol matches are filtered by the room bounding box, so a wide shared "
        "opening can be counted for both rooms. This is an evidence inventory, "
        "not a door assignment."
    )
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "door_symbol_inventory_audit.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for document in payload["documents"]:
        print(document["document_id"], "rooms", len(document["rooms"]),
              "wall_line_gaps", document["wall_line_gap_count"],
              "detected_symbols", document["canonical_detected_door_symbol_count"])
        for row in document["rooms"]:
            print("   ", row["label"], row["inventory_status"],
                  "gaps", row["wall_gap_candidate_count"], "symbols", row["detected_door_symbol_count"])
    print("written", target)


if __name__ == "__main__":
    main()
