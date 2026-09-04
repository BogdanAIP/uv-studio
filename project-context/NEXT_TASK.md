# Next Task

<!-- uv-next-slice: recipe-entrypoint-retirement -->

## Target

Execute the bounded D-070 `recipe-entrypoint-retirement` slice from lifecycle-closed `main` `1068694fac69eb02ff6e0651855c875c532e31a7`.

## Required scope

- exact-scan `frontend/lib/recipesApi.ts`, `frontend/lib/projectsApi.ts#createUVProject`, and all repository references to their recipe-backed clients;
- prove the supported New Project UI continues to use Production Direction discovery plus `createStudioProject()` / `POST /api/uv/projects/studio`;
- retire `/api/uv/recipes` and recipe-backed public project creation/recipe-switch metadata entrypoints only when caller evidence shows they are no longer required;
- preserve Project list/get/archive/import and non-recipe project metadata updates;
- preserve schema-v1/v2 read/import/export and exact historical `compatibility.recipe_id` behavior from PR #89;
- retain internal Recipe Registry definitions required by `/execution-plan` and later Product-Orchestrator compatibility until their accepted later slices;
- replace compatibility tests with explicit retirement/absence proof rather than deleting evidence without replacement.

## Completion evidence

- repository-recursive regression proof prevents supported frontend/runtime callers from reintroducing the retired recipe creation/catalog entrypoints;
- API tests prove retired routes reject/404 while modern Studio creation succeeds;
- legacy schema-v1/v2 project read/import/archive behavior remains green;
- frontend lint/build and browser Projects/New Project outcome remain green;
- all five permanent CI checks pass on the exact review head;
- because this changes mounted runtime/API authority, a fresh ordinary-ChatGPT semantic review is required before merge.

## Out of scope

Do not mix `/execution-plan` retirement, broad legacy `/projects/{id}` workflow migration, Product Orchestrator retirement, Stage8 runtime dependency migration/compatibility retirement, Production Direction redesign, Agent autonomy or Timeline identity work into this slice.

## After this slice

After merge and D-038 lifecycle closure, continue the accepted D-070 order with `execution-plan-retirement`.
