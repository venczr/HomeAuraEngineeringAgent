# UFH_PROJECT_OWNED_VALUES_TO_PROFILE_BINDING_V1

## Result

`UFH_PROJECT_OWNED_VALUES_TO_PROFILE_BINDING_READY`

The project room adapter now exports a typed collection of approved project-
owned profile values. The authoring loader consumes that collection explicitly;
it never opens a project file. For Test_01, `AirExchangeRate` is the only
currently eligible profile binding.

## Binding path and ownership

```text
rooms.json $.Rooms[].AirExchangeRate
  -> build_ufh_sizing_request_from_project_room()
  -> MappedProjectField(room.insulation.air_changes_per_hour)
  -> collect_project_owned_ufh_values()
  -> ProjectOwnedEngineeringValues
  -> project_context_from_adapter_result()
  -> ProjectContext.project_owned_values
  -> load_questionnaire_authoring(..., project_context)
  -> load_ufh_project_engineering_authoring_template(...)
  -> UFHProjectEngineeringProfile.building_physics.air_changes_per_hour
```

`PROJECT_OWNED_PROFILE_BINDINGS` is the allowlist. Each entry must map to the
existing ownership registry and declare canonical units. The collector accepts
only adapter-mapped values with project-room extraction or canonical project
domain provenance. Routing policy, linked product/normative data, user choices,
and engineering results are not accepted through this path.

The typed value retains project/room IDs, source file, original field path,
source SHA-256, units, transformation, and `PROJECT_DATA_VALUE` authority.
`AuthoringProvenance` carries the original source SHA and source kind through
to `ProfileValueProvenance`; profile digests therefore depend on the bound value
and the exact source revision. Because the current source digest covers the
whole `rooms.json`, even an unrelated edit to that file conservatively changes
the binding/profile digest. A field-level source digest could separate those
dependencies later, but does not exist in the current export contract.

## Test_01 result

The source value comes from the current `projects/Test_01/exports/rooms/rooms.json`
record for room `101DAA3`; tests read it and do not repeat its numeric value as
an expected constant. Its exact value, field path, and file hash are asserted
through the production adapter and binding result.

| Measure | Before binding | After binding |
|---|---:|---:|
| Authoring loader missing paths | 37 | 36 |
| ACH missing path | yes | no |
| Authoring/profile status | `INCOMPLETE` | `INCOMPLETE` |
| Bound project-owned fields | 0 | 1 |
| Project adapter missing inputs | 41 | 41 |

The adapter already mapped ACH before this block, so its 41 missing inputs do
not change. This block closes the separate authoring-loader gap by conveying
that existing mapping into profile construction. The adapter remains
`INCOMPLETE`; no construction, product, fluid, control, routing, or design
condition is invented.

## Conflicts and unresolved values

If a project binding and an authoring ACH value disagree, the loader returns
`INVALID` with `SOURCE_VALUE_CONFLICT`. An equal duplicate resolves to the
project source, preserving its provenance as the owner. If the source has no
ACH field, collection is empty and the loader reports
`AUTHORITATIVE_PROJECT_VALUE_REQUIRED`; there is no fallback.

The questionnaire context carries the typed collection and suppresses an
active question targeting a field already bound from the project. Current
Test_01 questions do not contain an ACH question; regression coverage injects
one to verify the suppression behavior.

## Rejected promotions

The adapter's audit-only room fields remain ineligible: `OutdoorTemperatureC`
is not a design outdoor temperature; `SupplyAirTemperatureC` is not a UFH
thermal boundary or supply condition; `StructuralHeatLossW` is not a U-value;
and `HeatLossWM2` is not declared floor output. No product, fluid, manufacturer,
control, or other physical value is bound.

## Validation boundary

The tests exercise project adaptation, binding, authoring conversion, conflict
handling, and questionnaire suppression. They do not call sizing, routing,
engineering assessment, automatic retry, or real-project shadow validation.
