# Current UFH state

LAST_UPDATED=2026-09-18
VERIFIED_CAPABILITIES=Rectangle baseline; original-frame horizontal/vertical routes; deterministic SVG; rectangular coverage partition; Test_01 room replay
VERIFIED_ARTIFACTS=dev/ufh_routing_v3/ufh_simple_rectangle.svg; dev/ufh_routing_v3/ufh_vertical_rectangle.svg; dev/ufh_routing_v3/ufh_exclusion.svg; dev/ufh_routing_v3/ufh_multi_circuit.svg
KNOWN_FAILURES=Interior exclusion route rejected as PIPE_PATH_DISCONTINUOUS; common-manifold transit not yet modeled; 2 rooms remain geometry-unresolved
ACTIVE_MILESTONE=Two-floor room routing preview complete
REAL_FLOOR_PROGRESS=Test_01 replay preserves source-frame room transforms in floor SVG/summary; 16 candidates: 7 ROUTED_VALID, 7 ROUTE_GENERATED_BUT_INVALID by area/spacing sanity, 2 geometry-unresolved
LATEST_METRICS=Global floor SVGs now use source-derived millimetre positions; valid counts first floor 3/8, mansard 4/8; project .venv still lacks declared Pillow/PyMuPDF because network install is unavailable
NEXT_PRIORITY=Implement continuous exclusion routing, then add common-manifold transit planning; keep engineering authority separate
