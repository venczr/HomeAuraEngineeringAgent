# Canonical HomeAura UFH runtime

This is a forward-looking development decision, not a claim about historical or deployed global canonicality.

CANONICAL_REPOSITORY=C:\\AI\\HomeAuraEngineeringAgent
CANONICAL_BRANCH=feature/room-geometry
CANONICAL_API_ENTRYPOINT=agent.api:app
CANONICAL_UFH_ENGINE=agent.floor_heating_engine:calculate_floor_heating
CANONICAL_UFH_PREVIEW_LAYER=agent.ufh_routing_preview:generate_ufh_routing_preview
CANONICAL_RENDERER=agent.ufh_routing_preview:render_ufh_routing_preview_svg
CANONICAL_REAL_PLAN_GENERATOR=scripts/build_real_floor_ufh_artifacts.py
TIER_A_CODE_CHECKPOINT=canonical imports, UFH engine/preview/API/coverage/installation/project/sizing/system-graph/retry regressions; no private Test_01 or external IFC data
TIER_B_TEST01_INTEGRATION_REPLAY=tests/test_test01_* and scripts/build_real_floor_ufh_artifacts.py; requires private Test_01 data
CANONICAL_TEST_SUITES=tests/test_floor_heating_engine.py; tests/test_floor_heating_preview_api.py; tests/test_ufh_routing_preview.py; tests/test_floor_heating_coverage*.py; tests/test_floor_heating_installation_rules.py; tests/test_floor_heating_project_preview_api.py; tests/test_floor_heating_sizing.py; tests/test_floor_heating_system_graph.py; tests/test_ufh_auto_retry.py

NON_CANONICAL_REFERENCE_PATHS=
- C:\\AI\\HomeAura-Codex-Contracts\\homeaura\\floor_heating\\engine.py (separate CLI/test implementation; reference only)
- dev/ and projects/Test_01/ generated outputs (artifacts, not source)

The EngineeringAgent `agent` package is the one canonical UFH source family for forward development. The Contracts implementation is classified separately and is not merged here.

No test or artifact may claim product verification unless it exercises the canonical source family.

## Contract comparison

- Core scanline/serpentine routing: DUPLICATE (different implementation and units).
- Typed result/graph contracts: UNIQUE_AND_USEFUL in Contracts; not runtime-linked here.
- EngineeringAgent API integration: UNIQUE_AND_USEFUL to EngineeringAgent.
- SVG preview/rendering: UNIQUE_AND_USEFUL to EngineeringAgent.
- Real-floor replay generator: UNIQUE_AND_USEFUL to EngineeringAgent.
- Hydraulic/engineering approval: UNKNOWN / out of scope for both preview families.
