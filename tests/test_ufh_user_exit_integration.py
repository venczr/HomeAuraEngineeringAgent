import json
from pathlib import Path

from agent.ufh_strategy_selector import select_layout


def test_user_selected_exit_is_geometry_preference_and_never_manifold_authority():
    project = json.loads((Path(__file__).parents[1] / "homeaura-editor/public/plans/test01-project.json").read_text(encoding="utf-8"))
    room = next(room for room in project["rooms"] if room["label"].startswith("3 /"))
    boundary = [tuple(point) for point in room["global_boundary_mm"]]
    result = select_layout(
        boundary,
        mode="AUTO",
        maximum_circuit_length_mm=90_000,
        spacing_mm=200,
        wall_offset_mm=100,
        bend_radius_mm=80,
        maximum_zones=3,
        preferred_exit_mm=tuple(boundary[0]),
    )
    assert result["strategy"] == "MULTI_BIFILAR_SPIRAL"
    assert len(result["routes"]) == 2
    assert all(route["MANIFOLD_CONNECTED"] == "UNVERIFIED" for route in result["routes"])
    assert all(route["endpoint_access"]["opening_authority"] == "UNVERIFIED_NO_AUTHORIZED_OPENING" for route in result["routes"])
    assert all(route["INTERNAL_PIPE_LENGTH"] == route["rounded_geometry"]["rounded_length_mm"] for route in result["routes"])
