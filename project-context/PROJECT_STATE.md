# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-planner-durable-tasks-skills -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 16 is in review on branch `stage-16/agent-planner-durable-tasks-skills`, PR #70. It was opened from lifecycle-closed idle `main` commit `fdc82fbdbd518e711a5f4b36d01cdbc6745a7e40` after Stage 15 / PR #69 merged as `273b5ea8f979cf759cfbf6510e1215a55e98d9c9`.

The final draft implementation head `092a4e5e8acd667d50a6df1c29e18052157fdefa` passed all five permanent CI jobs in one PR-event run, including full unit suites and browser E2E on Ubuntu and Windows. Review refinements remain subject to their own exact-head five-job gate before merge.

## Stage-16 implementation under review

The D-066 layer-2 implementation provides:

- bounded `AgentPlanner` validation over the merged Stage-15 context/catalog/policy authorities;
- append-only `AgentPlanRecord` descriptors bound to canonical context digest/references;
- derived `AgentPlanExecutionState` status with stable created/updated inspection timestamps rather than a second persisted mutable plan-status truth;
- durable dependency-aware `AgentTaskRecord` state under the existing project `tasks/` authority;
- strict planned/ready/running/succeeded/failed/cancelled task transitions;
- fail-closed restart reconciliation: abandoned `running` tasks become explicit failed/interrupted state and are never automatically replayed;
- bounded versioned `AgentSkillCatalog`, with proof Skill `production.scene_with_shot` expanding only to approved production actions and public schema/effects/authority metadata;
- foreground `AgentTaskCoordinator` execution solely through the existing `AgentHarness` and UV application authorities;
- direct plan/task/Skill correlation inside the same Stage-15 append-only `AgentTraceRecord` without a second trace store;
- execution-only D-017 authorization handling: tokens never enter durable plans/tasks, and generation supplies a null authorization value when no grant is required;
- dependency/cycle/unknown-authority rejection, durable failure blocking, unavailable-model, D-017 and generation idempotency/replay proof.

Agent Tasks remain orchestration state, not Generation Jobs, canonical production truth, Timeline truth or Undo/Redo history. Skills are bounded procedures over approved Agent actions, not arbitrary plugins or execution rights.

## Authority stack preserved

Stage 16 reuses rather than replaces Project Store/tasks, Production Semantic Core, canonical Timeline, Studio/Application Commands, `ProjectUnitOfWork`, Stage-15 Context/Catalog/Policy/Harness/Trace, Model Registry, Generation Job/Attempt authority, Capability Registry/effects and D-017.

## Known limitations

Execution is foreground and bounded. Functional subagents, background Agent work, critic/evaluation and repair, human takeover/edit/resume and long-form autonomy remain later D-066 layers. This slice does not claim a user-visible autonomous-Agent product surface and does not implement the unrelated desktop updater or a real continuation-provider UI.

`project-context/NEXT_TASK.md` remains the exact Stage-16 scope contract until PR #70 is merged and lifecycle-closed.
