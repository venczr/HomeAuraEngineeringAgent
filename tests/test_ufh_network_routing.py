from __future__ import annotations

from agent.ufh_network_routing import alternative_routes, build_building_graph


def _graph():
    edges = [
        ("C", "A", {"length": 2, "segment": "E"}),
        ("C", "W", {"length": 5, "segment": "W"}),
        ("A", "B", {"length": 6, "segment": "M"}),
        ("A", "W", {"length": 7, "segment": "X"}),
        ("A", "R1e", {"length": 3, "door": "D1e"}),
        ("W", "R1w", {"length": 6, "door": "D1w"}),
        ("B", "R2", {"length": 2, "door": "D2"}),
        ("B", "R3e", {"length": 4, "door": "D3e"}),
        ("W", "R3w", {"length": 10, "door": "D3w"}),
    ]
    return build_building_graph(edges)


def test_alternative_routes_find_two_paths_through_cycle() -> None:
    graph = _graph()
    routes = alternative_routes(graph, "C", "R1e", k=2)
    assert len(routes) == 2
    assert routes[0].estimated_length_m == 5.0
    assert routes[0].segments == ("E",)
    assert routes[1].estimated_length_m == 15.0
    assert set(routes[1].segments) == {"W", "X"}
    assert all(r.transition_status == "UNVERIFIED" for r in routes)


def test_alternative_routes_do_not_cross_solid_walls() -> None:
    graph = _graph()
    # R2 has no direct edge to W: the only routes go through M (the real corridor).
    routes = alternative_routes(graph, "C", "R2", k=4)
    for route in routes:
        assert "M" in route.segments


def test_supply_and_return_routes_can_differ() -> None:
    graph = _graph()
    supply = alternative_routes(graph, "C", "R1e", k=1)[0]
    ret = alternative_routes(graph, "C", "R1w", k=1)[0]
    # supply enters via the east door, return leaves via the west door
    assert supply.doors == ("D1e",)
    assert ret.doors == ("D1w",)
    assert supply.segments != ret.segments
