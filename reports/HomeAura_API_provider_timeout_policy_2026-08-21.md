# HomeAura multi-model API timeout policy — 2026-08-21

## Result

The canonical child-process broker now supports long-running reasoning models
without introducing retries or weakening accounting, IPC, credential, or
no-replay boundaries.

- Default provider timeout: `180` seconds.
- Dedicated non-secret configuration key:
  `HOMEAURA_MULTI_MODEL_API_TIMEOUT_SECONDS`.
- Allowed provider timeout range: canonical ASCII decimal integer `30..240`.
- Absolute provider timeout maximum: `240` seconds.
- Parent child-process lifecycle timeout: fixed `270` seconds
  (`240 + 30` seconds cleanup margin).
- Missing timeout setting uses `180`; malformed, duplicated, out-of-range, or
  conflicting env/explicit values fail closed.

The parent deliberately does not read the credential-bearing env file. The
child authenticates the ledger first, then reads only the dedicated timeout
entry, rejects invalid configuration and closes the ledger before resolving
the credential binding or opening transport.

## Preserved safety behavior

- Exactly one wire attempt per globally unique request identity.
- No automatic retry after timeout, network uncertainty, HTTP error, lost
  response, or parent lifecycle timeout.
- Chat reservation is committed before transport. Provider `TIMEOUT` or
  `NETWORK_ERROR` returns `UNCERTAIN`, reconciles the full reservation when
  usage is unknown, journals safe metadata, and keeps `replay_permitted=false`.
- `MODEL_LIST` claims its globally unique zero-token identity before transport.
  Transport uncertainty returns and journals `UNCERTAIN` with zero charged
  tokens and no replay.
- Parent lifecycle expiry kills and drains the child once, reports `TIMEOUT`,
  and does not pass process-level `API_KEY` or `AUTHORIZATION` values.
- Prompt/response persistence, response/message size limits, model-count bound,
  reservation bounds, and credential isolation are unchanged.

## Exact implementation bytes

- `C:\AI\HomeAuraOrchestrator\agent\autonomy\provider_broker_runtime.py`
  - SHA-256: `B040480B29126D13D28F1F431FF76A9416C8C1B9620182297DA26E6BAC9A732B`
- `C:\AI\HomeAuraOrchestrator\tests\test_autonomy_provider_broker_runtime.py`
  - SHA-256: `B37BAA6D3F92B16BE0843FA398F90D33CEC2822CD55FC2C9308FBB22F806192C`

## Evidence

- Focused timeout/broker suite: `16/16` passed.
- Post-freeze autonomy suite: `420/420` passed.
- Independent review: `FORMAL GO`, `P1=0`, `P2=0`, on the exact hashes above.
- All provider behavior in the focused acceptance suite was mocked; the
  implementation and tests made no provider calls.

A concurrently launched Luna request was audited read-only because its outer
shell ended without stdout. It is not an acceptance probe and must not be
retried. Its durable terminal state was:

- Request identity:
  `ha-c05c06/body-fast/EB1471F85DD6/0AA200340012/gpt-5.6-luna/v1`
- One journal record: `HTTP_502`, `provider_timeout_seconds=180`,
  `replay_permitted=false`, no raw content.
- Ledger row `72`: reserved/charged `33,792`, usage unknown, reconciled `1`.
- Open reservations after settlement: `0`.
- No provider-broker child process remained.

This terminal HTTP error is accounted evidence only; it does not prove model
capability and does not authorize semantic replay.

