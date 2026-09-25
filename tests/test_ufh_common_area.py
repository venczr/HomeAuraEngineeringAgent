from agent.ufh_common_area import build_common_corridor_area


def test_corridor_keeps_area_outside_first_three_stair_contact_zone_usable():
    result = build_common_corridor_area(
        [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
        stair_contact_zone_mm=[[400, 0], [600, 0], [600, 300], [400, 300]],
    )
    assert result["status"].startswith("PARTIAL_GEOMETRY")
    assert result["stair_contact_label"] == "FIRST_THREE_STAIR_TREADS_CONTACT_FLOOR"
    assert result["useful_heatable_area_mm2"] == 940000.0
    assert "REMAINING_CORRIDOR_AREA_AVAILABLE_FOR_LAYOUT" in result["diagnostics"]
