import unittest

from agent.ufh_routing_preview import (
    UfhRoutingPreviewRequest,
    generate_ufh_routing_preview,
    plan_ufh_circuits,
    render_ufh_routing_preview_svg,
    decompose_coverage_cells,
)


def p(x, y):
    return {"x_mm": x, "y_mm": y}


def poly(points):
    return {"points": [p(x, y) for x, y in points]}


def request(**overrides):
    value = {
        "project_id": "preview-project",
        "room_id": "room-1",
        "room_polygon": poly([(0, 0), (7000, 0), (7000, 3200), (0, 3200), (0, 0)]),
        "manifold_point": p(3500, 1100),
        "spacing_mm": 200,
        "wall_offset_mm": 100,
        "minimum_bend_radius_mm": 100,
        "maximum_preview_length_mm": 80000,
    }
    value.update(overrides)
    return UfhRoutingPreviewRequest.model_validate(value)


class UfhRoutingPreviewTests(unittest.TestCase):
    def test_rectangle_is_continuous_and_deterministic(self):
        first = generate_ufh_routing_preview(request())
        second = generate_ufh_routing_preview(request())
        self.assertEqual(first.status, "GEOMETRY_ONLY_UFH_ROUTING_CANDIDATE")
        self.assertGreater(len(first.pipe_centerline), 2)
        self.assertEqual(first.pipe_centerline, second.pipe_centerline)
        self.assertEqual(first.result_digest, second.result_digest)
        self.assertFalse(first.self_intersection)

    def test_exclusion_is_preserved(self):
        result = generate_ufh_routing_preview(request(exclusion_zones=[poly([
            (3000, 2050), (3200, 2050), (3200, 2090), (3000, 2090), (3000, 2050)
        ])]))
        self.assertEqual(result.exclusion_zones[0].points[0].x_mm, 3000)
        self.assertEqual(result.authority_status, "GEOMETRY_ONLY_NON_AUTHORITATIVE")

    def test_unverified_scale_never_becomes_engineering_authorized(self):
        result = generate_ufh_routing_preview(request(scale_status="UNVERIFIED"))
        self.assertIn("SCALE_UNVERIFIED_GEOMETRY_ONLY", result.diagnostics)
        self.assertEqual(result.authority_status, "GEOMETRY_ONLY_NON_AUTHORITATIVE")

    def test_narrow_geometry_fails_closed(self):
        result = generate_ufh_routing_preview(request(
            room_polygon=poly([(0, 0), (300, 0), (300, 300), (0, 300), (0, 0)]),
            manifold_point=p(150, 150),
            spacing_mm=200,
            wall_offset_mm=100,
        ))
        self.assertEqual(result.status, "IMPOSSIBLE")
        self.assertEqual(result.pipe_centerline, [])

    def test_maximum_length_is_reported(self):
        result = generate_ufh_routing_preview(request(maximum_preview_length_mm=1000))
        self.assertEqual(result.status, "IMPOSSIBLE")
        self.assertTrue(result.diagnostics)

    def test_l_shape_is_routed_or_fails_closed(self):
        result = generate_ufh_routing_preview(request(
            room_polygon=poly([(0, 0), (4000, 0), (4000, 2000), (2000, 2000),
                                (2000, 4000), (0, 4000), (0, 0)]),
            manifold_point=p(500, 500),
        ))
        self.assertIn(result.status, {"IMPOSSIBLE", "GEOMETRY_ONLY_UFH_ROUTING_CANDIDATE"})
        if result.status == "IMPOSSIBLE":
            self.assertTrue(result.diagnostics)
        else:
            self.assertGreater(len(result.pipe_centerline), 2)

    def test_horizontal_and_vertical_are_real_sweeps(self):
        horizontal = generate_ufh_routing_preview(request(orientation="horizontal"))
        vertical = generate_ufh_routing_preview(request(orientation="vertical"))
        self.assertNotEqual(horizontal.pipe_centerline, vertical.pipe_centerline)
        self.assertIn("XY_SWAP_ROUTING_FRAME", vertical.transformation_metadata)

    def test_auto_orientation_exposes_deterministic_candidates(self):
        first = generate_ufh_routing_preview(request(orientation="auto"))
        second = generate_ufh_routing_preview(request(orientation="auto"))
        self.assertEqual(first.result_digest, second.result_digest)
        self.assertEqual({item.orientation for item in first.candidate_orientations}, {"horizontal", "vertical"})
        self.assertTrue(first.selection_reason)

    def test_transit_is_separate_from_coverage(self):
        result = generate_ufh_routing_preview(request(orientation="horizontal"))
        self.assertGreaterEqual(result.supply_transit_length_mm, 0)
        self.assertGreaterEqual(result.return_transit_length_mm, 0)
        self.assertEqual(
            result.estimated_pipe_length_mm,
            result.supply_transit_length_mm + result.coverage_length_mm + result.return_transit_length_mm,
        )

    def test_split_foundation_creates_independent_circuits(self):
        plan = plan_ufh_circuits(request(maximum_preview_length_mm=45000))
        self.assertEqual(plan.status, "PLANNED")
        self.assertEqual(plan.circuit_count, 3)
        self.assertTrue(all(item.status != "IMPOSSIBLE" for item in plan.circuits))
        self.assertTrue(all(length <= 45000 for length in plan.circuit_lengths_mm))

    def test_svg_preview_is_deterministic(self):
        result = generate_ufh_routing_preview(request())
        svg = render_ufh_routing_preview_svg(result)
        self.assertEqual(svg, render_ufh_routing_preview_svg(result))
        self.assertIn('data-layer="coverage-route"', svg)
        self.assertIn('data-layer="supply-transit"', svg)
        self.assertIn('data-layer="return-transit"', svg)
        self.assertIn(f'data-circuit-id="{result.route_id}"', svg)

    def test_svg_route_elements_match_result(self):
        result = generate_ufh_routing_preview(request())
        svg = render_ufh_routing_preview_svg(result)
        self.assertEqual(svg.count('data-layer="coverage-route"'), 1)
        self.assertIn("TOTAL_LENGTH_M=", svg)
        self.assertIn("COVERAGE_LENGTH_M=", svg)

    def test_concave_scan_fallback_and_cells_are_deterministic(self):
        shape = poly([(0, 0), (6000, 0), (6000, 5000), (4000, 5000),
                      (4000, 2000), (2000, 2000), (2000, 5000), (0, 5000), (0, 0)])
        value = request(room_polygon=shape, manifold_point=p(1000, 1000), orientation="horizontal")
        cells = decompose_coverage_cells(value)
        self.assertEqual([c.cell_id for c in cells], [c.cell_id for c in decompose_coverage_cells(value)])
        result = generate_ufh_routing_preview(value)
        self.assertIn(result.status, {"GEOMETRY_ONLY_UFH_ROUTING_CANDIDATE", "IMPOSSIBLE"})
        if result.status != "IMPOSSIBLE":
            self.assertFalse(result.self_intersection)


if __name__ == "__main__":
    unittest.main()
