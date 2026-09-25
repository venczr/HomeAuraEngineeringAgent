# HomeAura UFH physical-layout correction — 2026-09-20

## 1. Root causes

### Spiral SVG/JSON mismatch
The route builder's first point was valid. The control SVG exporter discarded it and emitted a hard-coded `M (origin + wall_offset)` before appending the remaining translated points. For A1, A2 and A3 this created a visible A→B→A segment that did not exist in the source route. The JSON validator inspected the source route, so it correctly reported zero overlap for the wrong artifact.

The exporter now serializes the complete translated route with `_svg_path(candidate)`. A regression parses the first SVG vertex and compares it with the calculated route origin.

### Overlap gate gap
The prior gate counted point crossings but did not measure positive-length reuse of a segment, including reverse traversal. Both independent validators now measure coincident and partially coincident collinear segment length and fail on `DUPLICATE_CENTERLINE_OVERLAP` / `DUPLICATE_CENTERLINE_OVERLAP_GATE_FAILED`.

### Split promotion
`SPIRAL_ARCLENGTH_PARTITION` and other length-driven splits created fragments that shared an internal point. In the boiler room the shared point was `(16847, 6915)`. The split was then presented as two circuits even though neither new endpoint had an authorized collector path.

A new `validate_circuit_split` gate checks sibling endpoint uniqueness and explicit endpoint authorization. When the gate fails, the candidate split is reverted to the original continuous route and recorded as `RESPLIT_BLOCKED_NO_AUTHORIZED_ENDPOINTS` with the measured shared/unauthorized endpoints.

## 2. Current measured result

- Control spirals A1, A2 and A3: `valid=true`, duplicate overlap `0 mm`, rendered first vertex matches calculated first vertex.
- A4/A5 remain rejected for containment; A6 remains rejected as infeasible.
- Previous fragment count: 36.
- Current preliminary continuous route count: 15.
- Length-driven split candidates blocked: 12.
- Independent construction-ready circuit count: 0.
- Boiler room split: blocked; shared endpoint `(16847, 6915)` is retained in the diagnostic candidate record and is not promoted.
- Current routes with total preview length above 90 m: 10; they remain unresolved until independently accessible endpoints and project-owned hydraulic limits are supplied.
- Manifold-connected circuits: 0/15.

## 3. Bend and visualization checks

The physical validator now reports `BEND_VALID` separately. It checks tangent-leg clearance against `2 * minimum_bend_radius_mm` at every orthogonal corner, in addition to containment, obstacles and spacing. The model remains a centerline model; SVG uses that same centerline, with red/blue only as a role split at the measured arclength midpoint.

`visualization_validation.json` recomposes the rendered supply and return paths and verifies them against `physical_coverage_routes_mm`. Status: `VALID` for all emitted room routes.

## 4. Remaining engineering limits

- No building transit is construction-authorized: openings, corridor lanes, riser penetration, manifold position and hydraulic inputs remain unconfirmed.
- Rooms 2 and 9 remain geometry-unresolved around the stair.
- Pipe, flow, balancing, pressure-loss, pump and mixing-unit parameters are absent.
- The 15-route count is a preliminary geometry-only assessment, not a final heating design. It may increase after physically accessible zone decomposition is designed.

The previous artifacts remain in `dev/ufh_diagnostics/baseline_20260919/`; the regenerated package contains the corrected control SVG, split diagnostics, visualization validation and authority intake.
