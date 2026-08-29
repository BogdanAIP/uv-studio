# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: donor-ui-retirement -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`donor-ui-retirement` is the active review slice on `chore/donor-ui-retirement`, based on `main` at `1775e0391485fec829577cb1a8816226f7baebba`. PR #82 is non-draft and the implementation is frozen for exact-head review/verification.

The slice is bounded by the accepted D-070 legacy-surface inventory. It removes donor restoration authority and donor-only UI/client residue, but it does not retire live compatibility routes, Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 workspace/API/panels or useful domain state.

## Implemented architecture-compression work

The accepted caller/migration inventory is `docs/architecture/LEGACY_SURFACE_INVENTORY.md`.

This slice now:

1. removes the supported write-capable donor frontend promotion/restoration workflow and tool while retaining read-only provenance verification;
2. verifies the pinned donor source from canonical Git blobs and fails closed on tracked, staged or untracked donor-tree changes across Linux and Windows checkouts;
3. moves `/settings -> modelRegistry.ts -> fetchApiModels` off the broad donor `workflowApi.ts` client without changing the `/api/models` query contract;
4. removes the donor-only Workflow/Pipeline/Sandbox/stages component residue and the now-unused broad client after repository-level caller guards prove no supported caller remains;
5. updates development bootstrap/documentation so damaged tracked frontend source is restored from the current Git checkout rather than copied from the pinned donor snapshot.

The pinned VideoClaw frontend snapshot under `vendor/videoclaw-app/frontend` remains provenance/comparison material, not a supported source for restoring top-level `frontend/`.

## Preserved boundaries

Modern supported routes remain `/projects`, `/projects/[projectId]/studio` and `/settings`.

The legacy `/projects/[projectId]` route remains a live compatibility surface and is not deleted in this slice. The known timing-sensitive `ProductionWorkspacePanel` remount race also remains a separate defect/risk rather than being mixed into donor UI retirement.

Canonical Project Store, Production Direction, shared Production Semantic Core, Studio/Application Commands, Timeline, Model/Generation and Capability/D-017 authorities are unchanged by this slice.

## Review and verification

Repository-local independent semantic review is mandatory for this review-significant slice.

The exact review head must receive a separate fresh ordinary-ChatGPT review using `.agents/skills/code-review/SKILL.md`; Codex Review remains optional additional evidence only. Any material post-review change invalidates the prior semantic review.

Focused repository guards and cross-platform bootstrap verification have passed during implementation. The final frozen head must still pass the permanent exact-head checks:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

Zero unresolved GitHub review threads and an exact reviewed `BASE_SHA..HEAD_SHA` remain mandatory before merge.

## Handoff

The next slice is `github-ready-review-fallback`: add a trusted repository-owned label-triggered fallback for Draft -> Ready when the official GitHub connector mutation is unavailable, then resume `project-identity-v2-compat-reader`.
