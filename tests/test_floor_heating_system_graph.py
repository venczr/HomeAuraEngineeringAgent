import unittest

from agent.floor_heating_engine import calculate_floor_heating
from agent.floor_heating_models import FloorHeatingRequest
from agent.floor_heating_system_graph import build_floor_heating_project_preview


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def request(**overrides) -> FloorHeatingRequest:
    payload = {
        "project_id": "project-1",
        "room_id": "room-1",
        "boundary": {"points": [
            point(0, 0), point(7000, 0), point(7000, 3200),
            point(0, 3200), point(0, 0),
        ]},
        "exclusion_zones": [],
        "collector_point": point(3500, 1100),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
        "minimum_circuit_length_mm": 40000,
        "maximum_circuit_length_mm": 80000,
        "requested_circuit_count": 1,
        "field_spacing_mm": 200,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "exterior_wall_segments": [{
            "reference": "exterior-wall-south",
            "start": point(0, 0),
            "end": point(7000, 0),
        }],
        "perimeter_priority_mode": True,
    }
    payload.update(overrides)
    return FloorHeatingRequest.model_validate(payload)


class FloorHeatingSystemGraphV2Tests(unittest.TestCase):
    def test_validated_route_maps_once_with_exact_quantities(self) -> None:
        result = calculate_floor_heating(request())
        preview = build_floor_heating_project_preview(result)
        graph = preview.system_graph
        spec = preview.specification

        self.assertEqual(preview.status, "ok")
        self.assertEqual(graph.circuit_count, 1)
        circuit_nodes = [node for node in graph.nodes if node.kind == "circuit"]
        self.assertEqual(len(circuit_nodes), 1)
        attributes = circuit_nodes[0].attributes
        self.assertTrue(attributes["route_validation"]["valid"])
        self.assertFalse(attributes["route_validation"]["self_intersection"])
        self.assertEqual(
            attributes["collector_supply_point_mm"],
            result.circuit_routes[0].collector_supply_point.model_dump(mode="json"),
        )
        self.assertEqual(
            attributes["collector_return_point_mm"],
            result.circuit_routes[0].collector_return_point.model_dump(mode="json"),
        )
        schedule = spec.circuit_schedule[0]
        self.assertEqual(schedule.total_length_mm, result.circuits[0].length_mm)
        self.assertEqual(
            schedule.total_length_mm,
            schedule.laying_length_mm
            + schedule.supply_length_mm
            + schedule.return_length_mm,
        )
        self.assertEqual(
            spec.pipe_requirement.calculated_total_pipe_length_mm,
            result.circuit_routes[0].length_mm,
        )
        self.assertEqual(spec.collector_requirement.required_port_count, 1)

    def test_graph_ids_edges_and_output_are_deterministic(self) -> None:
        first = build_floor_heating_project_preview(calculate_floor_heating(request()))
        second = build_floor_heating_project_preview(calculate_floor_heating(request()))
        self.assertEqual(first.model_dump(mode="json"), second.model_dump(mode="json"))
        known = {node.node_id for node in first.system_graph.nodes}
        self.assertTrue(
            all(
                edge.source_node_id in known and edge.target_node_id in known
                for edge in first.system_graph.edges
            )
        )
        changed = build_floor_heating_project_preview(
            calculate_floor_heating(request(collector_point=point(4200, 1100)))
        )
        self.assertNotEqual(first.projection_digest, changed.projection_digest)

    def test_invalid_route_is_not_projectable_to_autocad_payload(self) -> None:
        result = calculate_floor_heating(request(maximum_circuit_length_mm=60000))
        preview = build_floor_heating_project_preview(result)
        self.assertEqual(result.status, "impossible")
        self.assertEqual(preview.status, "impossible")
        self.assertEqual(
            [node for node in preview.system_graph.nodes if node.kind == "circuit"],
            [],
        )
        self.assertEqual(preview.specification.circuit_schedule, [])
        self.assertTrue(preview.diagnostics)

    def test_old_multi_partition_request_is_fail_closed(self) -> None:
        result = calculate_floor_heating(request(requested_circuit_count=2))
        preview = build_floor_heating_project_preview(result)
        self.assertEqual(result.status, "impossible")
        self.assertEqual(preview.system_graph.circuit_count, 0)
        self.assertEqual(preview.specification.collector_requirement.required_port_count, 0)

    def test_neutral_specification_does_not_invent_products_or_hydraulics(self) -> None:
        preview = build_floor_heating_project_preview(calculate_floor_heating(request()))
        payload = str(preview.model_dump(mode="json")).lower()
        for forbidden in ("brand", "sku", "price"):
            self.assertNotIn(forbidden, payload)
        self.assertIn(
            "Hydraulic resistance is not calculated.",
            preview.specification.assumptions,
        )
        self.assertEqual(
            preview.specification.pipe_requirement.hydraulic_validation_status,
            "NOT_CALCULATED",
        )

    def test_perimeter_and_field_quantities_come_from_one_route(self) -> None:
        result = calculate_floor_heating(request())
        preview = build_floor_heating_project_preview(result)
        route = result.circuit_routes[0]
        circuit = result.circuits[0]
        self.assertEqual(preview.status, "ok")
        self.assertEqual(preview.system_graph.field_spacing_mm, 200)
        self.assertEqual(preview.system_graph.perimeter_spacing_mm, 100)
        self.assertEqual(preview.system_graph.perimeter_band_depth_mm, 1000)
        self.assertEqual(circuit.points, route.polyline)
        self.assertEqual(
            circuit.perimeter_laying_length_mm,
            sum(item.length_mm for item in route.outer_wall_segments),
        )
        self.assertEqual(
            circuit.field_laying_length_mm,
            sum(item.length_mm for item in route.field_segments),
        )


if __name__ == "__main__":
    unittest.main()
