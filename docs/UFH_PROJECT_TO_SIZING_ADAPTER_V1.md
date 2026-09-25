# UFH_PROJECT_TO_SIZING_ADAPTER_V1

## Scope

`agent.ufh_project_adapter` is a read-only, fail-closed adapter. It accepts a
typed room-export record plus project/building/level/room identity and optional
explicitly linked UFH sizing and engineering source fields. It can return
typed `UFHSizingRequest` and `UFHEngineeringIntegrationInputs` only when every
effective field is explicitly supplied, has field-level provenance, validates,
and agrees with the higher-priority room extraction data.

It does not write project state, generate AutoCAD geometry, call the routing
solver, or replace the sizing, engineering, or retry modules. An adapter
result marked `READY` can be passed to those existing production components.

## Source priority

1. Persisted canonical Project/Domain room and boundary data, when a caller
   selects that source and supplies its identity/provenance.
2. Production room extraction output (`RoomExportReport`), as used by
   `projects/Test_01/exports/rooms/rooms.json`.
3. Explicitly linked engineering metadata, with provenance for every field.

Visualization/export layouts are never consumed. Conflicting lower-priority
values do not override extracted room facts; the adapter reports
`SOURCE_VALUE_CONFLICT` and returns `INVALID`.

The current `Test_01` has no `canonical/current.json`, so this validation uses
the typed production room extraction report and does not create canonical
storage. V1's room-measurement source envelope is `RoomExportReport`; an
optional `DomainDocument` is accepted to verify the project/building/level/room
identity chain, not to silently replace room measurements. Building and level
IDs are not synthesized from the legacy adapter's "Unassigned" placeholders.
If persisted canonical room facts differ from extraction facts, the source
selection must prefer those canonical facts and this adapter must be extended
before those differing fields are mapped.

Repository search found no `.mrd` reader in `agent`, tests, or project APIs; the
binary `HomeAura_Test_01.mrd` is not parsed or treated as an authority here.

## Mappings

| Project field | UFH field | Conversion | Provenance |
| --- | --- | --- | --- |
| `DrawingName` plus caller's explicit project key | `coverage_request.project_id` | Drawing/project label retained; caller identifies the source project | `$.DrawingName` plus adapter input context |
| `Rooms[].SourceHandle` | `coverage_request.room_id` | Exact source handle | `$.Rooms[].SourceHandle` |
| `Rooms[].Boundary.Vertices` | `coverage_request.boundary` | Explicit drawing-unit scale to mm; straight segments only; coordinates rounded half-up to 1 mm; close ring if absent | Boundary vertex JSON path and transformation |
| valid closed mapped boundary | `room.room_area_mm2` | Integer-mm shoelace area | Boundary vertices and shoelace transformation |
| `Rooms[].NetAreaM2` | audit mapping only | × 1,000,000, half-up to integer mm²; not applied without a validated polygon | `$.Rooms[].NetAreaM2` |
| `Rooms[].RoomHeightMm` | `room.room_height_mm` | Round half-up to integer mm | `$.Rooms[].RoomHeightMm` |
| `Rooms[].HeatingTemperatureC` | `room.indoor_temperature_c` | °C unchanged | `$.Rooms[].HeatingTemperatureC` |
| `Rooms[].AirExchangeRate` | `room.insulation.air_changes_per_hour` | 1/h unchanged | `$.Rooms[].AirExchangeRate` |
| `OutdoorTemperatureC`, airflows, extracted heat-loss fields | audit-only `room_source.*` | Original source value/units retained | Exact room field path |
| linked design source | remaining sizing and engineering fields | No conversion unless stated in its field provenance | Per-field source file, SHA-256, path and transformation |

The adapter deliberately does not reinterpret `OutdoorTemperatureC` as an
outdoor design condition and does not feed precomputed `TotalHeatLossW` into
the sizing model, which recomputes its own heat loss from explicit inputs.

## Fail-closed inputs

Every field of `UFHSizingRequest` and `UFHEngineeringIntegrationInputs` must be
present in the linked input fragments, including fields whose model-level
defaults would otherwise fill a value, explicit `null`s, and intentionally
empty lists. Every supplied leaf/list-empty/null must have a provenance record.
This prevents hidden defaults from masquerading as project facts.

An incomplete input returns `INCOMPLETE` and
`PROJECT_UFH_INPUT_INCOMPLETE`, with the precise missing field paths and any
`MISSING_PROVENANCE` diagnostics. A malformed or conflicting source returns
`INVALID`. Neither result contains a partial production request.

## Test_01 finding

The extraction report identifies room code `101` / source handle `101DAA3`,
net area 17.231460571289062 m², height 2800 mm, heating temperature 20 °C,
air-exchange rate 1.0714285373687744 1/h, and extracted heat-loss/airflow
records. Its selected room object has no attached `Boundary`; the report has no
authoritative building/level identities, collector location, exclusions,
exterior-side/segment design, openings schedule, insulation U-values and
boundary temperatures, floor construction/output data, or linked hydraulic
product/engineering inputs. Therefore it maps only observed room facts and
returns `PROJECT_UFH_INPUT_INCOMPLETE`; it cannot become a route candidate.

The net-area conversion is reported for audit only and is not asserted equal
to floor coverage geometry. No UFH visualization export is used as a source.
The adapter result contains 60 precise missing field/identity paths for this
source and emits `PROJECT_UFH_INPUT_INCOMPLETE`; it returns neither a sizing
request nor engineering inputs.

## Digest and read-only behavior

`source_digest` is the caller-provided SHA-256 of the exact source bytes.
`room_geometry_digest` is the canonical digest of the selected room-boundary
object, or of explicitly sourced coverage geometry if room boundary extraction
is unavailable. `adapter_digest` covers identity, source digest, mapped fields,
diagnostics, missing paths, and any complete typed inputs. The adapter has no
file-write or project-store calls.

## Limits

The source geometry adapter currently accepts supported, valid, planar,
closed, straight-segment boundaries expressed in explicit millimetres, metres,
or with an explicit `MetersPerDrawingUnit` scale. Curved or underspecified
segments fail closed rather than being linearized. It does not infer collector position, exterior
wall role, exclusions, construction, or hydraulic data. These remain linked,
explicit source obligations.

The synthetic-complete test creates a `DomainDocument` through the existing
`adapt_rooms_payload` production adapter, gives it explicit test-only
building/level identities, verifies the domain identity chain, builds a typed
UFH request, and runs the existing sizing/routing/engineering/retry pipeline.
It is contract/pipeline compatibility evidence only; it is not a real-project
shadow validation. The separate
`UFH_AUTO_RETRY_REAL_PROJECT_SHADOW_VALIDATION_V1` remains the next block.
