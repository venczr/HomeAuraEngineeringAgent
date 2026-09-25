import pytest

from agent.ufh_coverage_metric import drawing_polygon_to_local_mm, measure_pipe_band_coverage


def test_pipe_coverage_uses_room_mm_and_union_of_body_bands():
    room = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    route = [(0, 500), (1000, 500)]
    single = measure_pipe_band_coverage(room, [route], half_pitch_mm=100)
    duplicated = measure_pipe_band_coverage(room, [route, route], half_pitch_mm=100)

    assert single["room_area_mm2"] == 1_000_000
    assert single["covered_area_mm2"] == pytest.approx(200_000)
    assert single["coverage_percent"] == pytest.approx(20)
    assert duplicated == single


def test_pipe_coverage_rejects_invalid_room_geometry():
    with pytest.raises(ValueError, match="valid room polygon"):
        measure_pipe_band_coverage([(0, 0), (1, 1)], [[(0, 0), (1, 1)]])


def test_drawing_boundary_is_converted_before_intersecting_mm_routes():
    drawing_room = [(10, 20), (20, 20), (20, 30), (10, 30)]
    room_mm = drawing_polygon_to_local_mm(drawing_room, origin=(10, 20), scale_m_per_drawing_unit=0.1)
    assert room_mm == [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    result = measure_pipe_band_coverage(room_mm, [[(0, 500), (1000, 500)]], half_pitch_mm=100)
    assert result["coverage_percent"] == pytest.approx(20)
