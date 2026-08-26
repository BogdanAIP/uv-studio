# Agent Planner, durable Tasks and Skills — Stage 16

**Status:** review implementation under PR #70  
**Date:** 2026-08-26  
**Decision authority:** D-066 + D-017

## Purpose

Stage 16 implements D-066 Agent Harness layer 2 on top of the merged Stage-15 Context Builder / Action Catalog / policy / trace foundation.

```text
bounded production goal
 -> Stage-15 Context Builder + Action Catalog + policy
 -> AgentPlanner validates structured proposal
 -> AgentPlanRecord + durable AgentTaskRecord state
 -> bounded Skills expand only into approved catalog actions
 -> AgentTaskCoordinator executes foreground runnable work
 -> Stage-15 AgentHarness
 -> existing Production / Timeline / Generation authorities
 -> same Stage-15 trace enriched with plan/task/Skill correlation
```

This layer deliberately does not add a second project graph, command registry, permission system, trace store or provider runtime.

## Planner contract

`AgentPlanner` persists no hidden/free-form reasoning. It validates a strict sequence of `AgentPlanStepProposal` values and produces a bounded `AgentPlanRecord`.

The contract enforces:

- bounded proposed/expanded task counts and portable payload size;
- stable plan/step/task identities;
- exactly one approved `action_id` or bounded `skill_id` per step;
- explicit dependency identities with missing-dependency, duplicate and cycle rejection;
- Stage-15 context digest and canonical-reference binding;
- existing Agent Action Catalog input fields and policy availability;
- fail-closed unknown actions/Skills;
- no persisted authorization tokens, secrets or absolute host paths.

Unavailable/configuration-required generation is rejected at planning time. D-017-required but otherwise available execution remains visible as authorization-required; planning never grants authorization.

## Durable Agent Tasks

`AgentPlanStore` and `AgentTaskStore` use the existing project `tasks/` root through `ProjectTaskRecordStore`.

Task lifecycle is strict and durable:

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

A dependent task becomes ready only after every dependency succeeds. Failed work never silently unlocks downstream tasks. Successful tasks are terminal, preventing accidental re-execution such as duplicate generation submission.

Task records keep orchestration facts only: project/plan/task/Skill/action identity, timestamps/status, resulting Stage-15 trace ID, canonical/result references and sanitized failures. They do not copy provider prompts, authorization tokens, provider-private runtime state or canonical production data.

## Skills

`AgentSkillCatalog` is a bounded reusable-procedure catalog over existing Agent actions. The proof Skill `production.scene_with_shot` expands to:

1. `production.create_scene`;
2. dependent `production.create_shot`.

Skill effects, authorities, Job Manager routing and possible D-017 requirement derive from the underlying action definitions. Skills cannot introduce shell, Python, arbitrary filesystem access, arbitrary provider calls or actions absent from the Agent catalog.

## Foreground execution

The public Stage-16 `AgentTaskCoordinator` preserves one execution path:

```text
AgentTaskCoordinator
 -> AgentHarness.execute(...)
 -> ProductionSemanticService / TimelineCommandService / GenerationService
```

The coordinator records `running` before dispatch and terminal state after dispatch. Execution remains foreground/synchronous in this slice.

For an action accepting D-017 authorization, `authorization_token` is execution-only. Plans/tasks never persist it. For local/free `generation.submit`, the coordinator supplies `authorization_token=None` when omitted so callers do not have to persist or manually provide a meaningless null token.

## Trace correlation

Stage 16 keeps the Stage-15 `AgentTraceStore` as the sole execution-trace authority. A small correlation proxy enriches the `AgentTraceRecord` before that same store appends it.

The trace therefore directly contains canonical references to:

- project/target entities from Stage 15;
- affected/result identities from Stage 15;
- `plan_id`;
- `task_id`;
- optional `skill_id`.

The durable task record also points back to the resulting `trace_id`. This gives bidirectional inspection without another trace schema/store.

## Generation and D-017

Generation continues to use the existing Model Registry, Generation Service, Job Manager and D-017 authority.

- unavailable/configuration-required offers fail before runnable task creation;
- remote/non-free work keeps its exact one-shot D-017 requirement;
- failed authorization creates no generation Job;
- Agent Task success does not replace Job/Attempt provenance;
- a succeeded generation task cannot silently replay and create another Job;
- Job idempotency remains owned by `GenerationJobManager`.

## Proof

`tests/test_agent_planning.py` and `tests/test_agent_stage16_runtime.py` cover:

1. bounded Skill expansion into dependency-ordered tasks;
2. dependency blocking and promotion;
3. restart/reopen from a fresh Project Store/runtime;
4. cycle/missing-dependency/unknown action/unknown Skill rejection;
5. secret/host-path and invalid state-transition rejection;
6. durable failed task state without downstream unlock;
7. unavailable generation rejection;
8. D-017-required execution failure without authorization and without Job creation;
9. generation task replay protection / one Job identity;
10. direct plan/task/Skill correlation in the same Stage-15 trace;
11. local generation submit without explicitly supplying a null authorization token;
12. no authorization token persisted in plan/task state.

Draft exact head `092a4e5e8acd667d50a6df1c29e18052157fdefa` passed all five permanent CI jobs in one PR-event run, including unit suites and browser E2E on Ubuntu and Windows. Review-state exact-head verification is required again before merge.

## Known limitations

This is internal bounded Agent infrastructure, not a user-visible autonomous-production claim. Functional subagents (`explore`, `plan`, `media`, `critic`), background Agent work, evaluate/repair, human takeover/edit/resume and long-form autonomy remain later D-066 layers. The unrelated desktop updater and real continuation-provider UI are also outside Stage 16.
