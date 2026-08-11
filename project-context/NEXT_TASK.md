# Next Task

**Primary target:** continue Stage 2 by turning registered recipes into explicit UV Studio execution plans for already-supported VideoClaw workflows, without implementing the general Capability Registry yet.

## Why this comes next

The first Stage 2 slice defines durable provider-neutral task recipes, production policies, API catalog and New Project selection. A recipe still describes intent only; opening a canonical project does not yet say which existing workflow can actually run or what inputs must be collected.

The next slice should bridge that gap for the three existing specialized VideoClaw pipelines while keeping the compatibility layer replaceable.

## Do first

1. Inspect the current VideoClaw API/pipeline launch contracts for:
   - `standard` (mapped from `narrated_video`);
   - `action_transfer`;
   - `digital_human`.
2. Add UV Studio-owned execution-planning models, for example:
   - `RecipeExecutionPlan`;
   - execution status such as `available | unavailable | missing_inputs`;
   - required input slots and accepted media kinds;
   - compatibility target metadata kept outside `RecipeDefinition`;
   - no provider credentials in the plan.
3. Add a small resolver that maps a canonical project's registered recipe to an execution plan.
4. `general_video` must report honestly that its full generic execution path is not implemented yet rather than silently using the narrated `standard` pipeline.
5. Expose project-level endpoint such as:

```text
GET /api/uv/projects/{project_id}/execution-plan
```

6. For the three compatible recipes, expose the exact existing pipeline target and input requirements through the plan, but do not duplicate the upstream pipeline implementation.
7. Add minimal project-workspace UI:
   - show recipe title/description;
   - show required inputs;
   - show whether the current workflow is available;
   - do not launch anything until input binding is explicit.
8. Add unit/API/frontend build coverage on Windows/Linux.
9. Document the migration boundary so future Stage 3 Capability Registry can replace native VideoClaw bindings without changing RecipeDefinition or Project Store.

## Production Policy integration

Execution plans should carry the recipe's resolved Production Policy so later execution can enforce:

- source review;
- sample-first;
- plan gate;
- scene ledger;
- final review;
- continuity policy.

Do not implement all gate mechanics in this slice. The important part is that execution does not lose the policy when it leaves the recipe catalog.

## Explicit honesty rule

Never make `general_video` run the existing `standard` pipeline merely because it is available. `standard` is narration-led and would recreate the architecture mistake where ordinary video implicitly requires speech.

If a recipe has no implementation yet, return an explicit unavailable execution plan with a reason.

## Capability boundary

Still out of scope:

- direct MCP execution;
- Qwen-MM runtime installation;
- OpenClaw runtime integration;
- provider/model routing;
- cost selection;
- generic `video.generate` resolution.

Those belong to Stage 3.

The compatibility resolver may call or identify existing native VideoClaw pipelines only.

## Suggested files

```text
uv_studio/recipes/execution.py
uv_studio/api/projects.py

tests/test_recipe_execution.py
tests_api/test_project_execution_api.py

frontend/lib/projectsApi.ts
frontend/app/projects/[projectId]/page.tsx

docs/architecture/RECIPE_EXECUTION.md
```

## Acceptance criteria

- execution planning is UV Studio-owned and provider-neutral above the compatibility target;
- `narrated_video`, `action_transfer`, `digital_human` resolve to truthful existing-pipeline plans;
- `general_video` is explicitly unavailable until a real generic path exists;
- project execution plan preserves Production Policy;
- no VideoClaw session ID becomes the canonical UV Studio project ID;
- no API key/provider/runtime dependency is added;
- no files under `vendor/videoclaw-app` are modified;
- tests + production frontend build pass on Windows/Linux.

After this slice, either bind inputs and launch the existing pipelines through a UV Studio wrapper, or begin Stage 3 Capability Registry depending on how cleanly the upstream launch contracts can be isolated.
