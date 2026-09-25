# UFH automatic split and retry v1

## Scope and sequence

`assess_with_automatic_split_retry(request, inputs)` first runs the established
sizing → coverage routing → candidate mapping → engineering assessment path.
Only a correctly routed and sizing-accepted candidate with an explicit
`SPLIT_REQUIRED` pressure result may trigger another attempt. The next request
sets `requested_circuit_count` to the prior actual count plus one and calls the
entire pipeline again. Every attempt therefore has newly computed zone areas,
heat allocation, thermal solutions, mass flows, Reynolds/friction values,
pressure losses, and balanceability whenever every circuit has complete
hydraulic results and a control characteristic is declared. Balanceability is
also explicitly evaluated by the retry path for a pressure-rejected candidate
when those inputs exist; it does not replace the pressure failure or its split
reason. Ordinary callers retain the existing integration behavior by default.

The search is bounded to the initial candidate and exact counts `N+1` and
`N+2`, never exceeding 3 circuits. The first engineering-accepted candidate
terminates the search. No global optimization or alternate partition method is
performed.

## Retry gates

Retryable: circuit pressure over the EN limit and a manufacturer circuit
pressure limit, when the existing integration explicitly reports
`recommendation=SPLIT_REQUIRED` and the source routing and sizing assessments
are accepted.

Not retryable: surface output/heat-flux failure, no physical thermal root,
thermal or numerical solver failure, missing inputs (rejected by the typed
input models before orchestration), candidate mapping/routing failure,
sizing-coverage rejection, balanceability failure without an explicit split
recommendation, or uncertain characteristic-domain results. In particular,
the current balanceability assessment does not imply that adding circuits will
fix the conflict.

## Legacy length policy

`LEGACY_MVP_ROUTING_POLICY` remains 40–80 m per circuit. The retry orchestrator
does not weaken or override route validation. An exact-count candidate rejected
by the router is recorded with `REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE`; the
original engineering failure remains in the prior attempt. If the source
length evidence is itself below `N+1` times the legacy minimum, the result also
records `LEGACY_MINIMUM_CIRCUIT_LENGTH_BLOCKED_SPLIT` with the measured total
and required minimum. This is a necessary-length warning, not a claim that a
different pipe design or an altered routing policy was evaluated.

## Audit record

Each attempt records index, requested and actual count, routing status, IDs,
actual route lengths, engineering status, triggering retry reason, diagnostic
codes/messages, per-circuit flow and pressure when calculated, and sizing,
routing, engineering, and combined candidate digests. The result records the
initial count, finite attempt history, terminal status, optional accepted
candidate, accumulated diagnostics, and deterministic result digest.

Statuses are `ACCEPTED_INITIAL`, `ACCEPTED_AFTER_RETRY`, or
`FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE`. The retry wrapper does not change
the underlying engineering statuses or kernel calculations. An infeasible
requested count terminates immediately; pressure failures at count 3 terminate
with `MAX_CIRCUIT_COUNT_REACHED`.
