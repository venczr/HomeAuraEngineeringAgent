# Source discovery and geometric openings milestone — 2026-09-17

## Reclassification
The prior NEEDS_HUMAN verdict was premature. Current gaps are separated as follows.

### ALGORITHM_LIMITATION
- Semantic face reconstruction for central circulation rooms 2 / 30.7 and 9 / 39.9 around stairs/open passages.
- Interior door/gap extraction and exact room connectivity.
- Exact wall-face reconstruction beyond observed room-space envelopes.

### SOURCE_EXISTS_NOT_YET_EXTRACTED
- Door/open-passage symbols visible in verified PDFs.
- Additional DWG/MRD geometry exists, but current model snapshot has no door/window entities and MRD has no established parser contract.

### SOURCE_MISSING
- Reviewed PDFs and one-space IFC contain no construction assemblies, material layers, conductivity, U-values, opening heights, or thermal opening properties.
- IFC contains one IfcSpace and no IfcDoor, IfcWindow, IfcWall, IfcSlab, IfcRoof, or IfcMaterial.

### ENGINEERING_AUTHORITY_MISSING
- Dimension labels are strongly corroborated as metres but have no explicit reviewed unit glyph/declaration.
- Polygon/wall/opening candidates are not yet authorized engineering geometry.
- Envelope construction and climate normative resolution remain absent.

### HUMAN_DECISION_REQUIRED
None for continued drawing/topology development. Later confirmation/authoring is required only for thermal properties and any source facts that remain absent after extraction.

## Sources discovered
- Verified floor-1 and attic PDFs plus ingestion manifest.
- Test_01.dwg and HomeAura_Test_01.mrd.
- model_snapshot.json, rooms.json and room discovery/analysis exports.
- IFC research export Test_01_rooms_ifc4.ifc and associated DWG/MRD copies.
- Snapshot declares MAGIDOORS/MAGIWINDOWS layers but contains zero entities on them.

## Facts extracted without user
- Source-backed locality is Узигонты, Низинское сельское поселение, Ломоносовский район, Ленинградская область. The repository source does not support replacing it with Знаменка.
- Document-unit interpretation: dimensions in metres is corroborated by title-block 1:100, eight dimension constraints, and 14/16 room-area checks; it remains document interpretation, not engineering authority.
- 12 deduplicated exterior WINDOW_OR_GLAZING geometric candidates: 7 floor 1 and 5 attic, with outer-contour association and drawing-space widths.
- Thermal opening properties remain absent.

## Geometry repair
Convex-hull and automatic unlabeled-region merging are rejected as unsupported. Visual source review confirms central rooms are semantic faces around stair graphics/open passages, so connected-white segmentation is insufficient. Area labels remain validation evidence only.

## Readiness
Whole-building drawing model: partial. Geometry is strong for 14 labeled rooms, approximate/unresolved for 2 central rooms; exterior geometric window inventory is partial; interior door connectivity and envelope authority are unresolved. SP60/UFH remain not ready.

## Validation
Drawing/PDF/intake/room targeted suite passed; compile and UTF-8 checks passed; no new regression.
