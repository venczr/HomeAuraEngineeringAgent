from decimal import Decimal

import pytest

from agent.ufh_sp50_surface_resistance import (
    EXTRACT_SOURCES, ExternalSurfaceCategory, InternalSurfaceCategory,
    SURFACE_HEAT_TRANSFER_DATASET, SurfaceApplicability,
    resolve_surface_resistances as _resolve_surface_resistances,
    verify_independent_extract_values,
)
from agent.ufh_envelope_construction_resolver import (
    ConstructionBoundaryKind, ConstructionSourceMode, EnvelopeAssemblyDefinition,
    EnvelopeConstructionSubmission, calculate_bundle,
)
from tests.test_ufh_envelope_construction_resolver import wall_payload


def resolve_surface_resistances(applicability):
    if (applicability.internal_category or applicability.external_category) and (
        not applicability.source_reference or not applicability.source_field
    ):
        applicability = applicability.model_copy(update={
            "source_reference": applicability.source_reference or "synthetic://TEST_ONLY/applicability",
            "source_field": applicability.source_field or "test.surface_category",
        })
    if (applicability.northern_climatic_zone_confirmed is True
            and not applicability.climatic_zone_source_reference):
        applicability = applicability.model_copy(update={
            "climatic_zone_source_reference": "synthetic://TEST_ONLY/climatic-zone",
            "climatic_zone_source_field": "building.climatic_zone",
        })
    return _resolve_surface_resistances(applicability)


def test_dataset_is_revision_pinned_and_project_approved_extract_not_mirror_authority():
    dataset = SURFACE_HEAT_TRANSFER_DATASET
    assert dataset.normative_document.startswith("SP 50.13330.2024")
    assert dataset.edition == "2024"
    assert dataset.approval_order == "327/пр"
    assert dataset.approval_date == "2024-05-15"
    assert dataset.effective_from == "2024-06-16"
    assert dataset.replaced_edition == "SP 50.13330.2012"
    assert dataset.current_status == "ACTIVE"
    assert dataset.authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    assert "protect.gost.ru" in dataset.official_status_source
    assert len(set(EXTRACT_SOURCES)) >= 2
    assert all(r.authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT" for r in dataset.records)
    assert all(r.alpha_w_m2k > 0 and r.record_digest for r in dataset.records)


def test_table4_all_extracted_rows_and_values_are_distinct():
    values = {r.row_id: r.alpha_w_m2k for r in SURFACE_HEAT_TRANSFER_DATASET.records
              if r.table_id == "Table 4"}
    assert values == {"row 1": Decimal("8.7"), "row 2": Decimal("7.6"),
                      "row 3": Decimal("8.0"), "row 4": Decimal("9.9")}


def test_table6_rows_are_typed_and_not_universal_external_fallback():
    values = {r.row_id: r.alpha_w_m2k for r in SURFACE_HEAT_TRANSFER_DATASET.records
              if r.table_id == "Table 6"}
    assert values == {"row 1": Decimal("23"), "row 2": Decimal("17"),
                      "row 3": Decimal("12"), "row 4": Decimal("6")}
    missing = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB))
    assert missing.external is None
    assert "EXTERNAL_SURFACE_APPLICABILITY_UNRESOLVED" in missing.diagnostics


def test_surface_category_without_provenance_is_not_bindable():
    missing = _resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE))
    assert missing.method is None
    assert missing.internal is None and missing.external is None
    assert "SURFACE_APPLICABILITY_PROVENANCE_REQUIRED" in missing.diagnostics


def test_northern_zone_wall_selection_derives_rsi_rse_and_envelope_u():
    selection = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE,
        northern_climatic_zone_confirmed=True,
        source_reference="project://synthetic-wall", source_field="wall.surfaces"))
    assert selection.status == "RESOLVED"
    assert selection.internal.alpha_w_m2k == Decimal("8.7")
    assert selection.internal.provenance_class == "DERIVED_FROM_NORMATIVE_COEFFICIENT"
    assert selection.external.alpha_w_m2k == Decimal("23")
    assert selection.method is not None

    raw = wall_payload()
    raw["assemblies"][0]["surface_applicability"] = {
        "internal_category": "WALL_FLOOR_SMOOTH_CEILING_LOW_RIB",
        "external_category": "EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE",
        "northern_climatic_zone_confirmed": True,
        "climatic_zone_source_reference": "project://building/rev-5",
        "climatic_zone_source_field": "climatic_zone",
    }
    definition = EnvelopeAssemblyDefinition.model_validate(raw["assemblies"][0])
    # The sourced synthetic layers in wall_payload have R_layers = 2.20.
    bundle = calculate_bundle(EnvelopeConstructionSubmission.model_validate(raw),
        surface_methods={definition.assembly_id: selection.method})
    assembly = bundle.assemblies[0]
    expected_r = Decimal(1) / Decimal("8.7") + Decimal("2.20") + Decimal(1) / Decimal("23")
    assert assembly.layered_resistance_m2k_w == Decimal("2.20")
    assert assembly.total_resistance_m2k_w == expected_r
    assert assembly.u_value_w_m2k == Decimal(1) / expected_r
    assert assembly.calculation_status == "LAYERED_RESISTANCE_RESOLVED"


def test_ribbed_ceiling_requires_explicit_h_over_a_category_evidence():
    no_ratio = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.RIBBED_CEILING_HIGH_RATIO))
    assert no_ratio.internal is None
    assert "RIBBED_CEILING_H_OVER_A_APPLICABILITY_UNRESOLVED" in no_ratio.diagnostics
    resolved = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.RIBBED_CEILING_HIGH_RATIO,
        rib_height_to_spacing=Decimal("0.31"),
        external_category=ExternalSurfaceCategory.UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE))
    assert resolved.internal.alpha_w_m2k == Decimal("7.6")
    assert resolved.external.alpha_w_m2k == Decimal("6")


def test_northern_rows_require_positive_zone_evidence_and_do_not_guess():
    result = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.COLD_BASEMENT_OR_CRAWLSPACE_OPEN_TO_OUTSIDE_NORTHERN_ZONE,
        northern_climatic_zone_confirmed=False))
    assert result.external is None
    assert "SURFACE_RESISTANCE_APPLICABILITY_UNRESOLVED" in result.diagnostics
    no_zone_provenance = _resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.COLD_BASEMENT_OR_CRAWLSPACE_OPEN_TO_OUTSIDE_NORTHERN_ZONE,
        northern_climatic_zone_confirmed=True,
        source_reference="project://wall/revision", source_field="surface-type"))
    assert no_zone_provenance.method is None
    assert "SURFACE_RESISTANCE_APPLICABILITY_UNRESOLVED" in no_zone_provenance.diagnostics


def test_ground_and_ventilated_scope_are_not_silently_simplified():
    ground = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.GROUND_COUPLED))
    assert ground.method is None
    assert "GROUND_BOUNDARY_MODEL_REQUIRED" in ground.diagnostics
    vent = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.EXTERIOR_WALL_WITH_OUTSIDE_VENTILATED_AIR_LAYER))
    assert vent.external.alpha_w_m2k == Decimal("12")
    assert vent.method is None
    assert "VENTILATED_CONSTRUCTION_METHODOLOGY_SCOPE_REVIEW_REQUIRED" in vent.diagnostics
    attic = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.ATTIC_FLOOR_OR_UNHEATED_BASEMENT_WITH_WALL_OPENINGS))
    assert attic.external.alpha_w_m2k == Decimal("12")
    assert attic.method is not None


def test_climate_is_not_an_input_and_normative_revision_invalidates_selection():
    app = SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WINDOW,
        external_category=ExternalSurfaceCategory.EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE,
        northern_climatic_zone_confirmed=True)
    a = resolve_surface_resistances(app)
    b = resolve_surface_resistances(app.model_copy(update={"source_reference": "unrelated climate revision"}))
    # Geometry provenance is part of the call envelope, but climate locality is not
    # accepted as an input to coefficient selection; the data revision is pinned.
    assert a.dataset_digest == b.dataset_digest
    assert a.external.record_id == b.external.record_id
    changed = a.model_copy(update={"dataset_digest": "0" * 64})
    assert changed.dataset_digest != a.dataset_digest
    assert a.dependency_digest != resolve_surface_resistances(app.model_copy(
        update={"external_category": ExternalSurfaceCategory.UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE})).dependency_digest


def test_same_applicability_is_deterministic():
    app = SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WINDOW,
        external_category=ExternalSurfaceCategory.UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE)
    assert resolve_surface_resistances(app) == resolve_surface_resistances(app)
    unrelated_provenance = resolve_surface_resistances(app.model_copy(update={
        "source_reference": "project://different-revision-label",
        "source_field": "room.unrelated-field",
    }))
    assert resolve_surface_resistances(app).dependency_digest == unrelated_provenance.dependency_digest


def test_independent_extract_disagreement_fails_closed():
    assert verify_independent_extract_values(["23", Decimal("23.0")]) == Decimal("23")
    with pytest.raises(ValueError, match="SOURCE_AMBIGUOUS"):
        verify_independent_extract_values(["23", "22"])
    with pytest.raises(ValueError, match="INDEPENDENT_SOURCE_CROSS_CHECK_REQUIRED"):
        verify_independent_extract_values(["23"])
