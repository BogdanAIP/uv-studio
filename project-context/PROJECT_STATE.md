# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: donor-ui-retirement -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is lifecycle-idle after `donor-ui-retirement` merged through PR #82 as `c1eb609ec1e4c9db082eaa8338ac7f1e4938da11`.

PR #82 retired supported donor-frontend restoration authority, removed donor-only Workflow/Pipeline/Sandbox/stages UI/client residue after caller proof, isolated the supported `/api/models` client, and made top-level `frontend/` unequivocally UV Studio-owned product source. The pinned VideoClaw frontend remains read-only provenance/comparison material.

## Verification state

The final PR #82 head `6601028e4c96e5e5591c8b44a315e66eaede58c8` received the required fresh ordinary-ChatGPT semantic review with `status=PASS`, `review_validity=CURRENT` and zero reported findings.

Exact-head CI run #3879 passed all five permanent checks and produced both browser E2E evidence artifacts. A duplicate Windows browser run initially hit two timing-sensitive UI failures on the same exact head; rerunning only that failed Windows job passed the full browser suite without changing repository bytes. All inline review threads were resolved before expected-head merge.

## Accepted architecture baseline

The accepted caller/migration inventory remains `docs/architecture/LEGACY_SURFACE_INVENTORY.md`. The D-070 architecture-compression gate is satisfied; the separate golden-vertical gate remains open.

Modern product work continues to target canonical Project Store, Production Directions, shared Production Semantic Core, Studio/Application Commands, canonical Timeline, Generation/Model Job authority and Capability/D-017 boundaries.

Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 composition and the legacy `/projects/[projectId]` route remain explicit compatibility/migration surfaces until later bounded retirement work proves otherwise.

## GitHub process state

A live post-merge capability check used the official connector's exposed `mark_pull_request_ready_for_review` mutation on draft closure PR #83. The call did not reach a successful mutation because the connector's GraphQL selection queried nonexistent `Repository.fullDatabaseId`.

This is classified as an external connector implementation defect, not evidence that GitHub lacks the Ready mutation. No privileged repository fallback is authorized merely to work around that connector bug. PR #83 was closed unmerged and the exact same closure branch/diff was reopened directly non-draft as PR #84.

## Known adjacent implementation risk

A timing-sensitive `ProductionWorkspacePanel` remount race remains open: production semantics can remount after history refresh and discard Shot input entered before refresh completion. This is separate from donor UI retirement and remains a later implementation defect/risk.

## Handoff

The next bounded slice is `actions-hardening`.

It will pin maintained `actions/*` uses to exact full commit SHAs, disable persisted checkout credentials in read-only workflows, keep write authority only on the genuine vendoring writer, and add a static guard preventing future workflow drift. After that security/process slice is merged and lifecycle-closed, resume `project-identity-v2-compat-reader`.
