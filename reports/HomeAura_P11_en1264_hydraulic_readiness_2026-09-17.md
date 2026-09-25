# HomeAura P11 EN1264 and hydraulic readiness chain — 2026-09-17

## Result
The engineering chain accepts only validated SP60 load outputs as entry to EN1264/UFH sizing and hydraulic evaluation. Geometry-only routes and missing real candidates remain fail-closed. Surface, manufacturer, balanceability, fixed-loss, and provenance constraints remain separate and are not overridden by hydraulic calculations.

## Validation
`python -m pytest -q tests/test_floor_heating_sizing.py tests/test_ufh_engineering_kernel.py tests/test_ufh_engineering_integration.py` — 66 passed.

No Test_01 engineering result was promoted because P10 source readiness is NOT_READY.
