# Universal UFH layout engine — implementation status

## Baseline audited on 2026-09-21

Canonical runtime is `agent.floor_heating_engine:calculate_floor_heating`,
called directly by the API and through
`agent.ufh_routing_preview:generate_ufh_routing_preview`.  The preview path
currently requests one circuit and selects the compact serpentine visual mode.

The prior `ufh_layout_engine` and Test_01 AUTO-zone work is useful geometry
research but is not yet the canonical layout dataflow.  It must not be
presented as a construction-ready routing result.

## Confirmed limitations

- The canonical engine rejects every requested circuit count other than one.
- Its counterflow spiral is limited to a rectangular envelope and has no
  selected-doorway input.
- The preview splitter is rectangular only and capped at three circuits.
- Existing Test_01 AUTO zones are three 63.088 m coverage candidates, but
  their six ends have no jointly validated doorway/corridor assignment.
- Splitting a continuous centreline by arclength is forbidden: sibling routes
  share an internal endpoint with no authorized collector path.

## Implemented foundation in this stage

- `FloorHeatingRequest` now accepts an explicit finite `selected_doorway`,
  1–5 requested circuits, pipe diameter, free-pipe clearance, doorway edge
  clearance and optional estimated building transit length.
- `reserve_doorway_lanes` reserves ordered, distinct supply/return centreline
  slots for all requested circuits before coverage geometry is built.  It
  reports exact required width and fails closed when the selected doorway is
  too narrow.

For example, ten 16 mm pipe centreline lanes with 16 mm free clearance and
50 mm edges require 404 mm.  This proves only room-side doorway capacity; it
does not authorize a wall penetration or manifold transit.

## Next implementation boundary

Build the doorway-aware canonical room planner before changing Test_01 again:

1. Generate and score partitions with reserved doorway lanes as constraints.
2. Materialize one continuous bifilar spiral or validated meander per zone.
3. Validate all room routes jointly against one another and obstacles.
4. Return the exact supply/return doorway terminals to the building router,
   keeping `ROOM_LAYOUT_VALID`, `DOORWAY_CONNECTION_VALID`,
   `BUILDING_TRANSIT_VALID` and `MANIFOLD_CONNECTED` separate.

No circuit is construction-ready at this point.
