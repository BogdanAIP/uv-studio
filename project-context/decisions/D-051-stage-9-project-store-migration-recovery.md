# D-051 — Fail-closed Project Store migration preparation and recovery

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

A desktop release can outlive the Project Store schema that created a user's projects. Future schema upgrades therefore need a product-owned migration boundary that cannot partially rewrite canonical state, cannot silently accept newer unsupported projects, and does not make application updates depend on enough free disk space to duplicate every source/video asset.

UV Studio already owns two useful primitives:

- `migrate_project_data()` defines the versioned `project.json` migration boundary;
- `.uvproj.zip` is the complete portable project backup/import format and is fully validated on import.

Those solve different problems. A schema migration only rewrites canonical project metadata; automatically creating a full archive of a very large project before changing a few kilobytes of JSON would duplicate media unnecessarily and can make an otherwise safe update fail on constrained disks.

## Decision

Stage 9 separates **automatic migration recovery** from **explicit full-project backup/recovery**.

### Automatic migration recovery

Before the packaged desktop launcher starts backend or frontend child processes, it prepares the canonical Project Store for the current schema.

The preparation algorithm is fail-closed:

1. enumerate every canonical project and read the exact original `project.json` bytes;
2. compute every required migration in memory;
3. validate every migrated `ProjectDocument`, project identity, and target schema **before the first canonical write**;
4. if no project changes, create no recovery data and perform no writes;
5. if changes are required, atomically publish a small migration-recovery snapshot containing the exact original `project.json` bytes for every changed project plus a strict manifest with file size and SHA-256;
6. only after that snapshot verifies, atomically replace migrated `project.json` files;
7. reload/validate the migrated projects;
8. if any write or post-write validation fails, restore the exact original bytes for every attempted project in reverse order and retain the verified recovery snapshot for explicit recovery.

The recovery snapshot has an exact file inventory. Symlinks, special entries, undeclared files, path drift, size drift and SHA-256 drift are rejected. A same-size metadata substitution therefore fails verification.

A project with a schema newer than the running application fails during preflight. UV Studio does not downgrade it or start against an unknown schema.

### Why metadata-only automatic snapshots

Schema migration is allowed to mutate `project.json`; it is not allowed to rewrite source media, assets, artifacts or exports as an incidental schema side effect. Therefore exact original metadata is sufficient for automatic rollback and remains cheap even for very large projects.

If a future migration truly needs to transform binary/project-tree contents, that migration must introduce an explicit migration-specific strategy and evidence rather than silently expanding this metadata contract.

### Full project backup/recovery

User-requested complete backups continue to use the existing `.uvproj.zip` format. That format inventories the complete canonical project, records file sizes and SHA-256, stages imports, validates identity/schema and only then atomically commits a project into the Project Store.

The recovery UI added later in Stage 9 may expose both:

- full `.uvproj.zip` project backups/restores;
- migration metadata snapshots for exceptional schema-recovery cases.

Neither path may automatically overwrite a currently trusted canonical project without an explicit recovery action.

## Launcher boundary

Migration preparation belongs in the packaged desktop launcher before child processes start. At that point there is no UV Studio backend/UI process concurrently mutating the Project Store, so the product can hold the Store's in-process lock through preflight/snapshot/write/rollback without introducing a second coordination service.

The launcher uses the same packaged mutable-data boundary as D-045. Default migration snapshots live beneath `%LOCALAPPDATA%/UV Studio/recovery/migrations`; an explicit Project Store override remains supported, but the recovery root may not overlap the canonical Project Store or immutable release payload.

A migration/preflight error aborts desktop startup with an actionable launcher error rather than starting an application against partially prepared state.

## Update/rollback relationship

D-050 versioned immutable releases and D-051 Project Store migration are separate trust boundaries:

- installing a new application payload never mutates Project Store data;
- D-044 deep-verifies a newly installed immutable release before activation;
- first launch of that verified release performs D-051 Project Store preparation before services start;
- a failed migration leaves the prior metadata restored and a recovery snapshot retained.

Version activation/rollback policy is handled separately from schema recovery; rolling application binaries backward must never implicitly reverse or overwrite user data.

## Verification requirements

Unit/regression coverage must prove:

- current-schema projects create no unnecessary snapshot;
- required migration publishes exact original metadata before canonical writes;
- same-size snapshot tampering fails SHA-256 verification;
- all projects preflight before any snapshot/write;
- failure on a later project rolls earlier writes back to exact original bytes;
- the verified recovery snapshot remains after rollback;
- newer unsupported schema fails before snapshot/write;
- packaged launcher invokes preparation before backend/frontend child processes.

The current project schema is v1 and has no production migration function yet. Migration write/rollback tests therefore use a deterministic simulated migration while exercising the real coordinator, atomic I/O and recovery verification code paths.
