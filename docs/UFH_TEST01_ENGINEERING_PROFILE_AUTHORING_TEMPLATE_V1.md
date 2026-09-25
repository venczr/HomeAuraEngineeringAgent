# UFH Test01 Engineering Profile Authoring Template V1

## Verdict

`UFH_TEST01_ENGINEERING_PROFILE_AUTHORING_TEMPLATE_READY`

This block creates a strict authoring contract for the remaining Test_01 UFH
engineering inputs. It does not fill any physical value for Test_01 and does
not run UFH sizing, routing, hydraulics, auto-retry or shadow validation.

## Artifacts

- `agent/ufh_project_engineering_profile_authoring.py`
- `docs/Test_01_UFH_engineering_profile_authoring_template.json`
- `tests/test_ufh_project_engineering_profile_authoring.py`

The Test_01 JSON template is intentionally incomplete. It records context that
is already known from authoritative project sources and leaves the remaining
engineering decisions as `UNSET`.

## Authoring Model

Each field carries a typed status:

- `UNSET`
- `EXPLICIT_VALUE`
- `CATALOG_REFERENCE`
- `NORMATIVE_REFERENCE`
- `DERIVED`
- `EXPLICIT_EMPTY`

Physical values require value, canonical unit and provenance. `UNSET` may not
carry a value. `EXPLICIT_EMPTY` is distinct from omission and requires
provenance.

## Remaining 41 Field Mapping

| Field | Authoring/source type |
|---|---|
| `sizing.room.outdoor_design_temperature_c` | `NORMATIVE_PROJECT_CONDITION` |
| `sizing.room.insulation.floor_boundary_temperature_c` | `NORMATIVE_PROJECT_CONDITION` |
| `sizing.room.insulation.ceiling_boundary_temperature_c` | `NORMATIVE_PROJECT_CONDITION` |
| `engineering.theta_below_c` | `DERIVED_AFTER_SELECTION` |
| `engineering.theta_supply_c` | `NORMATIVE_PROJECT_CONDITION` |
| `sizing.room.insulation.exterior_wall_u_value_w_m2k` | `BUILDING_CONSTRUCTION_PROPERTY` |
| `sizing.room.insulation.floor_u_value_w_m2k` | `BUILDING_CONSTRUCTION_PROPERTY` |
| `sizing.room.insulation.ceiling_u_value_w_m2k` | `BUILDING_CONSTRUCTION_PROPERTY` |
| `sizing.room.insulation.ventilation_heat_capacity_factor_wh_m3k` | `BUILDING_CONSTRUCTION_PROPERTY` |
| `sizing.room.insulation.thermal_bridge_allowance_percent` | `BUILDING_CONSTRUCTION_PROPERTY` |
| `sizing.coverage_request.collector_point.x_mm` | `USER_PROJECT_DECISION` |
| `sizing.coverage_request.collector_point.y_mm` | `USER_PROJECT_DECISION` |
| `sizing.coverage_request.spacing_mm` | `USER_PROJECT_DECISION` |
| `sizing.coverage_request.wall_offset_mm` | `USER_PROJECT_DECISION` |
| `sizing.room.insulation.design_margin_percent` | `USER_PROJECT_DECISION` |
| `engineering.area_basis` | `USER_PROJECT_DECISION` |
| `engineering.mode` | `USER_PROJECT_DECISION` |
| `engineering.sigma_k` | `NORMATIVE_PROJECT_CONDITION` |
| `sizing.coverage_request.exclusion_zones` | `EXPLICIT_EMPTY_CONFIRMATION` |
| `sizing.coverage_request.exterior_wall_segments` | `DERIVED_AFTER_SELECTION` |
| `sizing.room.exterior_wall_length_mm` | `DERIVED_AFTER_SELECTION` |
| `sizing.room.openings` | `EXPLICIT_EMPTY_CONFIRMATION` |
| `sizing.floor_construction.declared_output_at_100mm_w_m2` | `UFH_PRODUCT_SELECTION` |
| `sizing.floor_construction.declared_output_at_200mm_w_m2` | `UFH_PRODUCT_SELECTION` |
| `sizing.floor_construction.output_basis_reference` | `UFH_PRODUCT_SELECTION` |
| `engineering.k_h_w_m2k` | `UFH_PRODUCT_SELECTION` |
| `engineering.r_o_m2k_w` | `UFH_PRODUCT_SELECTION` |
| `engineering.r_u_m2k_w` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.inner_diameter_m` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.roughness_m` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.embedded_losses.continuous_bends_pa` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.embedded_losses.pipe_fittings_pa` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.embedded_losses.other_fixed_pipe_path_pa` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.fixed_manifold_losses` | `UFH_PRODUCT_SELECTION` |
| `engineering.common_circuit.manufacturer_max_circuit_pressure_pa` | `UFH_PRODUCT_SELECTION` |
| `engineering.c_w_j_kgk` | `FLUID_SELECTION` |
| `engineering.common_circuit.fluid.density_kg_m3` | `FLUID_SELECTION` |
| `engineering.common_circuit.fluid.dynamic_viscosity_pa_s` | `FLUID_SELECTION` |
| `engineering.common_circuit.fluid.specific_gravity` | `FLUID_SELECTION` |
| `engineering.surface_limit_w_m2` | `CONTROL_PRODUCT_SELECTION` |
| `engineering.common_circuit.control` | `CONTROL_PRODUCT_SELECTION` |

## Human Decision Groups

The low-level gaps are grouped for authoring into:

- design climate and boundary conditions;
- building construction physics;
- UFH layout policy and collector coordinate decision;
- floor system selection;
- pipe selection;
- manifold selection;
- fluid definition;
- control characteristic selection;
- explicit empty confirmations for exclusions/openings.

The template does not duplicate project identity, room boundary, room area,
indoor room temperature or ACH. These remain owned by authoritative project
sources.

## Mode Alternatives

The template supports both production modes:

- `solve_supply`: author `sigma_k`; `theta_supply_c` must remain `UNSET`.
- `solve_return`: author `theta_supply_c`; `sigma_k` must remain `UNSET`.

The mode-inapplicable value is not guessed.

## Product And Fluid Abstraction

The authoring model exposes logical groups such as `pipe_product_id`,
`manifold_product_id`, `control_characteristic`, `fluid_definition_id` and
`floor_system_product_id`. Because no real product catalog exists yet, raw
kernel fields are still materialized only from explicit values with provenance.
No fake catalog is created.

## Units And Provenance

Numeric fields use canonical units in field validation, including:

- `degC`
- `W/(m2*K)`
- `Wh/(m3*K)`
- `%`
- `mm`
- `m`
- `Pa`
- `kg/m3`
- `Pa*s`
- `J/(kg*K)`
- `W/m2`
- `m2*K/W`

Every physical value must include:

- `source_type`;
- `source_reference`;
- `source_field`;
- optional `author_or_confirmation`;
- `transformation`;
- `units`.

## Test01 Template

`docs/Test_01_UFH_engineering_profile_authoring_template.json` is an
unfilled project-side authoring artifact. It is safe because it is not stored
inside `projects/Test_01` and does not alter project persistence.

## Synthetic Complete Proof

Tests include a fully completed synthetic authoring payload. It converts to the
existing `UFHProjectEngineeringProfile`, including the existing
`UFHProjectEngineeringInputs` and `CommonCircuitInputs`. This is only a contract
proof and is not Test_01 project data.

## Limitations

The loader currently accepts direct authoring payloads. It does not load a real
manufacturer or normative catalog and does not infer any physical parameter
from room heat-loss results or visualization exports.

