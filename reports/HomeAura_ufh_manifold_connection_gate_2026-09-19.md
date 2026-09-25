# UFH manifold connection gate — 2026-09-19

## Finding

The building generator assigned every coverage circuit a supply and return port and constructed preview transit polylines. That assignment did not prove a physical connection: source-authorized openings, corridor lanes and riser penetrations are still absent. Reporting `MANIFOLD_CONNECTED=true` therefore overstated the result.

## Correction

`build_real_floor_ufh_artifacts.py` now treats a port assignment as an `ASSIGNED_PREVIEW_ENDPOINT`, emits `manifold_connections.json`, and sets `MANIFOLD_CONNECTED=false`, `MANIFOLD_CONNECTIONS_VALID=false` and `FULL_CIRCUIT_VALID=false` until the building transit authority gate passes. The preview routes remain in JSON for auditability, while the SVG continues to omit unverified transit lines and marks only unresolved endpoints.

## Current result

- Coverage circuits: 36.
- Room coverage routes physically validated: 36/36.
- Manifold connections physically validated: 0/36.
- Unresolved blockers: source or installer confirmation of openings, corridor path and riser penetration; hydraulic inputs are also absent.
- Control scenarios: A–F pass; G rejects the narrow spiral as infeasible.
- Targeted UFH regression suite: pass.

This is a geometry-only engineering preview and cannot be promoted to a construction-ready circuit schedule until the connection gate is resolved.
