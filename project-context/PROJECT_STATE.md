# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: recipe-entrypoint-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The lifecycle-closed `main` is `1068694fac69eb02ff6e0651855c875c532e31a7` after PR #89 (`project-identity-v2-compat-reader`) and D-038 closure PR #90. Bounded PR #91, `recipe-entrypoint-retirement`, is now frozen in review on branch `chore/recipe-entrypoint-retirement` from that exact base.

## Accepted baseline

Canonical Project persistence is schema v2 with exact historical recipe identity under `compatibility.recipe_id`; schema-v1 projects/archives remain readable without read-time rewrite, unknown historical recipe IDs remain exact, and modern Studio identity is typed through `extensions.studio` / Production Direction metadata.

Modern New Project authority is already `GET /api/uv/projects/studio/directions` + `POST /api/uv/projects/studio`. The Projects UI uses Production Directions and does not require Recipe Registry-backed public creation.

The internal Recipe Registry is still required by later compatibility slices such as `/execution-plan` and Product Orchestrator. PR #91 therefore retires only public recipe creation/catalog/rebinding entrypoints and their unused frontend clients, while preserving old-project read/import and internal compatibility definitions.

## Frozen implementation

PR #91 removes:

- mounted `/api/uv/recipes`;
- recipe-backed public `POST /api/uv/projects`;
- generic project PATCH `recipe_id` rebinding;
- `frontend/lib/recipesApi.ts`;
- `projectsApi#createUVProject` and `CreateProjectInput`.

It preserves project list/get/archive/import, non-recipe metadata updates, modern Studio creation, `/execution-plan`, Product Orchestrator, Stage8 and the internal Recipe Registry for their own later slices.

## Test-fixture reconciliation

Initial exact-head CI exposed two layers of stale test setup rather than product regressions:

1. Stage4A real-media fixtures still created recipe projects through the retired POST route. Three fixture files were migrated to direct canonical `ProjectStore.create_project(...)`.
2. Browser compatibility outcomes still used the same retired POST route and one reconciliation test still read `/api/uv/recipes`. PR #91 provides `e2e/legacy_project_fixture.py` for explicit test-only ProjectStore seeding of historical compatibility identity; affected browser outcomes use that fixture while all visible user interactions continue through the real frontend/backend. Catalog reconciliation now reads Production Directions.

The historical cross-workspace fallback test in `e2e/test_user_outcomes.py` remains explicitly excluded by `e2e/run_browser_e2e.py`; accepted Product Truth coverage is provided by the replacement product-owned outcomes. It is not an active acceptance caller of the retired create route.

This fixture pattern does not restore or emulate a public recipe-backed create route. Class-C modern cold-start evidence remains fully user-visible through Production Directions.

## Documentation state

`docs/architecture/LEGACY_SURFACE_INVENTORY.md` is synchronized to accepted PR #89/#90 history and PR #91 candidate behavior. It no longer describes #89 as pending or the recipe entrypoints as future work.

## Verification state

Implementation head `2344667deada22983e362d468db084ed5cede797` passed CI #4804 with all five permanent jobs SUCCESS:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

Both app-baseline jobs passed API integration, Stage4A real-media and browser Product Truth. The review refreeze changes only lifecycle/context and must now be bound to its own exact HEAD for the required fresh ordinary-ChatGPT semantic review. Any material change after review requires returning the PR to Draft and obtaining a fresh review on the new exact head.

## Handoff

PR #91 is frozen for review. Mark it Ready, resolve exact BASE/HEAD, and obtain the repository-required genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0. Require all five permanent CI jobs on the exact final review head and verify the reviewed BASE/HEAD still match before merge.

After fresh PASS and final exact-reviewed-head permanent CI, merge only the verified HEAD, perform mandatory D-038 closure to `idle`, and only then begin `execution-plan-retirement`.
