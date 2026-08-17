# D-054 — Secret-safe product diagnostics and recovery health

- **Status:** Proposed
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

Stage 9 already has strict release integrity (D-044), a packaged mutable-data boundary (D-045), manifest-owned media tools (D-047), a frozen desktop launcher (D-049), versioned installation (D-050), migration recovery snapshots (D-051) and installer update/rollback (D-053).

Support and end users still need one product-owned self-check that answers whether the installed application is intact, its required media tools are present, mutable storage is usable, and migration recovery metadata is healthy. That check must not become an environment dump or expose provider credentials, local absolute paths, or recovery file locations.

## Proposed decision

The existing `/api/uv/diagnostics` contract becomes diagnostics schema v2.

It keeps release/runtime/media checks and adds two product-owned sections:

- `storage`: health of user-data, canonical Project Store and machine-configuration storage;
- `recovery`: validation summary for D-051 migration recovery snapshots.

### Side-effect boundary

A normal diagnostics GET remains non-mutating. Storage writeability is tested only when the caller explicitly supplies `probe_storage=true`.

The opt-in storage probe:

1. resolves each mutable root through the same D-045 configuration functions used by the product;
2. creates the directory if needed;
3. rejects symlink/non-directory targets;
4. writes and fsyncs a random hidden marker with exclusive creation;
5. immediately deletes the marker;
6. reports only `writable` and filesystem `free_bytes`.

No absolute storage path is returned.

### Recovery health

When the storage probe is requested, diagnostics inspects `%user-data%/recovery/migrations` through D-051 validation rules.

The public result contains only aggregate health metadata:

- finalized snapshot count;
- valid and invalid snapshot counts;
- incomplete hidden `.staging` count;
- latest valid snapshot creation timestamp.

Diagnostics never returns recovery directory names, project identifiers, canonical project paths, snapshot paths, or recovered file content.

Invalid snapshots and incomplete staging sets produce warnings; diagnostics does not delete, rewrite, restore or otherwise repair them.

### Status semantics

- A broken packaged release remains `invalid_release` even if mutable storage is healthy.
- A structurally valid release/development runtime with storage/recovery issues becomes `degraded`.
- Diagnostics issues are stable code/severity/message records suitable for UI rendering and support logs.
- Provider secrets, authorization headers, environment dumps and absolute tool paths remain outside the contract.

## Required evidence before acceptance

1. unit tests prove the default diagnostics call performs no storage probe;
2. a successful opt-in probe proves all three mutable roots writable and leaves no marker behind;
3. returned JSON does not contain the temporary/private test paths;
4. a valid recovery snapshot is counted without exposing its identifier/path;
5. corrupt snapshots and incomplete `.staging` sets are surfaced as warnings without mutation;
6. D-044 same-size tamper behavior and packaged diagnostics remain unchanged;
7. ordinary Linux/Windows CI and the shipping Python runtime suite remain green.

## Follow-up UX

After this backend contract is accepted, Stage 9 will expose it in a product-facing diagnostics/recovery view. Explicit restore remains a separate fail-closed transaction; the diagnostics endpoint itself is read-only apart from the opt-in temporary writeability probe.
