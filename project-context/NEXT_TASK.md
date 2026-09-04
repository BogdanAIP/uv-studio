# Next Task

<!-- uv-next-slice: recipe-entrypoint-retirement -->

## Target

Finish the bounded D-070 `recipe-entrypoint-retirement` acceptance cycle in Draft PR #91 from lifecycle-closed base `1068694fac69eb02ff6e0651855c875c532e31a7`.

## Current implementation result

The candidate implementation now retires the public recipe creation/catalog/rebinding surfaces:

- `/api/uv/recipes` is not mounted;
- recipe-backed public `POST /api/uv/projects` is retired;
- generic project PATCH cannot change `recipe_id`;
- `frontend/lib/recipesApi.ts` is removed;
- `projectsApi#createUVProject` / `CreateProjectInput` are removed.

Modern New Project creation remains Production Direction discovery plus `POST /api/uv/projects/studio`. Project list/get/archive/import, schema-v1/v2 compatibility, `/execution-plan`, Product Orchestrator, Stage8 and internal Recipe Registry compatibility remain intentionally present for later slices.

API/real-media/browser fixtures that need historical recipe identity now seed canonical ProjectStore compatibility state directly instead of calling the retired public create route. Browser catalog reconciliation uses Production Directions instead of `/api/uv/recipes`.

## Immediate gate

Run/observe a fresh exact-head permanent CI after the synchronized code/tests/docs/context changes. Require all five jobs:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

The app-baseline jobs must pass API integration, Stage4A real-media, frontend lint/audit/build and browser Product Truth. Do not classify a browser failure as the historical Windows timing race without exact log evidence.

## Review transition

Only after the synchronized Draft head is fully green:

1. make a context-only refreeze commit that changes lifecycle `draft -> review` without altering runtime/tests/product behavior;
2. mark PR #91 Ready for review;
3. reconstruct exact BASE/HEAD and governing immutable-BASE review authority;
4. obtain a genuinely fresh ordinary-ChatGPT semantic review using `.agents/skills/code-review/SKILL.md` v1.0;
5. address any actionable finding by returning the PR to Draft before material changes.

## Completion evidence

- public recipe creation/catalog/rebinding entrypoints remain absent;
- Production Direction -> Studio Project remains the modern creation authority;
- old/imported projects remain readable/importable with exact compatibility identity;
- test fixtures do not resurrect retired public entrypoints;
- all five permanent CI jobs pass on the exact review head;
- fresh semantic review returns PASS with no actionable findings;
- final exact reviewed HEAD receives permanent CI before merge.

## Out of scope

Do not mix `/execution-plan` retirement, broad legacy `/projects/{id}` migration, Product Orchestrator retirement, Stage8 runtime/compatibility retirement, Production Direction redesign, Agent autonomy or Timeline identity work into PR #91.

## After this slice

After PR #91 merges, perform mandatory D-038 lifecycle closure to `idle`. Only after that closure merges may the accepted D-070 sequence continue with `execution-plan-retirement`.
