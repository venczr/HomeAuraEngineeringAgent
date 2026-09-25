import json
import math
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "dev" / "ufh_real_plan"
SUPPLY = "#d92d20"
RETURN = "#1570ef"


class RealFloorUfhColorCodingTests(unittest.TestCase):
    def test_floor_and_building_previews_expose_both_flow_roles(self):
        for name in ("first_floor_ufh.svg", "mansard_ufh.svg", "building_level_ufh.svg"):
            svg = (ARTIFACTS / name).read_text(encoding="utf-8")
            ElementTree.fromstring(svg)
            self.assertIn(SUPPLY, svg, name)
            self.assertIn(RETURN, svg, name)
            self.assertIn('data-flow-role="supply"', svg, name)
            self.assertIn('data-flow-role="return"', svg, name)
            self.assertIn("SUPPLY / ПОДАЧА", svg, name)
            self.assertIn("RETURN / ОБРАТКА", svg, name)

    def test_coverage_flow_split_preserves_continuous_route(self):
        building = json.loads(
            (ARTIFACTS / "building_level_ufh.json").read_text(encoding="utf-8")
        )
        self.assertEqual(building["flow_color_policy"]["supply"], SUPPLY)
        self.assertEqual(building["flow_color_policy"]["return"], RETURN)
        self.assertEqual(building["flow_color_policy"]["svg_role_attribute"], "data-flow-role")

        def length(route):
            return sum(math.dist(route[i - 1], route[i]) for i in range(1, len(route)))

        self.assertTrue(building["circuits"])
        for circuit in building["circuits"]:
            route = circuit["coverage_route_mm"]
            supply = circuit["supply_coverage_route_mm"]
            return_route = circuit["return_coverage_route_mm"]
            self.assertEqual(supply[0], route[0], circuit["circuit_id"])
            self.assertEqual(return_route[-1], route[-1], circuit["circuit_id"])
            self.assertEqual(supply[-1], return_route[0], circuit["circuit_id"])
            self.assertAlmostEqual(
                length(supply) + length(return_route), length(route), delta=2.0
            )


if __name__ == "__main__":
    unittest.main()
