# UFH_PRE_GENERATION_QUESTIONNAIRE_V1

## Scope and API

Added `agent/ufh_pre_generation_questionnaire.py`. Existing production modules and
project artifacts are unchanged. No sizing, routing, kernel, retry or shadow run.

`build_ufh_pre_generation_questions(ProjectContext, QuestionnaireState)` returns
ordered typed questions, outstanding resolver requirements and SHA-256 digest.
`apply_ufh_questionnaire_answers(context, state, list[Decision])` returns a copy:
application is ordered and atomic, inactive/invalid answers raise ValueError.
`load_questionnaire_authoring(state)` delegates to the existing typed loader.
The envelope contains the existing typed authoring payload and separate qualitative
decisions. No new project persistence or kernel contract is introduced.

Each question has ID, group, Russian prompt, answer type, options, required flag,
reason, target authoring paths, dependency conditions and canonical unit if relevant.
Explicit answer revision is required; no clock is read. Provenance includes question
ID, source reference, revision, decision source and transformation. Collector values
must use integer mm and exactly the authoritative context coordinate-system ID.
The caller must supply a trusted geometry context; this module cannot establish its
authority or verify whether the chosen point is physically installable.

## Test_01 questions

Source: existing `docs/Test_01_UFH_engineering_profile_authoring_template.json`,
the current unfilled authoring state. Room extraction has room 101DAA3, indoor
setpoint and ACH; these and identity/boundary/area are not questionnaire fields.
No physical answer was supplied or entered into Test_01.

| Order | Question | Why needed |
|---|---|---|
| 1 | Населённый пункт и регион? | Select an authoritative climate source; no inferred outdoor temperature |
| 2 | Что находится снизу? | Resolve floor boundary condition |
| 3 | Что находится сверху? | Resolve ceiling boundary condition |
| 4 | Источник конструкций наружных ограждений? | Construction data/resolver instead of asking for U-values |
| 5 | Покрытие пола? | Resolve documented thermal resistance |
| 6 | Есть запрещённые для трубы зоны? | Explicit absence or geometry-selection workflow |
| 7 | Положение коллектора на плане? | Missing geometry-linked point |
| 8 | Каталог, автоматический подбор или спецификация системы? | Pipe/floor/manifold/control properties need product sources |
| 9 | AUTO, COMFORT, LOW_TEMPERATURE или CUSTOM? | Explicit layout design intent |
| 10 | WATER, ANTIFREEZE или PROJECT_SYSTEM? | Resolve fluid properties at a stated temperature |
| 11 | AUTO_DESIGN, известная подача или известный перепад? | Select one thermal input branch |
| 12 | Назначение обогреваемой зоны? | Separate surface limitation resolver, not valve characteristic |
| 13 | Есть неописанные проёмы? | Existing contract requires explicit confirmation |

There are **13 total initial questions**, not 41 raw fields. `pages()` returns
8 + 5 questions; the target of 5–10 total is not met for this incomplete source.
No question is silently discarded to meet a count. Known authoritative decisions
or resolved authoring values suppress corresponding questions.

## Dependencies and resolver boundary

- GROUND below exposes construction-source question; HEATED_ROOM does not.
  Qualitative adjacency never implies a boundary temperature or U-value.
- CUSTOM finish asks for construction/product documentation.
- YES exclusions/openings emits GEOMETRY_SELECTION_REQUIRED; NO writes [] with
  EXPLICIT_EMPTY and provenance. Missing/UNKNOWN remains UNSET in authoring.
- CATALOG/CUSTOM system asks for a reference; AUTO records selection intent.
  No raw pipe dimensions are requested, no catalog values are invented.
- CUSTOM layout exposes spacing/offset; other policies require a resolver for
  spacing, margin and area basis. No optimizer is implemented.
- WATER asks for reference temperature; ANTIFREEZE/PROJECT_SYSTEM asks for the
  source specification (including concentration/temperature where applicable).
- Known supply maps to solve_return and only supply input; known delta maps to
  solve_supply and only sigma input. AUTO_DESIGN leaves engineering mode unresolved.
- Surface use needs an external normative resolver. No EN1264 numbers are embedded.

Resolution references and qualitative answers stay in the questionnaire envelope.
External resolvers must produce existing AuthoredValue records with independent
source provenance. This block does not implement or claim to validate catalog,
climate, layered construction, fluid, control or surface resolvers.

## Limits and fail-closed behavior

Questionnaire completion is not engineering readiness. Incomplete authoring goes
through the existing loader and remains INCOMPLETE. Only direct explicit numeric
answers (collector, custom spacing/offset, selected thermal input) are materialized.
This layer adds no physical defaults.

Pre-existing loader limitations were observed and left unchanged: it materializes
a hardcoded Test_01 ACH and legacy routing settings when building a full profile;
it only supports empty exclusions/openings. Thus this block does not certify a
completed real profile as free of inherited loader assumptions. Nonempty geometry
requires the existing project geometry workflow and subsequent adapter integration.
Answer revision/replacement and resolver invalidation are not implemented: V1
accepts currently active questions only; callers must restart from the original
authoring state for changed decisions rather than edit saved resolved values.

## Verification

Tests cover real template read-only use, known fields, climate, adjacency,
explicit empty, pipe AUTO/catalog decisions, thermal alternatives, units/frame,
atomic failure, provenance, determinism/JSON round-trip and loader delegation.
Protected SHA-256 baseline covers authoring/profile, kernel, sizing, routing,
coverage, retry, DWG and MRD. Final report records comparison and regression results.

Executed: questionnaire (16 tests), authoring, profile and project adapter:
45 passed together. `git diff --check` passed (existing LF/CRLF warnings only).
All nine protected before/after SHA-256 hashes match. Existing files modified: none.

## Next bounded block

UFH_QUESTIONNAIRE_RESOLVER_HANDOFF_CONTRACT_V1: typed resolver requests/responses,
source provenance and stale-decision invalidation, without choosing physical
values, modifying equations or generating routes.
