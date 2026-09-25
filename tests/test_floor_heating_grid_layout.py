import hashlib
import json
import re
import struct
import unittest
import xml.etree.ElementTree as ET

from pathlib import Path

from agent.floor_heating_grid_layout import build_grid_first_layout
from agent.floor_heating_grid_svg import LAYER_IDS, render_grid_layout


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "projects" / "Test_01" / "exports" / "floor_heating_svg" / "HA-FH-VIS-003"


class FloorHeatingGridLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.layout = build_grid_first_layout()
        cls.rendered = render_grid_layout(cls.layout)
        cls.svg = ET.fromstring(cls.rendered["svg"])

    def element(self, element_id: str):
        for value in self.svg.iter():
            if value.get("id") == element_id:
                return value
        self.fail(f"missing SVG element {element_id}")

    def test_grid_is_primary_and_all_coordinates_are_grid_derived(self) -> None:
        grid = self.layout["grid"]
        self.assertEqual((grid["origin_x_mm"], grid["origin_y_mm"], grid["cell_size_mm"]), (0, 0, 100))
        for circuit in self.layout["circuits"]:
            for point in circuit["ordered_points"]:
                self.assertEqual((point["x_mm"] % 100, point["y_mm"] % 100), (0, 0))
        self.assertTrue(self.layout["global_validation"]["all_routes_grid_generated"])
        self.assertFalse(self.layout["global_validation"]["post_generation_snapping_used"])

    def test_wall_types_are_explicit_and_only_south_is_exterior(self) -> None:
        self.assertEqual(
            {wall["wall_id"]: wall["wall_type"] for wall in self.layout["walls"]},
            {"SOUTH": "EXTERIOR_WALL", "NORTH": "INTERIOR_WALL", "WEST": "INTERIOR_WALL", "EAST": "INTERIOR_WALL"},
        )

    def test_exactly_three_south_passes_and_no_fixed_300_rule(self) -> None:
        spacing = self.layout["spacing_validation"]
        self.assertEqual(spacing["south_exterior_pass_count_per_territory"], 3)
        self.assertFalse(spacing["fixed_300_mm_wall_offset_rule_used"])
        for circuit in spacing["circuits"]:
            self.assertEqual(circuit["south_exterior_pass_lines_y_mm"], [100, 200, 300])
            self.assertEqual(circuit["south_adjacent_spacings_mm"], [100, 100])

    def test_interior_walls_and_field_remain_at_200(self) -> None:
        spacing = self.layout["spacing_validation"]
        self.assertFalse(spacing["interior_wall_three_pass_treatment"])
        for circuit in spacing["circuits"]:
            for key, values in circuit.items():
                if key.endswith("spacings_mm") and key != "south_adjacent_spacings_mm":
                    self.assertTrue(values)
                    self.assertEqual(set(values), {200})

    def test_no_exclusion_and_no_no_lay_zone(self) -> None:
        self.assertEqual(self.layout["room"]["exclusion_zones"], [])
        self.assertEqual(self.layout["room"]["no_lay_zones"], [])
        self.assertNotIn("NO-LAY", self.rendered["svg"])

    def test_wall_collector_is_outside_and_has_four_distinct_legs(self) -> None:
        collector = self.layout["collector"]
        self.assertTrue(collector["body_outside_useful_floor"])
        self.assertFalse(collector["reduces_useful_floor_area"])
        self.assertEqual(collector["distinct_transit_leg_count"], 4)
        self.assertEqual(collector["transit_crossing_count"], 0)
        self.assertEqual(collector["shared_transit_segment_count"], 0)
        self.assertEqual(len({(port["point"]["x_mm"], port["point"]["y_mm"]) for port in collector["ports"]}), 4)

    def test_exactly_two_independent_routes_with_unique_port_ownership(self) -> None:
        self.assertEqual(len(self.layout["circuits"]), 2)
        self.assertEqual({route["supply_port_id"] for route in self.layout["circuits"]}, {"C1-SUPPLY", "C2-SUPPLY"})
        self.assertEqual({route["return_port_id"] for route in self.layout["circuits"]}, {"C1-RETURN", "C2-RETURN"})

    def test_topology_is_exhaustively_valid(self) -> None:
        for route in self.layout["circuits"]:
            validation = route["validation"]
            self.assertEqual(validation["canonical_route_count"], 1)
            self.assertEqual(validation["connected_components"], 1)
            self.assertEqual(validation["endpoint_count"], 2)
            self.assertEqual(validation["branch_count"], 0)
            self.assertEqual(validation["self_intersection_count"], 0)
            self.assertEqual(validation["non_adjacent_overlap_count"], 0)
            self.assertEqual(validation["duplicate_consecutive_point_count"], 0)
            self.assertEqual(validation["zero_length_segment_count"], 0)
            self.assertEqual(validation["room_boundary_violation_count"], 0)
            self.assertTrue(validation["valid"])
        self.assertEqual(self.layout["global_validation"]["inter_circuit_crossing_count"], 0)
        self.assertEqual(self.layout["global_validation"]["inter_circuit_shared_segment_count"], 0)

    def test_centre_100_is_only_formally_classified_exception(self) -> None:
        for route in self.layout["circuits"]:
            self.assertEqual(route["centre_turn"]["classification"], "CENTER_TURN_100")
            classified = [segment for segment in route["ordered_segments"] if segment["spacing_classification"] == "CENTER_TURN_100"]
            self.assertEqual(len(classified), 3)
            self.assertEqual([segment["nominal_spacing_mm"] for segment in classified], [100, 100, 100])

    def test_length_is_actual_balanced_and_within_limits(self) -> None:
        self.assertEqual([route["total_length_mm"] for route in self.layout["circuits"]], [59700, 59700])
        for route in self.layout["circuits"]:
            self.assertEqual(route["heating_path_length_mm"], sum(segment["length_mm"] for segment in route["ordered_segments"]))
            self.assertTrue(40000 <= route["total_length_mm"] <= 80000)
        self.assertEqual({value["difference_mm"] for value in self.rendered["report"]["length_reconciliation"]}, {0})

    def test_partition_is_deterministic_and_not_an_exclusion(self) -> None:
        partition = self.layout["partition"]
        self.assertEqual(partition["winner_x_mm"], 3500)
        self.assertFalse(partition["physical_exclusion"])
        self.assertEqual(partition["candidates"][1]["status"], "SELECTED")
        self.assertEqual(self.layout["spacing_validation"]["partition_nearest_pipe_spacing_mm"], 200)

    def test_coverage_is_geometric_and_honest(self) -> None:
        coverage = self.layout["coverage"]
        self.assertGreater(coverage["coverage_ratio"], 0.95)
        self.assertGreater(coverage["unresolved_area_mm2"], 0)
        self.assertTrue(coverage["unresolved_regions"])
        self.assertFalse(coverage["full_coverage_claimed"])
        self.assertFalse(coverage["thermal_sufficiency_claimed"])
        self.assertFalse(coverage["normative_compliance_claimed"])

    def test_svg_preserves_exact_route_order_and_semantic_layers(self) -> None:
        child_ids = [child.get("id") for child in self.svg if child.get("id")]
        engineering = self.element("ENGINEERING_GEOMETRY")
        engineering_ids = [child.get("id") for child in engineering if child.get("id")]
        self.assertLess(engineering_ids.index("GRID"), engineering_ids.index("CIRCUIT_1"))
        for route in self.layout["circuits"]:
            expected = " ".join(
                [f'M {route["ordered_points"][0]["x_mm"]} {route["ordered_points"][0]["y_mm"]}']
                + [f'L {point["x_mm"]} {point["y_mm"]}' for point in route["ordered_points"][1:]]
            )
            self.assertEqual(self.element(f'ROUTE_{route["circuit_id"]}').get("d"), expected)
        for layer in LAYER_IDS:
            self.element(layer)
        self.assertIn("DIAGNOSTICS", child_ids)

    def test_html_has_matching_layer_controls_and_no_recalculation(self) -> None:
        controls = set(re.findall(r'data-layer="([A-Z0-9_]+)"', self.rendered["html"]))
        self.assertEqual(controls, set(LAYER_IDS))
        self.assertNotIn("ordered_points", self.rendered["html"])

    def test_identical_input_is_byte_deterministic(self) -> None:
        second_layout = build_grid_first_layout()
        second_rendered = render_grid_layout(second_layout)
        self.assertEqual(self.layout, second_layout)
        self.assertEqual(self.rendered, second_rendered)

    def test_equivalent_shifted_grid_origin_is_deterministic_and_recorded(self) -> None:
        first = build_grid_first_layout(grid_origin_x_mm=100)
        second = build_grid_first_layout(grid_origin_x_mm=100)
        self.assertEqual(first, second)
        self.assertNotEqual(first["geometry_digest"], self.layout["geometry_digest"])
        self.assertEqual(first["grid"]["origin_x_mm"], 100)
        with self.assertRaisesRegex(ValueError, "congruent"):
            build_grid_first_layout(grid_origin_x_mm=50)

    def test_renderer_does_not_modify_source(self) -> None:
        before = json.dumps(self.layout, sort_keys=True)
        render_grid_layout(self.layout)
        self.assertEqual(json.dumps(self.layout, sort_keys=True), before)

    def test_no_autocad_or_provider_path_is_present(self) -> None:
        text = json.dumps(self.layout) + self.rendered["svg"] + self.rendered["html"]
        for forbidden in ("DWG", "DXF", "MagiCAD", "NETLOAD", "TokenLedger", "OPENAI_API_KEY"):
            self.assertNotIn(forbidden, text)

    def test_published_append_only_package_has_exact_png_provenance(self) -> None:
        manifest = json.loads((PUBLISHED / "artifact_manifest.json").read_text(encoding="utf-8"))
        provenance = json.loads((PUBLISHED / "capture_provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["geometry_digest"], self.layout["geometry_digest"])
        self.assertEqual(manifest["verdict"], "TWO_SPIRAL_GRID_LAYOUT_READY_FOR_VISUAL_REVIEW")
        svg_hash = hashlib.sha256((PUBLISHED / "floor_heating_layout.svg").read_bytes()).hexdigest()
        self.assertEqual(provenance["source_svg_sha256"], svg_hash)
        self.assertFalse(provenance["canonical_coordinate_modification"])
        self.assertEqual(len(provenance["captures"]), 9)
        for capture in provenance["captures"]:
            data = (PUBLISHED / capture["name"]).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (capture["output_width_px"], capture["output_height_px"]))
            self.assertEqual(hashlib.sha256(data).hexdigest(), capture["png_sha256"])


if __name__ == "__main__":
    unittest.main()
