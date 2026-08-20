# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-truth-inventory -->

**Updated:** 2026-08-20

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-truth-inventory` is the active draft recovery slice on branch `fix/product-recovery-truth-inventory`, created from clean idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8.

Stage 9 PR #38 was closed **without merge** and retained as an archived engineering reference. Its branch contains substantial Windows packaging/native-shell work, but the installed application failed human product review and must not become the maintained baseline before D-062 Product Truth Recovery passes.

The first recovery PR attempt (#41) used a non-conforming branch prefix and is superseded by the `fix/` branch; no product behavior depends on that administrative attempt.

## Why recovery started from main

The product-truth defects predate Stage 9 packaging. The Stage 8 `main` baseline contained a direct contradiction:

- `uv_studio/server.py` deliberately mounts the UV-owned API boundary and does not mount historical `/api/pipelines/*` routes;
- `uv_studio/recipes/execution.py` nevertheless marked `narrated_video` and `action_transfer` as `AVAILABLE` and pointed them at `/api/pipelines/standard/tasks` and `/api/pipelines/action_transfer/tasks`;
- unit and API tests explicitly encoded those stale paths/readiness values as expected behavior.

This is a backend/product-contract defect, not a styling issue. The recovery branch now fails both recipes closed while preserving typed inputs, capability requirements and production policy, and adds a regression guard against advertising unmounted execution targets.

## Product Truth Inventory

`docs/architecture/PRODUCT_TRUTH_MATRIX.md` is now the working audit source. Initial classification:

- `photo_to_video` — `working`;
- `visualizer` — `working`;
- `performance_lip_sync` — `working_with_setup` under the verified optional MuseTalk runtime;
- targeted existing-video edit — mechanically working but UX/orchestration remains too state-machine-heavy;
- dubbing — substantial real workflow with setup/UX orchestration gaps;
- `music_video` — substantial real domain/assembly/review implementation but default authoring is too schema/state-heavy;
- `general_video`, `story_video`, `commercial_product`, `digital_human`, `free_project` — partial at product-journey level;
- `narrated_video` and `action_transfer` — the baseline metadata was misleading because its advertised legacy launch targets were not mounted; the recovery branch now reports them unavailable until current workflows exist.

## Legacy surface finding

The live UV-owned `frontend/` on `main` does **not** contain the historical `workflowApi.ts`, `HomePage` or `WorkflowPanel` names found during broader historical/vendor inspection. `vendor/videoclaw-app/frontend/lib/workflowApi.ts` still exists inside the pinned donor tree and is not current frontend authority. Therefore the confirmed active stale contract is the recipe execution/readiness layer and its tests; donor route families remain isolated inventory, not evidence that current React imports them.

## Architecture direction

D-062 Product Truth Recovery Gate is accepted. Recovery preserves:

- Project Store, archives and portable domain state;
- D-017 execution authorization and provider-neutral Capability Registry;
- deterministic FFmpeg media operations, provenance and cancellation;
- proven edit/dubbing/music state;
- MLT where it provides real value;
- archived Stage 9 installer/runtime/native-shell engineering.

The missing product layer is a Product Orchestrator that projects readiness, structured prerequisites and next semantic actions from canonical state plus runtime availability. The frontend should render that product truth instead of independently reconstructing internal plan/candidate/review/runtime state machines.

D-033 reuse-first remains binding. OpenCut/MLT/UV editor ownership must be explicitly re-evaluated before further generic NLE growth.

## Current slice deliverables

1. maintain `PRODUCT_TRUTH_MATRIX.md` for visible recipes and permanent scenarios;
2. fail closed stale `narrated_video` and `action_transfer` compatibility targets;
3. add a contract test that any advertised executable target is actually mounted by the current UV-owned FastAPI app;
4. classify historical VideoClaw frontend/API surfaces before deletion;
5. record the minimum Product Orchestrator contract and next handoff.

## Release status

Release/signing work is paused as a priority. D-059 trusted signing remains necessary for eventual public distribution, but it is downstream of product truth.

A future Stage 9 candidate must pass both the preserved release/security/integrity gates and the Product Truth Gate, including cold-start UI-only evidence and a successful installed Windows human review.

## Next handoff

After this inventory/contract-repair slice is reviewed and merged, continue with `product-recovery-orchestrator-foundation` as defined in `project-context/NEXT_TASK.md`.
