# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Security target

Maintained first-party GitHub Actions references will be pinned to exact full commit SHAs using the same Action revisions already executed by the current successful CI, avoiding an implicit dependency upgrade while removing floating major-tag resolution.

Read-only workflows will keep explicit `permissions: contents: read` and disable persisted checkout credentials. `vendor-videoclaw.yml` remains the only approved `contents: write` workflow because it contains an authenticated Git commit/push path; its write exemption must remain coupled to that real writer behavior.

A permanent unit guard will reject future floating first-party Action refs, unexpected write authority and persisted checkout credentials in read-only workflows.

## Native Ready connector state

The official connector currently exposes `mark_pull_request_ready_for_review` but its live invocation failed because the connector queries nonexistent GraphQL field `Repository.fullDatabaseId`. This external connector defect does not authorize a new privileged repository fallback in this slice.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
