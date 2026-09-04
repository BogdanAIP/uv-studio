# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: recipe-entrypoint-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The lifecycle-closed `main` is `1068694fac69eb02ff6e0651855c875c532e31a7` after PR #89 (`project-identity-v2-compat-reader`) and D-038 closure PR #90. Development is active in bounded Draft PR #91, `recipe-entrypoint-retirement`, on branch `chore/recipe-entrypoint-retirement` from that exact base.

## Accepted baseline

Canonical Project persistence is schema v2 with exact historical recipe identity under `compatibility.recipe_id`; schema-v1 projects/archives remain readable without read-time rewrite, unknown historical recipe IDs remain exact, and modern Studio identity is typed through `extensions.studio` / Production Direction metadata.

Modern New Project authority is already `GET /api/uv/projects/studio/directions` + `POST /api/uv/projects/studio`. The Projects UI uses Production Directions and does not require Recipe Registry-backed public creation.

The internal Recipe Registry is still required by later compatibility slices such as `/execution-plan` and Product Orchestrator. PR #91 therefore retires only public recipe creation/catalog/rebinding entrypoints and their unused frontend clients, while preserving old-project read/import and internal compatibility definitions.

## Active slice implementation

PR #91 currently removes:

- mounted `/api/uv/recipes`;
- recipe-backed public `POST /api/uv/projects`;
- generic project PATCH `recipe_id` rebinding;
- `frontend/lib/recipesApi.ts`;
- `projectsApi#createUVProject` and `CreateProjectInput`.

It preserves project list/get/archive/import, non-recipe metadata updates, modern Studio creation, `/execution-plan`, Product Orchestrator, Stage8 and the internal Recipe Registry for their own later slices.

## Test-fixture reconciliation

Initial exact-head CI exposed two layers of stale test setup rather than product regressions:

1. Stage4A real-media fixtures still created recipe projects through the retired POST route. Three fixture files were migrated to direct canonical `ProjectStore.create_project(...)`. The next CI proved Stage4A SUCCESS on both Ubuntu and Windows with all real-media tests passing.
2. Browser compatibility outcomes still used the same retired POST route and one reconciliation test still read `/api/uv/recipes`. PR #91 now provides `e2e/legacy_project_fixture.py` for explicit test-only ProjectStore seeding of historical compatibility identity; affected browser outcomes use that fixture while all visible user interactions continue through the real frontend/backend. Catalog reconciliation now reads Production Directions.

This fixture pattern does not restore or emulate a public recipe-backed create route. Class-C modern cold-start evidence remains fully user-visible through Production Directions.

## Documentation state

`docs/architecture/LEGACY_SURFACE_INVENTORY.md` is synchronized to accepted PR #89/#90 history and current PR #91 candidate behavior. It no longer describes #89 as pending or the recipe entrypoints as future work.

## Verification state

Fresh bootstrap re-resolved exact `main`, active PR/lifecycle, current architecture and decisions D-064/D-067/D-070. The repository skill set contains `code-review` v1.0, which applies only after the implementation head is frozen for independent review.

On earlier material head `d0841f8bddcd027f4cb401e3302555f44b4026c1`, CI #4772 proved:

- `development-context`: SUCCESS;
- both bootstrap/unit jobs: SUCCESS;
- API integration: SUCCESS on Ubuntu and Windows;
- Stage4A real-media: SUCCESS on Ubuntu and Windows;
- Windows browser failure was deterministically stale E2E setup using retired recipe endpoints, not the previously known timing race.

Those browser fixtures have now been migrated. The current exact head must still complete a fresh full permanent CI before this Draft can move to review.

## Handoff

Keep PR #91 Draft until the synchronized exact head passes all five permanent CI jobs, including browser Product Truth on Ubuntu and Windows. Then refreeze only lifecycle/context, move `draft -> review`, mark the PR Ready, and obtain the repository-required genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0.

After fresh PASS and final exact-reviewed-head permanent CI, merge only the verified HEAD, perform mandatory D-038 closure to `idle`, and only then begin `execution-plan-retirement`.
