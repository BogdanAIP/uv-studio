# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-recipe-workspace-reconciliation -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Recipe/workspace reconciliation is active in **Draft** on `fix/product-recovery-recipe-workspace-reconciliation`, based on idle `main` `2c53b50c847986c9a9486ed319d245e3d1944f21` after Commercial Product PR #55.

The slice closes the remaining Product Truth mismatch between the recipe catalog, Product Orchestrator projections and visible project workspaces. A recipe being registered or creatable must not by itself make unrelated editor, continuity or dubbing surfaces appear, and recipe capability declarations must not be treated as current executable readiness.

## Current audit findings

- recovered authoritative journeys already route through Product Orchestrator-owned workspaces;
- `free_project` is already the Targeted Edit recipe and must not be broadened into a second generic editor;
- recipes with no projected workspace currently fall through to a generic `ProjectEditor` plus Sequence Continuity and multiple Dubbing panels;
- `performance_lip_sync` has a direct setup-gated panel but, because it lacks a projected workspace, also inherits those unrelated fallback surfaces;
- unsupported Action Transfer / Digital Human recipes remain advertised in the recipe catalog but do not yet have a complete authoritative Product Orchestrator workflow;
- `ENGINEERING_BACKLOG.md` is stale and still describes Product Truth recovery steps that have already been completed.

## Required boundary

This slice will make unsupported/incomplete recipes fail closed and expose only product-owned surfaces. It will not remount retired pipeline routes, invent provider-backed readiness, broaden `free_project`, or promote Action Transfer / Digital Human beyond their currently audited contracts.

## Verification target

Add focused API and browser regression proof covering recipe creation, readiness and visible workspace routing, then require all five permanent CI jobs on exact Draft and Review heads before merge.

## Handoff after this slice

If reconciliation closes the remaining P0 Product Truth mismatch, the next planned slice is `product-usability-class-c-cold-start` for user-equivalent clean-state evidence before Stage 9. Installed Windows human acceptance remains a separate required gate, and missing `main` branch protection remains an external repository-setting P0.
