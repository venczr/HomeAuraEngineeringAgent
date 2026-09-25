# Hydronic floor-heating geometry rules used by VIS-008 R4C

This is a geometry and inspection note, not a code-compliance certificate.

## Rules adopted

- Keep the canonical ordered route as one continuous collector-to-collector polyline.
- Keep supply and return tails explicit through the planned floor-entry gates.
- Treat wall penetrations, movement joints and construction obstructions as design inputs; do not silently route through them.
- Keep bends orthogonal and reserve straight leg for a declared project bend-radius assumption. A kinked pipe is a rework condition.
- Validate actual route length against the design length and retain the measured circuit length in the artifact.
- Treat exclusion zones as clearance envelopes, not merely centerline polygons.

## Explicit MVP assumptions

R4C uses a 100 mm installation grid, 100 mm wall/exclusion clearance and a 100 mm assumed minimum bend radius. These values are configurable project assumptions; they are not a universal pipe-manufacturer or code requirement. Pipe diameter, material, hydraulic loss, flow, pump and mixing-unit selection remain outside this layer.

## Source guidance

- [REHAU Radiant Heating Systems Installation Guide](https://www.rehau.com/downloads/497834/radiantheatingsystemsinstallationguide-855603-rehau.pdf): design should identify spacing and circuit lengths before installation; obstructions and wall changes can require redesign; tails should be protected at penetrations; bends must avoid kinking; actual circuit length should be recorded and compared with design.
- [Danfoss Design Support Center](https://assets.danfoss.com/documents/latest/521121/AF531939137332en-010101.pdf): hydronic floor-heating design combines room heat loss, manifold position, pipe layout, spacing, circuit length and pressure-drop calculations. R4C deliberately implements only the geometry portion.

## What R4C proves

The two fixture routes retain the accepted canonical point order and lengths (43.7 m and 48.5 m), have separate north collector tails, remain grid-aligned, have no inter-circuit crossings, and pass the explicit bend/clearance checks in `installation_rules`.
