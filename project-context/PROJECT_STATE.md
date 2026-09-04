# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: recipe-entrypoint-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`recipe-entrypoint-retirement` merged through PR #91 as `050780d013276c3d3de9672244ad54da759f1ed3` from exact reviewed HEAD `6218437f78d6d8b842cda1d01f8c675147446513`. This D-038 closure returns the repository lifecycle to `idle`; no subsequent product-development slice has started from that merge.

The accepted next handoff is `execution-plan-retirement`. It may start only after this closure merges to protected `main` and the mandatory fresh bootstrap is rerun from the resulting lifecycle-closed main.

## Accepted recipe-entrypoint retirement

PR #91 retired obsolete public recipe-backed composition entrypoints:

- `/api/uv/recipes` is no longer mounted;
- recipe-backed public `POST /api/uv/projects` is retired;
- generic project PATCH can no longer rebind `recipe_id`;
- `frontend/lib/recipesApi.ts` is removed;
- `projectsApi#createUVProject` and `CreateProjectInput` are removed.

Modern New Project authority remains `GET /api/uv/projects/studio/directions` plus `POST /api/uv/projects/studio`. Project list/get/archive/import and non-recipe metadata updates remain supported. Schema-v1/v2 old/imported project compatibility remains explicit, and the internal Recipe Registry is intentionally retained for later compatibility consumers such as `/execution-plan` and Product Orchestrator until their own accepted retirement slices.

API, real-media and browser tests that require historical recipe identity now seed canonical ProjectStore compatibility state directly instead of restoring a retired public create endpoint. User-visible modern creation continues through Production Directions.

## Final review and verification

The required genuinely fresh ordinary-ChatGPT semantic review of exact `1068694fac69eb02ff6e0651855c875c532e31a7..6218437f78d6d8b842cda1d01f8c675147446513` returned `CURRENT / PASS / 0 findings / 6 rejected candidates` under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 at `2026-09-04T16:12:48Z`.

Material implementation head `2344667deada22983e362d468db084ed5cede797` passed CI #4804 with all five permanent jobs. After the review refreeze, final merge-authoritative CI #4810 (`33894022998`) passed all five permanent jobs on exact reviewed HEAD `6218437f78d6d8b842cda1d01f8c675147446513`, including both Ubuntu/Windows unit suites, API integration, Stage4A real-media, frontend lint/audit/build and browser Product Truth.

Intermediate duplicate CI events around Draft/Ready metadata transitions produced `development-context` failures because the event payload's `pull_request.draft` snapshot did not match lifecycle state. No repository content changed for those transitions; the clean Ready event CI #4810 passed the same check and the full permanent suite.

PR #91 was then merged with `expected_head_sha=6218437f78d6d8b842cda1d01f8c675147446513`, producing merge commit `050780d013276c3d3de9672244ad54da759f1ed3`.

## Handoff

The next bounded D-070 slice is `execution-plan-retirement`: replace the legacy `/api/uv/projects/{id}/execution-plan` surface and `projectsApi#getProjectExecutionPlan()` with direct canonical Production/Generation/Capability readiness after exact caller proof.

Do not begin that slice until this D-038 closure merges and `main` is verified lifecycle-idle. The next development invocation must rerun repository skill discovery and the full mandatory bootstrap against that exact new `main`.
