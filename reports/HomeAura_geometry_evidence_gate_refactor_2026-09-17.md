# Geometry evidence gate refactor — 2026-09-17

## Verdict

The four remaining unmatched boundaries are four 0.5 pt raster-contour steps. They are not missing physical walls and are not the blocker. The wall-centerline polygonizer remains incomplete because room/opening boundaries are not equivalent to closed wall centerlines. Continuing to tune that graph would add complexity without improving the strongest available room evidence.

The actual blocker was an authority-modeling error: `area_status` was used as the room-geometry gate. Rooms 2 and 9 already have independently observed connected white-space contours, unique contained labels, valid simple polygons, containment in the reviewed outer contour, and no overlap with other observed room faces. Their mismatch with 30.7/39.9 is retained as post-selection QA and does not choose or reject geometry.

## Change

Added `RoomGeometryEvidenceAssessment` and a generic fail-closed assessment for every observed room face. Geometry usability now depends on source face validity, unique label membership, outer-contour containment, and absence of competing room overlap. Area validation remains separate. No room number or Test_01 coordinate is encoded.

The geometry-only preview now uses this evidence status and attempts all 16 rooms. Router input canonicalization uses a non-negative local origin, counter-clockwise order, and a verified interior collector candidate. The existing router validator now admits any simple orthogonal room polygon to its existing compact-sweep fallback; exclusions remain rectangular.

## Result

- Usable drawing geometries: 16/16.
- Routing attempted: 16/16.
- Routes generated and validated: 14/16.
- Room 2: geometry usable; route generated but rejected for self-intersection.
- Room 9: geometry usable; route generated but rejected for self-intersection.
- Preview PNGs regenerated; failed rooms remain orange and do not display rejected routes.

The next localized blocker is the compact sweep connector ordering for multi-reflex orthogonal polygons. This is a routing capability issue, not drawing-understanding ambiguity. Engineering authority remains unavailable: envelope constructions, heights/opening thermal data, ventilation/infiltration basis, and exact normative climate binding remain unresolved.

## Validation

- 34 related tests passed.
- Python compilation passed.
- Scoped whitespace check passed.

