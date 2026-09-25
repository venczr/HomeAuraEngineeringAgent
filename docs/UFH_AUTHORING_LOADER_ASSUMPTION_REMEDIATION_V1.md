# UFH Authoring Loader Assumption Remediation V1

## Verdict

`UFH_AUTHORING_LOADER_ASSUMPTIONS_REMEDIATED`

The three suspicious inherited assumptions from the resolver handoff audit were
removed from the real-profile path or promoted to explicit routing policy
provenance. UFH math, routing geometry, AutoCAD, DWG/MRD, and 40-80 m legacy
policy were not changed.

## ACH Remediation

`air_changes_per_hour` is no longer hardcoded by the authoring loader.

The loader can build a complete profile only when ACH is supplied by:

- `project_owned_values["sizing.room.insulation.air_changes_per_hour"]`, with
  provenance; or
- an explicit test fixture value.

Missing ACH returns `AUTHORITATIVE_PROJECT_VALUE_REQUIRED` and remains
fail-closed.

## Routing Policy

`UFHRoutingPolicy` captures the algorithm-owned routing values:

- `policy_id = HOMEAURA_UFH_ROUTING_POLICY`
- `policy_version = V1`
- `routing_mode = legacy`
- `turn_radius_mm = 100`
- `perimeter_priority_mode = true`
- `minimum_circuit_length_mm = 40000`
- `maximum_circuit_length_mm = 80000`
- `requested_circuit_count_semantics = AUTO_WHEN_NONE_EXACT_1_TO_3`

`turn_radius_mm` and `perimeter_priority_mode` now carry
`routing_algorithm_policy` provenance in authoring profiles. Adapter-side
materialized policy values use `SYSTEM_ROUTING_POLICY` with
`HOMEAURA_UFH_ROUTING_POLICY:V1` or `LEGACY_MVP_ROUTING_POLICY` source labels.

## Provenance Defect

Profile provenance is converted to project-field provenance through an explicit
adapter gate. Invalid or unsupported provenance produces diagnostics such as
`PROFILE_PROVENANCE_INVALID` instead of an uncaught validation exception.

## Hidden Default Audit

The machine-readable audit now classifies:

- `PROJECT_DATA_VALUE`: 1
- `ROUTING_ALGORITHM_POLICY`: 2
- `LEGACY_ROUTING_POLICY`: 2
- `STRUCTURAL_SOFTWARE_DEFAULT`: 7
- `SUSPICIOUS_HIDDEN_ASSUMPTION`: 0

## Test_01 State

Test_01 remains incomplete because the remaining engineering/profile inputs are
still absent. No shadow validation, sizing, routing, or engineering run was
performed for the real project.
