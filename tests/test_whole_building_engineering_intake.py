import pytest
from agent.whole_building_engineering_intake import (
    ConstructionInput,
    MINIMUM_ENGINEERING_AUTHORITY_FIELDS,
    assess_minimum_engineering_intake,
    assess_uzigonty_climate_binding,
)
from agent.ufh_climate_resolver import load_climate_dataset

def test_construction_accepts_known_u_or_layers_for_downstream_resolvers():
    assert ConstructionInput(input_mode="KNOWN_U_VALUE",u_value_w_m2k=0.2,source_reference="approved").u_value_w_m2k==0.2
    value=ConstructionInput(input_mode="LAYER_ASSEMBLY",layers=({"material":"brick","thickness_mm":250},),source_reference="owner description")
    assert value.layers[0].thickness_mm==250

def test_uzigonty_requires_normative_binding_without_proximity_substitution():
    result=assess_uzigonty_climate_binding(load_climate_dataset())
    assert result.resolver_exact_match_available is False
    assert result.status=="NORMATIVE_LOCALITY_BINDING_REQUIRED"


def test_minimum_intake_exposes_exact_missing_authority_fields_without_defaults():
    partial = {
        "exterior_wall": {"input_mode": "KNOWN_U_VALUE", "u_value_w_m2k": 0.2},
        "openings": (),
    }
    result = assess_minimum_engineering_intake(partial)
    assert result.status == "AUTHORITY_INPUT_REQUIRED"
    assert result.missing_authority_fields == tuple(
        field for field in MINIMUM_ENGINEERING_AUTHORITY_FIELDS if field not in partial
    )
    assert "exterior_wall" not in result.missing_authority_fields
    assert "openings" not in result.missing_authority_fields
    assert partial == {
        "exterior_wall": {"input_mode": "KNOWN_U_VALUE", "u_value_w_m2k": 0.2},
        "openings": (),
    }


def test_minimum_intake_only_advances_after_all_authority_fields_are_present():
    payload = {field: {} for field in MINIMUM_ENGINEERING_AUTHORITY_FIELDS}
    result = assess_minimum_engineering_intake(payload)
    assert result.status == "READY_FOR_RESOLVER_VALIDATION"
    assert result.missing_authority_fields == ()
