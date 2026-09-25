# TEST01_SP60_ENGINEERING_SOURCE_BINDING_V1

## Result

The source/readiness adapter is read-only and targets only Test_01 Room Code
101 / marker `101DAA3`. It reuses the revision-pinned IFC geometry and identity
decision, the existing project-to-sizing adapter, and the existing
project-owned-value collector. It never invokes transmission, ventilation,
infiltration, A.1 aggregation, UFH sizing, routing, kernel, or retry code.

The current accepted source set resolves identity, the closed IFC room
boundary, MagiCAD net floor area, perimeter derived from the accepted ordered
vertices, source room height, net room volume derived from area × height, the
existing indoor setpoint, and project ACH as a project observation. IFC contour
area and MagiCAD net area are distinct and both are retained with provenance.
The exported `NetVolumeM3` is comparison-only; the derived volume is explicitly
linked to source `NetAreaM2` and `RoomHeightMm`.

The area readings are `NetAreaM2 = 17.231460571289062 m²` and accepted
IFC-contour area `17.321458459647975 m²` (difference `+0.089997888358913 m²`).
Accepted-boundary perimeter is derived as `16.76796776 m`; source height is
`2800 mm`; derived volume from net area × height is
`48.2480895996093736 m³`. The source's `NetVolumeM3` is not used in that
derivation. Current source-completion audit inspected 9 candidates and found
`UNCHANGED_INCOMPLETE`, with zero new authoritative bindings.

The current DWG-derived model snapshot contains four MagiCAD exterior-wall
objects (`MAGIEXTERIORWALLS`) whose extents touch the accepted room polygon.
They are reported as geometry candidates, not promoted to a complete thermal
boundary inventory. The IFC has no `IfcRelSpaceBoundary`, `IfcWall`, `IfcSlab`,
`IfcWindow`, `IfcDoor`, opening, or material/layer records. No floor/ceiling
semantics, wall net areas, openings-absent assertion, construction, U-value,
thermal bridge, or opposite-side temperature is fabricated.

## Input audit

| Group | Test_01 result |
| --- | --- |
| Identity / geometry | Bound from the reviewed current-DWG/companion-IFC revision set |
| Area / perimeter / room height / volume | Source-bound or explicitly derived; no building height inference |
| Room use / Q_mts | Unresolved; generic room name is not a use classification |
| Climate | Locality unresolved; `OutdoorTemperatureC` remains audit-only; SP131 dataset has no wind-speed field |
| Thermal boundaries | Four exterior-wall geometry candidates; complete room thermal-boundary relationships unresolved |
| Openings | No opening entities observed in inspected exports, but no explicit proof of an empty inventory |
| Constructions / U / bridges | No authoritative assemblies, layers, products, U-values, or bridge inventory |
| Ventilation | Supply/extract flows and ACH exist as room-export observations; required outside-air semantics are not established |
| Infiltration | No complete air-permeable element inventory, `Ru`, element heights, building height, wind, `kz`, or pressure mode |

The profile source audit paths under the project do not contain a linked
engineering profile. The existing file in `docs/` is only an unset authoring
template. No project-side questionnaire answer store was found. No project
authoring answers were inferred from the template or room labels.

## Minimum human/project input plan

The UI-consumable plan has eight top-level prompts: project locality; room use
and warming-process scope; conditions below and above; opening inventory;
construction source; ventilation design basis; and an infiltration source
package. Existing `climate`, `below`, `above`, `openings`, and `envelope`
question IDs are explicitly reused where compatible, except that the legacy
`openings` prompt only asks about undescribed UFH openings and is not proof of
an empty thermal-opening inventory; therefore the SP60 inventory confirmation
has a distinct question ID. Detailed construction,
ventilation, and infiltration data are conditional follow-ups. Design relative
humidity, construction moisture zone, SP345 operating condition, material
properties, and thermal bridge details remain conditional rather than being
shown as raw fields up front.

The plan converts to the existing UI-neutral `Question` model. It does not
persist answers or claim to complete the questionnaire session: Test_01 has no
project-side answer store, and the authoring JSON is still only an unset
template.

## Readiness

`Q_tr`, `Q_vent`, `Q_inf`, `Q_mts`, SP60 A.1, and the UFH heat-load handoff all
remain `NOT_READY`. The project adapter still reports 41 UFH engineering gaps;
this block does not alter or claim reduction of that separate profile gap
count. Test_01 files are read-only and no real heat-loss or UFH computation is
run. The current SP60 matrix has 6 `RESOLVED`, 2 `DERIVED`, 15 `UNRESOLVED`,
and 6 `BLOCKED_BY_PARENT_DEPENDENCY` entries.
