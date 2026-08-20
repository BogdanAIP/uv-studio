# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: product-recovery-truth-inventory -->

**Updated:** 2026-08-20

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-truth-inventory` is the active review recovery slice on branch `fix/product-recovery-truth-inventory`, created from clean idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8. The fail-closed review removed stale public `VIDEOCLAW_PIPELINE_BINDINGS` values and aligned recipe documentation so no current public recipe contract advertises the removed legacy routes. Implementation and durable context are frozen for exact-head review in PR #42.

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

- `photo_to_video` — real local intent-to-result capability path, though the page is polluted by unrelated global panels/shell UI;
- `visualizer` — same;
- `performance_lip_sync` — real `working_with_setup` path under the verified optional MuseTalk runtime;
- targeted existing-video edit — mechanically real but UX/orchestration remains too state-machine-heavy;
- dubbing — substantial real workflow with setup/UX orchestration gaps;
- `music_video` — substantial real domain/assembly/review implementation but default authoring is too schema/state-heavy;
- `general_video`, `story_video`, `commercial_product`, `digital_human`, `free_project` — partial at product-journey level;
- `narrated_video` and `action_transfer` — baseline metadata was misleading because advertised targets were not mounted; recovery now reports them unavailable until current UV-owned workflows exist;
- live `/pipelines/*`, old session/task/model/upload/sandbox surfaces — compiled/routable legacy frontend against disabled backend contracts and must be isolated/retired rather than used as release functionality.

## Product surface findings

- recipe selection promises that only relevant stages will load, but the project page globally mounts targeted edit, sequence continuity and three dubbing panels for every recipe;
- recipe cards do not express readiness before project creation;
- `Производственный интерфейс` points to `/`, while `/` redirects to `/projects` in the current route entry;
- the same AppShell simultaneously exposes legacy VideoClaw pipeline navigation;
- legacy pipeline pages carry separate Video-Claw branding/light controls and call unmounted APIs;
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

1. maintain Product Truth, surface, interaction and evidence maps;
2. fail closed stale `narrated_video` and `action_transfer` base compatibility targets;
3. add an API-boundary contract test for advertised executable targets;
4. classify live legacy VideoClaw frontend/API surfaces;
5. define the minimum Product Orchestrator contract and next handoff;
6. keep code changes bounded: no broad frontend rewrite in the inventory PR.

## Verification direction

Existing unit/API/real-media/informed browser tests remain valuable. D-062 adds a later cold-start product-evidence class that cannot seed workflow state through hidden APIs when discoverability/setup is what is being tested.

PR #42 must pass all ordinary permanent checks on its final exact review head before merge.

## Release status

Release/signing work is paused as a priority. D-059 trusted signing remains necessary for eventual public distribution, but it is downstream of product truth.

A future Stage 9 candidate must pass both the preserved release/security/integrity gates and the Product Truth Gate, including cold-start UI-only evidence and a successful installed Windows human review.

## Next handoff

After this inventory/contract-repair slice is reviewed, merged and context is returned to green `idle`, continue with `product-recovery-orchestrator-foundation` as defined in `project-context/NEXT_TASK.md`.
