# Agent Planner, durable Tasks and Skills — Stage 16

**Status:** draft implementation under PR #70  
**Date:** 2026-08-26  
**Decision authority:** D-066 + D-017

## Purpose

Stage 16 implements D-066 Agent Harness layer 2 on top of the merged Stage-15 Context Builder / Action Catalog / policy / trace foundation.

It adds three orchestration concepts without adding a second application authority:

```text
bounded production goal
 -> Stage-15 Context Builder + Action Catalog
 -> AgentPlanner validates a structured proposal
 -> AgentPlanRecord + durable AgentTaskRecord state
 -> bounded Agent Skills expand only into approved catalog actions
 -> AgentTaskCoordinator executes one foreground runnable task
 -> Stage-15 AgentHarness
 -> existing Production / Timeline / Generation authorities
 -> existing Stage-15 trace + durable task result link
```

This is still not a background or autonomous Agent runtime.

## Planner contract

`AgentPlanner` does not persist free-form reasoning. It accepts a strict sequence of `AgentPlanStepProposal` values and converts them into one validated `AgentPlanRecord`.

The planner contract is bounded:

- maximum proposed and expanded task counts;
- stable plan/step/task identities;
- bounded portable JSON inputs;
- bounded canonical references;
- Stage-15 context digest binding;
- exactly one `action_id` or `skill_id` per proposed step;
- explicit dependencies;
- unknown actions and Skills fail closed;
- action input keys must be part of the existing `AgentActionCatalog` contract;
- dependency cycles, missing dependencies and duplicate identities fail closed;
- an unavailable model/offer is rejected rather than becoming runnable;
- D-017-required but otherwise available work may be planned, but planning never supplies authorization.

The current planner is a deterministic validator/expander. A later model may propose the same structured data, but UV-owned validation remains authoritative and hidden model reasoning is not durable project state.

## Durable Agent Tasks

`AgentPlanStore` and `AgentTaskStore` use the existing project `tasks/` root through `ProjectTaskRecordStore`.

Plan descriptors are append-only. Concrete Agent Task state is mutable orchestration state with the bounded lifecycle:

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

`ready` is promoted only when every declared dependency has succeeded. A failed dependency does not silently unlock downstream work.

Each durable task record keeps only orchestration/inspection facts:

- project / plan / task identity;
- catalog action identity and optional Skill identity;
- current state and timestamps;
- Stage-15 `trace_id` for the execution attempt;
- canonical references copied from that trace;
- transaction / Job / Attempt / output / Take / Timeline result references exposed by that trace;
- sanitized failure type/message.

Task records do **not** copy plan inputs, provider prompts, authorization tokens or provider-private runtime state. They are not Generation Jobs, production truth, Timeline truth or Undo/Redo history.

## Skills

`AgentSkillCatalog` is deliberately small and built over the existing `AgentActionCatalog`.

The first proof Skill is:

- `production.scene_with_shot` — expands one bounded Skill step into `production.create_scene` followed by dependent `production.create_shot`.

Its effects, Job Manager routing, possible D-017 requirement and authority list are derived from its underlying catalog actions. The Skill does not own another permission model.

A Skill cannot request:

- `project.write_file`;
- shell or Python execution;
- arbitrary filesystem access;
- arbitrary provider calls;
- an action absent from the existing Agent catalog;
- reusable authorization or a D-017 bypass.

## Foreground task execution

`AgentTaskCoordinator` executes one task only when its durable status is `ready` and all dependencies are `succeeded`.

Execution remains on the existing Stage-15 seam:

```text
AgentTaskCoordinator
 -> AgentHarness.execute(...)
 -> existing ProductionSemanticService / TimelineCommandService / GenerationService
```

The coordinator records `running` before dispatch and then links the resulting Stage-15 trace into the task record. On failure it records the sanitized failure and leaves dependent tasks blocked. It does not auto-retry remote or cost-bearing work.

For actions that accept D-017 authorization, `authorization_token` is an execution-only `runtime_inputs` value. It is never accepted into Planner/Task durable payloads.

## Trace relationship

Stage 16 does **not** create another trace store. The Stage-15 `AgentTraceStore` remains the execution trace authority.

The durable Agent Task record provides the orchestration edge:

```text
plan_id + task_id + optional skill_id
 -> trace_id
 -> action / policy / effects / canonical result identities
```

This is enough to inspect which plan/task/Skill caused an action while avoiding a duplicate trace schema. Background concurrency is intentionally out of scope for this layer; task execution is foreground and serialized through the project authority.

## Generation and D-017

Planner policy comes from the same Stage-15 action/model/capability projection.

- configuration-required or unavailable generation is rejected at planning time;
- available remote/non-free work retains `authorization_required=true`;
- execution without the exact existing one-shot authorization fails through `GenerationService` / D-017;
- a succeeded Agent Task is terminal, so replaying the task does not silently submit a second generation Job;
- generation idempotency and Job/Attempt provenance remain owned by the existing Generation Job Manager.

## Proof

`tests/test_agent_planning.py` covers:

1. one Skill expanding to two dependency-ordered production tasks;
2. blocked dependent work before its dependency succeeds;
3. foreground execution through existing production commands;
4. Stage-15 trace IDs and canonical identities linked from durable task records;
5. restart/reopen through a fresh `ProjectStore` / Agent runtime;
6. cycle and missing-dependency rejection;
7. unknown action / unknown Skill / direct project-file mutation rejection;
8. secret and absolute-host-path rejection;
9. invalid task-state transition rejection;
10. durable failed task state without downstream unlock or false plan success;
11. unavailable generation rejected during planning;
12. D-017-required execution failing without authorization;
13. a succeeded generation-submit task refusing replay while the underlying Job count remains one.

## Explicitly deferred by D-066

Stage 16 does **not** implement:

- functional subagents (`explore`, `plan`, `media`, `critic`) — layer 3;
- background Agent work through Job Manager — layer 4;
- critic/evaluation and dependency-aware local repair — layer 5;
- human takeover/edit/resume — layer 6;
- long-form autonomous production — layer 7;
- an Agent-only canonical write path;
- a duplicate JarvisHub protocol/tool/permission authority;
- a user-facing autonomous-Agent product claim without a separate D-067 surface/proof slice.
