# UFH visual QA — regenerated physical preview — 2026-09-19

## Inspected artifacts

- `dev/ufh_real_plan/first_floor_ufh.svg` rendered to `first_floor_ufh.png`.
- `dev/ufh_real_plan/mansard_ufh.svg` rendered to `mansard_ufh.png`.
- `dev/ufh_real_plan/building_level_ufh.svg` rendered to `building_level_ufh.png`.

## Findings

- Room coverage is drawn from the ordered centerline model and split at the route midpoint into red supply and blue return. No second decorative route is added for coloring.
- The boiler room (`4 / 15.9; Котельная`) visibly uses the gate-approved nested bifilar spiral with a central hairpin; its route is split into two circuits only by the length policy.
- Other routed rooms visibly use continuous meanders; each room remains a separate contour.
- The building-level image contains coverage centerlines and unresolved endpoint markers only. The previous long green/red/blue transit lines across rooms are absent because corridor/opening/riser authority is unresolved.
- No building-level supply or return transit path is presented as installed pipe.

## Gate result

Visual output is consistent with the calculated routes and strict transit display gate. It is a geometry-only preview: 36/36 coverage routes pass the independent physical validator, while 0/36 manifold connections are physically validated.
