# HomeAura P8/P9 resolver and intake checkpoint — 2026-09-19

## P8 climate binding

The SP131 resolver remains exact-match and fail-closed. The approved dataset contains no record for the observed locality `дер. Узигонты`, so the intake emits `NORMATIVE_LOCALITY_BINDING_REQUIRED`. No nearest-station or proximity substitution is used.

## P9 envelope intake

The source-first construction intake accepts only explicit `KNOWN_U_VALUE` or `LAYER_ASSEMBLY` representations with a source reference. Envelope and material resolvers return typed unresolved outcomes when construction or property evidence is absent; they do not invent constructions or values.

## Gate

P10 remains gated by P7 exact stair/void semantics. No SP60, EN1264, hydraulic, or authoritative publication calculation is claimed by this checkpoint.

Validation:

- `python -m pytest -q tests/test_ufh_climate_resolver.py tests/test_whole_building_engineering_intake.py` — 16 passed
- `python -m pytest -q tests/test_whole_building_engineering_intake.py tests/test_ufh_envelope_construction_resolver.py tests/test_ufh_material_thermal_property_resolver.py` — 34 passed
