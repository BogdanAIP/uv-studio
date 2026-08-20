# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-orchestrator-foundation -->

**Updated:** 2026-08-20

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-orchestrator-foundation` is the active draft slice in PR #43 on branch `fix/product-recovery-orchestrator-foundation`, created from exact green idle `main@0d148afb7d47b52196197559328897d85ea7c8eb` after Product Truth Inventory PR #42 merged and its lifecycle was closed. Review repairs align readiness with the executor's strict selection policy, retain current settings without restoring legacy navigation, and verify image bytes through the existing Project Source Media Store. The remaining bounded repair makes fresh verified uploads recover a project without requiring a new source-deletion API.

This slice adds a read projection and one semantic action for `photo_to_video`, makes the project UI consume readiness/prerequisites/relevant-workspace truth, and removes the legacy pipeline/session/task/sandbox model from normal AppShell navigation without remounting its backend.

Stage 9 PR #38 was closed **without merge** and retained as an archived engineering reference. Its branch contains substantial Windows packaging/native-shell work, but the installed application failed human product review and must not become the maintained baseline before D-062 Product Truth Recovery passes.

The first recovery PR attempt (#41) used a non-conforming branch prefix and is superseded by PR #42 on the `fix/` branch; no product behavior depends on that administrative attempt.

## Why recovery started from main

The product-truth defects predate Stage 9 packaging. The Stage 8 `main` baseline contains two coupled contradictions.

### Backend execution truth

- `uv_studio/server.py` deliberately mounts the UV-owned API boundary and does not mount historical `/api/pipelines/*` routes;
- `uv_studio/recipes/execution.py` nevertheless marked `narrated_video` and `action_transfer` as `AVAILABLE` and pointed them at `/api/pipelines/standard/tasks` and `/api/pipelines/action_transfer/tasks`;
- unit and API tests explicitly encoded those stale paths/readiness values as expected behavior.

The recovery branch now fails both recipes closed while preserving typed inputs, capability requirements and production policy, and adds an API-boundary regression guard against advertising unmounted base execution targets.

### Frontend architecture split

The live Stage 8 `frontend/` contains both the newer UV Project Store/product UI and a still-compiled VideoClaw workflow UI.

Confirmed live files include:

- `frontend/lib/workflowApi.ts`;
- `frontend/components/HomePage.tsx`;
- `frontend/components/WorkflowPanel.tsx`;
- `frontend/components/pipelines/PipelinePage.tsx`;
- `/pipelines/standard`, `/pipelines/action-transfer`, `/pipelines/digital-human` pages.

The root `AppShell` itself imports `workflowApi`, polls old session/pipeline/sandbox task APIs and places `/sandbox` plus all three pipeline pages in the main sidebar. `frontend/app/layout.tsx` wraps all routes in that AppShell. The old pipeline pages call backend endpoints that Stage 3.5 intentionally stopped mounting.

Therefore the product is not merely “new UV UI plus harmless vendor residue”. Two frontend eras coexist in the live build, with different state models, backend contracts, branding and visual styles. This is a major source of the observed confusing/dead UI.

## Product Truth Inventory

`docs/architecture/PRODUCT_TRUTH_MATRIX.md` is the working audit source. Current classification:

- `photo_to_video` — first Product Orchestrator reference flow: truthful readiness/prerequisites, relevant `photo_composition` workspace and semantic `compose_photos` action over the real local capability path;
- `visualizer` — same;
- `performance_lip_sync` — real `working_with_setup` path under the verified optional MuseTalk runtime;
- targeted existing-video edit — mechanically real but UX/orchestration remains too state-machine-heavy;
- dubbing — substantial real workflow with setup/UX orchestration gaps;
- `music_video` — substantial real domain/assembly/review implementation but default authoring is too schema/state-heavy;
- `general_video`, `story_video`, `commercial_product`, `digital_human`, `free_project` — partial at product-journey level;
- `narrated_video` and `action_transfer` — baseline metadata was misleading because advertised targets were not mounted; recovery now reports them unavailable until current UV-owned workflows exist;
- live `/pipelines/*`, old session/task/model/upload/sandbox surfaces — compiled/routable migration debt against disabled backend contracts; the normal shell no longer links, polls or brands itself through that model.

## Product surface findings

- the D-062 baseline globally mounted targeted edit, sequence continuity and three dubbing panels for every recipe; the first orchestrated Photo-to-Video flow now mounts only its relevant composition workspace;
- recipe cards do not express readiness before project creation;
- the looping `Производственный интерфейс` CTA has been removed from the projects page;
- the normal AppShell is now UV-owned and exposes Project Store projects plus the current provider/runtime settings route, with no legacy VideoClaw pipeline/sandbox navigation or session/task polling;
- the settings route no longer mounts its historical Video-Claw header; its older mixed-language field copy remains explicit frontend migration debt rather than a second shell/runtime contract;
- legacy pipeline pages remain compiled migration debt and are deliberately not remounted or advertised;
- informed browser E2E proves known paths, not cold-start discoverability.

## Architecture direction

D-062 Product Truth Recovery Gate is accepted. Recovery preserves:

- Project Store, archives and portable domain state;
- D-017 execution authorization and provider-neutral Capability Registry;
- deterministic FFmpeg media operations, provenance and cancellation;
- proven edit/dubbing/music state;
- MLT where it provides real value;
- archived Stage 9 installer/runtime/native-shell engineering.

The missing product layer is a Product Orchestrator that projects readiness, structured prerequisites, relevant workspaces and next semantic actions from canonical state plus runtime availability.

The frontend migration has **two parallel responsibilities**:

1. stop React from independently reconstructing every new UV domain state machine;
2. isolate/retire the live VideoClaw shell/pipeline/session/task/model surfaces whose backend contracts no longer exist.

Stage 3.5 is not rolled back to make old UI function.

D-033 reuse-first remains binding. OpenCut/MLT/UV editor ownership must be explicitly re-evaluated before further generic NLE growth.

## Current slice deliverables

1. add `ProjectWorkflowState` as a read-only projection over Project Store, recipes and runtime capability availability;
2. expose explicit readiness, structured prerequisites, relevant workspaces and stable semantic next actions;
3. route `compose_photos` through the existing `video.compose_photos` capability execution/authorization boundary;
4. make the Photo-to-Video page render the projected action and only its relevant composition workspace;
5. remove legacy `/pipelines/*`, sandbox/session/task polling and Video-Claw branding from the normal AppShell;
6. prove blocked and executable Photo-to-Video states through unit, API, build and browser evidence without a second workflow store.

## Current implementation evidence

- `ProjectWorkflowState` schema v1 projects Project Store, Recipe Registry and Capability Registry state without persisting orchestration data;
- `GET /api/uv/projects/{project_id}/workflow` fails non-migrated recipes closed and reports unknown recovered recipes without losing project data;
- `POST /api/uv/projects/{project_id}/workflow/actions/compose_photos` validates bounded semantic inputs and delegates to the existing D-017 capability execution function and local FFmpeg offer;
- readiness and action execution now share strict `local_free_first` eligibility, so remote or non-free offers cannot enable the local action;
- the image prerequisite verifies registered images through the existing Project Source Media Store and suggests only verified IDs; damaged references are excluded, while a fresh upload can recover a project whose old bytes are all missing or hash-mismatched;
- 371 domain/unit tests pass (`2` optional skips) and 186 API tests pass;
- the frontend production build and TypeScript pass; ESLint reports zero errors (pre-existing legacy-source warnings remain);
- the real Stage 8 browser outcome passes through `/workflow/actions/compose_photos`, produces a `photo_to_video_render` artifact, and asserts absence of legacy navigation and unrelated Photo-to-Video workspaces;
- rendered 1600×1000 and 390×844 checks show no horizontal overflow, visible keyboard focus, an above-the-fold mobile Photo-to-Video workspace, and a reachable UV-shell settings page without Video-Claw branding; visual QA caused the task workspace to move ahead of secondary project statistics.

## Verification direction

Focused projection/API tests must prove the same prerequisite/action semantics as the frontend. The existing real Photo-to-Video browser outcome must execute through the semantic workflow action, and all permanent cross-platform checks remain required on the final review head.

## Release status

Release/signing work is paused as a priority. D-059 trusted signing remains necessary for eventual public distribution, but it is downstream of product truth.

A future Stage 9 candidate must pass both the preserved release/security/integrity gates and the Product Truth Gate, including cold-start UI-only evidence and a successful installed Windows human review.

## Next handoff

After this foundation slice is reviewed, merged and context returns to green `idle`, continue with `product-recovery-editor-ownership-resolution` as defined in `project-context/NEXT_TASK.md`. That follow-up may change the D-033 ownership map, so it is an ADR decision slice rather than an implicit implementation extension.
