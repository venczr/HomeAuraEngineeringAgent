# UFH Project Adapter → Pre-generation Session V1

## Scope

This application layer composes the existing room adapter, project-owned value
collector, dynamic questionnaire, climate resolver, resolver handoff, and
authoring loader. It does not call sizing execution, coverage/routing,
engineering integration, the engineering kernel, or automatic retry.

## Entry points

- `create_ufh_pre_generation_session(source, normative_profile=...)` accepts an
  already sourced `ProjectRoomUfhSource`, runs the production project adapter,
  binds identity/context and project-owned values, then creates dynamic
  questions and authoring readiness.
- `create_test01_ufh_pre_generation_session(project_directory, ifc_directory,
  normative_profile=...)` calls the existing read-only, revision-pinned geometry
  authority assessment. It fails closed unless the existing authority decision
  is `AUTHORITATIVE`.
- `apply_ufh_questionnaire_answer(session, answer)` validates an active question,
  applies it with existing questionnaire semantics, dispatches the available
  local climate resolver, applies resolved output through the existing resolver
  handoff, and recomputes questions/readiness.
- `replace_ufh_questionnaire_answer(session, answer)` is the explicit correction
  path for a previously answered question. It invalidates dependent bindings
  before applying and resolving the replacement.
- `rebuild_ufh_pre_generation_session(session, source)` re-runs project mapping
  against a new source revision, preserves user decisions, refreshes
  project-owned values, invalidates stale bindings, and re-resolves climate
  when its location answer remains available.

## Session/readiness semantics

`active_questions` is the dynamic user-facing question set. A failed local
resolution re-exposes its question so the user can correct the answer.
`remaining_required_engineering_fields` is a separate union of the adapter's
missing project-to-UFH inputs and authoring-loader gaps; these are not
presented as questionnaire questions.

`READY_FOR_ENGINEERING` requires both the authoring loader to report `READY` and
the project adapter to report `READY`. It still does not launch engineering.
Unsupported resolvers return typed `UNSUPPORTED` results without authoring
physical values.

Session revisions use the project adapter digest, which includes the room
source, mapped fields/provenance, and geometry binding. Resolver requests add
their own normalized relevant decisions and resolver dataset context. Thus an
unrelated answer does not stale the climate binding, while a project revision
change does.

## Test_01 behavior

Test_01 is read through its explicit authoritative geometry evidence path; no
location is inferred or persisted. The initial session has the active climate
question, one project-owned ACH binding sourced from `AirExchangeRate`, and
remains incomplete. Synthetic test answers are held only in copied in-memory
session state. The SP 131.13330.2025 record is reached only via the registered
climate resolver and existing authoring handoff.

## Limitations

Only `CLIMATE_RESOLVER` is implemented. Other resolver types are dispatched as
typed unsupported results until their real resolver modules exist. No GUI,
session persistence, asynchronous job layer, or downstream UFH generation is
introduced here.
