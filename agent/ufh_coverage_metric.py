"""Measure plan coverage by BODY pipe bands in a single millimetre frame."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal, ROUND_HALF_UP

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def drawing_polygon_to_local_mm(
    points: Sequence[Sequence[float]],
    origin: Sequence[float],
    scale_m_per_drawing_unit: float,
) -> list[tuple[int, int]]:
    """Put a drawing polygon into the local millimetre frame of BODY routes."""
    ox, oy = (Decimal(str(value)) for value in origin)
    factor = Decimal(str(scale_m_per_drawing_unit)) * 1000
    return [
        (
            int(((Decimal(str(x)) - ox) * factor).to_integral_value(rounding=ROUND_HALF_UP)),
            int(((Decimal(str(y)) - oy) * factor).to_integral_value(rounding=ROUND_HALF_UP)),
        )
        for x, y in points
    ]


def measure_pipe_band_coverage(
    room_boundary_mm: Sequence[Sequence[float]],
    body_routes_mm: Iterable[Sequence[Sequence[float]]],
    *,
    half_pitch_mm: float = 100.0,
) -> dict[str, float]:
    """Return BODY-only buffer coverage; inputs must share millimetre coordinates.

    This is a plan-area estimate, not a heat-output or circuit-validity gate.
    Transit routes must not be passed as ``body_routes_mm``.
    """
    try:
        room = Polygon(room_boundary_mm)
    except (TypeError, ValueError) as exc:
        raise ValueError("valid room polygon in millimetres required") from exc
    if room.is_empty or not room.is_valid or room.area <= 0:
        raise ValueError("valid room polygon in millimetres required")
    if half_pitch_mm <= 0:
        raise ValueError("half_pitch_mm must be positive")

    bands = []
    for route in body_routes_mm:
        if len(route) >= 2:
            bands.append(LineString(route).buffer(half_pitch_mm))
    covered = room.intersection(unary_union(bands)).area if bands else 0.0
    return {
        "room_area_mm2": float(room.area),
        "covered_area_mm2": float(covered),
        "uncovered_area_mm2": float(room.area - covered),
        "coverage_percent": float(100.0 * covered / room.area),
    }
