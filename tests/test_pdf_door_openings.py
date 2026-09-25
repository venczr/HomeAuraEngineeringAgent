from pathlib import Path

from agent.pdf_door_openings import extract_pdf_door_openings
from agent.test01_drawing_understanding import reconstruct_test01_room_candidates


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "Test_01"


def _rooms(drawing, floor):
    return [
        (
            room.room_hypothesis_id,
            [
                (float(point.x), float(point.y))
                for point in next(h for h in drawing.understanding.hypotheses if h.hypothesis_id == room.room_hypothesis_id).geometry.points
            ],
        )
        for room in drawing.building_rooms
        if room.floor_source_id == floor
    ]


def test_source_pdf_door_pattern_finds_room_12_openings():
    drawing = reconstruct_test01_room_candidates(PROJECT)
    scale = float(next(s.scale_m_per_drawing_unit for s in drawing.scale_candidates if s.frame.frame_id.startswith("ATTIC_PLAN"))) * 1000
    doors = extract_pdf_door_openings(
        PROJECT / "engineering/source_documents/Test_01_attic_plan.pdf",
        "ATTIC_PLAN",
        scale_mm_per_drawing_unit=scale,
        rooms=_rooms(drawing, "ATTIC_PLAN"),
    )
    room12 = [d for d in doors if "ATTIC_PLAN:3d760ac099594432:ROOM" in d.adjacent_room_ids]
    assert len(room12) >= 2
    assert any(d.width_mm == 895 and "DOOR_LEAF_VECTOR" in d.vector_evidence for d in room12)
    assert all(d.manifold_connected == "UNVERIFIED" for d in room12)


def test_wall_gap_without_jamb_and_leaf_is_not_promoted():
    # A bare gap is deliberately insufficient evidence for a passage.
    from agent.pdf_door_openings import _door_candidates

    assert _door_candidates(((0, 0, 100, 1), (0, 6, 40, 7))) == []
