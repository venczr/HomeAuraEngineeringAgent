# TEST01_GEOMETRY_SOURCE_AUTHORITY_BINDING_V1

## VERDICT

TEST01_GEOMETRY_SOURCE_BOUND_AUTHORITATIVE.

A reviewed, revision-pinned, read-only binding is implemented for room 101 /
DWG marker 101DAA3. This decision accepts a combination of DWG revision,
historical export provenance, room identity and four-wall geometric fingerprint.
It does not require byte-identical MRD files and does not claim MRD equivalence.
No automatic general promotion policy for arbitrary IFC exports was added.

## FILES_CHANGED

Created agent/test01_geometry_source_authority.py,
tests/test_test01_geometry_source_authority.py and this document.
Modified only agent/ufh_project_adapter.py among existing files:
optional authoritative_boundary + boundary_provenance reuse the existing
boundary unit conversion and area derivation. An existing extracted boundary
cannot be overwritten by this optional input. Old callers remain unchanged.
No canonical storage format, project JSON binding file or serialization change.

## CURRENT_DWG_IDENTITY

projects/Test_01/Test_01.dwg:
5A673AAA50F8D29C21555D60D7FEC740FF3CE214CD7EB65AE329DC3B701397AC.

## IFC_COMPANION_DWG_IDENTITY

C:/AI/HomeAuraEngineeringAgent-ifc-research/manual-export/Test_01_ifc_copy.dwg:
5A673AAA50F8D29C21555D60D7FEC740FF3CE214CD7EB65AE329DC3B701397AC.
The bytes are identical to the current DWG.

## REVISION_LINK_EVIDENCE

Level A:
- The current and companion DWG have the same SHA-256, freshly recomputed.
- reports/HomeAura_IfcSpace_room101_research_2026-07-26.txt records that exact
  companion DWG hash before its manual IFC export procedure and then records
  the resulting IFC SHA-256 and geometry.
- The IFC header records 2026-07-26T00:45:19 and BSProLib 2023.7.0.17.
- IFC digest matches the historical report:
  01F10257CFCD31DE8B682A2CED11045A3816970B9724C9FD6BA8133325954943.
- No embedded DWG hash, export receipt, CAD marker handle or direct drawing
  GUID was found in IFC header/property sets. Historical reports corroborate
  the export path; they are not a signed exporter receipt.

Level B:
- Current rooms SourceHandle 101DAA3 / Code 101 / Name Тестовая комната.
- Production importer uniquely matches IfcSpace 101, with LongName confirming
  the room name. The match method remains normalized_name_to_room_code.
- IFC contains no direct 101DAA3 link. The handle in historical candidate JSON
  came from the input rooms/example document, not from an IFC CAD identifier.
- Consequently name matching alone is explicitly insufficient.

Level C:
- Existing model_snapshot.json contains neighboring MAGIEXTERIORWALLS handles
  101DAAB, 101DABF, 101DAC7, 101DAB7 and original marker/boundary identities.
- Four IFC side coordinates coincide with the corresponding wall-side extents
  to less than 0.000005 mm (see fingerprint). No shape was generated from these
  extents. The imported IFC analytic profile remains the geometry source.
- The marker position lies inside the IFC extent; this is supporting evidence,
  not a substitute for the production polygon validation.

These pieces jointly support the bounded authority decision for the reviewed
source set. The module pins all seven source hashes; changing even one file
invalidates this decision and requests new evidence.

## MRD_ROLE_ANALYSIS

Official local MagiCAD Room help:
- [Project selection](C:/AI/HomeAuraEngineeringAgent-ifc-research/help-room/creating_or_selecting_the_project.htm)
  describes the selected project as a building database.
- [Close Edit Mode](C:/AI/HomeAuraEngineeringAgent-ifc-research/help-room/close_edit_mode.htm)
  describes separately updating that database when Room objects change.
- [IFC export](C:/AI/HomeAuraEngineeringAgent-ifc-research/help-room/ifc_export.htm)
  defines IfcSpace from the inner surfaces of surrounding Room walls.
- [Area methods](C:/AI/HomeAuraEngineeringAgent-ifc-research/help-room/area_methods.htm)
  documents selectable inner-surface/centerline/outer-surface area conventions.

The vendor's [Room overview](https://www.magicad.com/applications/magicad-room/)
describes a building model containing room/space geometry, and its
[IFC export documentation](https://www.magicad.com/tools/ifc-export-with-space-information/)
states that Room models export to IFC. Its
[2021 release notes](https://portal.magicad.com/Downloader.ashx?id=8940&type=product)
explicitly describe buildings and floor heights in an MRD.

Therefore MRD is more than an irrelevant filename/sidecar. A database change
can affect Room/IFC state while DWG bytes remain unchanged. The difference in
the two MRD hashes does not itself establish a change in this room's boundary.
The reviewed geometry fingerprint supplies independent positive evidence for
this room; MRD-wide equality is neither assumed nor accepted.

Native HA_EXPORT_ROOMS reads Document.Database entities and MagiCAD-R Xrecords
through ForRead transactions. Its implementation has no external MRD reader;
it can export geometry already represented in the loaded DWG without parsing
the MRD. This is distinct from MagiCAD's own IFC export from its Room project.

Unknown: the exact semantic/binary differences between the MRD revisions.
No binary reverse engineering or engineering-value transfer was attempted.

## ROOM_IDENTITY_EVIDENCE

Current project Test_01 / room handle 101DAA3 / code 101
-> existing production name/code matching, unique IfcSpace #31
-> GlobalId 3Vmsu$eoz6VAzSuuOWXaVz.
The exact room/snapshot/IFC hashes and four neighboring wall handles are part
of the binding evidence. A changed room source cannot reuse the binding.

## GEOMETRIC_FINGERPRINT

| Wall handle / comparison | Absolute difference in mm |
|---|---:|
| 101DAAB Maximum.X vs IFC minimum X | 0.000004465970505407313 |
| 101DABF Minimum.X vs IFC maximum X | 0.000000534028913534712 |
| 101DAC7 Maximum.Y vs IFC minimum Y | 0.0000014464425817095616 |
| 101DAB7 Minimum.Y vs IFC maximum Y | 0.0000002723063516896218 |

The 0.000005 mm comparison tolerance corresponds to the IFC coordinate precision
for these reviewed axis-aligned sides. It is an evidence comparison tolerance,
not a new routing or physical tolerance.

Production importer: 4 distinct planar vertices, closed, CCW, no
self-intersection, no holes. Native source length unit millimetres; normalized
world vertices metres. Analytic area and independent triangulation agree.
IFC area = 17.321458459647975 m².
NetAreaM2 = 17.231460571289062 m².
Difference = +0.08999788835891209 m² / +0.5222882180333914%.
Different net-area conventions are a possible explanation, not a proven cause.

The existing UFH adapter rounds vertices half-up to integer mm and closes
the polygon. Result:
(153,153), (4847,153), (4847,3843), (153,3843), (153,153).
Derived area = 17,320,860 mm² = 17.320860 m².
Difference from IFC analytic area = -0.000598459647975 m² due to that existing
coordinate quantization. No area fit or geometry algorithm change.

## NATIVE_EXPORT_GAP_CAUSE

Current rooms.json: FormatVersion 1.0, parser MagiCAD-R-2024-UR2-rev1,
GeneratedAtUtc 2026-07-25T15:29:30.6350367Z.
The boundary implementation first appears in commit ef76aac,
2026-07-25 23:12:07 +0300 (20:12:07Z); Polyline3d support follows in 131234a.
Current native exporter emits version 1.1 / rev2.
Thus the saved report is from the pre-boundary exporter. There is no evidence
that current serialization stripped a boundary or that rev2 discovery failed.
Current native export remains absent, but the accepted alternate IFC binding
does not need to rewrite rooms.json.

## AUTHORITY_DECISION

GeometryAuthorityDecision.status supports AUTHORITATIVE, VALIDATED_CANDIDATE,
REJECTED, NEEDS_FRESH_NATIVE_EXPORT, with evidence/reasons and a deterministic
decision_digest. Actual reviewed result: AUTHORITATIVE.

API:
assess_test01_geometry_authority(project_directory: Path, ifc_directory: Path)
-> GeometryAuthorityDecision.
On authority success its ufh_source is passed explicitly to the existing
build_ufh_sizing_request_from_project_room. This is opt-in; old source-only
calls do not discover or silently promote IFC data.

Binding digest:
94d923fc353c8ac9b6312d1f24115e73b3b43b80b551bc25548e9e2da282f6d9
Adapter digest:
cab40a39b3236de7e1fc9c3d4d5b7326c9f42d3e1f048bf2e31106a7a8474a54

## AUTHORITY_DECISION_REASONS

1. Exact reviewed current/companion DWG revision equality.
2. Historical export provenance with matching IFC hash.
3. Traceable unique production room match plus the existing room marker.
4. Four independently recorded wall-side coordinates match the IFC profile.
5. Production geometry validation, not visual similarity or area matching alone.
6. Explicit limitation to reviewed room geometry/IFC hierarchy; the MRD
   difference is retained in evidence and no general MRD equivalence is claimed.

Missing/unreviewed source files produce NEEDS_FRESH_NATIVE_EXPORT without
a bound source. Match/geometry/identity inconsistency produces REJECTED.
The binder rechecks hashes after IFC reads to detect source mutation.

## BUILDING_LEVEL_BINDING

Accepted together with the IFC geometry binding:
- IfcSpace #31: 3Vmsu$eoz6VAzSuuOWXaVz.
- IfcRelAggregates #57 -> IfcBuildingStorey #29:
  0oQei_Jnn60QnqOIJ3NBzE (Этаж 1).
- IfcRelAggregates #56 -> IfcBuilding #17:
  1kDE4UYl903ebi3UdgvjXG.

These are source IFC GUIDs, not invented canonical UUIDs or DWG handles.
The raw DomainDocument hierarchy and its placeholder UUIDs are untouched.
Each binding has IFC path/hash/STEP reference and evidence digest provenance.

## ADAPTER_RESULT_BEFORE

Source-only current room: INCOMPLETE, 45 gap paths.
MISSING_BUILDING_ID, MISSING_LEVEL_ID, MISSING_ROOM_BOUNDARY,
PROJECT_UFH_INPUT_INCOMPLETE.

## ADAPTER_RESULT_AFTER

Explicit authority-bound source: INCOMPLETE, 41 gap paths.
Only PROJECT_UFH_INPUT_INCOMPLETE remains as top-level diagnostic.
Removed exactly:
identity.building_id; identity.level_id;
sizing.coverage_request.boundary.points; sizing.room.room_area_mm2.

The mapped boundary/derived area are present with IFC provenance. Existing
adapter semantics mark mappings unapplied until a complete request exists;
there is still no complete UFHSizingRequest and no heating plan.

## HUMAN_ACTION_REQUIRED

NONE for this reviewed source set.
For changed/missing sources, obtain new revision evidence. Existing native
procedure is: load the current compatible plugin in AutoCAD with the relevant
drawing, run HA_DISCOVER_ROOM_BOUNDARIES then HA_EXPORT_ROOMS, retain diagnostics
and generated rooms.json, and close without saving DWG changes. No AutoCAD UI
or command was executed in this block.

## READ_ONLY_PROOF

387 baseline files covered agent, AutoCAD source and Test_01 project files
(excluding caches/bin/obj), plus the external manual-export set.
386 existing files were unchanged; the sole intended existing-file change is
agent/ufh_project_adapter.py. One production module was added.
Project/DWG/MRD/IFC contents and protected mathematics/contracts are identical
before/after. Tests/documentation are the other intended additions.

| Protected source | SHA-256 before | After |
|---|---|---|
| `C:\AI\HomeAuraEngineeringAgent\agent\project_foundation.py` | `1CE37F81A80C4533ECF3AADCBFDB31CAEA57A352AFEE90496241A1D93B1E5E9F` | identical |
| `C:\AI\HomeAuraEngineeringAgent\projects\Test_01\Test_01.dwg` | `5A673AAA50F8D29C21555D60D7FEC740FF3CE214CD7EB65AE329DC3B701397AC` | identical |
| `C:\AI\HomeAuraEngineeringAgent\projects\Test_01\HomeAura_Test_01.mrd` | `145BC790981253A1B42F5857FF1B9E64DD4175FF3155D4D8F76437B31A512252` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\floor_heating_engine.py` | `19D46EF12170645524D0792FA0EED23A50E88915A18D20CFB5149DE1C2005326` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\domain_adapter.py` | `FA763BFC84BC4614E8941ABA679536859BF4424B7FF8560E5F99966BAB6C8963` | identical |
| `C:\AI\HomeAuraEngineeringAgent\projects\Test_01\exports\rooms\rooms.json` | `30EE1828E74ECBF1E1B46064C39CE30755A4692FC4CD972D1E38328AFFE0992E` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\ufh_auto_retry.py` | `A368319EA6A8ACF596A589F2C5747CEA39FEA885855A0B66A417EAFC6E1D93C7` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\domain_models.py` | `EFC0B3E5ED54C8A2E2D90BBD59C9405F4FE2B19C26D48519DA97747F7AFE28B2` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\floor_heating_coverage.py` | `98FB3289186FBF3B42C48EFB027EC0FB12C99E6E3784CB85CA587B18A92C307B` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\ufh_engineering_kernel.py` | `56C3D342202005F1948C098D03AF0CEF61D3075EE59993940A95F5923EB346C2` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\floor_heating_sizing.py` | `F1277BB71C154DBAF2C0D26D19BA229BC1F101490BA6C8A118DFADFD15C1FAFE` | identical |
| `C:\AI\HomeAuraEngineeringAgent-ifc-research\manual-export\HomeAura_Test_01.mrd` | `8651E8B8A2F9320283F0C05CBF27F54F3BA4AC01F9AE94F3D27C5D89EE282897` | identical |
| `C:\AI\HomeAuraEngineeringAgent\agent\project_models.py` | `A38A10D0EE469BCECE5A5A3B01C71E71EC076E789AD3389B28AF4CA0985965AA` | identical |

## TEST_RESULTS

- tests/test_test01_geometry_source_authority.py: 8 passed.
- tests/test_ufh_project_adapter.py: 8 passed.
- tests/test_ufh_project_engineering_profile.py: 11 passed.
- tests -k floor_heating: 100 passed.
- git diff --check: exit 0; pre-existing LF/CRLF advisories only.

Tests cover real revision evidence, room/IFC hierarchy and provenance,
boundary-to-area mapping, four removed gaps, unchanged engineering failure,
read-only hashes, deterministic decisions, changed DWG/MRD rejection and
no sizing/retry invocation by the binding workflow.
External-source tests explicitly skip if the real IFC evidence is unavailable;
this run used the real sources and had no skips.

## DETERMINISM

Repeated reviewed input produced identical decision, boundary and adapter
digests. Mutated temporary DWG/MRD fixtures deterministically return
NEEDS_FRESH_NATIVE_EXPORT. No actual project source was modified by those tests.

## REMAINING_GAPS

41 paths: UFH settings 8; fluid 4; control 2; product 13;
design conditions 5; explicit exclusions declaration 1;
room geometry 3 (exterior wall segments, exterior wall length, openings);
building physics 5.
There are no building/level identity or boundary/derived-area gaps in the
authority-bound result. This count is not a count of independent user parameters.

## LIMITATIONS

- Authority is a reviewed evidence-combination decision, not an embedded signed
  IFC-to-DWG export receipt. The exact source set is pinned to prevent expansion.
- Full MRD equivalence is unresolved; no MRD engineering parameters were copied.
- Fingerprint is specific to this room, not a universal bounding-box authority rule.
- IFC extraction depends on the existing IfcOpenShell installation.
- The accepted source set lives partly outside the repository; directory inputs
  are explicit and no new persistence architecture was introduced.
- No geometry, sizing math, routing, hydraulics or engineering-profile values changed.
- No UFH real-project shadow validation ran. Regression tests may exercise their
  existing synthetic UFH fixtures; the real binding only maps data.

## NEXT_RECOMMENDED_BLOCK

TEST01_UFH_ENGINEERING_PROFILE_SOURCE_COMPLETION_V1:
collect and provenance-check the remaining actual project/design/product/fluid
inputs against the accepted geometry binding, with fail-closed handling of
missing data. Do not run shadow validation until its inputs are complete.
This next bounded block was not implemented.

