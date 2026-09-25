"""Render the isolated room-8 upper-zone BODY experiment (not Test_01 output)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Polygon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.ufh_bend_geometry import build_rounded_centerline, validate_rounded_centerline
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral


SOURCE = ROOT / "dev/ufh_real_plan/test01_room8_staggered_zone_geometry_20260923.json"
OUT = ROOT / "dev/ufh_real_plan"
STEM = "test01_room8_top_zone_shifted_splice_preview_20260924"


def svg_polygon(points: list[list[float]]) -> str:
    return " ".join(f"{x},{y}" for x, y in points)


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    top = source["zones"]["top"]["polygon_mm"]
    bottom = source["zones"]["bottom"]["polygon_mm"]
    room = source["room_mm"]
    sharp = build_accessible_bifilar_spiral(
        (4369, 5515, 9195, 6915), 200, minimum_bend_radius_mm=80
    )
    candidate = [
        sharp[0],
        (9195, 7275),
        (6882, 7275),
        (6882, 7075),
        (9095, 7075),
        (9095, 6915),
        *sharp[2:],
    ]
    rounded = build_rounded_centerline(candidate, bend_radius_mm=80)
    report = validate_rounded_centerline(
        candidate, top, bend_radius_mm=80, pipe_outer_radius_mm=8
    )
    line = LineString(rounded.points)
    zone = Polygon(top)
    band_covered = zone.intersection(line.buffer(100)).area
    metrics = {
        "status": "ONE_ZONE_BODY_PREVIEW_ONLY",
        "source": str(SOURCE.relative_to(ROOT)),
        "boundary_status": "STRAIGHT_WALL_PREVIEW_DWG_UNVERIFIED",
        "sharp_points_mm": candidate,
        "rounded_points_mm": rounded.points,
        "terminals_mm": [candidate[0], candidate[-1]],
        "r80_valid": rounded.valid,
        "physical_validation_valid": report.valid,
        "physical_validation_diagnostics": report.diagnostics,
        "self_intersects": not line.is_simple,
        "body_length_m": rounded.length_mm / 1000,
        "sampled_line_length_m": line.length / 1000,
        "top_zone_area_m2": zone.area / 1e6,
        "pipe_band_covered_m2": band_covered / 1e6,
        "pipe_band_uncovered_m2": (zone.area - band_covered) / 1e6,
        "pipe_band_coverage_percent": 100 * band_covered / zone.area,
        "minimum_non_adjacent_clearance_mm": report.minimum_non_adjacent_clearance_mm,
        "TRANSIT_VALID": False,
        "FULL_CIRCUIT_VALID": False,
        "second_circuit_valid": False,
    }
    if not report.valid or not rounded.valid or not line.is_simple:
        raise RuntimeError(f"Invalid preview BODY: {report.diagnostics}")
    OUT.joinpath(f"{STEM}.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="4000 5150 5550 3900" width="1110" height="780">
<rect x="4000" y="5150" width="5550" height="3900" fill="#fafbfc"/>
<text x="4269" y="5300" font-size="95" fill="#222">Test_01 room 8 — upper zone BODY preview</text>
<polygon points="{svg_polygon(room)}" fill="none" stroke="#344054" stroke-width="18"/>
<polygon points="{svg_polygon(bottom)}" fill="#edf0f3" stroke="#aab4c0" stroke-width="8"/>
<polygon points="{svg_polygon(top)}" fill="#e7f3ff" stroke="#4b82ad" stroke-width="10"/>
<path d="{rounded.svg_path_data}" fill="none" stroke="#d92d20" stroke-width="26" stroke-linejoin="round" stroke-linecap="round"/>
<circle cx="{candidate[0][0]}" cy="{candidate[0][1]}" r="42" fill="#d92d20"/>
<circle cx="{candidate[-1][0]}" cy="{candidate[-1][1]}" r="42" fill="#1570ef"/>
<text x="4300" y="8940" font-size="92" fill="#222">BODY {rounded.length_mm/1000:.2f} m; pipe-band {100*band_covered/zone.area:.2f}% of upper zone</text>
<text x="4300" y="9040" font-size="80" fill="#a11212">PREVIEW — second circuit and collector transit unverified</text>
</svg>"""
    OUT.joinpath(f"{STEM}.svg").write_text(svg, encoding="utf-8")
    print(
        f"BODY={rounded.length_mm/1000:.4f} m, "
        f"coverage={100*band_covered/zone.area:.4f}%, "
        f"physical_valid={report.valid}"
    )


if __name__ == "__main__":
    main()
