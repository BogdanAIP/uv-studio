# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice in review on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Implemented security boundary

All maintained first-party `actions/*` references in the three repository workflows are pinned to exact full commit SHAs. The selected SHAs are the revisions resolved by the previously used major tags at implementation time, so the hardening does not intentionally upgrade Action behavior.

Read-only `ci.yml` and `editor-foundation-spike.yml` keep `permissions: contents: read` and every checkout step explicitly sets `persist-credentials: false`.

`vendor-videoclaw.yml` remains the only approved `contents: write` workflow because it contains the actual authenticated Git commit/push path. Its checkout explicitly keeps `persist-credentials: true`, making the write exception visible and reviewable rather than relying on the checkout default.

`tests/test_actions_workflow_security.py` now validates the security policy with a fail-closed structural scanner for the supported GitHub workflow YAML forms. It validates block and flow mappings for `permissions` and checkout `with`, rejects unsupported alias/complex permission syntax rather than guessing, binds `persist-credentials` specifically to the checkout `with` mapping, and still requires every maintained first-party Action to use a full 40-character commit SHA.

## Semantic review history

Fresh ordinary-ChatGPT review of exact `66410db447c896fb898636634258402fae1edbff..d5f7b5fb4f12e191e12111aff7477b201e275da2` returned `FINDINGS` with one P2 and three rejected candidates.

The P2 was **CONFIRMED**: the first version of the permanent workflow-security guard could fail open on valid YAML, including job-level `permissions: {contents: write}`, and could mistake a `persist-credentials: false` decoy outside checkout `with` for the actual checkout input. The reviewer also confirmed that the current maintained workflows themselves were configured safely and that the pinned Action SHAs matched the previous major-tag resolutions.

The guard was materially fixed after review. Regression coverage now proves that job-level flow-style `contents: write` is rejected, a credential decoy outside `with` is rejected, valid flow-style checkout `with` is structurally validated, and permission aliases fail closed. Because this is a material acceptance/security-test change, the prior review is stale and a fresh ordinary-ChatGPT semantic review is required on the new final exact head before merge.

## Verification state

Preliminary hosted CI on an earlier implementation head proved that the exact pinned checkout/setup-python/setup-node revisions execute successfully, both Ubuntu and Windows bootstrap jobs pass the full unit suite, and Ubuntu app-baseline including browser evidence succeeds. The early development-context failure on that stale head was caused by the then-unbound PR number/write-scope and was corrected before review freeze.

After the confirmed P2 fix, the final exact head must pass all five permanent checks, including both browser suites/evidence uploads. The fresh semantic review must bind the same final BASE/HEAD. Any further material change invalidates that review again.

## Native Ready connector state

The official connector exposes `mark_pull_request_ready_for_review`, but repeated live invocation failed because the connector queried nonexistent GraphQL field `Repository.fullDatabaseId`. Draft PR #85 was therefore closed unmerged and the same branch was reopened directly as non-draft PR #86. No privileged repository fallback was introduced.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
