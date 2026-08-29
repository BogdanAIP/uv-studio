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

## Known adjacent implementation risk

A timing-sensitive `ProductionWorkspacePanel` remount race remains open: production semantics can remount after history refresh and discard Shot input entered before refresh completion. This is separate from donor UI retirement and remains a later implementation defect/risk.

## Handoff

`github-ready-review-fallback` remains only a provisional post-merge capability decision point. Before starting any new process slice, the lifecycle closure must re-resolve the live official GitHub `mark_pull_request_ready_for_review` capability.

If the native mutation is available and works, no fallback workflow is created. The repository can then advance to the next explicitly selected bounded slice without adding privileged Ready-for-review automation.
