from agent.ufh_endpoint_access import check_endpoint_access, review_zone_route_endpoints


def rect(w=1000, h=1000):
    return [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]


def test_endpoint_reaches_own_room_boundary_without_authorizing_opening():
    result = check_endpoint_access((100, 100), rect())
    assert result.status == "ROOM_BOUNDARY_REACHABLE"
    assert result.distance_mm == 100
    assert result.obstacle_clear


def test_endpoint_access_rejects_obstacle_on_exit_path():
    obstacle = [(0, 0), (150, 0), (150, 150), (0, 150), (0, 0)]
    result = check_endpoint_access((100, 100), rect(), obstacles=[obstacle])
    assert result.status == "NO_GEOMETRIC_EXIT_PATH"
    assert "EXIT_PATH_CROSSES_OBSTACLE" in result.diagnostics


def test_zone_review_keeps_opening_and_manifold_unverified():
    route = [(100, 100), (900, 100), (900, 900)]
    result = review_zone_route_endpoints(route, rect())
    assert result["endpoint_access_state"] == "VALID"
    assert result["opening_authority"] == "UNVERIFIED_NO_AUTHORIZED_OPENING"
    assert result["manifold_connected"] == "UNVERIFIED"
