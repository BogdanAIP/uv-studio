# Next Task

<!-- uv-next-slice: execution-plan-retirement -->

## Target

Execute the bounded D-070 `execution-plan-retirement` slice in Draft PR #93 from lifecycle-closed base `af9ff888145661381caaacdec78244637058bce2`.

## Immediate gate

1. require `development-context` SUCCESS on the context-only opening head before product implementation;
2. exact-scan `/api/uv/projects/{id}/execution-plan`, `getProjectExecutionPlan()` and every runtime/frontend/test caller from the exact active head;
3. classify each caller as supported modern behavior, compatibility-only evidence or dead residue;
4. widen `write_scope` only for concrete affected paths;
5. migrate supported readiness to direct canonical Production / Generation / Capability authorities;
6. retire the legacy endpoint/client only after caller and persisted-project compatibility proof.

## Required preservation

- Production Direction -> Studio Project remains modern creation authority;
- Project list/get/archive/import and unrelated `projectsApi.ts` functions remain;
- schema-v1/v2 old/imported project compatibility remains readable;
- internal Recipe Registry and Product Orchestrator compatibility remain wherever still required by later slices;
- Stage8 runtime/compatibility is not broadly retired here;
- tests/evidence migrate with the authority change rather than being deleted as absence proof.

## Completion evidence

- no supported caller remains for `/api/uv/projects/{id}/execution-plan` or `getProjectExecutionPlan()`;
- canonical readiness is obtained directly from Production / Generation / Capability owners rather than Recipe Registry composition;
- persisted legacy projects remain readable/recoverable through intended compatibility paths;
- current architecture/inventory/context docs describe the as-built retirement accurately;
- all five permanent CI jobs pass on exact final head;
- exact frozen review head receives the repository-required fresh ordinary-ChatGPT semantic review with no unresolved actionable findings.

## Out of scope

Do not mix broad legacy `/projects/{id}` migration, Product Orchestrator retirement, Stage8 runtime/compatibility retirement, contextual-tool extraction, Production Direction redesign, Agent autonomy or Timeline identity work into this slice.

## After this slice

After merge, perform mandatory D-038 lifecycle closure to `idle` before beginning the next accepted D-070 migration slice.
