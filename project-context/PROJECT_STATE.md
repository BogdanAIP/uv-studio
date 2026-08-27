# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-planner-durable-tasks-skills -->

**Updated:** 2026-08-27

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 16 remains in review on branch `stage-16/agent-planner-durable-tasks-skills`, PR #70. It was opened from lifecycle-closed idle `main` commit `fdc82fbdbd518e711a5f4b36d01cdbc6745a7e40` after Stage 15 / PR #69 merged as `273b5ea8f979cf759cfbf6510e1215a55e98d9c9`.

The exact review candidate is always the PR #70 branch head containing this document; this current-authority file intentionally does not duplicate its own commit SHA because changing that literal would create a permanently self-stale follow-up commit. The latest completed exact-head evidence before this self-consistency refinement is documentation-only head `cf69e67d8fa2f5ea45ae951dee3893db9dcdeb22`, whose PR CI #3406 (`33051435225`) completed successfully across all five permanent jobs, including Ubuntu/Windows bootstrap+unit suites and both app-baseline browser E2E suites. The code-bearing parent `5a1e6e23cd6f55f8991366c7fe08dfa0b651473b` likewise passed exact-head CI #3402 (`33049944377`). Merge eligibility is determined from the actual PR head plus the seven-item review gate below, not from a copied “current SHA” literal inside that same commit.

## Stage-16 implementation under review

The D-066 layer-2 implementation provides:

- bounded `AgentPlanner` validation over the merged Stage-15 context/catalog/policy authorities;
- append-only `AgentPlanRecord` descriptors with cross-runtime create-if-absent semantics and deterministic canonical target-context binding;
- derived `AgentPlanExecutionState` status with stable created/updated inspection timestamps rather than a second persisted mutable plan-status truth;
- durable dependency-aware `AgentTaskRecord` state under the existing project `tasks/` authority;
- strict planned/ready/running/succeeded/failed/cancelled transitions, storage-level CAS and one cross-runtime project task lock;
- recoverable partial task initialization, complete custom Plan-ID discovery, mixed-terminal status and dependency-aware cancellation;
- bounded versioned `AgentSkillCatalog`, with proof Skill `production.scene_with_shot` expanding only to approved production actions;
- foreground `AgentTaskCoordinator` execution solely through the existing `AgentHarness` and UV application authorities;
- typed trace correlation with exact input-digest/start-window checks and preparation-failure provenance;
- post-commit/pre-trace recovery from the existing correlated `ProjectUnitOfWork` journal and exact durable Generation Job/idempotency evidence without replay;
- exact execution-time context binding before canonical/cost-bearing dispatch;
- bounded append-only execution-policy evidence under the existing project `tasks/` authority so recovered traces use the policy actually used at execution time rather than stale Plan-time policy;
- recoverable handling of ordinary success-trace persistence failure: if a committed transaction/Job already proves success, the task remains `running` for reopen reconciliation rather than being falsely terminalized as `failed`;
- Timeline result reconstruction from committed before/after snapshots, including authority-generated track/clip IDs and the clip/track created by `production.accept_take`;
- execution-only D-017 authorization handling: tokens never enter durable Plans, Tasks, trace-correlation evidence or execution-policy evidence;
- dependency/cycle/unknown-authority rejection, command-level input validation, unavailable-model, D-017 and generation idempotency/replay proof.

Agent Tasks remain orchestration state, not Generation Jobs, canonical production truth, Timeline truth or Undo/Redo history. Skills remain bounded procedures over approved Agent actions, not arbitrary plugins or execution rights. The small execution-evidence record is provenance attached to the existing Agent Task authority; it is not a second project graph, transaction journal, permission system or trace store.

## Authority stack preserved

Stage 16 reuses rather than replaces Project Store/tasks, Production Semantic Core, canonical Timeline, Studio/Application Commands, `ProjectUnitOfWork`, Stage-15 Context/Catalog/Policy/Harness/Trace, Model Registry, Generation Job/Attempt authority, Capability Registry/effects and D-017.

## Review gate

Before PR #70 may merge, the actual PR head must satisfy all of the following together:

1. `development-context` success;
2. Ubuntu bootstrap/unit suite success;
3. Windows bootstrap/unit suite success;
4. Ubuntu app-baseline including browser E2E success;
5. Windows app-baseline including browser E2E success;
6. no unresolved inline review threads;
7. a fresh Codex review of that exact PR head with no new blocking finding.

## Known limitations

Execution is foreground and bounded. Functional subagents, background Agent work, critic/evaluation and repair, human takeover/edit/resume and long-form autonomy remain later D-066 layers. This slice does not claim a user-visible autonomous-Agent product surface and does not implement the unrelated desktop updater or a real continuation-provider UI.

`project-context/NEXT_TASK.md` remains the exact Stage-16 scope contract until PR #70 is merged and lifecycle-closed.
