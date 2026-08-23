# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-commercial-product-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Commercial Product recovery is active in **Draft** on `fix/product-recovery-commercial-product-orchestration`, based on idle `main` `98a8f475804aca2d58ee39b313db2973baedb70f` after Story Video PR #54.

The slice is recovering `commercial_product` through Product Orchestrator without creating a product-specific workflow database, reopening editor ownership, or treating recipe policy declarations as evidence that source review, direction, sample, plan or final-review gates have already been completed.

## As-built boundary under recovery

- Stage 8 already owns the Commercial brief, optional script and SHA-bound image/video/audio bindings;
- verified image/video bindings are the current project-owned product references; stale or tampered bytes must fail closed;
- the Commercial recipe declares required source-review, direction, sample-first, plan and final-review policy gates, but there is no audited Commercial-specific approval store proving those gates today;
- this slice therefore recovers a truthful **product preparation state**, not a final advertising production workflow;
- provider-backed generation and `timeline.assemble` remain outside this preparation-only recovery until a concrete end-to-end contract is audited;
- no `render_commercial`, hidden approval seeding, generic NLE authority or parallel advertising workflow store will be introduced.

## Verification status

Implementation and focused tests are in progress. Exact Draft and Review heads must each pass all five permanent Ubuntu/Windows CI checks before merge.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

`product-recovery-recipe-workspace-reconciliation`, as defined by `project-context/NEXT_TASK.md`. This follows the P0 backlog requirement to reconcile remaining recipe/workspace leakage and readiness-blind creation; broader `free_project`, Action Transfer and Digital Human work stays explicitly outside this handoff.
