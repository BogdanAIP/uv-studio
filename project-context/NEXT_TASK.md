# Next Task

<!-- uv-next-slice: recipe-entrypoint-retirement -->

## Target

Complete the bounded D-070 `recipe-entrypoint-retirement` review and merge cycle for PR #91 from lifecycle-closed base `1068694fac69eb02ff6e0651855c875c532e31a7`.

## Frozen implementation result

The candidate implementation retires the public recipe creation/catalog/rebinding surfaces:

- `/api/uv/recipes` is not mounted;
- recipe-backed public `POST /api/uv/projects` is retired;
- generic project PATCH cannot change `recipe_id`;
- `frontend/lib/recipesApi.ts` is removed;
- `projectsApi#createUVProject` / `CreateProjectInput` are removed.

Modern New Project creation remains Production Direction discovery plus `POST /api/uv/projects/studio`. Project list/get/archive/import, schema-v1/v2 compatibility, `/execution-plan`, Product Orchestrator, Stage8 and internal Recipe Registry compatibility remain intentionally present for later slices.

API/real-media/browser fixtures that need historical recipe identity seed canonical ProjectStore compatibility state directly instead of calling the retired public create route. Browser catalog reconciliation uses Production Directions instead of `/api/uv/recipes`.

Implementation head `2344667deada22983e362d468db084ed5cede797` passed CI #4804 with all five permanent jobs, including API integration, Stage4A real-media and browser Product Truth on Ubuntu and Windows.

## Immediate gate

1. Mark PR #91 Ready for review after this context-only lifecycle refreeze.
2. Resolve the exact live BASE/HEAD.
3. Obtain a genuinely fresh ordinary-ChatGPT semantic review using `.agents/skills/code-review/SKILL.md` v1.0 and an immutable `REVIEW_REQUEST_V1`.
4. Validate every reported finding as `CONFIRMED`, `REJECTED` or `SUPERSEDED`. A confirmed material finding requires returning PR #91 to Draft before changes and repeating exact-head review.
5. Require the exact final review head to pass all five permanent CI jobs and verify the reviewed BASE/HEAD still match before merge.

## Completion evidence

- public recipe creation/catalog/rebinding entrypoints remain absent;
- Production Direction -> Studio Project remains the modern creation authority;
- old/imported projects remain readable/importable with exact compatibility identity;
- test fixtures do not resurrect retired public entrypoints;
- all five permanent CI jobs pass on the exact final review head;
- fresh semantic review returns PASS with no actionable findings;
- final live PR BASE/HEAD exactly match the reviewed identity immediately before merge.

## Out of scope

Do not mix `/execution-plan` retirement, broad legacy `/projects/{id}` migration, Product Orchestrator retirement, Stage8 runtime/compatibility retirement, Production Direction redesign, Agent autonomy or Timeline identity work into PR #91.

## After this slice

After PR #91 merges, perform mandatory D-038 lifecycle closure to `idle`. Only after that closure merges may the accepted D-070 sequence continue with `execution-plan-retirement`.
