from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from agent.building_heat_loss import (
    SP60_METHOD_DIGEST,
    BuildingHeatLossInput,
    ProjectTransmissionSource,
    ThermalBridge,
    TransmissionBoundaryInput,
    build_building_heat_loss_input,
    calculate_room_transmission,
    project_transmission_source_from_adapter,
    adapt_project_heat_loss,
)
from agent.ufh_project_adapter import MappedProjectField, ProjectFieldProvenance, ProjectUfhAdapterResult
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance


D = Decimal
HASH = "a" * 64


def provenance(path, units, source="test_only"):
    return AuthoringProvenance(
        source_type=source,
        source_reference=f"test-fixture://{path}",
        source_sha256=HASH,
        source_field=path,
        transformation="TEST_ONLY sourced fixture; no production binding",
        units=units,
    )


def boundary(
    boundary_id="wall-1", *, room="room-1", kind="OUTDOOR_AIR", fragment="OPAQUE",
    area="10", u="0.3", ti="20", to="-20", role="HOMOGENEOUS_COMPONENT",
    parent=None, internal=False,
):
    return TransmissionBoundaryInput(
        boundary_id=boundary_id,
        room_id=room,
        boundary_kind=kind,
        fragment_kind=fragment,
        geometry_reference=f"fixture://geometry/{boundary_id}",
        geometry_digest=HASH,
        area_m2=D(area) if area is not None else None,
        area_provenance=provenance(f"geometry.{boundary_id}.area", "m2") if area is not None else None,
        u_value_w_m2k=D(u) if u is not None else None,
        u_value_role=role if u is not None else None,
        u_value_provenance=provenance(f"construction.{boundary_id}.U", "W/(m2*K)") if u is not None else None,
        inside_temperature_c=D(ti) if ti is not None else None,
        inside_temperature_provenance=provenance(f"temperature.{boundary_id}.inside", "°C") if ti is not None else None,
        opposite_temperature_c=D(to) if to is not None else None,
        opposite_temperature_provenance=provenance(f"temperature.{boundary_id}.opposite", "°C") if to is not None else None,
        internal_partition=internal,
        parent_boundary_id=parent,
    )


def heat_input(*boundaries, mode="PLANAR_TRANSMISSION_ONLY", bridges=(), inventory="UNRESOLVED",
               boundary_inventory="COMPLETE"):
    return BuildingHeatLossInput(
        project_id="project-1", building_id="building-1", level_id="level-1",
        room_id="room-1", project_revision_digest=HASH,
        normative_method_digest=SP60_METHOD_DIGEST, calculation_mode=mode,
        boundaries=list(boundaries), thermal_bridges=list(bridges),
        boundary_inventory=boundary_inventory,
        boundary_inventory_provenance=(provenance("boundary_inventory", "1") if boundary_inventory == "COMPLETE" else None),
        thermal_bridge_inventory=inventory,
        thermal_bridge_inventory_provenance=(provenance("bridge_inventory", "1") if inventory == "COMPLETE" else None),
    )


def test_sourced_exterior_planar_transmission_uses_decimal_signed_delta():
    result = calculate_room_transmission(heat_input(boundary()))
    assert result.room_transmission_heat_loss_w == D("120.0000")
    assert result.boundary_results[0].delta_t_c == D("40")
    assert result.completeness_status == "PLANAR_ONLY"
    assert "THERMAL_BRIDGES_NOT_INCLUDED" in result.boundary_results[0].diagnostics
    assert result.total_design_heating_load_w is None


def test_opening_is_subtracted_from_wall_and_counted_once_as_separate_fragment():
    wall = boundary(area="10.10")
    window = boundary(
        "window-1", fragment="WINDOW", parent="wall-1", area="2.00", u="1.0",
    )
    result = calculate_room_transmission(heat_input(wall, window))
    parent, child = result.boundary_results
    assert parent.net_opaque_area_m2 == D("8.10")
    assert parent.planar_heat_flow_w == D("97.2000")
    assert child.planar_heat_flow_w == D("80.0000")
    assert result.room_transmission_heat_loss_w == D("177.2000")


def test_opening_duplicate_or_area_exceeding_gross_is_rejected():
    parent = boundary(area="1.00")
    opening_a = boundary("window-a", fragment="WINDOW", parent="wall-1", area="0.60")
    opening_b = boundary("window-b", fragment="WINDOW", parent="wall-1", area="0.50")
    with pytest.raises(ValidationError, match="OPENING_AREAS_EXCEED_GROSS_AREA"):
        heat_input(parent, opening_a, opening_b)
    with pytest.raises(ValidationError, match="DUPLICATE_(BOUNDARY_ID|PHYSICAL_BOUNDARY_PATH)"):
        heat_input(parent, parent.model_copy(deep=True))


def test_area_is_quantized_to_normative_cent_square_metre_resolution():
    result = calculate_room_transmission(heat_input(boundary(area="10.004")))
    assert result.boundary_results[0].gross_area_m2 == D("10.00")
    assert result.room_transmission_heat_loss_w == D("120.0000")


def test_internal_partition_omission_applies_at_four_and_not_above_four_degrees():
    at_four = boundary(kind="HEATED_INTERIOR_SPACE", to="16", internal=True)
    over_four = boundary("partition-2", kind="HEATED_INTERIOR_SPACE", to="15.99", internal=True)
    result = calculate_room_transmission(heat_input(at_four, over_four))
    values = {r.boundary_id: r for r in result.boundary_results}
    assert values["wall-1"].omitted_by_internal_partition_rule is True
    assert values["wall-1"].planar_heat_flow_w == 0
    assert "SP60_INTERNAL_PARTITION_OMISSION_RULE" in values["wall-1"].diagnostics
    assert values["partition-2"].omitted_by_internal_partition_rule is False
    assert values["partition-2"].planar_heat_flow_w == D("12.0300")


def test_temperature_differences_are_boundary_specific_and_signed():
    exterior = boundary("outer", to="-20")
    adjacent = boundary("adjacent", kind="HEATED_INTERIOR_SPACE", to="18")
    warmer_adjacent = boundary("warmer", kind="HEATED_INTERIOR_SPACE", to="22")
    result = calculate_room_transmission(heat_input(exterior, adjacent, warmer_adjacent))
    assert {item.boundary_id: item.delta_t_c for item in result.boundary_results} == {"outer": D("40"), "adjacent": D("2"), "warmer": D("-2")}
    assert result.room_transmission_heat_loss_w == D("120.0000")


def test_unheated_adjacent_without_design_temperature_fails_closed():
    item = boundary(kind="UNHEATED_INTERIOR_SPACE", to=None)
    result = calculate_room_transmission(heat_input(item))
    assert result.completeness_status == "ADJACENT_TEMPERATURE_REQUIRED"
    assert result.room_transmission_heat_loss_w is None
    assert "ADJACENT_SPACE_TEMPERATURE_REQUIRED" in result.unresolved_dependencies


def test_ground_never_uses_ordinary_u_a_delta_t_even_if_area_and_u_exist():
    item = boundary(kind="GROUND", to=None)
    result = calculate_room_transmission(heat_input(item))
    assert result.completeness_status == "GROUND_MODEL_REQUIRED"
    assert result.room_transmission_heat_loss_w is None
    assert result.boundary_results[0].planar_heat_flow_w is None
    assert "GROUND_HEAT_LOSS_MODEL_REQUIRED" in result.unresolved_dependencies


def test_planar_and_detailed_bridge_contributions_remain_separate():
    item = boundary()
    linear = ThermalBridge(
        bridge_id="psi-1", boundary_id="wall-1", kind="LINEAR",
        coefficient=D("0.2"), quantity=D("5"), coefficient_units="W/(m*K)",
        quantity_units="m", provenance=provenance("bridge.psi", "W/(m*K)"),
        quantity_provenance=provenance("bridge.length", "m"),
    )
    point = ThermalBridge(
        bridge_id="chi-1", boundary_id="wall-1", kind="POINT",
        coefficient=D("0.5"), quantity=D("2"), coefficient_units="W/K",
        quantity_units="count", provenance=provenance("bridge.chi", "W/K"),
        quantity_provenance=provenance("bridge.count", "count"),
    )
    planar = calculate_room_transmission(heat_input(item))
    detailed = calculate_room_transmission(
        heat_input(item, mode="DETAILED_TRANSMISSION", bridges=(linear, point), inventory="COMPLETE")
    )
    assert planar.room_transmission_heat_loss_w == D("120.0000")
    assert detailed.planar_total_w == D("120.0000")
    assert detailed.linear_total_w == D("40.0")
    assert detailed.point_total_w == D("40.0")
    assert detailed.room_transmission_heat_loss_w == D("200.0000")
    assert detailed.completeness_status == "COMPLETE_DETAILED"


def test_detailed_requires_explicit_complete_bridge_inventory():
    result = calculate_room_transmission(heat_input(boundary(), mode="DETAILED_TRANSMISSION"))
    assert result.completeness_status == "THERMAL_BRIDGE_DATA_REQUIRED"
    assert result.planar_total_w == D("120.0000")
    assert result.room_transmission_heat_loss_w is None
    assert "THERMAL_BRIDGE_DATA_REQUIRED" in result.unresolved_dependencies


def test_room_total_requires_explicit_complete_boundary_inventory():
    result = calculate_room_transmission(
        heat_input(boundary(), boundary_inventory="UNRESOLVED")
    )
    assert result.planar_total_w == D("120.0000")
    assert result.room_transmission_heat_loss_w is None
    assert result.completeness_status == "INCOMPLETE_BOUNDARY_DATA"
    assert "ROOM_BOUNDARY_INVENTORY_REQUIRED" in result.unresolved_dependencies
    assert result.boundary_results[0].planar_heat_flow_w == D("120.0000")


def test_a2_requires_explicit_reduced_fragment_u_role():
    result = calculate_room_transmission(heat_input(boundary(role="HOMOGENEOUS_COMPONENT"), mode="A2_REDUCED_FRAGMENT"))
    assert result.completeness_status == "INCOMPLETE_BOUNDARY_DATA"
    assert result.room_transmission_heat_loss_w is None
    assert "SP50_REDUCED_RESISTANCE_REQUIRED_FOR_A2" in result.unresolved_dependencies


def test_projection_adapter_only_binds_sourced_room_and_climate_temperatures():
    source = ProjectTransmissionSource(
        project_id="project-1", building_id="building-1", level_id="level-1", room_id="room-1",
        project_revision_digest=HASH,
        indoor_design_temperature_c=D("20"),
        indoor_temperature_provenance=provenance("project.HeatingTemperatureC", "°C"),
        climate_outdoor_design_temperature_c=D("-23"),
        climate_temperature_provenance=provenance("climate.resolver.record", "°C", "project_approved_normative_extract"),
        boundaries=[boundary(ti=None, to=None)], boundary_inventory="COMPLETE",
        boundary_inventory_provenance=provenance("boundary_inventory", "1"),
        thermal_bridge_inventory="UNRESOLVED",
    )
    adapted = build_building_heat_loss_input(source, calculation_mode="PLANAR_TRANSMISSION_ONLY")
    result = calculate_room_transmission(adapted)
    assert result.room_transmission_heat_loss_w == D("129.0000")
    assert result.boundary_results[0].inside_temperature_c == D("20")
    assert result.boundary_results[0].opposite_temperature_c == D("-23")


def test_project_adapter_does_not_promote_non_climate_opposite_temperature_or_ach():
    source = ProjectTransmissionSource(
        project_id="project-1", building_id="building-1", level_id="level-1", room_id="room-1",
        project_revision_digest=HASH,
        indoor_design_temperature_c=D("20"),
        indoor_temperature_provenance=provenance("project.HeatingTemperatureC", "°C"),
        climate_outdoor_design_temperature_c=D("-23"),
        climate_temperature_provenance=provenance("climate.resolver.record", "°C", "project_approved_normative_extract"),
        boundaries=[boundary(kind="HEATED_INTERIOR_SPACE", ti=None, to=None)],
        boundary_inventory="COMPLETE", boundary_inventory_provenance=provenance("boundary_inventory", "1"),
        thermal_bridge_inventory="UNRESOLVED",
    )
    adapted = build_building_heat_loss_input(source, calculation_mode="PLANAR_TRANSMISSION_ONLY")
    assert adapted.boundaries[0].inside_temperature_c == D("20")
    assert adapted.boundaries[0].opposite_temperature_c is None
    result = calculate_room_transmission(adapted)
    assert result.room_transmission_heat_loss_w is None


def test_existing_project_adapter_and_real_climate_resolver_have_narrow_binding():
    from agent.ufh_climate_resolver import resolve_climate_for_questionnaire
    from agent.ufh_pre_generation_questionnaire import (
        Decision, ProjectContext, QuestionnaireState, apply_ufh_questionnaire_answers,
    )
    from agent.ufh_project_engineering_profile_authoring import test01_authoring_template_payload
    project_provenance = ProjectFieldProvenance(
        source_kind="room_extraction", source_file="synthetic://rooms.json",
        source_sha256=HASH, source_path="$.Rooms[].HeatingTemperatureC",
        transformation="source scalar preserved",
    )
    adapter = ProjectUfhAdapterResult(
        status="INCOMPLETE", project_id="synthetic", building_id="bldg-fixture",
        level_id="storey-fixture", room_id="synthetic-room", source_file="synthetic://rooms.json",
        source_digest=HASH, mapped_fields=[MappedProjectField(
            target_path="room.indoor_temperature_c", value=20.0,
            provenance=project_provenance, applied_to_request=False)],
        adapter_digest="b" * 64,
    )
    state = QuestionnaireState(authoring=test01_authoring_template_payload())
    state = apply_ufh_questionnaire_answers(
        ProjectContext(source_reference="synthetic://questionnaire", coordinate_system="fixture-mm"),
        state, [Decision(question_id="climate",
                         value={"settlement": "Санкт-Петербург", "region": "Ленинградская область"},
                         source_reference="synthetic://explicit-location", revision="fixture-1")],
    )
    climate_request, climate_result = resolve_climate_for_questionnaire(
        adapter.project_id, adapter.room_id, adapter.source_digest, state, "RU_CURRENT")
    assert climate_result.status == "RESOLVED"
    mapped_boundary = boundary("exterior", room="synthetic-room", ti=None, to=None)
    prepared = adapt_project_heat_loss(
        adapter, boundaries=[mapped_boundary], climate_result=climate_result,
        climate_request=climate_request, calculation_mode="PLANAR_TRANSMISSION_ONLY",
        boundary_inventory="COMPLETE", boundary_inventory_provenance=provenance("boundary_inventory", "1"),
    )
    assert prepared.status == "INPUT_PREPARED"
    mapped = prepared.input_data.boundaries[0]
    source_temperature = D(str(climate_result.values[0].authored_value.value))
    assert mapped.opposite_temperature_c == source_temperature
    assert mapped.inside_temperature_provenance.source_field == project_provenance.source_path
    assert mapped.opposite_temperature_provenance.source_reference == climate_result.values[0].authored_value.provenance.source_reference
    assert calculate_room_transmission(prepared.input_data).room_transmission_heat_loss_w == (
        mapped.area_m2 * mapped.u_value_w_m2k * (mapped.inside_temperature_c - source_temperature))
    changed_ufh = adapter.model_copy(update={"adapter_digest": "e" * 64})
    second = adapt_project_heat_loss(
        changed_ufh, boundaries=[mapped_boundary], climate_result=climate_result,
        climate_request=climate_request, calculation_mode="PLANAR_TRANSMISSION_ONLY",
        boundary_inventory="COMPLETE", boundary_inventory_provenance=provenance("boundary_inventory", "1"))
    assert calculate_room_transmission(second.input_data).calculation_digest == calculate_room_transmission(prepared.input_data).calculation_digest
    foreign = adapter.model_copy(update={"room_id": "foreign-room"})
    rejected = adapt_project_heat_loss(
        foreign, boundaries=[], climate_result=climate_result,
        climate_request=climate_request, calculation_mode="PLANAR_TRANSMISSION_ONLY")
    assert rejected.status == "INVALID"
    assert "STALE_OR_MISMATCHED_CLIMATE_BINDING" in rejected.diagnostics[0]


def test_no_ventilation_infiltration_or_internal_gains_are_combined_and_ach_is_absent():
    result = calculate_room_transmission(heat_input(boundary()))
    assert result.ventilation_status == "VENTILATION_HEAT_LOSS_NOT_EVALUATED_V1"
    assert result.infiltration_status == "INFILTRATION_NOT_EVALUATED_V1"
    assert result.internal_gains_status == "INTERNAL_GAINS_NOT_EVALUATED_V1"
    assert result.total_design_heating_load_w is None
    assert "air_changes_per_hour" not in BuildingHeatLossInput.model_fields


def test_result_is_deterministic_and_ufh_irrelevant_state_is_not_an_input():
    source = heat_input(boundary())
    first = calculate_room_transmission(source)
    second = calculate_room_transmission(source.model_copy(deep=True))
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    changed = heat_input(boundary(area="11"))
    third = calculate_room_transmission(changed)
    assert third.calculation_digest != first.calculation_digest
    assert "pipe_diameter" not in BuildingHeatLossInput.model_fields


def test_existing_envelope_resolver_u_is_consumed_without_relabelling():
    from agent.ufh_envelope_construction_resolver import (
        ConstructionBoundaryKind, ConstructionLayer, ConstructionSourceMode,
        EnvelopeAssemblyDefinition, SurfaceResistanceMethod, calculate_assembly,
    )
    assembly = calculate_assembly(EnvelopeAssemblyDefinition(
        assembly_id="synthetic-wall", boundary_kind=ConstructionBoundaryKind.EXTERIOR_WALL,
        layers=[ConstructionLayer(material_product_id="TEST_ONLY", thickness_m=D("0.2"),
                                  lambda_w_mk=D("0.1"), lambda_provenance=provenance("lambda", "W/(m*K)"))],
        source_reference="test://assembly", source_field="wall"),
        ConstructionSourceMode.LAYERED_CUSTOM_ASSEMBLY,
        surface_method=SurfaceResistanceMethod(
            method_id="TEST_ONLY", method_revision="1", r_si_m2k_w=D("0.1"), r_se_m2k_w=D("0.05"),
            provenance=provenance("surfaces", "m2*K/W")))
    wall = TransmissionBoundaryInput.model_validate({**boundary(u=None).model_dump(), "construction": assembly})
    result = calculate_room_transmission(heat_input(wall))
    with localcontext() as context:
        context.prec = 50
        expected = wall.area_m2 * assembly.u_value_w_m2k * (wall.inside_temperature_c - wall.opposite_temperature_c)
    assert result.planar_total_w == expected
    with pytest.raises(ValidationError, match="CANNOT_BE_RELABELLED"):
        TransmissionBoundaryInput.model_validate({**wall.model_dump(), "u_value_role": "REDUCED_FRAGMENT"})
    a2 = calculate_room_transmission(heat_input(wall, mode="A2_REDUCED_FRAGMENT"))
    assert a2.room_transmission_heat_loss_w is None


def test_opening_bridge_and_missing_temperature_are_safe():
    window = boundary("window", fragment="WINDOW", parent="wall-1", area="2", u="1")
    bridge = ThermalBridge(
        bridge_id="window-edge", boundary_id="window", kind="LINEAR",
        coefficient=D("0.2"), quantity=D("3"), coefficient_units="W/(m*K)", quantity_units="m",
        provenance=provenance("psi", "W/(m*K)"), quantity_provenance=provenance("edge", "m"))
    result = calculate_room_transmission(heat_input(boundary(), window, mode="DETAILED_TRANSMISSION",
                                                  bridges=[bridge], inventory="COMPLETE"))
    assert result.linear_total_w == D("24")
    assert result.room_transmission_heat_loss_w == D("200")
    unknown = boundary("window", fragment="WINDOW", parent="wall-1", area="2", u="1", to=None)
    incomplete = calculate_room_transmission(heat_input(boundary(), unknown, mode="DETAILED_TRANSMISSION",
                                                      bridges=[bridge], inventory="COMPLETE"))
    assert incomplete.room_transmission_heat_loss_w is None


def test_rounding_preserves_partition_area_and_context_does_not_change_result():
    wall = boundary(area="10.00")
    a = boundary("a", fragment="WINDOW", parent="wall-1", area="1.005")
    b = boundary("b", fragment="WINDOW", parent="wall-1", area="1.005")
    request = heat_input(wall, a, b)
    first = calculate_room_transmission(request)
    assert sum((r.net_opaque_area_m2 for r in first.boundary_results), D(0)) == D("10.00")
    with localcontext() as context:
        context.prec = 6
        second = calculate_room_transmission(request)
    assert first == second
    assert calculate_room_transmission(heat_input(b, wall, a)) == first


def test_a2_reduced_and_a3_homogeneous_cannot_double_count_bridges():
    reduced = boundary(role="REDUCED_FRAGMENT")
    result = calculate_room_transmission(heat_input(reduced, mode="A2_REDUCED_FRAGMENT"))
    assert result.room_transmission_heat_loss_w == D("120")
    detailed = calculate_room_transmission(heat_input(reduced, mode="DETAILED_TRANSMISSION", inventory="COMPLETE"))
    assert detailed.room_transmission_heat_loss_w is None
    assert "HOMOGENEOUS_U_REQUIRED_FOR_A3" in detailed.unresolved_dependencies


def test_method_revision_and_provenance_fail_closed():
    data = heat_input(boundary()).model_dump()
    data["normative_method_digest"] = "f" * 64
    with pytest.raises(ValidationError, match="SP60_METHOD_REVISION_UNSUPPORTED"):
        BuildingHeatLossInput.model_validate(data)
    wall = boundary().model_dump()
    wall["u_value_provenance"] = None
    with pytest.raises(ValidationError, match="PROVENANCE_MUST_BE_PAIRED"):
        TransmissionBoundaryInput.model_validate(wall)
    wall = boundary().model_dump()
    wall["internal_partition"] = True
    with pytest.raises(ValidationError, match="INTERNAL_PARTITION_SCOPE_INVALID"):
        TransmissionBoundaryInput.model_validate(wall)


def test_project_temperature_conflict_is_not_silently_ignored():
    source = ProjectTransmissionSource(
        project_id="p", building_id="b", level_id="l", room_id="room-1", project_revision_digest=HASH,
        indoor_design_temperature_c=D("21"), indoor_temperature_provenance=provenance("project-ti", "°C"),
        boundaries=[boundary()], boundary_inventory="COMPLETE",
        boundary_inventory_provenance=provenance("boundary_inventory", "1"),
        thermal_bridge_inventory="UNRESOLVED")
    with pytest.raises(ValueError, match="SOURCE_VALUE_CONFLICT"):
        build_building_heat_loss_input(source, calculation_mode="PLANAR_TRANSMISSION_ONLY")


def test_method_package_pins_verified_current_revision_and_formula_roles():
    from agent.building_heat_loss import SP60_METHOD_PACKAGE as method
    assert method["consolidated_amendments"] == [1, 2, 3, 4, 5, 6]
    assert method["climate_dependency"] == "SP 131.13330.2025"
    assert method["amendment_6_effective_from"] == "2026-07-07"
    assert method["official_identity_authority"] == "NORMATIVE_DOCUMENT_IDENTITY_AUTHORITY"
    assert method["text_carrier_role"] == "TEXT_CARRIER_ONLY"
    assert set(method["visually_verified_equation_sha256"]) == {"A.2", "A.3"}
    assert method["symbol_units"]["psi"] == "W/(m*K)"


def test_climate_change_only_invalidates_the_affected_boundary_result():
    outside = boundary("outside")
    inside = boundary("inside", kind="HEATED_INTERIOR_SPACE", to="14", internal=True)
    first = calculate_room_transmission(heat_input(outside, inside))
    changed = outside.model_copy(update={"opposite_temperature_c": D("-21")})
    second = calculate_room_transmission(heat_input(changed, inside))
    a = {r.boundary_id: r for r in first.boundary_results}
    b = {r.boundary_id: r for r in second.boundary_results}
    assert a["inside"] == b["inside"]
    assert a["outside"].provenance_digest != b["outside"].provenance_digest
    assert first.calculation_digest != second.calculation_digest


def test_pure_calculation_never_reads_files_or_invokes_ufh(monkeypatch):
    from pathlib import Path
    import builtins
    import agent.floor_heating_sizing as sizing
    import agent.ufh_engineering_kernel as kernel
    import agent.ufh_auto_retry as retry
    request = heat_input(boundary())
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O or UFH execution inside transmission core")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(sizing, "size_ufh_requirement", forbidden)
    monkeypatch.setattr(sizing, "size_ufh_requirement_and_coverage", forbidden)
    monkeypatch.setattr(kernel, "evaluate", forbidden)
    monkeypatch.setattr(retry, "assess_with_automatic_split_retry", forbidden)
    assert calculate_room_transmission(request).room_transmission_heat_loss_w is not None


def test_actual_test01_readiness_only_and_sources_unchanged(monkeypatch):
    import hashlib
    from pathlib import Path
    import agent.building_heat_loss as core
    from agent.test01_geometry_source_authority import assess_test01_geometry_authority
    from agent.ufh_project_adapter import build_ufh_sizing_request_from_project_room
    root = Path(__file__).resolve().parents[1]
    project = root / "projects/Test_01"
    companion = root.parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"
    if not (companion / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("Reviewed external IFC unavailable; no synthetic replacement")
    paths = [project / "Test_01.dwg", project / "HomeAura_Test_01.mrd",
             project / "exports/rooms/rooms.json"]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    def no_real_calculation(*args, **kwargs):
        raise AssertionError("Real Test_01 transmission calculation forbidden")
    monkeypatch.setattr(core, "calculate_room_transmission", no_real_calculation)
    authority = assess_test01_geometry_authority(project, companion)
    assert authority.status == "AUTHORITATIVE"
    adapter = build_ufh_sizing_request_from_project_room(authority.ufh_source)
    source = project_transmission_source_from_adapter(adapter, boundaries=[])
    assert source.indoor_design_temperature_c == D(str(authority.ufh_source.selected_room.HeatingTemperatureC))
    assert source.climate_outdoor_design_temperature_c is None
    prepared = adapt_project_heat_loss(adapter, boundaries=[], calculation_mode="PLANAR_TRANSMISSION_ONLY")
    assert prepared.status == "INCOMPLETE"
    assert "TRANSMISSION_BOUNDARIES_REQUIRED" in prepared.diagnostics
    assert adapter.sizing_request is None
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
