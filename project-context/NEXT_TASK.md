# Next Task

<!-- uv-next-slice: recipe-entrypoint-retirement -->

## Target

Continue the accepted D-070 migration sequence with the bounded `recipe-entrypoint-retirement` slice after PR #89 is lifecycle-closed on protected `main`.

## Required scope

- exact-scan `frontend/lib/recipesApi.ts` and all imports/callers of its `/api/uv/recipes` clients;
- exact-scan `frontend/lib/projectsApi.ts#createUVProject` and any remaining modern or compatibility creation callers that still require `recipe_id`;
- move any genuine modern creation/metadata caller to Production Direction / Studio project creation authority;
- remove recipe-backed frontend/API creation or metadata entrypoints only when exact caller evidence proves they are no longer required;
- retain bounded compatibility metadata where old/imported projects still need exact historical recipe identity;
- preserve schema-v1/v2 read/import/export and Undo/Redo compatibility established by PR #89.

## Entry gate

Do not start this product slice until:

1. PR #89 is merged as `a0150e1543b8b4c8f5d3ae8d1b701118fcb112d2`;
2. its D-038 lifecycle closure has merged and `main` is verified `idle`;
3. the mandatory fresh bootstrap is rerun against that exact lifecycle-closed `main`;
4. a new bounded slice is opened from that exact `main` using the normal `idle -> draft -> review` lifecycle.

## Out of scope

Do not mix `/execution-plan` retirement, broad legacy `/projects/{id}` workflow migration, Product Orchestrator retirement, Stage8 runtime dependency migration/compatibility retirement, further Agent autonomy, provider-selection redesign, Production Direction redesign or Timeline identity work into this slice.
