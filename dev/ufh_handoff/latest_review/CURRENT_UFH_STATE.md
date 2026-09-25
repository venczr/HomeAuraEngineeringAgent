# Current UFH state

LAST_UPDATED=2026-09-18
VERIFIED_CAPABILITIES=Rectangle baseline; original-frame horizontal/vertical routes; deterministic SVG; rectangular coverage partition; Test_01 room replay
VERIFIED_ARTIFACTS=dev/ufh_routing_v3/ufh_simple_rectangle.svg; dev/ufh_routing_v3/ufh_vertical_rectangle.svg; dev/ufh_routing_v3/ufh_exclusion.svg; dev/ufh_routing_v3/ufh_multi_circuit.svg
KNOWN_FAILURES=Interior exclusion route rejected as PIPE_PATH_DISCONTINUOUS; common-manifold transit not yet modeled; 2 rooms remain geometry-unresolved
ACTIVE_MILESTONE=Two-floor room routing preview complete
REAL_FLOOR_PROGRESS=Test_01 manifest replay completed for 16 room candidates: 14 generated, 2 geometry-unresolved; source scale metadata is 1:100; outputs remain geometry-only
LATEST_METRICS=Rectangle coverage 99.82%; measured spacing 200mm; vertical bounds restored to 100..6900 x 100..3100; 114 UFH tests pass; real rooms 14/16 generated
NEXT_PRIORITY=Implement continuous exclusion routing, then add common-manifold transit planning; keep engineering authority separate
