# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: donor-ui-retirement -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`donor-ui-retirement` is the active draft slice on `chore/donor-ui-retirement`, based on idle `main` at `1775e0391485fec829577cb1a8816226f7baebba`.

The slice is bounded by the accepted D-070 legacy-surface inventory. It removes donor restoration authority and donor-only UI/client residue, but it does not retire live compatibility routes, Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 workspace/API/panels or useful domain state.

## Accepted review policy

Repository-local independent semantic review is mandatory for this review-significant slice.

After implementation and focused verification, the PR must freeze exact `BASE_SHA..HEAD_SHA` and receive a separate fresh ordinary-ChatGPT review using `.agents/skills/code-review/SKILL.md`. Codex Review remains optional additional evidence only.

Any material post-review change invalidates the prior semantic review. Exact-head permanent CI/browser gates and zero unresolved GitHub review threads remain mandatory before merge.

## Active architecture-compression work

The accepted caller/migration inventory is `docs/architecture/LEGACY_SURFACE_INVENTORY.md`.

This slice will:

1. remove every supported write-capable donor frontend restoration path while retaining read-only provenance verification;
2. move `/settings -> modelRegistry.ts -> fetchApiModels` off the broad donor `workflowApi.ts` client without changing the `/api/models` contract;
3. delete the donor-only Workflow/Pipeline/Sandbox/stages component residue and then the broad client remainder only after repository-level caller guards, TypeScript build and browser evidence prove no supported caller remains.

The pinned VideoClaw frontend snapshot under `vendor/videoclaw-app/frontend` remains provenance/comparison material, not a supported source for restoring top-level `frontend/`.

## Preserved boundaries

Modern supported routes remain `/projects`, `/projects/[projectId]/studio` and `/settings`.

The legacy `/projects/[projectId]` route remains a live compatibility surface and is not deleted in this slice. The known timing-sensitive `ProductionWorkspacePanel` remount race also remains a separate defect/risk rather than being mixed into donor UI retirement.

Canonical Project Store, Production Direction, shared Production Semantic Core, Studio/Application Commands, Timeline, Model/Generation and Capability/D-017 authorities are unchanged by this slice.

## Verification target

Required proof includes:

- no supported workflow/script/tool can repopulate top-level `frontend/` from the pinned donor snapshot;
- retained frontend provenance verification is read-only;
- `/settings` model listing preserves its current `/api/models` query contract through a focused modern client;
- the accepted donor-only component/client paths are absent and repository-level caller guards find no surviving `workflowApi` caller;
- frontend lint/build pass;
- permanent Ubuntu/Windows CI and browser user-outcome gates pass on the final reviewed head.

## Handoff

The next slice after this one is `project-identity-v2-compat-reader`.
