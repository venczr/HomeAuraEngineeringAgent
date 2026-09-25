# TEST01_INTERACTIVE_ENGINEERING_INTAKE_V1

This block adds a UI-neutral intake/session layer for Test_01 Room Code 101,
SourceHandle `101DAA3`. It reuses the revision-bound SP60 source audit and the
existing UFH pre-generation questionnaire, resolver handoff, and authoring
loader. It does not calculate SP60 heat loss or execute UFH sizing/routing.

## Persistence and authority

Answers are stored separately at
`projects/Test_01/engineering/ufh_engineering_intake_v1.json` only when the
caller commits an answer. The file is schema version `1.0`, digest-bearing,
and atomically replaced with an expected-artifact-digest check. `DWG`, `MRD`,
`rooms.json`, IFC, and source snapshots are read-only. The artifact keeps
answers, stale answers, and source/user conflict records; it does not copy
project source files or claim normative/manufacturer authority.

Each answer carries `PROJECT_APPROVED_USER_INPUT`, source type/reference,
question and room identity, timestamp, units where applicable, normalized and
original value, dependency digest, transformation, and validation state.
Resolver outputs remain owned by the existing resolver handoff. A parent
replacement/clear makes dependent answers stale and re-runs supported existing
resolvers. Locality is the first fully connected path: locality answer → the
SP131 resolver and normative dataset → existing authoring binding. Unknown
localities stay actionable.

Typical API flow:

1. `create_persistent_test01_intake_session(...)` reads current sources and
   restores a compatible answer artifact.
2. `answer_and_persist_engineering_intake(...)` validates the currently active
   question, updates the session/resolvers, then persists the complete sidecar
   atomically. `replace_engineering_intake_answer` and
   `clear_engineering_intake_answer` are available for in-memory edits; persist
   the resulting session with `persist_engineering_intake_session`.
3. Reopening rebuilds the source binding and resolver state; stale source
   dependencies are not silently reused.

## Question groups

The initial session presents ten top-level questions: locality; room use;
above and below semantics; four candidate wall sides in one structured human
question; openings; construction method; ventilation mode; infiltration
source; and thermal-bridge handling. Follow-up questions are conditional.
The four wall IDs (A–D) include room-relative endpoints/length and source
digests for UI highlighting, but remain geometric candidates and are never
silently promoted to exterior thermal boundaries.

Observed supply/extract/ACH values are displayed as project observations.
Only explicit confirmation can create a user-confirmed semantic claim; no
airflow resolver is fabricated here. `AirExchangeRate` is never treated as
design ventilation flow or infiltration flow. `NONE` for openings is stored
as a provenance-bearing explicit confirmation (`COMPLETE_EMPTY` inventory),
while the overall opening/net-area readiness stays partial until area
accounting is actually bound.

## Readiness and calculation boundary

The session exposes a readiness dashboard, profile-loader status/missing
paths, current questions, stale answers, conflicts, and a deterministic
dependency/session digest. Current Test_01 remains `INCOMPLETE`; geometry is
ready, but climate locality, thermal-boundary inventory/areas, openings/net
areas, constructions/U-values/bridges, required ventilation flow,
infiltration inputs, and Q_mts applicability still block a first supported
SP60 calculation. Consequently the readiness gate does not emit
`READY_FOR_FIRST_SP60_CALCULATION` for this project. No calculation is run
automatically, even if a future session reaches that state.

The existing construction/material resolvers are invoked only through their
existing questionnaire handoff when a supplied structured construction
submission is valid. They do not accept user-asserted normative/catalog
authority. Room-use and process answers remain semantic claims until a
source-backed SP60 applicability resolver can classify Q_mts.
