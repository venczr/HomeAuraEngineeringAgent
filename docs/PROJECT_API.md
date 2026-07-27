# HomeAura Canonical Project Preview API

## Scope

PROJECT-2B adds one isolated, local-only validation endpoint:

`POST /api/v1/projects/canonical/preview`

The raw JSON body is a `CanonicalProjectModel`. There is no wrapper and no
path supplied by the caller. A successful response is deterministic canonical
JSON for the same validated model.

The route is a preview only. It does not create or persist a project.

## Successful request and response

The request must contain a complete `CanonicalProjectModel` JSON object.
The handler validates the raw bytes with:

`CanonicalProjectModel.model_validate_json(raw_body)`

This single strict PROJECT JSON path rejects duplicate keys at every depth,
non-finite JSON constants, malformed UTF-8/JSON, extra fields, invalid
coordinates and references, and invalid readiness or catalog evidence.

HTTP 200 returns `application/json` with no wrapper. The response is produced
with `canonical_json_bytes(validated_model)`, so keys are sorted, separators
are compact, Unicode is UTF-8, non-finite values are forbidden, and equivalent
models produce byte-identical responses. The returned bytes must themselves
pass `CanonicalProjectModel.model_validate_json`.

The response adds no timestamp or identifier and does not change source-point,
readiness, issue, assumption, variant, or other model state.

## Local access boundary

Both the direct ASGI client and the raw `Host` header are checked.

The direct client must be a valid IP loopback address. Forwarded headers are
never trusted.

There must be exactly one raw `Host` header. Accepted authorities are:

- `localhost`;
- `127.0.0.1`;
- `[::1]`;
- any of the above with one optional ASCII decimal port from 1 through 65535.

`localhost` matching is case-insensitive. The route performs no DNS lookup.
Missing, duplicate, non-local, malformed, whitespace-containing, comma-list,
userinfo, trailing-dot, alternate integer IP, or invalid-port Host values are
rejected. `Forwarded`, `X-Forwarded-For`, and `X-Forwarded-Host` do not
override the direct client or raw Host.

The application does not install permissive CORS middleware. Requiring a
strict JSON Content-Type also blocks browser-simple `text/plain` form-style
POST requests.

## Content-Type

The request must contain exactly one raw `Content-Type` header.

Accepted:

- `application/json`;
- `application/json; charset=utf-8`.

Media type and charset names are case-insensitive, and surrounding optional
whitespace around those parsed components is accepted. No other parameter is
allowed. Missing, repeated, malformed, non-ASCII, or other media types are
rejected before the body is read.

## Content-Length and streaming limit

The raw request-body limit is inclusive:

`10 * 1024 * 1024` bytes (10 MiB).

`Content-Length` may be absent. If present, there must be exactly one raw
header containing only ASCII decimal digits. Empty, whitespace, signed,
negative, nonnumeric, comma-list, equal duplicate, and conflicting duplicate
values are rejected before the body is read.

A declared value above 10 MiB is rejected before reading. The body is then
read with `Request.stream()` and actual raw bytes are counted. An absent or
smaller declared length cannot bypass the same 10 MiB streaming limit. No
temporary file is created.

## Fixed error envelope

Every controlled error has this shape:

```json
{
  "detail": {
    "code": "fixed_machine_code",
    "message": "fixed safe message"
  }
}
```

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `project_payload_invalid` | Invalid Content-Length, UTF-8/JSON, duplicate key, non-finite constant, or non-object JSON root |
| 403 | `loopback_required` | Direct client or raw Host is not an accepted local authority |
| 413 | `project_payload_too_large` | Declared or actual raw body exceeds 10 MiB |
| 415 | `project_content_type_invalid` | Required JSON Content-Type is absent or invalid |
| 422 | `project_model_invalid` | A valid JSON object violates `CanonicalProjectModel` |
| 500 | `project_preview_failed` | Unexpected internal preview failure |

Errors do not expose exception text, tracebacks, Pydantic error details,
request values, UUIDs, local paths, environment values, credentials, or other
caller-supplied strings. An existing `HTTPException` is re-raised and is not
converted into an internal error.

## No-I/O contract

The preview route:

- does not read or write a file;
- does not create a directory or temporary file;
- does not consult the project registry;
- does not load the external sheet manifest;
- does not call snapshot, room, or analysis persistence;
- does not call the DOMAIN adapter;
- does not call the IFC importer;
- does not open a socket or start a subprocess;
- does not start the API listener.

The embedded `DomainDocument` and `SheetManifestReference` are validated as
data already present in `CanonicalProjectModel`.

## Compatibility

`agent/api.py` remains the composition root and includes the project preview
router once. API version `0.6.0` is unchanged.

All existing health, project listing, snapshot, rooms, analysis, IFC preview,
and DOMAIN preview route methods, request/response formats, file behavior, and
AutoCAD clients remain unchanged.

## Explicit non-scope

PROJECT-2B does not implement:

- project creation, storage, update, migration, or revision persistence;
- reading a project from a request-supplied path;
- changing `rooms.json`, DWG, BAK, IFC, MRD, exports, or AutoCAD objects;
- DOMAIN conversion or IFC conversion;
- coordinate or identity inference;
- readiness or human-confirmation mutation;
- engineering calculations;
- routing or system generation;
- Budget, Comfort, or Premium engineering results;
- sheet generation, layout, or branded document output;
- AutoCAD, MagiCAD, NETLOAD, or DLL operations.
