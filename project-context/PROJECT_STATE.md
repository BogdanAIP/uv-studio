# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice, frozen for review on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Implemented security boundary

All maintained first-party `actions/*` references in the three repository workflows are pinned to exact full commit SHAs. The selected SHAs are the revisions resolved by the previously used major tags at implementation time, so the hardening does not intentionally upgrade Action behavior.

Read-only `ci.yml` and `editor-foundation-spike.yml` keep `permissions: contents: read` and every checkout step explicitly sets `persist-credentials: false`.

`vendor-videoclaw.yml` remains the only approved `contents: write` workflow because it contains the actual authenticated Git commit/push path. Its checkout explicitly keeps `persist-credentials: true`, making the write exception visible and reviewable rather than relying on the checkout default.

`tests/test_actions_workflow_security.py` scans every maintained workflow and fails if a first-party Action is not pinned to a 40-character commit SHA, if write-all or `contents: write` appears outside the approved vendoring writer, or if checkout credential persistence differs from the read-only/writer policy.

## Verification state

Preliminary hosted CI on an earlier implementation head proved that the exact pinned checkout/setup-python/setup-node revisions execute successfully, both Ubuntu and Windows bootstrap jobs pass the full unit suite, and Ubuntu app-baseline including browser evidence succeeds. The early development-context failure on that stale head was caused by the then-unbound PR number/write-scope and was corrected before review freeze.

The frozen review identity must receive the mandatory fresh ordinary-ChatGPT semantic review because this slice changes repository CI/security/acceptance mechanics. After the review result is current, the final exact head must pass all five permanent checks, including both browser suites/evidence uploads, before merge. Any material post-review fix invalidates the review.

## Native Ready connector state

The official connector exposes `mark_pull_request_ready_for_review`, but an earlier live invocation failed because the connector queried nonexistent GraphQL field `Repository.fullDatabaseId`. This external connector defect does not authorize a privileged repository fallback in this slice.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
