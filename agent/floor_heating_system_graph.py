"""Pure floor-heating projection into a deterministic system graph.

The projection deliberately stays independent from HTTP, storage, provider
brokers, credentials, and CAD integrations.  It is a neutral engineering
preview, not a product or hydraulic selection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import Field, model_validator

from agent.floor_heating_models import (
    FloorHeatingPoint,
    FloorHeatingPolygon,
    FloorHeatingResult,
    FloorHeatingWallSegment,
)
from agent.project_models import StrictProjectModel


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return hashlib.sha256(
        prefix.encode("utf-8") + b":" + _canonical(value)
    ).hexdigest()


class FloorHeatingGraphNode(StrictProjectModel):
    node_id: str = Field(min_length=1, max_length=160)
    kind: Literal["floor_heating_system", "room", "collector", "circuit"]
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    circuit_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class FloorHeatingGraphEdge(StrictProjectModel):
    edge_id: str = Field(min_length=1, max_length=160)
    kind: Literal["contains", "serves", "supply_connection", "return_connection", "circuit_to_room"]
    source_node_id: str = Field(min_length=1, max_length=160)
    target_node_id: str = Field(min_length=1, max_length=160)
    circuit_id: str | None = None


class FloorHeatingSystemGraph(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    graph_id: str = Field(min_length=1, max_length=160)
    system_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    status: Literal["ok", "impossible"]
    nodes: list[FloorHeatingGraphNode]
    edges: list[FloorHeatingGraphEdge]
    circuit_count: int = Field(ge=0, le=3)
    spacing_mm: int = Field(ge=1)
    heated_area_mm2: int = Field(ge=0)
    wall_offset_mm: int = Field(ge=0)
    maximum_circuit_length_mm: int = Field(ge=1)
    turn_radius_mm: int = Field(default=0, ge=0, le=500)
    routing_mode: str = Field(default="legacy", max_length=48)
    collector_point_mm: FloorHeatingPoint | None = None
    source_result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnostics: list[str] = Field(default_factory=list)
    field_spacing_mm: int | None = Field(default=None, ge=1)
    perimeter_spacing_mm: int | None = Field(default=None, ge=1)
    perimeter_band_depth_mm: int | None = Field(default=None, ge=1)
    installation_grid_spacing_mm: int | None = Field(default=None, ge=1)
    preferred_topology: str | None = Field(default=None, max_length=96)
    exterior_wall_segments: list[FloorHeatingWallSegment] = Field(
        default_factory=list,
        max_length=16,
    )
    perimeter_band_polygon: FloorHeatingPolygon | None = None
    perimeter_band_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    room_boundary: FloorHeatingPolygon | None = None
    exclusion_zones: list[FloorHeatingPolygon] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def validate_references(self) -> FloorHeatingSystemGraph:
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("graph node ids must be unique")
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("graph edge ids must be unique")
        known = set(node_ids)
        if any(
            edge.source_node_id not in known or edge.target_node_id not in known
            for edge in self.edges
        ):
            raise ValueError("graph edge references must resolve")
        return self


class FloorHeatingCircuitScheduleItem(StrictProjectModel):
    display_index: int = Field(ge=1)
    circuit_id: str = Field(min_length=1, max_length=96)
    room_id: str = Field(min_length=1, max_length=128)
    laying_length_mm: int = Field(ge=0)
    supply_length_mm: int = Field(ge=0)
    return_length_mm: int = Field(ge=0)
    total_length_mm: int = Field(ge=0)
    spacing_mm: int = Field(ge=1)
    maximum_length_status: Literal["within_limit", "not_evaluated"]
    zone_role: str | None = Field(default=None, max_length=48)
    topology: str | None = Field(default=None, max_length=64)
    nominal_spacing_mm: int | None = Field(default=None, ge=1)
    perimeter_laying_length_mm: int = Field(default=0, ge=0)
    field_laying_length_mm: int = Field(default=0, ge=0)
    exterior_wall_references: list[str] = Field(default_factory=list, max_length=16)


class FloorHeatingPipeRequirement(StrictProjectModel):
    calculated_laying_length_mm: int = Field(ge=0)
    calculated_supply_transit_length_mm: int = Field(ge=0)
    calculated_return_transit_length_mm: int = Field(ge=0)
    calculated_total_pipe_length_mm: int = Field(ge=0)
    unit: Literal["mm"] = "mm"
    source_circuit_ids: list[str]
    procurement_reserve_status: Literal["NOT_APPLIED"] = "NOT_APPLIED"
    unresolved_procurement_recommendation: str = (
        "Procurement reserve is unresolved and was not applied."
    )
    perimeter_band_depth_mm: int | None = Field(default=None, ge=1)
    installation_grid_spacing_mm: int | None = Field(default=None, ge=1)
    exterior_wall_references: list[str] = Field(default_factory=list, max_length=16)
    heat_loss_validation_status: Literal["NOT_CALCULATED"] = "NOT_CALCULATED"
    hydraulic_validation_status: Literal["NOT_CALCULATED"] = "NOT_CALCULATED"


class FloorHeatingCollectorRequirement(StrictProjectModel):
    required_port_count: int = Field(ge=0, le=3)
    source_circuit_ids: list[str]
    catalog_selection: Literal["UNRESOLVED"] = "UNRESOLVED"
    product_selection_note: str = (
        "Commercial collector product selection is unresolved in this MVP."
    )


class FloorHeatingNeutralSpecification(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    specification_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    status: Literal["ok", "impossible"]
    pipe_requirement: FloorHeatingPipeRequirement
    collector_requirement: FloorHeatingCollectorRequirement
    circuit_schedule: list[FloorHeatingCircuitScheduleItem]
    assumptions: list[str]
    diagnostics: list[str]
    source_result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class FloorHeatingProjectPreview(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    preview_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    status: Literal["ok", "impossible"]
    system_graph: FloorHeatingSystemGraph
    specification: FloorHeatingNeutralSpecification
    diagnostics: list[str]
    source_result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    projection_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


MVP_ASSUMPTIONS = [
    "Pipe diameter is not selected.",
    "Collector product is not selected.",
    "Flow rate is not calculated.",
    "Hydraulic resistance is not calculated.",
    "Actuator and thermostat selection is not calculated.",
    "Heat-loss sufficiency is not calculated.",
    "Pump and mixing unit are not selected.",
    "Normative compliance is not asserted.",
]


def _polyline_length(points: list[Any]) -> int:
    return sum(
        abs(points[index].x_mm - points[index - 1].x_mm)
        + abs(points[index].y_mm - points[index - 1].y_mm)
        for index in range(1, len(points))
    )


def _id(kind: str, payload: Any) -> str:
    return f"fh-{kind}-{_digest(f'homeaura.floor-heating.{kind}.v1', payload)}"


def _projection_diagnostics(result: FloorHeatingResult) -> list[str]:
    diagnostics = [
        f"{item.code}: {item.message}"
        for item in result.diagnostics
    ]
    return diagnostics + list(result.warnings)


def build_floor_heating_project_preview(
    result: FloorHeatingResult,
    collector_point: FloorHeatingPoint | None = None,
) -> FloorHeatingProjectPreview:
    """Build deterministic graph/spec output without external side effects."""
    base = {
        "project_id": result.project_id,
        "room_id": result.room_id,
        "result_digest": result.result_digest,
    }
    graph_id = _id("graph", base)
    system_id = _id("system", base)
    room_node_id = _id("room", {**base, "kind": "room"})
    collector_node_id = _id("collector", {**base, "kind": "collector"})
    diagnostics = _projection_diagnostics(result)
    valid_circuits: list[tuple[Any, int, int, int, int]] = []
    mapping_failed = bool(result.diagnostics)

    if result.status == "ok":
        routes = {route.id: route for route in result.circuit_routes}
        if result.circuit_count != len(result.circuits):
            diagnostics.append("GRAPH_CIRCUIT_COUNT_MISMATCH")
            mapping_failed = True
        else:
            for circuit in result.circuits:
                route = routes.get(circuit.circuit_id)
                if (
                    route is None
                    or not route.validation.valid
                    or route.polyline != circuit.points
                    or route.length_mm != circuit.length_mm
                ):
                    diagnostics.append(
                        f"GRAPH_ROUTE_NOT_VALIDATED:{circuit.circuit_id}"
                    )
                    mapping_failed = True
                    continue
                supply = _polyline_length(circuit.supply_transit)
                return_length = _polyline_length(circuit.return_transit)
                laying = circuit.length_mm - supply - return_length
                if laying < 0 or circuit.length_mm != laying + supply + return_length:
                    diagnostics.append(
                        f"GRAPH_LENGTH_MISMATCH:{circuit.circuit_id}"
                    )
                    mapping_failed = True
                    continue
                valid_circuits.append(
                    (circuit, laying, supply, return_length, circuit.length_mm)
                )
        if len(valid_circuits) != result.circuit_count:
            diagnostics.append("GRAPH_RESULT_NOT_PROJECTABLE")
            mapping_failed = True

    accepted = result.status == "ok" and not mapping_failed
    circuits = sorted(valid_circuits, key=lambda item: item[0].circuit_id)
    normal_count = len(circuits) if accepted else 0
    graph_status = "ok" if accepted else "impossible"
    graph_circuit_count = normal_count
    nodes = [
        FloorHeatingGraphNode(
            node_id=system_id,
            kind="floor_heating_system",
            project_id=result.project_id,
            room_id=result.room_id,
            attributes={
                "spacing_mm": result.spacing_mm,
                "heated_area_mm2": result.usable_heated_area_mm2,
                "wall_offset_mm": result.wall_offset_mm,
                "maximum_circuit_length_mm": result.maximum_circuit_length_mm,
                "turn_radius_mm": result.turn_radius_mm,
                "routing_mode": result.routing_mode,
                "source_result_digest": result.result_digest,
                "field_spacing_mm": result.field_spacing_mm,
                "perimeter_spacing_mm": result.perimeter_spacing_mm,
                "perimeter_band_depth_mm": result.perimeter_band_depth_mm,
                "installation_grid_spacing_mm": result.installation_grid_spacing_mm,
                "preferred_topology": result.preferred_topology,
                "exterior_wall_segments": [
                    item.model_dump(mode="json")
                    for item in result.exterior_wall_segments
                ],
                "perimeter_band_polygon": (
                    result.perimeter_band_polygon.model_dump(mode="json")
                    if result.perimeter_band_polygon is not None
                    else None
                ),
                "perimeter_band_digest": result.perimeter_band_digest,
                "room_boundary": (
                    result.room_boundary.model_dump(mode="json")
                    if result.room_boundary is not None
                    else None
                ),
                "exclusion_zones": [
                    item.model_dump(mode="json")
                    for item in result.exclusion_zones
                ],
            },
        ),
        FloorHeatingGraphNode(
            node_id=room_node_id,
            kind="room",
            project_id=result.project_id,
            room_id=result.room_id,
            attributes={"room_reference": result.room_id},
        ),
        FloorHeatingGraphNode(
            node_id=collector_node_id,
            kind="collector",
            project_id=result.project_id,
            room_id=result.room_id,
            attributes={
                "required_port_count": graph_circuit_count,
                **(
                    {
                        "collector_point_mm": {
                            "x_mm": collector_point.x_mm,
                            "y_mm": collector_point.y_mm,
                        }
                    }
                    if collector_point is not None
                    else {}
                ),
            },
        ),
    ]
    edges = [
        FloorHeatingGraphEdge(
            edge_id=_id("edge", {**base, "kind": "contains", "target": collector_node_id}),
            kind="contains",
            source_node_id=system_id,
            target_node_id=collector_node_id,
        ),
        FloorHeatingGraphEdge(
            edge_id=_id("edge", {**base, "kind": "serves", "target": room_node_id}),
            kind="serves",
            source_node_id=system_id,
            target_node_id=room_node_id,
        ),
    ]
    schedule: list[FloorHeatingCircuitScheduleItem] = []
    total_laying = total_supply = total_return = total_pipe = 0
    source_circuit_ids: list[str] = []
    for display_index, (circuit, laying, supply, return_length, total) in enumerate(circuits, 1):
        circuit_node_id = _id("circuit", {**base, "circuit_id": circuit.circuit_id})
        nodes.append(
            FloorHeatingGraphNode(
                node_id=circuit_node_id,
                kind="circuit",
                project_id=result.project_id,
                room_id=result.room_id,
                circuit_id=circuit.circuit_id,
                attributes={
                    "points_mm": [
                        {"x_mm": point.x_mm, "y_mm": point.y_mm}
                        for point in circuit.points
                    ],
                    "supply_transit_mm": [
                        {"x_mm": point.x_mm, "y_mm": point.y_mm}
                        for point in circuit.supply_transit
                    ],
                    "return_transit_mm": [
                        {"x_mm": point.x_mm, "y_mm": point.y_mm}
                        for point in circuit.return_transit
                    ],
                    "laying_length_mm": laying,
                    "supply_length_mm": supply,
                    "return_length_mm": return_length,
                    "total_length_mm": total,
                    "spacing_mm": result.spacing_mm,
                    "maximum_length_status": "within_limit",
                    "zone_role": circuit.zone_role,
                    "topology": circuit.topology,
                    "nominal_spacing_mm": circuit.nominal_spacing_mm,
                    "perimeter_laying_length_mm": circuit.perimeter_laying_length_mm,
                    "field_laying_length_mm": circuit.field_laying_length_mm,
                    "exterior_wall_references": circuit.exterior_wall_references,
                    "route_validation": next(
                        route.validation.model_dump(mode="json")
                        for route in result.circuit_routes
                        if route.id == circuit.circuit_id
                    ),
                    "collector_supply_point_mm": next(
                        route.collector_supply_point.model_dump(mode="json")
                        for route in result.circuit_routes
                        if route.id == circuit.circuit_id
                    ),
                    "collector_return_point_mm": next(
                        route.collector_return_point.model_dump(mode="json")
                        for route in result.circuit_routes
                        if route.id == circuit.circuit_id
                    ),
                },
            )
        )
        source_circuit_ids.append(circuit.circuit_id)
        for kind, source, target in (
            ("supply_connection", collector_node_id, circuit_node_id),
            ("return_connection", circuit_node_id, collector_node_id),
            ("circuit_to_room", circuit_node_id, room_node_id),
        ):
            edges.append(
                FloorHeatingGraphEdge(
                    edge_id=_id("edge", {**base, "kind": kind, "circuit_id": circuit.circuit_id}),
                    kind=kind,
                    source_node_id=source,
                    target_node_id=target,
                    circuit_id=circuit.circuit_id,
                )
            )
        schedule.append(
            FloorHeatingCircuitScheduleItem(
                display_index=display_index,
                circuit_id=circuit.circuit_id,
                room_id=result.room_id,
                laying_length_mm=laying,
                supply_length_mm=supply,
                return_length_mm=return_length,
                total_length_mm=total,
                        spacing_mm=result.spacing_mm,
                        maximum_length_status="within_limit",
                        zone_role=circuit.zone_role,
                        topology=circuit.topology,
                        nominal_spacing_mm=circuit.nominal_spacing_mm,
                        perimeter_laying_length_mm=circuit.perimeter_laying_length_mm,
                        field_laying_length_mm=circuit.field_laying_length_mm,
                        exterior_wall_references=circuit.exterior_wall_references,
            )
        )
        total_laying += laying
        total_supply += supply
        total_return += return_length
        total_pipe += total

    graph = FloorHeatingSystemGraph(
        graph_id=graph_id,
        system_id=system_id,
        project_id=result.project_id,
        room_id=result.room_id,
        status=graph_status,
        nodes=nodes,
        edges=edges,
        circuit_count=graph_circuit_count,
        spacing_mm=result.spacing_mm,
        heated_area_mm2=result.usable_heated_area_mm2,
        wall_offset_mm=result.wall_offset_mm,
        maximum_circuit_length_mm=result.maximum_circuit_length_mm,
        turn_radius_mm=result.turn_radius_mm,
        routing_mode=result.routing_mode,
        collector_point_mm=collector_point,
        source_result_digest=result.result_digest,
        diagnostics=diagnostics,
        field_spacing_mm=result.field_spacing_mm,
        perimeter_spacing_mm=result.perimeter_spacing_mm,
        perimeter_band_depth_mm=result.perimeter_band_depth_mm,
        installation_grid_spacing_mm=result.installation_grid_spacing_mm,
        preferred_topology=result.preferred_topology,
        exterior_wall_segments=result.exterior_wall_segments,
        perimeter_band_polygon=result.perimeter_band_polygon,
        perimeter_band_digest=result.perimeter_band_digest,
        room_boundary=result.room_boundary,
        exclusion_zones=result.exclusion_zones,
    )
    specification = FloorHeatingNeutralSpecification(
        specification_id=_id("specification", base),
        project_id=result.project_id,
        room_id=result.room_id,
        status=graph_status,
        pipe_requirement=FloorHeatingPipeRequirement(
            calculated_laying_length_mm=total_laying,
            calculated_supply_transit_length_mm=total_supply,
            calculated_return_transit_length_mm=total_return,
            calculated_total_pipe_length_mm=total_pipe,
            source_circuit_ids=source_circuit_ids,
            perimeter_band_depth_mm=result.perimeter_band_depth_mm,
            installation_grid_spacing_mm=result.installation_grid_spacing_mm,
            exterior_wall_references=[
                item.reference for item in result.exterior_wall_segments
            ],
        ),
        collector_requirement=FloorHeatingCollectorRequirement(
            required_port_count=graph_circuit_count,
            source_circuit_ids=source_circuit_ids,
        ),
        circuit_schedule=schedule,
        assumptions=list(dict.fromkeys(MVP_ASSUMPTIONS + result.assumptions)),
        diagnostics=diagnostics,
        source_result_digest=result.result_digest,
    )
    payload = {"graph": graph.model_dump(mode="json"), "specification": specification.model_dump(mode="json")}
    projection_digest = _digest("homeaura.floor-heating.projection.v1", payload)
    return FloorHeatingProjectPreview(
        preview_id=_id("preview", base),
        project_id=result.project_id,
        room_id=result.room_id,
        status=graph_status,
        system_graph=graph,
        specification=specification,
        diagnostics=diagnostics,
        source_result_digest=result.result_digest,
        projection_digest=projection_digest,
    )


__all__ = [
    "FloorHeatingProjectPreview",
    "FloorHeatingSystemGraph",
    "FloorHeatingNeutralSpecification",
    "build_floor_heating_project_preview",
]
