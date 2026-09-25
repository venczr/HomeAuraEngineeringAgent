# UFH Project Engineering Input Contract V1

## Decision and boundary

This contract separates the authoritative room source from project/system
engineering settings. It does not change the room/project serialization model,
geometry algorithms, heat-loss equations, engineering kernel, auto-retry, or the
40–80 m legacy routing policy. Test_01 remains intentionally incomplete.

The new `UFHProjectEngineeringProfile` owns design conditions, building
physics, floor construction/product data, non-geometric routing settings, and
engineering integration inputs. It contains no room boundary or room identity.
Every leaf represented by the profile must have a source file, SHA-256, source
field path, source kind, and optional deterministic transformation.

Source priority is: (1) canonical project/domain object when its IDs and values
resolve to the selected room; (2) the production room-extraction record for
room identity/geometry/observed room quantities; (3) an explicitly linked,
provenance-bearing engineering profile or input fragment. Conflicting sources
are invalid; they are not silently merged. UFH visualization exports and
historical snapshots are comparison evidence only.

## Ownership classification of every sizing/integration input

“External” means the value needs an authoritative source/declaration before it
can affect a request. “Default” means the adapter may materialize a value only
with the stated explicit provenance. Empty geometry collections require an
explicit empty declaration; omission does not prove that the room has no such
features.

| Input field(s) | Source class | External? | Current owner/source | Default allowed? | Action |
|---|---|---:|---|---|---|
| `identity.project_id`, `coverage_request.project_id` | STRUCTURAL_METADATA | Yes, identity | Drawing/project label; canonical Project preferred | No invented ID | Preserve source identity/provenance |
| `identity.building_id`, `identity.level_id` | STRUCTURAL_METADATA | Yes, identity | Canonical project hierarchy only | No | Require true IDs; reject provisional “unassigned” placeholders |
| `identity.room_id`, `coverage_request.room_id` | STRUCTURAL_METADATA | Yes, identity | Persistent room source handle (`101DAA3`) | No | Preserve source handle and reference |
| `schema_version` at sizing and coverage levels | STRUCTURAL_METADATA | No | Fixed API schema tag | Yes: `SYSTEM_STRUCTURAL_DEFAULT` | Materialize `1.0`; no physical calculation effect |
| `room.room_area_mm2` | CALCULATED | No separate area datum | Derive deterministically from accepted boundary in mm | No independent area default | Missing boundary is the blocker; never substitute net-area estimate into polygon contract |
| `room.room_height_mm`, `room.exterior_wall_length_mm`, `room.openings` | ROOM_GEOMETRY | Yes | Room extraction/boundary plus opening geometry | No | Map from accepted room geometry; openings need explicit collection, including empty |
| `coverage_request.boundary.points` | ROOM_GEOMETRY | Yes | Selected production Room Boundary | No | Use only closed/valid/supported boundary with explicit units |
| `coverage_request.exterior_wall_segments` | ROOM_GEOMETRY | Yes | Selected room boundary plus authoritative façade-side evidence | No | Do not infer exterior side from the visual export |
| `coverage_request.exclusion_zones` | OPTIONAL_EXPLICIT_EMPTY | Yes, explicit declaration | Room/project plan owner | No inferred empty | An empty list must be explicit; a kitchen is not an exclusion by itself |
| `room.indoor_temperature_c`, `engineering.theta_indoor_c` | DESIGN_CONDITION | Yes | Room design setpoint / linked design conditions | No | Provenance required; observed sensor values are not design conditions |
| `room.outdoor_design_temperature_c`, `engineering.theta_below_c`, `engineering.theta_supply_c` | DESIGN_CONDITION | Yes when consumed | Project design conditions / floor-boundary conditions | No | `theta_below_c` reuses sizing's floor-boundary value and is not a second external input; outdoor observation is not design temperature; supply temperature only for `solve_return` |
| `floor_boundary_temperature_c`, `ceiling_boundary_temperature_c` | DESIGN_CONDITION | Yes | Adjacent-space / project boundary condition | No | Require explicit values; no ambient assumptions |
| `exterior_wall_u_value_w_m2k`, `floor_u_value_w_m2k`, `ceiling_u_value_w_m2k`, `air_changes_per_hour`, `ventilation_heat_capacity_factor_wh_m3k`, `thermal_bridge_allowance_percent` | BUILDING_PHYSICS | Yes | Validated building assemblies, ventilation design, or linked heat-loss source | No | Preserve units and source; measured room air exchange does not silently become design ventilation |
| `design_margin_percent` | UFH_DESIGN_SETTING | Yes | Explicit project sizing policy | No | No implicit margin |
| `wall_offset_mm`, `spacing_mm`, `field_spacing_mm`, `perimeter_spacing_mm`, `perimeter_band_depth_mm`, `perimeter_priority_mode`, `preferred_topology`, `routing_mode`, `turn_radius_mm`, `installation_grid_spacing_mm` | UFH_DESIGN_SETTING | Yes for non-default choices | Project UFH routing profile | Existing documented API defaults only, materialized with provenance | Geometry-affecting choices are not physical engineering constants; do not present defaults as owner choices |
| `requested_circuit_count` | UFH_DESIGN_SETTING | No when automatic mode selected | Orchestration request | Yes: `None`, with explicit system provenance | `None` preserves production automatic count; 1–3 must be explicit exact-count requests |
| `collector_point` | UFH_DESIGN_SETTING | Yes | Project/manifold layout | No | Must be project-sourced; adapter does not choose it |
| `minimum_circuit_length_mm`, `maximum_circuit_length_mm` | LEGACY_ROUTING_POLICY | No project authoring | `LEGACY_MVP_ROUTING_POLICY` | Yes: 40,000/80,000 mm with policy provenance | This is not represented as an EN 1264 limit |
| `request_reference` | STRUCTURAL_METADATA | No | Optional request correlation metadata | Yes: explicit `None` default record | Does not alter physics |
| `declared_output_at_100mm_w_m2`, `declared_output_at_200mm_w_m2`, `output_basis_reference`, `k_h_w_m2k`, `r_o_m2k_w`, `r_u_m2k_w`, pipe ID/roughness, fixed losses and manufacturer maximum pressure | PRODUCT_PROPERTY | Yes | Validated floor build-up, pipe/manifold manufacturer data, or sourced pressure calculation | No | Store product/document revision and scope; do not infer from visualization |
| `surface_limit_w_m2`, `common_circuit.control` | CONTROL_PROPERTY | Yes when balance/control evaluation is claimed | Applicable control/manufacturer characteristic and design limit | No hidden control model | Explicitly source or explicitly declare unavailable; do not claim balanceability without the characteristic |
| `common_circuit.fluid.density_kg_m3`, `dynamic_viscosity_pa_s`, `specific_gravity`, `c_w_j_kgk` | FLUID_PROPERTY | Yes under current adapter contract | Named fluid and temperature/source data; kernel V1 restricts `c_w` to its declared water constant | No undocumented fluid defaults | Retain explicit values/provenance and validate against kernel support |
| `engineering.area_basis`, `engineering.mode`, `engineering.sigma_k` | UFH_DESIGN_SETTING | Yes when selected by current integration mode | Explicit integration method/thermal design condition | No | `sigma_k` is required for `solve_supply`; the kernel solves it for `solve_return` |
| `engineering.theta_supply_c` | DESIGN_CONDITION / CALCULATED | Conditional | Project design value for `solve_return`; kernel output for `solve_supply` | Unused counterpart is omitted, not guessed | Adapter does not require it in `solve_supply` |
| `engineering.common_circuit.embedded_losses.continuous_bends_pa` | PRODUCT_PROPERTY | Yes in current V1 input shape | Sourced bend-loss data/calculation | No | Current production adapter does not derive bend pressure from geometry, so it remains explicit |
| Heat loss breakdown, required heat, served area, heat allocation, q, mass flow, Reynolds, friction, pressure and balance result | CALCULATED | No | Existing sizing/coverage/engineering pipeline | Not applicable | Never accept as project input; recompute per candidate |

`FIELD_CLASSIFICATION` in `agent/ufh_project_engineering_profile.py` is the
machine-readable registry for every leaf request input. Conditional semantics
are documented above: in `solve_return`, sigma is solved and supply temperature
is an input; in `solve_supply`, supply is solved and sigma is an input. The
adapter skips only the mode-inapplicable counterpart.

## Defaults made explicit

Only defaults already declared by the current public model are eligible for
materialization. The adapter records each default in `mapped_fields` with a
stable digest and source marker. Structural/API routing defaults include
`requested_circuit_count=None`, `routing_mode="legacy"`, turn radius 100 mm,
perimeter priority true and unset optional topology/spacing refinements. These
are routing semantics—not verified owner preferences—and are visible in
provenance. The 40,000/80,000 mm limits are separately sourced to
`LEGACY_MVP_ROUTING_POLICY`. Schema tags are fixed metadata. Physical parameters
and exclusions do not receive system defaults.

The materialized structural defaults do not make Test_01 complete: mandatory
project geometry, design conditions, building physics, floor/product values,
fluid and engineering inputs remain absent and fail closed.

## Test_01 findings

Selected source: `projects/Test_01/exports/rooms/rooms.json`, the production
room-extraction result. It is the best currently persisted room source because
it contains room handle/code, room height, area, indoor setpoint, ventilation
observations and precomputed heat-loss figures with a direct extractor
provenance. It does not contain `Boundary` for handle `101DAA3`.

`agent/domain_adapter.py` only promotes `Room.Boundary` when that field exists;
otherwise boundary is `None`. Its legacy importer creates deterministic
“Unassigned Building” and “Unassigned Level” placeholders and explicitly marks
them provisional. These are not authoritative building/level IDs. A historical
model snapshot contains a `MAGIROOMBORDERS` entity extent for `101DAA3`-adjacent
data, but only a bounding box, not the selected room contour vertices or a
validated room-to-boundary relation. No `.mrd` reader/source producing a linked
canonical room boundary was found. The CORE-R3 visualization export is not used
as a geometry source. Finding: `ROOM_BOUNDARY_SOURCE_MISSING`.

The current adapter reports 45 classified gap paths and 27 mapped fields for
Test_01. This is a re-audit count after removal of safe system/policy defaults;
it is not a claim that all gaps are user-authored parameters. Of those paths,
2 are identity metadata, 1 is calculated room area, and
`engineering.theta_below_c` is an alias of the sizing floor-boundary input,
not a distinct external value. `sigma_k` and `theta_supply_c` are mode-specific
alternatives, so only one is externally supplied for a selected solve mode.

| Source class | Test_01 gap count | Gaps |
|---|---:|---|
| STRUCTURAL_METADATA (2) | `identity.building_id`; `identity.level_id` |
| ROOM_GEOMETRY (4) | `sizing.coverage_request.boundary.points`; `sizing.coverage_request.exterior_wall_segments`; `sizing.room.exterior_wall_length_mm`; `sizing.room.openings` |
| BUILDING_PHYSICS (5) | `sizing.room.insulation.exterior_wall_u_value_w_m2k`; `.floor_u_value_w_m2k`; `.ceiling_u_value_w_m2k`; `.ventilation_heat_capacity_factor_wh_m3k`; `.thermal_bridge_allowance_percent` |
| DESIGN_CONDITION (5 paths; 4 independent values before mode selection) | `sizing.room.outdoor_design_temperature_c`; `sizing.room.insulation.floor_boundary_temperature_c`; `.ceiling_boundary_temperature_c`; `engineering.theta_below_c` (alias of floor boundary, not separately external); `.theta_supply_c` (only for solve-return mode) |
| UFH_DESIGN_SETTING (8) | `engineering.area_basis`; `.mode`; `.sigma_k` (only for solve-supply mode); `sizing.coverage_request.collector_point.x_mm`; `.collector_point.y_mm`; `sizing.coverage_request.spacing_mm`; `.wall_offset_mm`; `sizing.room.insulation.design_margin_percent` |
| PRODUCT_PROPERTY (13) | `engineering.common_circuit.embedded_losses.continuous_bends_pa`; `.other_fixed_pipe_path_pa`; `.pipe_fittings_pa`; `.fixed_manifold_losses`; `.inner_diameter_m`; `.manufacturer_max_circuit_pressure_pa`; `.roughness_m`; `engineering.k_h_w_m2k`; `.r_o_m2k_w`; `.r_u_m2k_w`; `sizing.floor_construction.declared_output_at_100mm_w_m2`; `.declared_output_at_200mm_w_m2`; `.output_basis_reference` |
| FLUID_PROPERTY (4) | `engineering.c_w_j_kgk`; `engineering.common_circuit.fluid.density_kg_m3`; `.dynamic_viscosity_pa_s`; `.specific_gravity` |
| CONTROL_PROPERTY (2) | `engineering.surface_limit_w_m2`; `engineering.common_circuit.control` |
| OPTIONAL_EXPLICIT_EMPTY (1) | `sizing.coverage_request.exclusion_zones` |
| CALCULATED (1) | `sizing.room.room_area_mm2` (requires the absent accepted boundary; `NetAreaM2` remains informational) |
| LEGACY_ROUTING_POLICY | 0 | 40–80 m was materialized from policy with provenance |

`engineering.theta_indoor_c` is not a Test_01 gap: the adapter reuses the
explicit room `HeatingTemperatureC` design setpoint with its source reference
and a deterministic copy transformation. The exact complete gap set is available in the adapter result's
`classified_gaps`; tests assert every current gap is classified and none is
`UNKNOWN`. Room extraction currently maps 12 source values (including
non-request observations such as `TotalHeatLossW`); other mapped records are
system defaults/policy values or that linked setpoint. The extracted total
heat loss is not substituted for the sizing calculation.

## Integration and failure semantics

`ProjectRoomUfhSource.engineering_profile` accepts the typed profile. The
adapter maps it to existing `UFHSizingRequest` and
`UFHEngineeringIntegrationInputs`, merges only agreeing source fragments,
requires leaf provenance, reports categorized gaps, and fails closed on any
missing required datum, conflict, invalid model value, or identity mismatch.
Geometry remains in the room source/linked geometry fragment and is not copied
into the engineering profile. Identical source/profile data produce identical
adapter digests.

This is a contract and adapter-validation result only. It does not validate a
real-project retry run and does not authorize publication or DWG changes.
