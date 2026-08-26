# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-agent-planner-durable-tasks-skills -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 16 is active in draft on branch `stage-16/agent-planner-durable-tasks-skills`, PR #70, created from lifecycle-closed idle `main` commit `fdc82fbdbd518e711a5f4b36d01cdbc6745a7e40`.

Stage 15 / PR #69 merged as `273b5ea8f979cf759cfbf6510e1215a55e98d9c9` and its closure head passed all five permanent CI jobs on Ubuntu/Windows, including browser E2E.

## Stage-16 implementation state

Current implementation head introduced D-066 Agent Harness layer 2 under `uv_studio/agent/`:

- `AgentPlanner` validates bounded structured proposals against the merged Stage-15 Context Builder / Action Catalog / policy authorities;
- `AgentPlanRecord` is an append-only project-scoped descriptor bound to a Stage-15 context digest;
- durable `AgentTaskRecord` values implement explicit dependency/state semantics under the existing project `tasks/` root;
- `AgentSkillCatalog` provides bounded reusable procedures that expand only into approved Agent catalog actions;
- first proof Skill `production.scene_with_shot` expands to existing `production.create_scene` -> dependent `production.create_shot` actions;
- `AgentTaskCoordinator` executes only READY tasks in the foreground through the existing `AgentHarness`, then links durable task state to the resulting Stage-15 trace and canonical transaction/Job/entity references;
- unavailable generation fails during planning; D-017-required generation remains plan-visible but fails at execution without the existing exact one-shot authorization;
- succeeded tasks are terminal and cannot silently replay a generation submit;
- restart/reopen reconstructs plan/task state from the existing Project Store.

Focused Stage-16 tests cover Skill expansion, dependency blocking/unlock, restart/reopen, cycle/missing dependency rejection, unknown action/Skill rejection, secret/host-path rejection, invalid task transitions, durable failure semantics, unavailable generation, D-017 failure and no duplicate Job on replay.

The first implementation head `1e8836aac896ed3304fbd967164668ed4402fb68` has already passed `development-context` and full unit suites on both Ubuntu and Windows. Full app-baseline/browser CI is still being completed and this slice remains `draft` until a later exact head passes all five permanent jobs.

## Current authority stack

Stage 16 must reuse, not replace:

- Project Store and existing project `tasks/` root;
- Production Semantic Core and canonical Timeline;
- Studio/Application Commands and `ProjectUnitOfWork`;
- Stage-15 `AgentContextBuilder`, `AgentActionCatalog`, policy, `AgentHarness` and `AgentTraceStore`;
- Model Registry and Generation Job/Attempt authority;
- Capability Registry / effects / D-017.

Agent Tasks are orchestration state, not Generation Jobs, canonical production truth or Undo/Redo history. Skills are bounded procedures over approved Agent actions, not plugins with arbitrary execution rights.

## Active slice

`studio-v2-agent-planner-durable-tasks-skills`

```text
bounded production goal
 -> Stage-15 Context Builder + Action Catalog + policy
 -> validated AgentPlanner plan
 -> durable dependency-aware Agent Tasks
 -> bounded Skills expand to approved catalog-backed work
 -> foreground execution through AgentHarness
 -> existing Production / Timeline / Generation authorities
 -> Stage-15 trace + canonical result links
```

## Explicit non-goals

- no functional subagents (`explore`, `plan`, `media`, `critic`) — D-066 layer 3;
- no background Agent work through Job Manager — layer 4;
- no critic/evaluation + dependency-aware repair — layer 5;
- no human takeover/edit/resume — layer 6;
- no long-form autonomous production — layer 7;
- no Agent-only project write path, shell/Python authority or duplicate tool/permission system;
- no unrelated desktop updater or real continuation-provider implementation;
- no user-facing autonomous-Agent readiness claim without a later D-067 surface/proof slice.

`project-context/NEXT_TASK.md` remains the exact Stage-16 scope contract until this slice is reviewed, merged and lifecycle-closed.
