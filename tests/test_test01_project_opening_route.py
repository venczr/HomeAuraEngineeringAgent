"""Regression coverage for the Test_01 AUTO-layout/transit hand-off."""

from scripts.build_test01_project_opening_route import load_auto_kitchen_routes


def test_project_opening_preview_uses_current_auto_kitchen_zones():
    """Transit must not silently fall back to the obsolete two-spiral export."""
    _summary, routes = load_auto_kitchen_routes()

    assert [route["spiral_route_id"] for route in routes] == [
        "zone-3-1",
        "zone-3-2",
        "zone-3-3",
    ]
    assert [route["INTERNAL_PIPE_LENGTH"] for route in routes] == [63088.0] * 3
    assert all(route["internal_geometry_source"] == "11_KITCHEN_AUTO_ZONE_RESULT.routes" for route in routes)
    assert len({tuple(route["route_mm"][0]) for route in routes}) == 3
