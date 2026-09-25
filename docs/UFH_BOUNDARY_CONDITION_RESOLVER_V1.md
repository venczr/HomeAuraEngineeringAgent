# UFH Boundary Condition Resolver V1

## Boundary between semantics and physics

The existing `below` and `above` questionnaire items now dispatch to one
side-scoped `BOUNDARY_CONDITION_RESOLVER`. Its typed result is stored through
the existing `ResolverResult` → `apply_resolver_result` → authoring handoff at
`thermal_boundary_conditions.below|above`.

The authoring template stores the semantic object and its user-decision
provenance. Numeric `floor_boundary_temperature_c` and
`ceiling_boundary_temperature_c` remain separately owned and are never filled
by this resolver. Consequently, a resolved semantic boundary does not make the
authoring profile ready or remove those numeric adapter/profile gaps.

## V1 mapping

| Existing answer | Semantic boundary type | Additional dependency |
| --- | --- | --- |
| `HEATED_ROOM` | `HEATED_INTERIOR_SPACE` | Adjacent zone/design temperature; no zone is inferred |
| `UNHEATED_BASEMENT`, `UNHEATED_ATTIC` | `UNHEATED_INTERIOR_SPACE` | Explicit reference temperature or a future normative method |
| `OUTDOOR`, `ROOF_OUTDOOR` | `OUTDOOR_AIR` | Existing climate condition dependency; no new climate lookup |
| `GROUND` | `GROUND` | Future ground-boundary model |
| `VENTILATED_VOID` | `VENTILATED_VOID` | Future void-specific thermal method |
| `OTHER` | `UNKNOWN_PROJECT_SPECIFIC` | Further project-specific classification/method |

The `VENTILATED_VOID` choice was added to the existing below/above questions;
it is not collapsed into outdoor air. `OTHER` is retained as an explicit
unknown category and never mapped to an assumed physical temperature.

## Dependency and invalidation semantics

Each side has its own resolver request and output. The below request depends
only on `below` and its conditional `below.details`; the above request depends
only on `above` and `above.details`. A change to one side leaves the other
side's binding intact. An unrelated floor-finish answer does not invalidate
either side.

For an outdoor boundary, the request additionally records the climate resolver
dependency digest and whether the climate design condition is resolved. A
climate answer/revision therefore rebinds the outdoor-side semantic dependency
while leaving `OUTDOOR_AIR` unchanged. Interior, ground, and ventilated-void
semantic results do not depend on climate.

## Project adjacency source audit

The revision-pinned Test_01 IFC evidence contains the target `IfcSpace`, but no
`IfcRelSpaceBoundary`, `IfcZone`, zone assignment, or adjacent-space thermal
relationship. The existing importer records the space geometry and spatial
containment; it does not expose vertical thermal adjacency. Therefore the
resolver leaves `adjacent_zone_id` unset and reports that authoritative
adjacent-zone/design-temperature data is unavailable. It does not infer a
neighbor from room names, elevations, or geometry.

## Scope and limitations

This is classification and dependency bookkeeping only. No U-value,
transmission heat loss, ground model, unheated-space factor, thermal bridge,
or numeric boundary temperature is calculated. Test_01 receives no boundary
answer; test answers exist only in copied in-memory sessions. No sizing,
routing, kernel, retry, DWG, MRD, or AutoCAD path is invoked.
