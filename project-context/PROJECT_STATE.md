# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: donor-ui-retirement -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`donor-ui-retirement` is the active review slice on `chore/donor-ui-retirement`, based on `main` at `1775e0391485fec829577cb1a8816226f7baebba`. PR #82 is non-draft and remains in exact-head review/verification.

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

A fresh ordinary-ChatGPT review of exact head `6c62dfc5ade21d3a8f9e55b85451d9e55ec089f2` returned two P2 findings. The development context independently validated both as **CONFIRMED**:

1. browser E2E output was written under `e2e-artifacts/${runner.os}` while upload searched `${matrix.os}`, so the exact-head CI run stayed green without either intended `browser-e2e-*` artifact;
2. `NEXT_TASK.md` unconditionally instructed implementation of `github-ready-review-fallback` even though current architecture requires a live native-Ready capability check before any such process slice begins.

The browser artifact uploader is corrected to the producer path and now fails when browser evidence is absent. The fallback handoff is now explicitly a provisional post-merge capability decision: lifecycle closure must re-resolve native `mark_pull_request_ready_for_review`; when it is available, no fallback slice is started and the idle handoff advances directly to `project-identity-v2-compat-reader`.

These are material post-review changes, so the review of `6c62dfc5...` is stale by policy. The new exact head must receive another separate fresh ordinary-ChatGPT review using `.agents/skills/code-review/SKILL.md`; Codex Review remains optional additional evidence only.

The final frozen head must also pass the permanent exact-head checks:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

The app-baseline jobs must now produce durable `browser-e2e-ubuntu-latest` and `browser-e2e-windows-latest` artifacts; missing browser evidence is a CI failure rather than a warning.

Zero unresolved GitHub review threads and an exact reviewed `BASE_SHA..HEAD_SHA` remain mandatory before merge.

## Handoff

`github-ready-review-fallback` is a provisional capability-check handoff, not an unconditional implementation slice. During post-merge closure, re-resolve the official GitHub Ready mutation. If native Ready is available, skip the fallback and advance directly to `project-identity-v2-compat-reader`; preserve the fallback as a bounded process slice only if the native capability is genuinely unavailable.
