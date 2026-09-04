# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: recipe-entrypoint-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The lifecycle-closed `main` is `1068694fac69eb02ff6e0651855c875c532e31a7` after PR #89 (`project-identity-v2-compat-reader`) and its D-038 closure PR #90. The repository is now in the bounded `recipe-entrypoint-retirement` draft slice on `chore/recipe-entrypoint-retirement`, tracked by Draft PR #91 from that exact `main`.

## Accepted baseline

Canonical Project persistence is schema v2 with exact historical recipe identity under `compatibility.recipe_id`; schema-v1 projects/archives remain readable without read-time rewrite, unknown historical recipe IDs remain exact, and modern Studio identity is typed through `extensions.studio` / Production Direction metadata.

The current Projects UI already discovers Production Directions with `listProductionDirections()` and creates new projects only through `createStudioProject()` -> `POST /api/uv/projects/studio`. The retained `frontend/lib/recipesApi.ts`, `frontend/lib/projectsApi.ts#createUVProject`, `/api/uv/recipes`, and legacy recipe-backed create/update entrypoints are therefore migration surfaces, not canonical modern creation authority.

The internal Recipe Registry itself is not retired by this slice because `/execution-plan` and later Product-Orchestrator compatibility still depend on recipe definitions. Old/imported projects must remain readable/importable through the explicit compatibility boundary established by PR #89.

## Active slice

`recipe-entrypoint-retirement` follows item 3 of the accepted D-070 retirement sequence. It will exact-scan repository callers, migrate any genuine supported caller if one exists, remove recipe-backed frontend/API creation and catalog entrypoints only after proof, and add regression evidence that modern Production Direction creation plus legacy read/import remain intact.

This slice does **not** retire `/execution-plan`, Product Orchestrator, the legacy `/projects/{id}` workflow, Stage8 runtime/state, or the Recipe Registry definitions still needed by those later slices.

## Verification state

Fresh bootstrap resolved exact `main=1068694fac69eb02ff6e0651855c875c532e31a7`, re-read `AGENTS.md`, lifecycle/context, D-064, D-067, D-070, current architecture, the active legacy-surface inventory, architecture principles, roadmap/upstream, recent `main` commits, and enumerated the current `.agents/skills` set. The only repository skill is `code-review` v1.0; its trigger applies later at the independent-review phase, not to implementation planning.

Draft PR #91 is now the canonical active PR. Before product implementation, its synchronized exact head must pass the repository `development-context` validator.

## Handoff

Complete this bounded retirement with exact caller proof, focused tests, permanent CI and fresh semantic review because the final runtime/API deletion is review-significant. After merge and lifecycle closure, the accepted next D-070 slice is `execution-plan-retirement`.
