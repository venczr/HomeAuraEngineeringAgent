# HomeAura DOMAIN-1 Contract

## Scope

DOMAIN-1 is a read-only, in-memory compatibility layer over the existing
MagiCAD/AutoCAD rooms export. DOMAIN-2B exposes that layer through one
isolated read-only preview route. Neither layer changes `rooms.json`, API
version 0.6.0, the AutoCAD plugin, DLLs, `HA_SYNC_MODEL`, `HA_SYNC_ROOMS`,
Boundary extraction, the existing room routes, or the IFC importer and its
preview route.

The first hierarchy is:

`DomainDocument -> Project -> Building -> Level -> Room -> Boundary`

`IfcSpaceGeometry` remains an optional candidate attached to a room. It
never replaces the AutoCAD Boundary.

## Schema and strict output

The domain schema version is the literal string `1.0`.

Every Pydantic model owned by DOMAIN-1 uses `extra="forbid"`. The
document contains:

- `schema_version`
- `legacy_format_version`
- one `project`
- document diagnostics

Project, Building, Level, Room and Boundary expose `stable_id`,
`source`, `validation_status`, their own business fields and
diagnostics. The new output is independent from the input object.

The allowed validation statuses are:

- `validated`
- `provisional`
- `requires_confirmation`
- `invalid`
- `missing`

The source kinds used by DOMAIN-1 are:

- `derived_deterministic`
- `legacy_placeholder`
- `legacy_room`
- `legacy_boundary`
- `ifc_space_candidate`

## Deterministic UUIDv5 identities

The fixed namespace UUID is:

`b62d9c24-0c2f-5e2a-8c7d-2d4bb9c98772`

Text normalization for `project_id`, `DrawingName` and room `Code` is:

1. Unicode NFKC
2. trim leading and trailing whitespace
3. Unicode `casefold`

AutoCAD handles use Unicode NFKC, trim and uppercase.

Every UUIDv5 name is built by one collision-safe helper:

```python
json.dumps(
    [
        "homeaura-domain-id",
        1,
        entity_type,
        *canonical_components,
    ],
    ensure_ascii=False,
    separators=(",", ":"),
    allow_nan=False,
)
```

The exact component arrays are:

- Project:
  `["project", canonical_project_id, canonical_drawing_name]`
- Building placeholder:
  `["building", project_uuid, "unassigned"]`
- Level placeholder:
  `["level", building_uuid, "unassigned"]`
- Room with SourceHandle:
  `["room", project_uuid, canonical_drawing_name, "handle",
  canonical_handle]`
- Room fallback without SourceHandle:
  `["room", project_uuid, canonical_drawing_name, "code",
  canonical_code]`
- Boundary:
  `["boundary", room_uuid, "handle", canonical_boundary_handle]`

The complete raw-field-to-UUID map is:

| Entity | Raw or derived source | Transform | UUID component |
| --- | --- | --- | --- |
| Project | caller `project_id` | reject path; NFKC; trim; casefold | `canonical_project_id` |
| Project | payload `DrawingName` | validate; reject path; NFKC; trim; casefold | `canonical_drawing_name` |
| Building | Project UUID | lowercase UUID string | `project_uuid` |
| Building | no raw field | fixed literal | `"unassigned"` |
| Level | Building UUID | lowercase UUID string | `building_uuid` |
| Level | no raw field | fixed literal | `"unassigned"` |
| Room | Project UUID | lowercase UUID string | `project_uuid` |
| Room | Project `DrawingName` | already canonicalized | `canonical_drawing_name` |
| Room | `SourceHandle`, when present | reject path; NFKC; trim; uppercase | `"handle"`, `canonical_handle` |
| Room | `Code`, only when handle is absent | reject path; NFKC; trim; casefold | `"code"`, `canonical_code` |
| Boundary | owning Room UUID | lowercase UUID string | `room_uuid` |
| Boundary | `Boundary.SourceHandle` | reject path; NFKC; trim; uppercase | `"handle"`, `canonical_boundary_handle` |

There are no other UUID inputs. Raw Building, Level, IFC GlobalId,
IFC StepId, IFC file fields, room Name, geometry, status and portable
evidence never enter a UUID name. The IFC GlobalId is an alias only.

The entity type is the third JSON element after
`"homeaura-domain-id"` and integer schema discriminator `1`.
Components are not joined and `repr` is not used. Compact JSON array
encoding preserves component boundaries even when values contain `|`,
commas, quotes or other separator-like characters.

Absolute local paths are not used in UUID names or emitted in domain
output. Absolute Windows, UNC, device, POSIX and `file://` values are
rejected for `project_id`, `DrawingName`, Room `SourceHandle` and
`Boundary.SourceHandle` with controlled `unsafe_identity_path`.
`Room.Code` is rejected by the same rule when it is the identity
fallback because SourceHandle is absent. The error contains only the
safe identity field name, never the supplied path or basename.
`DrawingFullPath` is never emitted.

The Project UUID is `derived_deterministic`, not a permanent external
identifier. Renaming `project_id` or `DrawingName` changes it. Therefore
Project has `requires_confirmation`. The automatically created
`Unassigned Building` and `Unassigned Level` also have
`legacy_placeholder` source and `requires_confirmation`.

A room with a unique SourceHandle is validated within the current
drawing identity. A Code fallback is allowed only when SourceHandle is
absent and is always `requires_confirmation`. Empty normalized Handles
or Codes are rejected. Duplicate normalized SourceHandles and duplicate
normalized Codes are also rejected.

DOMAIN-1A changed every derived ID relative to the first uncommitted
DOMAIN-1 implementation. No migration is required: the initial
delimiter-joined IDs were never integrated, persisted, staged or
committed.

DOMAIN-1B does not change UUIDs for valid non-path identity inputs.
Rejecting path-shaped identity values prevents two different paths with
the same basename from collapsing to one identity.

DOMAIN-1C extends that rejection to `Room.Code` only while it is the
active identity fallback. Valid non-path Code values preserve their
pre-DOMAIN-1C UUIDs in both legacy formats 1.0 and 1.1.

## Legacy adapter

The canonical adapter input is the original `Mapping`/`dict` rooms
payload plus a caller-supplied `project_id`.

The adapter:

- supports exactly legacy formats 1.0 and 1.1;
- rejects any other version, including an unknown 1.x minor version,
  with `DomainAdaptationError`;
- validates the known legacy structure with the existing
  `RoomExportReport`;
- works from a deep validation copy and never mutates the input;
- does not serialize the input back through `RoomExportReport`;
- reads `IfcSpaceGeometry` from the raw room mapping before Pydantic
  `extra="ignore"` can discard unknown nested evidence;
- deep-copies transferable nested values into the domain result;
- lists unknown root, room, Boundary and IFC fields in diagnostics
  instead of silently losing them;
- recursively excludes Mapping entries whose keys are absolute paths or
  `file://` URIs;
- records `unsafe_mapping_key_excluded`, a safe structural location and
  exact `removed_count` without including the unsafe key;
- preserves all safe sibling entries, including a literal
  `<absolute_field_name_redacted>` key;
- performs no file writes.

When SourceHandle is missing, the validation copy receives an empty
handle only so the known legacy fields can still be checked by the
current required-string contract. The original mapping remains
unchanged and the resulting room identity is the guarded Code fallback.

## Read-only DOMAIN preview API

The only DOMAIN API connection is:

`POST /api/v1/rooms/domain/preview`

It accepts this strict JSON envelope:

```json
{
  "project_id": "Test_01",
  "rooms_payload": {
    "FormatVersion": "1.0",
    "DrawingName": "Test_01.dwg",
    "Rooms": []
  }
}
```

`project_id` is a strict string from 1 to 128 characters.
`rooms_payload` must be a JSON object. Unknown envelope fields are rejected.
The project identity is passed directly to the DOMAIN-1 identity checks; it
is not resolved as a file-system path.

The successful HTTP 200 response is a strict `DomainDocument`. The route
calls only `adapt_rooms_payload` and performs the conversion in memory. It
does not consult the project registry, read `rooms.json`, read any other
project file, persist the result, create history, open a connection, or start
a subprocess.

The route is available only when both the direct ASGI `Request.client` is a
loopback address and the single raw `Host` header names a supported local
authority. `Forwarded`, `X-Forwarded-For` and `X-Forwarded-Host` are not
trusted. This is independent from the known launchers binding Uvicorn to
`127.0.0.1`.

The accepted Host authorities are only `localhost`, `127.0.0.1` and `[::1]`,
with an optional ASCII decimal port from 1 to 65535. The comparison for
`localhost` is case-insensitive. Missing, repeated, conflicting, malformed,
non-ASCII, whitespace-containing, userinfo, comma-list, zone-qualified,
trailing-dot, alternate integer IP and non-local Host values are rejected
without DNS resolution and without reflecting the supplied value. This
prevents a loopback client reached through a DNS-rebinding Host from using
the route.

The request must contain exactly one raw
`Content-Type: application/json` header. The only permitted parameter is
`charset=utf-8`. Equal or conflicting duplicate Content-Type headers are
rejected before the body is read. Requiring that unambiguous non-simple
content type prevents a browser page from using a simple `text/plain`
form-style POST to a local service.

The raw request limit is 10 MiB. The handler checks raw `Content-Length`
headers for duplication and syntax, rejects a declared over-limit body before
reading, and then counts bytes from `Request.stream()`. It does not call
`request.body()` or `request.json()`. Missing `Content-Length` is allowed, but
the same streaming limit still applies.

UTF-8 and JSON are decoded only after the byte limit. JSON objects with
duplicate keys at any nesting level are rejected. `NaN`, `Infinity` and
`-Infinity` are rejected. The top-level JSON value must be an object. Pydantic
validation runs only after these checks.

Errors have this fixed structure:

```json
{
  "detail": {
    "code": "stable_machine_code",
    "message": "safe fixed message"
  }
}
```

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `domain_payload_invalid` | Invalid length, UTF-8, JSON, duplicate key, non-finite number, or top-level value |
| 403 | `loopback_required` | Direct client is not loopback |
| 413 | `domain_payload_too_large` | Declared or actual raw body exceeds 10 MiB |
| 415 | `domain_content_type_invalid` | Required JSON content type is absent or invalid |
| 422 | `domain_request_invalid` | Strict request envelope is invalid |
| 422 | `domain_rooms_payload_invalid` | Legacy rooms payload cannot be adapted |
| 422 | `unsafe_identity_path` | DOMAIN-1 returned its typed unsafe identity signal |
| 500 | `domain_preview_failed` | Unexpected preview failure |

Error responses never include exception text, tracebacks, Pydantic input
values, `project_id`, `DrawingFullPath`, local paths, file URIs, environment
values, or supplied credentials. `unsafe_identity_path` is selected only from
the typed `DomainAdaptationError.code`; exception text is never searched.

AutoCAD and the existing room synchronization, snapshot, analysis, and IFC
flows do not call this route. No existing reader or writer is redirected to
the domain models.

## Boundary compatibility

DOMAIN-1 does not recalculate geometry.

- An existing `validated` LWPOLYLINE Boundary stays `validated`.
- An existing `provisional` Polyline3d Boundary stays `provisional`.
- `ambiguous`, `invalid` and `unsupported` never become validated.
- `missing` never becomes validated.
- Boundary identity uses the owning Room UUID and normalized
  `Boundary.SourceHandle`.
- The legacy Boundary object is deep-copied as evidence.

## IfcSpace candidate compatibility

`IfcSpaceGeometry` remains `ifc_space_candidate`.

`geometry_status="validated_candidate"` maps to domain
`validation_status="provisional"` because it is evidence, not the
authoritative room Boundary. Its `GlobalId` is stored as an
`ifc_global_id` alias and source evidence. It does not replace or
re-key the room.

The adapter does not import `ifcopenshell` or
`agent.ifc_space_importer`.

If `IfcFile.Path` contains an absolute local path:

- the path is not emitted;
- the safe file name is retained;
- the supplied SHA-256 and IFC schema are retained;
- IFC GlobalId and StepId are retained;
- an exact redaction diagnostic is added;
- the original input payload is not changed.

Any other absolute path found in transferable nested evidence is
redacted. Detection covers Windows drive paths, UNC paths, Windows
device paths, POSIX absolute paths and `file://` URIs. The same rule
applies to diagnostics, identifiers, aliases, safe evidence fields and
portable payload values. This deliberately prioritizes portable,
non-sensitive domain output over byte-for-byte preservation of
arbitrary local payloads.

Mapping keys use a stricter rule than values. An unsafe key causes its
entire entry to be excluded. It is never replaced with a shared
placeholder, so multiple unsafe keys cannot overwrite one another.
Nested mappings are handled recursively. Diagnostics report only the
safe structural location and number of excluded entries. The input
Mapping remains unchanged.

## Migration strategy

DOMAIN-1 is an adapter, not a storage migration.

1. Keep existing `rooms.json` 1.0/1.1 as the source contract.
2. Build `DomainDocument` in memory for read-only consumers.
3. Preserve Boundary and IFC candidate statuses exactly as evidence.
4. Surface placeholders, fallbacks and unknown fields as diagnostics.
5. Confirm authoritative Project, Building and Level identities in a
   later vertical.
6. Keep the DOMAIN preview in-memory and read-only.
7. Add persistence only in a separately reviewed job.

No current project-data reader or writer is redirected to the domain models
in this stage.

## Compatibility guarantees

DOMAIN-1 must keep these baselines unchanged:

- API version 0.6.0
- behavior and methods of every pre-existing API route
- legacy rooms 1.0 parsing
- Boundary 1.1 parsing
- optional IfcOpenShell behavior
- AutoCAD plugin 1.2.0.0
- current C# room geometry executable
- all DWG, BAK, IFC and MRD files

## Non-scope

DOMAIN-1 does not implement:

- persistent Project/Building/Level records
- write APIs or any additional DOMAIN route
- schema migration of `rooms.json`
- changes to AutoCAD or MagiCAD commands
- heat-loss itemization
- water, drainage, electrical or automation design
- equipment, routes, specifications or packages
- drawing sheets or release workflows
