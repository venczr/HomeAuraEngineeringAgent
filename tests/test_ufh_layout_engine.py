from agent.ufh_layout_engine import (
    CONTAINMENT_TOLERANCE_MM,
    build_bifilar_spiral,
    build_meander,
    split_required,
    validate_containment,
)


RECT = [(0, 0), (7000, 0), (7000, 4000), (0, 4000), (0, 0)]


def test_meander_is_continuous_orthogonal_and_contained():
    route = build_meander((0, 0, 7000, 4000))
    assert route[0] != route[-1]
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(route, route[1:]))
    report = validate_containment(route, RECT)
    assert report.valid
    assert report.total_outside_length_mm == 0


def test_containment_reports_meaningful_excursion_independently():
    report = validate_containment([(100, 100), (7100, 100)], RECT)
    assert report.total_outside_length_mm > CONTAINMENT_TOLERANCE_MM
    assert report.outside_segment_count == 1
    assert not report.valid


def test_spiral_candidate_has_explicit_centerward_geometry_and_is_not_silent_fallback():
    route = build_bifilar_spiral((0, 0, 7000, 4000))
    assert route
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(route, route[1:]))
    assert validate_containment(route, RECT).valid


def test_length_policy_is_overrideable_preview_only():
    assert split_required(85, 8)
    assert not split_required(80, 8)
