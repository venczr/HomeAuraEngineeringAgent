# HomeAura Project Foundation

## Status

PROJECT-1 adds a strict, local-first project contract without producing
engineering calculations or drawing routes.

Implemented artifacts:

- `CanonicalProjectModel`;
- `ProjectSeed`;
- serialized in-memory `SourcePoint` revision history;
- `Assumption` and `Issue`;
- `RuleRegistryEntry`;
- `EquipmentCatalogItem`;
- `DesignVariantMetadata`;
- `SheetManifest` and `SheetManifestEntry`;
- `AuditEvent`;
- an external 130-sheet manifest.

All models use `schema_version="1.0"` where they are document roots and reject
unknown output fields.

## Safety boundary

This stage does not:

- calculate heat loss, hydraulics, ventilation, electrical loads, or cost;
- invent equipment, materials, prices, climate data, or normative values;
- add or change an API route;
- write a project file;
- modify `rooms.json`, DWG, BAK, IFC, or AutoCAD objects;
- launch AutoCAD, MagiCAD, NETLOAD, or an API listener.

Design variants begin with `status="not_implemented"`. This is deliberate:
Budget, Comfort, and Premium may not contain fabricated engineering results.

## Source plans reviewed

The supplied architectural PDFs contain one first-floor plan and one mansard
plan. They provide useful architectural evidence for a two-level house. A
boiler room is labelled on the first floor.

The PDFs do not provide a confirmed water-inlet source point with world/local
coordinates, level relation, wall normal, and confidence. Handwritten room
labels and dimensions remain reference evidence until they are tied to the
authoritative AutoCAD model. PROJECT-1 therefore does not create a real project
seed from the PDFs and does not draw approximate networks.

## Source points

The two required source-point kinds are:

- `boiler_room`;
- `water_inlet`.

Every active boiler-room point, including a `proposed` point, requires:

- world coordinates in metres;
- local coordinates in metres;
- stable level ID;
- stable room ID;
- confidence and source evidence.

An active `proposed` boiler-room point with this complete context remains a
proposal: it is not human-confirmed and cannot satisfy project readiness. An
incomplete proposed boiler-room point may exist only as an inactive draft.
Missing coordinates, room IDs, and level IDs are never generated from a rule
or assumption.

A marked water inlet requires:

- world coordinates in metres;
- local coordinates in metres;
- stable level ID;
- level elevation;
- unit wall-normal vector;
- confidence and source evidence.

`build_project_seed()` returns `status="incomplete"` and an explicit
`missing_required_source_points` list until both points are human-confirmed.
The only confirmation combinations are:

- `state="marked"` with `evidence.kind="user_marked"` for a point placed
  directly by a person;
- `state="accepted"` with `evidence.kind="user_approved"` for a separately
  and explicitly accepted point.

`state="marked"` alone is not proof of a human action. In particular,
`evidence.kind="rule_proposed"` never satisfies readiness, even if coordinates
and a marked or accepted state are present.

At canonical-project validation time, every referenced level and room must
exist in the embedded `DomainDocument`. The boiler-room level must be the same
level that contains its referenced DOMAIN room. No missing coordinate, room,
or level is inferred from an assumption. A boiler-room wall normal is not
required because the point need not be wall-mounted.

`CanonicalProjectModel` cannot use `status="ready_for_design"` while the seed
is incomplete or while an open blocking assumption or issue exists.

Repeated selection is non-destructive. `replace_active_source_point()` marks
the previous record as inactive and `replaced`, keeps it in history, requires a
sequential revision, and creates a new deterministic seed revision.
PROJECT-1 serializes this revision history in the model, but durable disk or
database storage is not implemented yet.

## Equipment evidence

`EquipmentCatalogItem.verification_status="verified"` is allowed only when
`verified_fields` is non-empty and at least one source has:

- an official manufacturer or official publisher source type;
- a completed source-verification status and timestamp;
- a named publisher or manufacturer;
- a non-empty locator;
- the SHA-256 of saved verification evidence.

The permitted `verified_fields` are the actual equipment-data fields:

- `manufacturer`;
- `brand`;
- `model`;
- `article`;
- `category`;
- `compatible_systems`;
- `properties`;
- `service_clearances_m`;
- `connection_ports`.

Field names are trimmed, case-normalized, unique, and restricted to this
allowlist. Each item-level verified field must be listed in
`source.confirmed_fields` by at least one completed official manufacturer or
publisher source. Publisher and locator values are trimmed and must remain
non-empty. Retrieval and verification timestamps must include a timezone.

VERIFIED means both that the field name has completed official-source coverage
and that the equipment item contains a substantive value for that field.
The persisted `manufacturer`, `brand`, `model`, `article`, and `category`
strings are preserved exactly, including Unicode code points, case, hyphens,
and leading, trailing, or repeated internal whitespace. `strip()` is used only
as a non-mutating nonblank test. Lists and dictionaries must be non-empty, and
nested values may not hide `null`, blank strings, empty lists, or empty
dictionaries. Numeric zero and boolean false remain substantive values where
the declared field type permits them. Fields that are not named in
`verified_fields` remain ordinary draft data and are not promoted
automatically.

An `official_manufacturer` evidence record carries a separate
`manufacturer_identity`. The identity is normalized deterministically with
Unicode NFKC, trimming, repeated-whitespace collapse, and `casefold()`. No fuzzy
matching, legal-suffix removal, or alias inference is performed. Every attached
official-manufacturer record must match the equipment item's manufacturer
under this normalization. `publisher` is not a substitute and may differ when
the manufacturer identity matches. This normalization is computed only for the
separate identity comparison; it does not migrate or rewrite persisted catalog
keys or display strings.

The model records evidence that an independent verification was completed. It
does not access the network or verify a source by itself. A plain URL, an
unverified source, a third-party source, or incomplete verification metadata
cannot provide verified-field coverage. Auxiliary unverified sources may be
stored when they claim no confirmed fields. Automatic comparison of document
contents and contradiction detection are not implemented.
`manufacturer_identity` is a provenance statement stored in that evidence
record; it is not online authentication or cryptographic proof of manufacturer
identity.

## Determinism

The foundation uses:

- canonical UTF-8 JSON;
- sorted keys;
- finite JSON numbers only;
- SHA-256 input and domain hashes;
- a fixed UUIDv5 namespace for seed identity.

Source-point observation timestamps and seed creation time do not affect the
identity hash. Ordering of otherwise identical input points does not affect the
result. Source-point IDs and per-kind revisions must be unique. Drawing
evidence stores a file name only and rejects local path-shaped values.

## Strict PROJECT JSON

Every `StrictProjectModel.model_validate_json()` call uses the same strict
PROJECT JSON path. It decodes UTF-8, rejects duplicate keys at every nesting
level, and rejects `NaN`, `Infinity`, and `-Infinity` before Pydantic model
validation. Unknown fields remain forbidden and typed numeric fields do not
accept booleans.

All model validation also recursively rejects non-finite floats in free
`JsonValue` content, including assumptions, issues, equipment properties and
ports, and audit details. Deeply nested strings, booleans, and null values
remain valid JSON evidence. `canonical_json_bytes()` keeps `allow_nan=False` as
an independent serialization safety layer.

## External sheet manifest

`config/sheet_manifest.v1.json` is generated from:

`HomeAura_Professional_Engineering_Project_130_Sheets_v1.md`

Source document SHA-256:

`db1ab8021e4453b28e3a25771d99ea40f8d4d28eda7d6653710872cf57de1b64`

The manifest contains exactly 130 ordered, unique sheet codes:

| Discipline code | Meaning | Count |
|---|---|---:|
| GEN | General and coordination | 35 |
| OV | Heating | 25 |
| TM | Plant room and heat-mechanical systems | 21 |
| VK | Water supply and sewer | 19 |
| VENT | Ventilation and cooling | 10 |
| EM | Electrical | 6 |
| AUT | Automation | 4 |
| SPEC | Specifications, commissioning, handover | 10 |

The baseline applies to a two-storey individual residential house. Additional
storeys, collectors, equipment units, zones, or complex details may add sheets.
Excluding a baseline sheet requires a recorded reason.

The manifest defines content and identity, not final graphic layout. HomeAura
navy/turquoise branding, title blocks, fonts, line weights, and PDF/DWG sheet
templates belong to the later DOCUMENT stage and must be visually verified.

The manifest reference is the SHA-256 of its strictly validated, canonical
UTF-8 JSON. Keys are sorted, separators are compact, non-finite numbers and
duplicate keys are rejected, and raw file line endings are not part of the
identity. LF, CRLF, whitespace, and JSON key order therefore do not change the
reference; a semantic content change does.

## Explicitly unimplemented outputs

Engineering calculations, routing, and the Budget, Comfort, and Premium design
variants remain `NOT_IMPLEMENTED`. A not-implemented variant has no generation
time or calculation-case references. Issue references may still record why
work is blocked; they do not assert that a result exists. A standalone variant
requires unique issue IDs. `CanonicalProjectModel` resolves every referenced
ID to exactly one current `Issue` and accepts it only when the issue is open
and blocking. Orphan, duplicate, non-blocking, and resolved issue references
are rejected.

## Usage

```python
from datetime import datetime, timezone

from agent.project_foundation import (
    build_project_seed,
    load_sheet_manifest,
    sheet_manifest_reference,
)

manifest = load_sheet_manifest()
manifest_ref = sheet_manifest_reference()

seed = build_project_seed(
    domain_document,
    source_points,
    created_at=datetime.now(timezone.utc),
)
```

## Validation

Run the focused tests:

```text
.venv\Scripts\python.exe -m unittest discover -s tests -p test_project_foundation.py -v
```

Then run the complete Python and existing C# regression suites.

## Next compatible step

PROJECT-2 should add a hardened local API for project creation and source-point
updates using these models. It should keep legacy project-name routes intact,
persist revisions without overwriting history, and return explicit
`NOT_IMPLEMENTED` states for calculations and variants that do not exist yet.
