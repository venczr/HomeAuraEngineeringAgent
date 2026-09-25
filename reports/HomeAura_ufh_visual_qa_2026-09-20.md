# UFH visual QA — corrected route/split export — 2026-09-20

- `dev/ufh_spiral_validation/spiral_validation.svg` now starts each control path at the calculated first vertex. A1, A2 and A3 show one continuous spiral without the former A→B→A export artifact.
- The boiler-room route is no longer displayed as two independent physical circuits. The split candidate and shared point `(16847, 6915)` remain in JSON diagnostics; the emitted preview keeps one continuous route.
- The floor and building previews use the current 15 preliminary coverage routes. Red/blue segments are recomposed from one centerline and `visualization_validation.json` reports `VALID`.
- Unverified manifold/corridor/riser paths remain endpoint markers only.

This is geometry-only QA. No manifold connection is construction-authorized and no hydraulic result is claimed.
