import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from pathlib import Path

from agent.floor_heating_coverage import solve_floor_heating_coverage
from agent.floor_heating_svg_fixture import (
    build_primary_fixture,
    build_primary_fixture_request,
)
from agent.floor_heating_svg_renderer import (
    render_floor_heating_layout,
    write_floor_heating_layout,
)


SVG = "{http://www.w3.org/2000/svg}"


class FloorHeatingSvgRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request, cls.plan, cls.bundle = build_primary_fixture()
        cls.root = ET.fromstring(cls.bundle.svg)
        cls.report = cls.bundle.report

    def element(self, element_id: str):
        for element in self.root.iter():
            if element.get("id") == element_id:
                return element
        self.fail(f"missing SVG element {element_id}")

    def test_01_exact_room_dimensions(self) -> None:
        boundary = self.element("ROOM_BOUNDARY")
        self.assertEqual(boundary.get("data-width-mm"), "7000")
        self.assertEqual(boundary.get("data-height-mm"), "3200")
        self.assertIn("7000 mm", self.bundle.svg)
        self.assertIn("3200 mm", self.bundle.svg)

    def test_02_correct_exterior_wall_identity(self) -> None:
        wall = self.element("EXTERIOR_WALL_1")
        self.assertEqual(wall.get("data-wall-reference"), "exterior-wall-south")
        self.assertEqual((wall.get("x1"), wall.get("y1"), wall.get("x2"), wall.get("y2")), ("0", "0", "7000", "0"))

    def test_03_correct_perimeter_band_depth(self) -> None:
        layer = self.element("PERIMETER_ZONE")
        band = self.element("PERIMETER_BAND_GEOMETRY")
        self.assertEqual(layer.get("data-depth-mm"), "1000")
        self.assertEqual(band.get("height"), "1000")

    def test_04_grid_is_before_every_pipe(self) -> None:
        child_ids = [child.get("id") for child in self.root if child.get("id")]
        self.assertLess(child_ids.index("REFERENCE_GRID"), child_ids.index("CIRCUIT_ROUTES"))
        self.assertEqual(self.element("REFERENCE_GRID").get("data-engineering-role"), "installation-reference-only")

    def test_05_exact_canonical_route_order_is_preserved(self) -> None:
        for index, route in enumerate(self.plan.circuit_routes, 1):
            expected = " ".join(
                [f"M {route.polyline[0].x_mm} {route.polyline[0].y_mm}"]
                + [f"L {point.x_mm} {point.y_mm}" for point in route.polyline[1:]]
            )
            self.assertEqual(self.element(f"CIRCUIT_ROUTE_{index}").get("d"), expected)
            self.assertEqual(
                self.bundle.geometry["circuits"][index - 1]["ordered_points"],
                [point.model_dump(mode="json") for point in route.polyline],
            )

    def test_06_one_visual_route_per_circuit(self) -> None:
        routes = list(self.element("CIRCUIT_ROUTES").findall(f"{SVG}path"))
        self.assertEqual(len(routes), len(self.plan.circuit_routes))
        self.assertEqual(len(routes), 2)

    def test_07_exact_collector_port_mapping(self) -> None:
        mappings = self.report["collector_port_mapping"]
        self.assertEqual(len(mappings), 2)
        for index, (mapping, route) in enumerate(zip(mappings, self.plan.circuit_routes), 1):
            self.assertEqual(mapping["route_id"], route.id)
            self.assertEqual(mapping["supply_point"], route.collector_supply_point.model_dump(mode="json"))
            self.assertEqual(mapping["return_point"], route.collector_return_point.model_dump(mode="json"))
            self.assertEqual(self.element(f"COLLECTOR_SUPPLY_PORT_{index}").get("data-route-id"), route.id)
            self.assertEqual(self.element(f"COLLECTOR_RETURN_PORT_{index}").get("data-route-id"), route.id)

    def test_08_route_continuity(self) -> None:
        for circuit in self.report["validation"]["circuits"]:
            self.assertEqual(circuit["overall_status"], "PASS")
            self.assertTrue(circuit["collector_connectivity"])

    def test_09_exactly_two_endpoints(self) -> None:
        self.assertEqual(
            [item["endpoint_count"] for item in self.report["validation"]["circuits"]],
            [2, 2],
        )

    def test_10_zero_branches(self) -> None:
        self.assertEqual([item["branch_count"] for item in self.report["validation"]["circuits"]], [0, 0])

    def test_11_zero_self_intersections(self) -> None:
        self.assertEqual([item["self_intersection_count"] for item in self.report["validation"]["circuits"]], [0, 0])

    def test_12_zero_inter_circuit_crossings(self) -> None:
        self.assertEqual(self.report["validation"]["inter_circuit_crossing_count"], 0)

    def test_13_exclusion_avoidance(self) -> None:
        self.assertEqual([item["exclusion_intersection_count"] for item in self.report["validation"]["circuits"]], [0, 0])
        self.assertEqual(
            self.report["validation"]["spacing_validation"]["clearance"]["observed_minimum_pipe_to_exclusion_mm"],
            400.0,
        )

    def test_14_room_containment(self) -> None:
        self.assertEqual([item["room_boundary_violation_count"] for item in self.report["validation"]["circuits"]], [0, 0])

    def test_15_perimeter_spacing_evidence(self) -> None:
        value = self.report["validation"]["spacing_validation"]["perimeter"]
        self.assertEqual(value["requested_spacing_mm"], 100)
        self.assertEqual(value["observed_minimum_mm"], 100.0)
        self.assertEqual(value["observed_maximum_mm"], 100.0)
        self.assertEqual(value["sample_count"], 6)
        self.assertEqual(value["status"], "PASS")

    def test_16_field_spacing_evidence(self) -> None:
        value = self.report["validation"]["spacing_validation"]["field"]
        self.assertEqual(value["requested_spacing_mm"], 200)
        self.assertEqual(value["observed_minimum_mm"], 200.0)
        self.assertEqual(value["observed_maximum_mm"], 200.0)
        self.assertEqual(value["sample_count"], 18)
        self.assertEqual(value["status"], "PASS")

    def test_17_spacing_transition_is_connected(self) -> None:
        value = self.report["validation"]["spacing_validation"]["transition"]
        self.assertGreater(value["sample_count"], 0)
        self.assertTrue(value["connected"])
        self.assertEqual(value["status"], "PASS")

    def test_18_route_length_equals_svg_geometry(self) -> None:
        for circuit in self.report["validation"]["circuits"]:
            self.assertLessEqual(circuit["length_delta_mm"], 1.0)
            self.assertEqual(circuit["actual_length_mm"], circuit["geometry_length_mm"])

    def test_19_circuit_lengths_are_40_to_80_metres(self) -> None:
        self.assertEqual([route.length_mm for route in self.plan.circuit_routes], [41700, 41700])
        self.assertTrue(all(40000 <= route.length_mm <= 80000 for route in self.plan.circuit_routes))

    def test_20_identical_input_is_byte_deterministic(self) -> None:
        _, _, second = build_primary_fixture()
        self.assertEqual(self.bundle.geometry_digest, second.geometry_digest)
        self.assertEqual(self.bundle.svg, second.svg)
        self.assertEqual(self.bundle.html, second.html)
        self.assertEqual(self.bundle.report, second.report)

    def test_21_meaningful_geometry_change_changes_digest_and_svg(self) -> None:
        payload = build_primary_fixture_request().model_dump(mode="json")
        payload["exclusion_zones"][0]["points"] = [
            {"x_mm": 1201, "y_mm": 800}, {"x_mm": 1401, "y_mm": 800},
            {"x_mm": 1401, "y_mm": 840}, {"x_mm": 1201, "y_mm": 840},
            {"x_mm": 1201, "y_mm": 800},
        ]
        changed_request = type(self.request).model_validate(payload)
        changed_plan = solve_floor_heating_coverage(changed_request)
        changed = render_floor_heating_layout(changed_request, changed_plan)
        self.assertEqual(changed.verdict, "TWO_D_SVG_LAYOUT_READY_FOR_VISUAL_REVIEW")
        self.assertNotEqual(self.bundle.geometry_digest, changed.geometry_digest)
        self.assertNotEqual(self.bundle.svg, changed.svg)

    def test_22_invalid_route_generates_rework_evidence(self) -> None:
        route = self.plan.circuit_routes[0]
        invalid_validation = route.validation.model_copy(update={"valid": False, "connected": False})
        invalid_route = route.model_copy(update={"validation": invalid_validation})
        invalid_plan = self.plan.model_copy(update={
            "circuit_routes": [invalid_route, self.plan.circuit_routes[1]],
        })
        value = render_floor_heating_layout(self.request, invalid_plan)
        self.assertEqual(value.verdict, "REWORK_ROUTING_GEOMETRY")
        self.assertEqual(ET.fromstring(value.svg).get("data-status"), "REWORK")
        self.assertTrue(value.report["failures"])

    def test_23_renderer_never_modifies_source_route(self) -> None:
        before = self.plan.model_dump(mode="json")
        render_floor_heating_layout(self.request, self.plan)
        self.assertEqual(before, self.plan.model_dump(mode="json"))

    def test_24_coverage_status_is_honest(self) -> None:
        coverage = self.report["coverage"]
        self.assertEqual(coverage["status"], "partial")
        self.assertFalse(coverage["full_coverage_claimed"])
        self.assertFalse(coverage["unresolved_region_geometry_available"])
        self.assertEqual(coverage["unresolved_region_polygon_count"], 0)
        self.assertIn('data-full-coverage-claimed="false"', self.bundle.svg)

    def test_25_html_layer_ids_correspond_to_svg_elements(self) -> None:
        layer_ids = set(re.findall(r'data-layer="([A-Z0-9_]+)"', self.bundle.html))
        self.assertTrue(layer_ids)
        svg_ids = {element.get("id") for element in self.root.iter() if element.get("id")}
        self.assertTrue(layer_ids <= svg_ids)
        for feature in ("zoom-in", "zoom-out", "fit", "pipes-only", "debug"):
            self.assertIn(f'id="{feature}"', self.bundle.html)

    def test_26_output_package_is_complete_and_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "HA-FH-VIS-001-v1"
            paths = write_floor_heating_layout(self.bundle, output)
            self.assertEqual(set(paths), {"svg", "html", "report", "geometry"})
            self.assertTrue(all(path.is_file() for path in paths.values()))
            self.assertEqual(json.loads(paths["report"].read_text(encoding="utf-8"))["geometry_digest"], self.bundle.geometry_digest)
            with self.assertRaises(FileExistsError):
                write_floor_heating_layout(self.bundle, output)


if __name__ == "__main__":
    unittest.main()
