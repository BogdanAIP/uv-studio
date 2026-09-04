# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: execution-plan-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `af9ff888145661381caaacdec78244637058bce2` after `recipe-entrypoint-retirement` PR #91 and D-038 closure PR #92. Bounded Draft PR #93, `execution-plan-retirement`, is open on branch `chore/execution-plan-retirement` from that exact base.

## Accepted baseline

Modern project creation is Production Direction -> Studio Project. Public recipe catalog/creation/rebinding entrypoints are retired. Old/imported recipe projects remain readable through explicit compatibility identity. Internal Recipe Registry and Product Orchestrator remain compatibility authorities until their separately accepted D-070 slices.

## PR #93 as-built candidate

Exact caller reconstruction established that the modern project page already consumes `getProjectWorkflow()` plus project/Studio Timeline APIs and has no supported `getProjectExecutionPlan()` caller. GitHub Code Search returned incomplete/empty results for known symbols, so zero-search results are not used as absence proof; the retirement proof is exact-head file inspection, focused regression tests, permanent CI and the required fresh semantic review.

The current candidate removes the isolated recipe-derived execution projection:

- `frontend/lib/projectsApi.ts` no longer exports execution-plan types or `getProjectExecutionPlan()`;
- `uv_studio/api/execution.py` is deleted and `uv_studio/server.py` no longer imports/mounts `execution_router`;
- `uv_studio/recipes/execution.py` and its public projection exports are deleted;
- projection-only `tests/test_recipe_execution.py`, `tests_api/test_project_execution_api.py` and `tests_api/test_recipe_target_mounting.py` are deleted;
- `tests/test_execution_plan_retirement.py` protects the removed files/client/server mount and the preserved Recipe Registry/Product Workflow/Studio router boundary.

No replacement Recipe-like planner was introduced. `/api/uv/projects/{id}/workflow`, internal Recipe Registry, Production Directions, Studio creation, Project Store/archive/import compatibility and Stage8 remain intentionally present.

## Verification history

- opening context-only head passed the permanent CI as run #4816;
- scope-widen heads passed `development-context` before affected product/test paths were changed;
- CI #4820 exposed only stale projection-test residue plus an invalid first regression-test assumption; product server import and the remaining test graph otherwise progressed;
- after removing the stale API residue, CI #4824 showed API integration green and reduced the remaining failure to the new retirement test's FastAPI route-introspection assumption;
- CI #4826 showed API integration, real-media, frontend lint/build and the preserved Product Orchestrator/Recipe Registry tests succeeding; both bootstrap jobs had one failure only because the new regression test matched the substring `execution_router` inside the valid `capability_execution_router` name;
- commit `d08367d30c94fde596242cfad2992f90af6114ce` narrows that assertion to the exact retired import and exact retired mount expression.

Current architecture, v2 architecture map and legacy inventory are synchronized to PR #93 candidate status and to the already accepted PR #91/#92 history.

## Immediate gate

Freeze the final Draft implementation/docs/context head and require all five permanent checks to pass on that exact head. Do not transition to review while any exact-head check is pending or failing.

After a green 5/5 Draft head, perform a context-only `draft -> review` refreeze, mark PR #93 Ready, require exact-head CI again, and obtain a genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0. Material review findings return the PR to Draft before fixes.

## Handoff

Finish only `execution-plan-retirement` in PR #93. Broad legacy `/projects/{id}` migration, contextual-tool extraction, Product Orchestrator retirement, Stage8 runtime/compatibility retirement and the separate `micro_drama` golden vertical remain later D-070 work.

After an exact reviewed-head PASS and final green CI, merge exact HEAD and perform mandatory D-038 closure to `idle` before starting the next bounded D-070 slice.
