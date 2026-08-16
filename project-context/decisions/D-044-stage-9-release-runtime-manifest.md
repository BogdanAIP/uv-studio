# D-044 — Stage 9 product-owned release runtime manifest

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

UV Studio is now proven as an application through development/test environments, but Stage 9 must turn that application into a native Windows product. The user-facing requirement is stronger than a development setup script: a normal user must not need to prepare Python, Node/npm, FFmpeg or MLT independently before UV Studio can start.

The current product also has two important constraints:

1. the frontend is a Next.js application with an arbitrary dynamic `/projects/[projectId]` route and currently uses Next as the same-origin proxy for `/api/uv/*`;
2. media execution already depends on bounded FFmpeg/FFprobe/MLT behavior and must not silently switch to unknown executables on an installed machine.

An installer by itself does not solve either problem. Without a machine-readable product-owned payload contract, installer scripts, launchers, diagnostics and CI could each make different assumptions about which runtime files are present and trusted.

## Decision

Stage 9 introduces a strict `release-manifest.json` as the canonical identity of one immutable installed UV Studio application payload.

The manifest schema is product-owned and versioned. For schema v1 it contains:

- product name, version and build identity;
- target operating system and architecture;
- the exact required component set: backend, frontend, Node runtime, FFmpeg, FFprobe and MLT;
- a version and canonical relative entrypoint for every component;
- a complete, sorted inventory of payload files with exact byte size and SHA-256.

The manifest itself is excluded from its own file inventory. Installer/uninstaller bookkeeping, user data, logs, backups and mutable machine configuration must live outside the immutable payload root rather than being tolerated as untracked files inside it.

Manifest paths are portable relative paths only. Absolute paths, traversal, backslashes, Windows-unsafe colon segments, duplicate paths/components and component entrypoints that are absent from the inventory are rejected.

The payload boundary is fail-closed:

- symlink files/directories are rejected;
- missing files are rejected;
- unlisted extra files are rejected;
- byte-size mismatches are rejected;
- deep verification additionally rejects SHA-256 mismatches, including same-size substitutions.

A quick structural/inventory check and an explicit deep hash check are both supported. Launcher/startup may use the quick check for responsiveness; installer verification, support diagnostics, update/recovery and release CI can request the deep check.

## Runtime packaging direction

The no-system-toolchain requirement is a **user-facing** contract, not a requirement that the installed product contain only one process. Stage 9 may ship pinned/versioned runtime payloads owned by the release manifest.

In particular, the current dynamic Next routing means Stage 9 will not remove Node from the packaged runtime merely to simplify the file layout. A bundled Node runtime and a production Next server are acceptable if they preserve arbitrary project routes and same-origin API behavior. Node may be removed later only after an equivalent packaged frontend routing path is proven by the permanent browser outcomes.

Likewise, the packaged release must resolve its required FFmpeg/FFprobe/MLT from the trusted release payload rather than depending on whichever executable happens to appear first on the user's system `PATH`.

Optional heavyweight runtimes such as MuseTalk remain outside the baseline release manifest under their own verified optional-pack boundaries. WSL, cloud providers and paid APIs also remain non-blocking for normal native-Windows startup.

## Diagnostics contract

UV Studio exposes one secret-safe diagnostics model usable by HTTP, launcher/support tooling and future installer/recovery flows.

Diagnostics may report product/runtime versions, release mode, manifest validity, component versions/relative entrypoints, integrity failures and required media-tool availability. They must not dump environment variables, provider credentials, authorization headers or arbitrary absolute developer tool paths.

When no release root is configured, diagnostics explicitly report development mode instead of pretending the repository checkout is an installed release.

## Consequences

- Installer implementation must build on a verified release payload, not define product truth independently.
- Future updates can compare explicit manifest/build identities and verify staged payloads before activation.
- Recovery can distinguish corrupted application payload from mutable project/configuration data.
- Release CI gets a deterministic artifact boundary that can be hashed and signed.
- The installed payload layout may be replaced later without changing canonical project state because release/runtime identity remains machine state, not project semantics.
- Stage 9 still needs reproducible dependency locking, actual payload assembly, launcher supervision, user-data migration, installer/update/recovery, signing and clean-machine evidence; this decision provides the invariant those phases must share.
