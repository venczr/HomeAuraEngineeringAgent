# UFH Project Engineering Profile Source Completion V1

## Verdict

`IMPLEMENTED_NO_NEW_AUTHORITATIVE_ENGINEERING_BINDINGS_FOR_TEST01`

The completion pass inspected the existing Test_01 project sources that are
allowed for engineering input recovery. It did not promote any physical value
without explicit project/profile authority. Test_01 remains fail-closed and
incomplete.

## Scope

This block does not change UFH mathematics, routing, AutoCAD, geometry binding,
the engineering kernel, optimizer behavior, the 40-80 m legacy routing policy,
or public API contracts.

## Sources Inspected

Authoritative and read-only sources:

- `projects/Test_01/exports/rooms/rooms.json`
- the already reviewed Test_01 geometry authority binding source, when
  available through `assess_test01_geometry_authority(...)`

Expected explicit profile sidecar locations were checked but are absent:

- `projects/Test_01/ufh_project_engineering_profile.json`
- `projects/Test_01/exports/engineering/ufh_project_engineering_profile.json`
- `projects/Test_01/exports/ufh/ufh_project_engineering_profile.json`

UFH visualization exports were not used as engineering input sources.

## Candidate Values

Accepted as already bound before this block:

| Source field | Existing target | Status |
|---|---|---|
| `HeatingTemperatureC` | `sizing.room.indoor_temperature_c` | already bound |
| `AirExchangeRate` | `sizing.room.insulation.air_changes_per_hour` | already bound |

Inspected but not promoted:

| Source field | Requested target | Reason |
|---|---|---|
| `OutdoorTemperatureC` | `sizing.room.outdoor_design_temperature_c` | room extraction does not prove design-condition authority |
| `SupplyAirTemperatureC` | `sizing.room.insulation.floor_boundary_temperature_c` | supply-air temperature is not a floor-boundary condition |
| `StructuralHeatLossW` | `sizing.room.insulation.exterior_wall_u_value_w_m2k` | precomputed heat-loss output is not a U-value source |
| `HeatLossWM2` | `sizing.floor_construction.declared_output_at_100mm_w_m2` | room heat-loss intensity is not a floor product declaration |

## Before And After

On the bound Test_01 source from the previous authority block, the adapter
starts and ends with 41 missing paths. No required external gap was covered by
this pass because no explicit UFH engineering profile/product/fluid/control
source exists in the reviewed project.

## Provenance Coverage

Definition:

`newly covered required-external classified gap paths / required-external gap paths before completion`

For Test_01:

- newly covered: 0
- required-external gaps before: 40
- required-external gaps after: 40
- coverage: 0.0%

All accepted new bindings have provenance by construction. In this block the
accepted-new-binding set is empty.

## Remaining Source Gaps

Remaining gaps still require explicit project/profile sources:

- design conditions such as outdoor design temperature and boundary
  temperatures;
- building physics such as U-values, ventilation heat-capacity factor and
  thermal bridge allowance;
- UFH routing/design settings such as collector point, spacing and margin;
- floor construction and pipe/manifold product properties;
- fluid properties;
- control characteristic data;
- explicit empty declarations for optional project collections such as
  exclusions.

## Tests

The focused tests are in
`tests/test_ufh_project_engineering_source_completion.py`.

