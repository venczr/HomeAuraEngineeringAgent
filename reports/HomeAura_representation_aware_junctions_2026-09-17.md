# Representation-aware junction solver ? 2026-09-17

## Test_01 decisions
- ATTIC_PLAN:PAGE_0: {'NO_SUPPORTED_JUNCTION': 9, 'OPENING_GAP_PRESERVED': 18, 'CONFIRMED_JUNCTION': 5}; junctions={'T_JUNCTION': 5}; dangling=27; protected_gaps=8.
  - unresolved endpoint (279.25, 161) wall=ATTIC_PLAN:002d8a7bb040635f:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (126.75, 448) wall=ATTIC_PLAN:2eaeee74f0cdacec:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (258.25, 484.5) wall=ATTIC_PLAN:32b0bef7b7929325:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (258.25, 557) wall=ATTIC_PLAN:32b0bef7b7929325:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (448.75, 303) wall=ATTIC_PLAN:3857acf9473aaffe:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (531.25, 220) wall=ATTIC_PLAN:5c68cd185ef1b68a:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (531.25, 414.5) wall=ATTIC_PLAN:5c68cd185ef1b68a:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (371.25, 161) wall=ATTIC_PLAN:a243a0719da3316a:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (126.75, 184.5) wall=ATTIC_PLAN:b3edbe483d4d0127:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
- FLOOR_1_PLAN:PAGE_0: {'CONFIRMED_JUNCTION': 7, 'NO_SUPPORTED_JUNCTION': 29, 'OPENING_GAP_PRESERVED': 2}; junctions={'T_JUNCTION': 7}; dangling=31; protected_gaps=6.
  - unresolved endpoint (248.75, 553) wall=FLOOR_1_PLAN:01d01036345411f8:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (302.75, 410) wall=FLOOR_1_PLAN:20b23acc02e5897c:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (366, 241.75) wall=FLOOR_1_PLAN:29d279d8f58a08b7:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (517.5, 241.75) wall=FLOOR_1_PLAN:29d279d8f58a08b7:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (114.75, 174.5) wall=FLOOR_1_PLAN:3d47e97747ee015d:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (138.5, 472.25) wall=FLOOR_1_PLAN:4e4766fc480e5e48:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (476.5, 472.25) wall=FLOOR_1_PLAN:4e4766fc480e5e48:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (476.5, 470.25) wall=FLOOR_1_PLAN:4f61e72c1ae4af8a:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (517.5, 470.25) wall=FLOOR_1_PLAN:4f61e72c1ae4af8a:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY
  - unresolved endpoint (524.75, 355) wall=FLOOR_1_PLAN:57d9271fd95aec79:INTERVAL_BAND: NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY

## Polygonization V4
Both floors produce one outer-contour face containing all eight labels. Quality: zero one-label faces, one multi-label conflict per floor, no tiny slivers. This graph is not promoted.

## Exact blocker
The endpoint solver confirms 12 unique T-junction closures, but 40 semantic endpoints have no perpendicular semantic centerline within the 6 pt policy. Interval centerlines represent only locally paired wall faces; missing counterpart intervals prevent long boundary continuity. Eighteen attic and two floor-1 endpoint decisions are protected by sustained-gap constraints. Residual evidence must next be converted into inferred centerline continuation only where one paired neighbor supplies a local wall-width/offset model.

## Rooms and routing
Rooms 2 and 9 remain AMBIGUOUS. Routing remains 14/16; previews unchanged.

## Tests
41 targeted junction, drawing, routing, coverage and room-geometry tests passed. Compile and whitespace checks passed.
