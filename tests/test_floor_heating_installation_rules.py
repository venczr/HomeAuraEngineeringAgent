import unittest

from agent.floor_heating_installation_rules import (
    InstallationRuleSet,
    validate_installation_geometry,
)


class InstallationRulesTests(unittest.TestCase):
    def test_r4b_routes_have_installable_grid_turns(self):
        import json
        from pathlib import Path
        path = Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-R4B-TWO-CIRCUIT/canonical_geometry.json')
        model = json.loads(path.read_text())
        room = [(0, 0), (7000, 0), (7000, 3200), (0, 3200), (0, 0)]
        for route in model['circuits']:
            result = validate_installation_geometry(
                [tuple(p) for p in route['ordered_points']], room,
                rules=InstallationRuleSet(wall_clearance_mm=0),
                floor_start_index=3,
                floor_end_index=-3,
            )
            self.assertEqual(result['result'], 'PASS')

    def test_obstacle_clearance_fails_closed(self):
        result = validate_installation_geometry(
            [(0, 0), (1000, 0), (1000, 1000)],
            [(0, 0), (2000, 0), (2000, 2000), (0, 2000), (0, 0)],
            [[(900, 100), (1100, 100), (1100, 300), (900, 300), (900, 100)]],
            InstallationRuleSet(wall_clearance_mm=0, exclusion_clearance_mm=100),
        )
        self.assertEqual(result['exclusion_clearance_valid'], False)
        self.assertEqual(result['result'], 'REWORK')

    def test_short_bend_fails_closed(self):
        result = validate_installation_geometry(
            [(0, 0), (100, 0), (100, 50), (300, 50)],
            [(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)],
            rules=InstallationRuleSet(wall_clearance_mm=0, minimum_bend_radius_mm=100),
        )
        self.assertEqual(result['short_turn_count'], 1)
        self.assertEqual(result['result'], 'REWORK')


if __name__ == '__main__':
    unittest.main()
