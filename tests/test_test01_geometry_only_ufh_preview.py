from pathlib import Path

from agent.test01_geometry_only_ufh_preview import build_test01_geometry_only_ufh_preview


PROJECT = Path(__file__).resolve().parents[1] / "projects/Test_01"


def test_per_room_geometry_preview_skips_faces_with_stair_exclusion_overlap(tmp_path):
    result = build_test01_geometry_only_ufh_preview(PROJECT, tmp_path)
    assert len(result.rooms) == 16
    attempted = [room for room in result.rooms if room.routing_attempted]
    skipped = [room for room in result.rooms if not room.routing_attempted]
    assert len(attempted) == 14
    assert {room.label.split(" / ")[0] for room in skipped} == {"2", "9"}
    assert all(room.routing_status == "SKIPPED_GEOMETRY_UNRESOLVED" for room in skipped)
    assert any(room.routing_status == "GENERATED" for room in attempted)
    assert sum(room.routing_status == "GENERATED" for room in attempted) == 14
    assert all(room.routing_status == "GENERATED" for room in attempted)
    assert all(room.authority == "GEOMETRY_ONLY_NON_ENGINEERING_NOT_FOR_CONSTRUCTION" for room in result.rooms)
    assert result.spacing_policy == "VISUAL_TEST_POLICY_NOT_ENGINEERING_DESIGN_INPUT"
    assert result.engineering_calculations_run is False
    assert Path(result.first_floor_preview_path).is_file()
    assert Path(result.mansard_preview_path).is_file()


def test_legacy_length_policy_is_diagnostic_and_does_not_erase_generated_geometry(tmp_path):
    result = build_test01_geometry_only_ufh_preview(PROJECT, tmp_path)
    rejected = [room for room in result.rooms
                if room.routing_status == "GENERATED" and room.legacy_policy_status == "WOULD_REJECT"]
    assert rejected
    assert all(room.route_polylines_mm and room.candidate_lengths_mm for room in rejected)


def test_small_rectangles_and_simple_orthogonal_room_use_generic_existing_engine_fallback(tmp_path):
    result = build_test01_geometry_only_ufh_preview(PROJECT, tmp_path)
    by_number = {room.label.split(" / ")[0]: room for room in result.rooms}
    for number in ("5", "6", "11", "13"):
        room = by_number[number]
        assert room.routing_status == "GENERATED"
        assert room.coverage == 1
        assert room.candidate_lengths_mm
