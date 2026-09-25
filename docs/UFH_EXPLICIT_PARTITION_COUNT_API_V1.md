# UFH explicit partition count API v1

## Contract

`FloorHeatingCoverageRequest.requested_circuit_count` accepts `None`, `1`, `2`,
or `3`. `None` retains the existing automatic calculation:

```text
max(1, ceil(estimated_required_pipe_length_mm / maximum_circuit_length_mm))
```

An explicit integer asks the coverage planner to create exactly that many
deterministic zone partitions, then routes each zone with the existing V2
single-circuit router. This is orchestration around the production router, not
a second geometry or partition algorithm. A returned plan must contain exactly
the requested number of valid circuits. The planner never silently substitutes
another count.

Invalid values (including booleans, floats, strings, values below 1, and values
above 3) fail request validation with `INVALID_REQUESTED_CIRCUIT_COUNT`.
An explicit request that cannot produce a valid candidate returns an impossible
plan with `REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE`, followed by the underlying
route/coverage diagnostic when available.

## Length policy

The existing per-circuit `40000–80000 mm` limits remain in force in both modes.
This is the `LEGACY_MVP_ROUTING_POLICY`; it is not presented as an EN 1264
physical limit. Exact-count requests do not waive route geometry validation,
coverage validation, or measured circuit-length checks.

Consequently, a 44.1 m route cannot be split into two routes that each meet the
40 m minimum: their combined available length is less than 80 m even before
additional geometry effects. The existing 44.1 m fixture fails an explicit
two-circuit request, and a separate three-zone fixture produces a 32.1 m route
that is rejected with `ROUTE_LENGTH_INVALID` and `ACTUAL_LENGTH_MM=32100`.
Therefore the minimum can block a hydraulic split for a short overloaded
circuit; this API does not weaken the minimum.

## Backward compatibility and identity

Callers omitting the field behave identically to callers setting it to `None`.
Automatic circuit selection and route geometry are unchanged. The request
model includes the optional field in the canonical digest payload, as it does
for all serialized request inputs. Explicit counts are part of the request and
therefore produce distinct plan identities.

## Scope

This API enables orchestration to request candidates with 1, 2, or 3 circuits.
It does not implement automatic engineering retry, hydraulic optimization,
geometry balancing, route-pattern changes, or an alternative to the legacy
40–80 m policy.
