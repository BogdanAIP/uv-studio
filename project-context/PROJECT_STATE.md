# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: execution-plan-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `af9ff888145661381caaacdec78244637058bce2` after `recipe-entrypoint-retirement` PR #91 and D-038 closure PR #92. PR #93, `execution-plan-retirement`, is now frozen in review on branch `chore/execution-plan-retirement` from that exact base.

The final material Draft head is `f7e0c1929de2da3f4cdd300b62cb232c669a38c9`. Exact-head CI #4839 passed all five permanent checks on that head. The review refreeze changes lifecycle/context only; runtime, frontend, tests and architecture behavior are unchanged from the green material head.

## Accepted baseline

Modern project creation is Production Direction -> Studio Project. Public recipe catalog/creation/rebinding entrypoints are retired. Old/imported recipe projects remain readable through explicit compatibility identity. Internal Recipe Registry and Product Orchestrator remain compatibility authorities until their separately accepted D-070 slices.

## PR #93 as-built candidate

Exact caller reconstruction established that the modern project page already consumes `getProjectWorkflow()` plus project/Studio Timeline APIs and has no supported `getProjectExecutionPlan()` caller. GitHub Code Search returned incomplete/empty results for known symbols, so zero-search results are not used as absence proof; the retirement proof is exact-head file inspection, focused regression tests, permanent CI and the required fresh semantic review.

The candidate removes the isolated recipe-derived execution projection:

- `frontend/lib/projectsApi.ts` no longer exports execution-plan types or `getProjectExecutionPlan()`;
- `uv_studio/api/execution.py` is deleted and `uv_studio/server.py` no longer imports/mounts `execution_router`;
- `uv_studio/recipes/execution.py` and its public projection exports are deleted;
- projection-only `tests/test_recipe_execution.py`, `tests_api/test_project_execution_api.py` and `tests_api/test_recipe_target_mounting.py` are deleted;
- `tests/test_execution_plan_retirement.py` protects the removed files/client/server mount and the preserved Recipe Registry/Product Workflow/Studio router boundary.

No replacement Recipe-like planner was introduced. `/api/uv/projects/{id}/workflow`, internal Recipe Registry, Production Directions, Studio creation, Project Store/archive/import compatibility and Stage8 remain intentionally present.

## Verification history

- opening context-only head passed the permanent CI as run #4816;
- scope-widen heads passed `development-context` before affected product/test paths were changed;
- CI #4820 exposed only stale projection-test residue plus an invalid first regression-test assumption;
- CI #4824 showed API integration green and reduced the remaining failure to the new retirement test's FastAPI route-introspection assumption;
- CI #4826 showed API integration, real-media, frontend lint/build and preserved Product Orchestrator/Recipe Registry tests succeeding; its bootstrap failure was only an over-broad test substring matching `execution_router` inside valid `capability_execution_router`;
- the final Draft candidate head `f7e0c1929de2da3f4cdd300b62cb232c669a38c9` passed exact-head CI #4839 with all five permanent checks SUCCESS, including unit/API integration, Stage4A real-media, frontend lint/audit/build and Stage4C+Stage5 browser outcomes on Ubuntu and Windows.

Current architecture, v2 architecture map and legacy inventory are synchronized to PR #93 candidate status and to the already accepted PR #91/#92 history.

## Immediate gate

Keep product code frozen. Mark PR #93 Ready for review, require all five permanent checks on the exact context-only review head, and obtain a genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0 bound to exact BASE/HEAD.

Any material review finding returns the PR to Draft before any fix. After PASS/CURRENT and final exact-head 5/5 CI, merge exact reviewed HEAD and perform mandatory D-038 closure to `idle` before starting another product slice.

## Handoff

Finish only `execution-plan-retirement` in PR #93. Broad legacy `/projects/{id}` migration, contextual-tool extraction, Product Orchestrator retirement, Stage8 runtime/compatibility retirement and the separate `micro_drama` golden vertical remain later D-070 work.
