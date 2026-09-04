# Next Task

<!-- uv-next-slice: execution-plan-retirement -->

## Target

Continue the accepted D-070 migration sequence with the bounded `execution-plan-retirement` slice after PR #91 is lifecycle-closed on protected `main`.

## Required scope

- exact-scan `/api/uv/projects/{id}/execution-plan`, `projectsApi#getProjectExecutionPlan()` and every runtime/frontend/test caller;
- replace any supported readiness caller with direct canonical Production, Generation and Capability readiness rather than another recipe-like execution planner;
- retire the execution-plan endpoint/client only after exact caller and persisted-project evidence proves removal is safe;
- preserve Project list/get/archive/import, modern Production Direction -> Studio Project creation, schema-v1/v2 compatibility and unrelated live `projectsApi.ts` functions;
- retain the internal Recipe Registry wherever Product Orchestrator or another later accepted compatibility slice still requires it;
- migrate tests/evidence with the authority change rather than deleting tests as absence proof.

## Entry gate

Do not start this product slice until:

1. PR #91 is merged as `050780d013276c3d3de9672244ad54da759f1ed3`;
2. its D-038 lifecycle closure has merged and `main` is verified `idle`;
3. the mandatory fresh bootstrap and repository-skill discovery are rerun against that exact lifecycle-closed `main`;
4. a new bounded slice is opened from that exact `main` using the normal `idle -> draft -> review` lifecycle.

## Completion evidence

- `/api/uv/projects/{id}/execution-plan` and `projectsApi#getProjectExecutionPlan()` have no supported caller before retirement;
- supported readiness is expressed through canonical Production/Generation/Capability authorities, not Recipe Registry composition;
- old/imported project recovery and unrelated compatibility readers remain intact;
- all five permanent CI jobs pass on the exact final head;
- because this changes mounted runtime/API authority, the exact frozen review head receives the repository-required fresh ordinary-ChatGPT semantic review before merge.

## Out of scope

Do not mix broad legacy `/projects/{id}` migration, Product Orchestrator retirement, Stage8 runtime/compatibility retirement, contextual-tool extraction, Production Direction redesign, Agent autonomy or Timeline identity work into this slice.

## After this slice

After `execution-plan-retirement` merges, perform its mandatory D-038 lifecycle closure to `idle` before beginning the next accepted D-070 migration slice.
