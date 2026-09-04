# Next Task

<!-- uv-next-slice: execution-plan-retirement -->

## Target

Finish bounded D-070 `execution-plan-retirement` in Draft PR #93 from lifecycle-closed base `af9ff888145661381caaacdec78244637058bce2`.

## Immediate gate

The caller classification and bounded implementation are complete. The next step is acceptance of one frozen exact Draft head:

1. require all five permanent CI jobs to pass on the exact final Draft head;
2. if any job fails, classify the exact failure and make only a bounded Draft repair;
3. after 5/5 green, perform a context-only lifecycle refreeze from `draft` to `review`;
4. mark PR #93 Ready for review;
5. require all five permanent checks on the exact review head;
6. obtain a genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0 for exact BASE/HEAD;
7. any material finding returns the PR to Draft before repair;
8. after review PASS/CURRENT and final exact-head 5/5 CI, merge exact reviewed HEAD;
9. immediately perform mandatory D-038 closure to `idle` before another product slice begins.

## As-built retirement boundary

- no supported modern UI caller exists for `getProjectExecutionPlan()`; the modern project page already uses Product Workflow plus project/Studio Timeline APIs;
- stale execution-plan frontend types/getter are removed;
- `uv_studio/api/execution.py` and its server mount are removed;
- `uv_studio/recipes/execution.py` and its recipe-derived projection exports are removed;
- projection-only tests are removed and a focused retirement regression protects the boundary;
- no replacement Recipe-like planner is introduced.

## Required preservation

- Production Direction -> Studio Project remains modern creation authority;
- Project list/get/archive/import and unrelated `projectsApi.ts` functions remain;
- schema-v1/v2 old/imported project compatibility remains readable;
- internal Recipe Registry remains for Product Orchestrator and other separately scheduled compatibility readers;
- `/api/uv/projects/{id}/workflow` / Product Orchestrator remain until their own migration/retirement slices;
- Stage8 runtime/compatibility is not broadly retired here;
- tests/evidence move with authority changes rather than treating deletion alone as absence proof.

## Completion evidence

- exact caller evidence establishes no supported execution-plan consumer;
- retired frontend/backend/projection surfaces remain absent;
- preserved Product Workflow, Recipe Registry, Production Directions, Studio creation and persisted-project compatibility remain covered;
- current architecture/inventory/context docs agree with the as-built candidate;
- all five permanent CI jobs pass on the frozen exact review head;
- fresh semantic review returns PASS/CURRENT with no actionable findings.

## Out of scope

Do not mix broad legacy `/projects/{id}` migration, Product Orchestrator retirement, Stage8 runtime/compatibility retirement, contextual-tool extraction, Production Direction redesign, Agent autonomy or Timeline identity work into PR #93.

## After this slice

After merge, perform D-038 lifecycle closure to `idle`. Only then bootstrap the next bounded D-070 migration slice; the accepted map continues with legacy direction/tool migration before later Product Orchestrator and Stage8 retirement.
