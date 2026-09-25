# Raster wall centerlines and opening-gap policy ? 2026-09-17

## Wall reconstruction
- 96 deterministic source-linked orthogonal wall candidates: 49 first floor, 47 attic.
- PDF text spans, reviewed stair boxes, page content outside the reviewed outer contour, and sub-pixel strokes are suppressed.
- Output remains RASTER_WALL_CANDIDATE_NOT_PROJECT_FACT.

## Gap policy
The former fixed 12 pt threshold was replaced by an explicit extraction policy. A 0.45 m candidate passage noise floor is converted through each dimension-derived document scale:
- first floor: 12.75620008828604679160479955 pt;
- attic: 12.78690101198958434590891887 pt.
This is PHYSICAL_POLICY_USING_UNVERIFIED_DOCUMENT_SCALE: a geometric extraction policy, not a normative door width and not engineering authority.

## Openings and topology
20 room-pair boundary corridors remain: 19 solid and one with short artifacts. No sustained gap passes policy, so no room-room connectivity is promoted. Rooms 2 and 9 remain ambiguous; area labels were not used for selection.

## UFH preview gate
Geometry-only preview readiness is BLOCKED_GEOMETRY_INCOMPLETE. Fourteen rooms have usable candidates, two semantic faces are unresolved, and connectivity is absent. The routing engine was not invoked. This prevents a misleading partial preview while preserving the requested GEOMETRY_ONLY / NON_ENGINEERING / NOT_FOR_CONSTRUCTION boundary.

## Validation
40 targeted tests passed; compilation and diff whitespace checks passed.
