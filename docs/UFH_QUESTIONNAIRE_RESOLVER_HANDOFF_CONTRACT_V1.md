# UFH Questionnaire Resolver Handoff Contract V1

Verdict note: the typed handoff contract is implemented. The inherited loader
assumptions identified by the V1 audit were remediated in
`UFH_AUTHORING_LOADER_ASSUMPTION_REMEDIATION_V1`.

## Contract

The resolver boundary is:

`QuestionnaireState.decisions` -> `ResolverRequest` -> `ResolverResult` ->
`apply_resolver_result(...)` -> authoring payload.

Resolvers never write kernel inputs directly. They can only produce
`ResolvedValue` envelopes for fields allowed by `POLICIES` in
`agent/ufh_questionnaire_resolver_contract.py`. Binding rejects stale results,
non-bindable authority classes, `test_only` provenance, wrong units, and
project/room context conflicts.

## Resolver Categories

- `CLIMATE_RESOLVER`
- `BUILDING_CONSTRUCTION_RESOLVER`
- `BOUNDARY_CONDITION_RESOLVER`
- `FLOOR_FINISH_RESOLVER`
- `UFH_PRODUCT_RESOLVER`
- `PIPE_PRODUCT_RESOLVER`
- `MANIFOLD_PRODUCT_RESOLVER`
- `FLUID_PROPERTY_RESOLVER`
- `CONTROL_CHARACTERISTIC_RESOLVER`
- `SURFACE_LIMIT_RESOLVER`

## Dependency And Invalidation

Each request has a dependency digest built only from the resolver type,
project/room identity, project source digest, and the questionnaire answers that
the resolver actually consumes. Changing an unrelated answer preserves the
binding. Changing a relevant answer marks the result `STALE_INPUT` and clears
only the fields previously written by that resolver value.

## Authority Classes

Accepted binding authorities are:

- `PROJECT_AUTHORITATIVE`
- `NORMATIVE_AUTHORITATIVE`
- `MANUFACTURER_AUTHORITATIVE`
- `USER_CONFIRMED_PROJECT_DECISION`
- `DERIVED_FROM_AUTHORITATIVE_INPUTS`

`REFERENCE_ONLY` and `UNACCEPTABLE_FOR_BINDING` are modeled but rejected for
authoring updates. Physical values always require units and provenance.

## Test_01 Question Map

The machine-readable map is `TEST01_QUESTION_RESOLVER_MAP`. The 13 currently
visible initial Test_01 questions are required because no catalog/normative
resolver has yet supplied their outputs. Conditional questions remain hidden
until their parent answer activates them.

Count analysis:

- `ALWAYS_REQUIRED`: climate, below, above, envelope, finish, exclusions,
  collector, system, layout, fluid, thermal, surface.
- `CAN_BE_DEFERRED`: openings.
- `CONDITIONAL_ONLY`: below/above details, source references, custom layout,
  water/fluid source, thermal known inputs, custom surface.
- `CAN_BE_MERGED_IN_UI`: system plus system.source, layout plus custom details,
  fluid plus temperature/source, surface plus source.
- `CAN_BE_AUTO_RESOLVED_FROM_PROJECT`: none newly proven in this block.

## Inherited Assumption Audit

The machine-readable audit is
`docs/UFH_QUESTIONNAIRE_RESOLVER_HANDOFF_CONTRACT_V1_ASSUMPTION_AUDIT.json`.

Resolved inherited assumptions:

- `sizing.room.insulation.air_changes_per_hour`: no production fallback remains.
  The loader requires authoritative project-owned ACH or an explicit test-only
  fixture value.
- `sizing.coverage_request.turn_radius_mm`: owned by versioned
  `HOMEAURA_UFH_ROUTING_POLICY:V1`.
- `sizing.coverage_request.perimeter_priority_mode`: owned by versioned
  `HOMEAURA_UFH_ROUTING_POLICY:V1`.

Legacy routing policy:

- `minimum_circuit_length_mm = 40000`
- `maximum_circuit_length_mm = 80000`

This remains `LEGACY_MVP_ROUTING_POLICY`, not a universal engineering limit.

Safe structural/API defaults include schema tags and unset optional refinements.
Automatic circuit count semantics and legacy routing mode are now explicit
routing-policy provenance rather than hidden physical facts.
