# TEST01_ROOM_BOUNDARY_AND_IDENTITY_RECOVERY_V1

## VERDICT

BLOCKED: ROOM_BOUNDARY_EXPORT_NOT_MATERIALIZED for the current project.
An existing extraction implementation is available; accepted current-project
boundary/identity bindings are not. This is more precise than claiming that
no boundary source exists anywhere.

An important additional source was recovered during investigation: the actual
historical IFC at
C:/AI/HomeAuraEngineeringAgent-ifc-research/manual-export/Test_01_rooms_ifc4.ifc.
Its geometry and building/storey identifiers were reproduced read-only with
the existing production IFC importer and IfcOpenShell. They remain historical
IFC candidates, not newly accepted current project data.

## FILES_CHANGED

Only this document was created. No production adapter or synthetic recovery
test was created. No project, IFC, MRD, DWG, routing or engineering file changed.

## SOURCES_INSPECTED

- agent/domain_models.py: DomainDocument/Project/Building/Level/Room/Boundary.
- agent/domain_adapter.py: _make_boundary, adapt_rooms_payload, placeholder hierarchy.
- agent/project_models.py: SourcePoint and CanonicalProjectModel identity validation.
- agent/project_foundation.py: build_project_seed/build_canonical_project_preview.
- agent/rooms_api.py: RoomBoundary serializer, report reader and persistence endpoints.
- agent/ufh_project_adapter.py: selected room linkage, boundary mapping and area derivation.
- agent/ifc_space_importer.py, ifc_space_models.py, ifc_space_preview_api.py:
  analytic profile/placement/units validation, matching and candidate-only output.
- AutoCAD RoomExportCommands.cs, RoomBoundaryCommands.cs, RoomSyncCommands.cs,
  Commands.cs: extraction, matching, normalization, serialization and snapshot scope.
- All five current/history room JSON files under projects/Test_01/exports/rooms.
  Four are FormatVersion 1.0; one is a placeholder report with version "string".
  None contains Boundary or IfcSpaceGeometry.
- Test_01 model snapshot and historical snapshots; room discovery exports.
- reports/HomeAura_room_geometry_report_2026-07-25.txt,
  HomeAura_Polyline3d_inner_boundary_stage_2026-07-25.txt,
  HomeAura_101DA95_diagnostic_2026-07-25.txt, and IFC research/importer/audit reports.
- docs/examples/rooms.v1.1.polyline3d.example.json: documentation example,
  not a newly authenticated export of the current project.
- CORE-R3 README/manifest; scripts/build_vis008_core_r3.py and
  agent/fh_vis008_core_r3.py. The builder uses explicit design coordinates;
  its named canonical_geometry.json is not an extracted room source.
- C:/AI/HomeAuraEngineeringAgent-ifc-research/manual-export:
  actual IFC, historical candidate JSON, DWG copy and MRD copy.
- Existing temp-build locations referenced by reports: no room export found there;
  the old Local/Temp/HomeAura-room-geometry-verification directory is absent.

## ROOM_101DAA3_BOUNDARY_SOURCE

Current authoritative room extraction: projects/Test_01/exports/rooms/rooms.json,
room SourceHandle 101DAA3, Code 101, NetAreaM2 17.231460571289062.
The file predates the 1.1 boundary payload and lacks Boundary.

Historical native extraction evidence identifies Polyline3d handle 101DA95,
MAGIROOMBORDERS, with selected room marker 101DAA3 and area
19.926653652183532 m². The saved example/reports mark it provisional and report
a 15.64111799893029% area difference. Reports are navigation evidence;
their coordinates were not copied into the current room.

The external IFC is real source data, not a rectangle fabricated from area.
Its exporter is BSProLib 2023.7.0.17 and its header date is 2026-07-26.
The production importer freshly matched it to the current room code/name.
However:
1. the current room has no saved IFC GlobalId binding;
2. matching is normalized_name_to_room_code;
3. existing production semantics produce validated_candidate and do not
   replace Boundary or establish authoritative DomainBuilding/DomainLevel;
4. the associated DWG copy matches the current DWG hash, but the associated
   MRD differs; no export receipt binds this IFC to the current MRD revision.
This mismatch does not prove that geometry changed. It prevents claiming
verified revision equivalence without an explicit source-authority decision.

## BOUNDARY_TRACEABILITY

Historical IFC file SHA-256
-> IfcSpace #31 / GlobalId 3Vmsu$eoz6VAzSuuOWXaVz
-> analytic Body/SweptSolid/IfcExtrudedAreaSolid profile
-> production analyze_ifc_spaces(current rooms payload)
-> normalized_name_to_room_code (101), matching LongName
-> room SourceHandle 101DAA3
-> IfcSpaceGeometry validated_candidate.

Break: candidate selection is not persisted/accepted as the authoritative
Boundary of current project room. The current production importer intentionally
leaves Boundary absent. No acceptance flag, identity binding or geometry was
invented in this block.

## BOUNDARY_GEOMETRY

Fresh read-only production import, run twice:
- distinct vertices: 4; source contains 5 points with repeated endpoint;
- source length unit: millimetre, scale to metres 0.001;
- world loop: metres, planar, CCW, closed, no self-intersection, no holes;
- area: 17.321458459647975 m²;
- perimeter: 16.76796776 m;
- NetAreaM2: 17.231460571289062 m²;
- difference: +0.08999788835891209 m² / +0.5222882180333914%;
- independent production triangulation area difference: 0 m²;
- IFC SHA-256: 01F10257CFCD31DE8B682A2CED11045A3816970B9724C9FD6BA8133325954943;
- diagnostic canonical geometry-payload SHA-256:
  2dcec01aa001038737f62c3b2ee4285922cae872965525fa9ea6f08b567e8260.

The diagnostic geometry digest hashes the production geometry model using
sorted compact JSON; it is not a UFH candidate digest and includes source
metadata. The area difference may arise from different MagiCAD net-area rules
or source revision; the cause was not established. No polygon fitting occurred.

## DWG_TO_ROOM_CHAIN

Existing native implementation:
DWG ModelSpace Polyline/planar Polyline3d
-> RoomBoundaryService.Discover
-> existing normalization/CCW, closure, self-intersection, area/unit checks
-> MatchMarker(position, handle, NetAreaM2)
-> ReadMagiCadRooms, Boundary selection/diagnostics
-> HA_EXPORT_ROOMS
-> exports/rooms/rooms.json plus immutable history
-> RoomExportReport / domain_adapter._make_boundary
-> ufh_project_adapter boundary unit mapping
-> existing integer-mm shoelace area
-> coverage_request.boundary.

Command HA_DISCOVER_ROOM_BOUNDARIES supplies diagnostic discovery.
HA_SYNC_ROOMS reads the same extraction and publishes through the rooms API.
GET /api/v1/projects/Test_01/rooms only reads the saved report; it does not
extract geometry from DWG. No AutoCAD command or UI was started.

Break: no materialized current 1.1 native report was found in project history.
The model snapshot exporter stores entity extents, not ordered room vertices.
A new CAD extractor is not the prerequisite.

## BUILDING_ID_SOURCE

An actual IFC building identifier exists:
IfcBuilding #17, GlobalId 1kDE4UYl903ebi3UdgvjXG, name mc-building.
IfcRelAggregates #56 relates building #17 to storeys including #29.
It is authoritative within that IFC file, but not yet bound to current
HomeAura DomainBuilding. No placeholder ID was promoted.

## LEVEL_ID_SOURCE

An actual IFC storey identifier exists:
IfcBuildingStorey #29, GlobalId 0oQei_Jnn60QnqOIJ3NBzE,
name Этаж 1, elevation 0.
IfcRelAggregates #57 relates it to IfcSpace #31.
Current importer retains StoreyName/elevation but not the storey GlobalId
in IfcSpaceInfo; no canonical identity binding is performed.

The project domain adapter creates LEGACY_PLACEHOLDER objects named
Unassigned Building / Unassigned Level, marked requires_confirmation.
Canonical project construction consumes the supplied domain; it does not
recover missing building/storey identity from the drawing.
Thus current source-binding gaps remain, although external IFC IDs were found.

## ADAPTER_RESULT_BEFORE / ADAPTER_RESULT_AFTER

Unchanged: INCOMPLETE, sizing_request absent, 45 classified gap paths.
Diagnostics:
MISSING_BUILDING_ID, MISSING_LEVEL_ID, MISSING_ROOM_BOUNDARY,
PROJECT_UFH_INPUT_INCOMPLETE.
Adapter digest:
680d3feac65f84beba05283aba6c8950fcfc61bb5248c305b84e4c3f9e87e547.
Two evaluations produced the same digest. No candidate was fed to UFH
sizing/routing/engineering/retry.

## REMAINING_GAPS

Metadata 2; room geometry 4; calculated area 1; building physics 5;
design conditions 5; UFH design settings 8; product properties 13;
fluid properties 4; control properties 2; explicit exclusions declaration 1.
Total 45 paths, unchanged. This is not 45 independent engineering values.
New knowledge: a validated historical IFC geometry and building/storey
identities exist; authority/revision binding, rather than their universal
absence, is the unresolved IFC prerequisite.

## READ_ONLY_PROOF

SHA-256 baseline captured before analysis/tests and compared afterwards:
383 files under agent, autocad-plugin and projects/Test_01 (excluding
__pycache__, bin and obj) plus 4 files in the linked manual-export directory.
387/387 hashes unchanged. No source file was removed. Test caches are outside
this proof; it is a file-content proof, not a claim about all OS metadata.

| Source/protected file | SHA-256 before = after |
|---|---|
| `C:\AI\HomeAuraEngineeringAgent\agent\floor_heating_coverage.py` | `98FB3289186FBF3B42C48EFB027EC0FB12C99E6E3784CB85CA587B18A92C307B` |
| `C:\AI\HomeAuraEngineeringAgent\projects\Test_01\exports\rooms\rooms.json` | `30EE1828E74ECBF1E1B46064C39CE30755A4692FC4CD972D1E38328AFFE0992E` |
| `C:\AI\HomeAuraEngineeringAgent\agent\ufh_engineering_kernel.py` | `56C3D342202005F1948C098D03AF0CEF61D3075EE59993940A95F5923EB346C2` |
| `C:\AI\HomeAuraEngineeringAgent\agent\ufh_auto_retry.py` | `A368319EA6A8ACF596A589F2C5747CEA39FEA885855A0B66A417EAFC6E1D93C7` |
| `C:\AI\HomeAuraEngineeringAgent\agent\ufh_project_adapter.py` | `A2854ECBB69CEF226F5C045486E94879402C83D16B92B22C5650F1B0B7832CF9` |
| `C:\AI\HomeAuraEngineeringAgent\projects\Test_01\Test_01.dwg` | `5A673AAA50F8D29C21555D60D7FEC740FF3CE214CD7EB65AE329DC3B701397AC` |
| `C:\AI\HomeAuraEngineeringAgent\projects\Test_01\HomeAura_Test_01.mrd` | `145BC790981253A1B42F5857FF1B9E64DD4175FF3155D4D8F76437B31A512252` |
| `C:\AI\HomeAuraEngineeringAgent-ifc-research\manual-export\Test_01_rooms_ifc4.ifc` | `01F10257CFCD31DE8B682A2CED11045A3816970B9724C9FD6BA8133325954943` |
| `C:\AI\HomeAuraEngineeringAgent-ifc-research\manual-export\HomeAura_Test_01.mrd` | `8651E8B8A2F9320283F0C05CBF27F54F3BA4AC01F9AE94F3D27C5D89EE282897` |
| `C:\AI\HomeAuraEngineeringAgent-ifc-research\manual-export\Test_01_ifc_copy.dwg` | `5A673AAA50F8D29C21555D60D7FEC740FF3CE214CD7EB65AE329DC3B701397AC` |

## TEST_RESULTS

- tests/test_project_room_geometry_source.py: not created/run; no accepted
  source was connected, and no artificial success fixture was introduced.
- tests/test_ufh_project_adapter.py: 8 passed.
- tests/test_ufh_project_engineering_profile.py: 11 passed.
- tests -k floor_heating: 100 passed.
- git diff --check: exit 0; existing LF/CRLF advisory warnings only.
- Existing production IFC importer: two read-only calls on actual IFC and
  current room JSON; matched/validated_candidate, identical geometry.
- Existing adapter: two calls on current room source; identical INCOMPLETE.

## DETERMINISM

The IFC geometry payload, hierarchy GUIDs and adapter result are reproducible
for these unchanged sources. No full import-report timestamp determinism or
UFH shadow-validation determinism is claimed.

## BLOCKERS

Primary: ROOM_BOUNDARY_EXPORT_NOT_MATERIALIZED in current Test_01 source.
Alternative IFC path: candidate authority/current-source revision not bound.
Building/level: current HomeAura binding missing, although original IFC GUIDs
are recovered and documented.

## LIMITATIONS

No new adapter was justified until source authority is resolved.
No C# change, manual polygon reconstruction, bbox substitute, MRD decoder,
engineering-profile completion or shadow validation was performed.
Historical IFC validation is not acceptance of a current heating plan.

## NEXT_RECOMMENDED_BLOCK

TEST01_GEOMETRY_SOURCE_AUTHORITY_BINDING_V1:
resolve one authoritative geometry revision for Test_01 using the located
IFC and its DWG/MRD evidence; record the accepted IFC-to-room/building/storey
binding (or obtain the existing native boundary export if that source is
selected). Do not change geometry algorithms or run UFH shadow validation.
This next block was not implemented.

