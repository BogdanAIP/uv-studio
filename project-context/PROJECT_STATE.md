# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice in draft PR #85 on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Implemented security boundary

All maintained first-party `actions/*` references in the three repository workflows are pinned to exact full commit SHAs. The selected SHAs are the revisions currently resolved by the previously used major tags, so the hardening does not intentionally upgrade Action behavior.

Read-only `ci.yml` and `editor-foundation-spike.yml` keep `permissions: contents: read` and every checkout step explicitly sets `persist-credentials: false`.

`vendor-videoclaw.yml` remains the only approved `contents: write` workflow because it contains the actual authenticated Git commit/push path. Its checkout explicitly keeps `persist-credentials: true`, making the write exception visible and reviewable rather than relying on the checkout default.

`tests/test_actions_workflow_security.py` scans every maintained workflow and fails if a first-party Action is not pinned to a 40-character commit SHA, if `contents: write` appears outside the approved vendoring writer, or if checkout credential persistence differs from the read-only/writer policy.

## Verification state

Preliminary exact-head CI is required before freezing the review identity. The final frozen BASE/HEAD must then receive the mandatory fresh ordinary-ChatGPT semantic review because this slice changes repository CI/security/acceptance mechanics. Any material fix after that review invalidates it and requires a fresh review.

## Native Ready connector state

The official connector currently exposes `mark_pull_request_ready_for_review` but its live invocation failed because the connector queries nonexistent GraphQL field `Repository.fullDatabaseId`. This external connector defect does not authorize a new privileged repository fallback in this slice.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
