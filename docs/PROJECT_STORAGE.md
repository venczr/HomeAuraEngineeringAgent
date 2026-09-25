# Canonical project storage

HomeAura stores the current canonical project and immutable revision history
under the selected local project directory:

```text
projects/<project_name>/canonical/current.json
projects/<project_name>/canonical/history/project.r########.json
```

The local loopback API exposes:

- `POST /api/v1/projects/{project_name}/canonical` to create the first
  revision, retry an identical revision idempotently, or advance by exactly
  one revision;
- `GET /api/v1/projects/{project_name}/canonical` to return the exact current
  canonical JSON bytes.

Writes publish immutable history first with create-only semantics and replace
the current file atomically second. An existing history file is accepted only
when its bytes are identical, which makes an interrupted current-file update
safe to retry. If an atomic current-file replace reports an operating-system
error after another writer has already published identical bytes, the write is
treated as converged; different bytes remain an error. Reads require current
and history bytes to match.

The API accepts only loopback requests. Selected project write routes enforce
an actual-body limit of 10 MiB before endpoint parsing. Responses contain a
project ID, revision, digest, or stable error code; they never expose local
filesystem paths, request content, or operating-system exception details.
