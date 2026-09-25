# HomeAura canonical API ledger continuation — 2026-08-21

## Result

The configured multi-model API ledger was continued without resetting or
deleting any accounting history. The owner-reported unlimited provider
entitlement does not remove the local safety boundary: the broker now derives
and enforces the authenticated absolute usable ceiling as
`50,000,000 - 2,500,000 = 47,500,000` tokens.

No provider request was made during implementation, migration, verification,
or independent review.

## Runtime state

- Durable ledger UUID (unchanged): `1b9fff6c-d806-4229-b326-6424e6a9a3f8`
- Requests / reservation rows: `68 / 68`
- Accounted spend: `999,641`
- Recovered starting spend: `854,173`
- Live charged total: `145,468`
- Open reservations: `0`
- Historical tombstones: `160`; all retained with no-replay/delta-zero semantics
- Global ceiling: `50,000,000`
- Protected safety reserve: `2,500,000`
- Effective/live ceiling: `47,500,000`
- Settlement aggregate: `a95f5abc94a230adb02b3007828c35f85845c40445bd37f45a89260f9e993223`

## Continuity evidence

- Authoritative in-database checkpoint:
  `14fd28e245fcb93fab43c422ce058d1332dc49e3816f9e2fe75273bfc9a7eaac`
- It binds request count `68`, spend `999,641`, open count `0`, and previous
  checkpoint `a84b0028634de95d1a6f47fde76037a65c27bf1bfb3f7fe4d6c6cc7ee47a292e`.
- The prior external prefix checkpoint remains byte-for-byte at its original
  path; file SHA-256:
  `a63a3caeff1afcd43201b4b2fd9736ea1747289c08b8e83897e79253c44d52e3`.
- Embedded recovery checkpoint remains:
  `7a8d7760af5d10234d44db07e89eae628adc2f2f4739118243af690745ef6925`.
- Canonical ledger file SHA-256 after migration:
  `a72b541380feb4a5ec65affad7cfd7ed992f0d74cc600125d3a4fdea25fd04e7`.
- Derived continuation mirror file SHA-256:
  `d49fca21ff46fbed6a33cffd9726b595ae1c3c5a840b03376d2ee06dc23dcea1`.

## Safety behavior added

- The original recovery checkpoint is immutable; live checkpoints form a
  separate append-only hash chain inside SQLite.
- Reservation and reconciliation changes append their checkpoint in the same
  `BEGIN IMMEDIATE` transaction.
- Core and continuation table schemas, uniqueness, check constraints, and
  append-only triggers are verified fail-closed.
- The broker validates ledger authority before loading the credential binding.
- Chat and zero-token `MODEL_LIST` request identities are globally disjoint and
  atomically claimed; duplicate identities cannot reach provider transport.
- The migration opens SQLite with `mode=rw`, never creates a replacement
  ledger, and refuses mirror targets that overlap the ledger, identity, or
  historical checkpoint.
- The external checkpoint is a derived mirror only; it is not the transactional
  authority.

## Exact implementation hashes

- `agent/autonomy/canonical_ledger_continuation.py`:
  `E95F33BDE1F52EC963DEAA52E6CB2B9CBF53C3F64D875EFADCDE1B786AA96E75`
- `agent/autonomy/token_ledger.py`:
  `71C38B91A185C5674C07C490142D0B6DEB2BB530BE1AB6C16167CD0A52F9AA87`
- `agent/autonomy/provider_broker_runtime.py`:
  `265F6AD89F8B7AF726BCDDC8D223E01722D26CBEE5552D92BFECF73F97ABD0C7`
- `scripts/migrate_canonical_ledger_continuation.py`:
  `47DF5DFAA42D439C454D30C7B50E74BD4CF41FA70F54AF2D8B82FBB66C116F1C`
- `tests/test_autonomy_canonical_ledger_continuation.py`:
  `E3879AA5ED585D95CD08C51E10F641E223D51E55A721712779F64F8BACED654B`
- `tests/test_autonomy_provider_broker_runtime.py`:
  `41DFB1AA7315C30C187E8C57EE75BAD9F4D9B78A6DCB8E5C3ADC843C3C607513`

## Validation and review

- Focused implementation suite: `23/23` passed.
- Post-migration autonomy suite: `409/409` passed.
- Independent final audit: `FORMAL FINAL GO`, `P1=0`, `P2=0`.
- Independent compatibility suite: `86/86` passed.
- Independent broker EOF preflight: clean exit with no stdout/stderr, no ledger
  or journal mutation, and no provider call.

This closes the ledger-continuation safety boundary. Future provider work must
still use `ChildBrokerClient`, unique request identities, bounded reservations,
and independent evidence checks; no direct provider transport is authorized.

