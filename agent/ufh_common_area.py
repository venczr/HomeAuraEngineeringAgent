"""Shared corridor/stair area model for Test_01.

The source room polygon remains authoritative.  The first three stair treads
are represented as a separately identified contact zone; the remaining area of
the observed corridor polygon is available for UFH coverage and transit
candidate searches.  No staircase void is invented and no transit crossing is
authorized by this metadata alone.
"""
from __future__ import annotations

from shapely.geometry import Polygon


def build_common_corridor_area(
    room_boundary_mm: list[list[int]] | list[tuple[int, int]],
    *,
    stair_contact_zone_mm: list[list[int]] | list[tuple[int, int]],
    additional_useful_zones_mm: list[list[list[int]] | list[tuple[int, int]]] | None = None,
    stair_contact_label: str = "FIRST_THREE_STAIR_TREADS_CONTACT_FLOOR",
) -> dict[str, object]:
    room = Polygon(room_boundary_mm)
    contact = Polygon(stair_contact_zone_mm)
    additions = [Polygon(zone) for zone in (additional_useful_zones_mm or [])]
    if room.is_empty or not room.is_valid or contact.is_empty or not contact.is_valid:
        return {"status": "GEOMETRY_UNVERIFIED", "usable_area_mm2": 0.0, "diagnostics": ["INVALID_COMMON_AREA_GEOMETRY"]}
    recovered = room
    for zone in additions:
        if zone.is_valid and not zone.is_empty:
            recovered = recovered.union(zone)
    contact_inside = recovered.intersection(contact)
    useful = recovered.difference(contact_inside)
    if useful.geom_type != "Polygon":
        useful_for_export = max(getattr(useful, "geoms", [useful]), key=lambda g: g.area)
    else:
        useful_for_export = useful
    if contact_inside.geom_type != "Polygon":
        contact_for_export = max(getattr(contact_inside, "geoms", [contact_inside]), key=lambda g: g.area)
    else:
        contact_for_export = contact_inside
    return {
        "status": "PARTIAL_GEOMETRY_SOURCE_BOUNDARY_WITH_USER_CLARIFICATION",
        "source_boundary_mm": [[int(round(x)), int(round(y))] for x, y in room.exterior.coords],
        "recovered_source_zones_mm": [[[int(round(x)), int(round(y))] for x, y in zone.exterior.coords] for zone in additions if zone.is_valid and not zone.is_empty],
        "reconstructed_corridor_boundary_mm": [[int(round(x)), int(round(y))] for x, y in recovered.exterior.coords] if recovered.geom_type == "Polygon" else [],
        "source_boundary_area_mm2": round(float(room.area), 3),
        "reconstructed_corridor_area_mm2": round(float(recovered.area), 3),
        "stair_contact_zone_mm": [[int(round(x)), int(round(y))] for x, y in contact_for_export.exterior.coords] if not contact_for_export.is_empty else [],
        "stair_contact_label": stair_contact_label,
        "stair_contact_geometry_status": "SOURCE_PDF_VECTOR_PLUS_USER_CLARIFICATION",
        "useful_heatable_area_mm2": round(float(useful.area), 3),
        "useful_area_mm": [[int(round(x)), int(round(y))] for x, y in useful_for_export.exterior.coords] if not useful_for_export.is_empty else [],
        "useful_area_geometry_mm": {
            "outer_mm": [[int(round(x)), int(round(y))] for x, y in useful_for_export.exterior.coords] if not useful_for_export.is_empty else [],
            "holes_mm": [[[int(round(x)), int(round(y))] for x, y in ring.coords] for ring in getattr(useful_for_export, "interiors", [])],
        },
        "transit_crossing_status": "UNVERIFIED",
        "diagnostics": [
            ("SIX_STAIR_TREADS_EXCLUDED_FROM_UFH" if "SIX" in stair_contact_label else "FIRST_THREE_STAIR_TREADS_EXCLUDED_FROM_UFH"),
            "REMAINING_CORRIDOR_AREA_AVAILABLE_FOR_LAYOUT",
            "STAIR_TRANSIT_PATH_REQUIRES_CLEARANCE_CHECK",
        ],
    }


__all__ = ["build_common_corridor_area"]
