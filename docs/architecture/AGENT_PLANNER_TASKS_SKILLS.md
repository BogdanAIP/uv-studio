# Agent Planner, durable Tasks and Skills — Stage 16

**Status:** implemented and merged in PR #70  
**Date:** 2026-08-27  
**Merge commit:** `bd258b7564f864c7f5fe636cb1336515f0dacce2`  
**Decision authority:** D-066 + D-017

## Purpose

Stage 16 implements D-066 Agent Harness layer 2 on top of the merged Stage-15 Context Builder / Action Catalog / policy / trace foundation.

```text
bounded production goal
 -> Stage-15 Context Builder + Action Catalog + policy
 -> AgentPlanner validates structured proposal
 -> AgentPlanRecord + durable AgentTaskRecord state
 -> bounded versioned Skills expand only into approved catalog actions
 -> AgentTaskCoordinator executes foreground runnable work
 -> Stage-15 AgentHarness
 -> existing Production / Timeline / Generation authorities
 -> same Stage-15 trace enriched with plan/task/Skill correlation
```

This layer does not add a second project graph, command registry, permission system, trace store or provider runtime.

## Planner contract

`AgentPlanner` persists no hidden/free-form reasoning. It validates a strict sequence of `AgentPlanStepProposal` values and produces a bounded `AgentPlanRecord`.

The contract enforces bounded proposed/expanded task counts and payload size, stable plan/step/task identities, exactly one approved action or Skill per step, explicit acyclic dependencies, Stage-15 context-digest/canonical-reference binding, catalog input/policy validation, and fail-closed rejection of unknown authorities, secrets, authorization tokens and absolute host paths.

Every current Production/Timeline action is validated through the same bounded domain or command constructors used by runtime execution before the Plan is persisted. Canonical prerequisites are checked against current state and transitive dependency closure: missing Scene/Shot/Take/track/clip/media identities fail closed unless an allowed dependency deterministically creates the required identity. Duplicate planned outputs are rejected. `production.accept_take` additionally enforces a video target track and one planned acceptance per Shot.

Generation validates required fields, named Shot/model identity, nested request inputs, Generation Contract and idempotency key. Proposal-specific target Shots are validated and deterministically bound into Plan/execution context; deferred generation targets are allowed only when dependency closure creates the exact input Shot.

Unavailable/configuration-required generation is rejected at planning time. D-017-required but otherwise available execution remains visible as authorization-required; planning never grants authorization.

Plan descriptors are append-only and use cross-runtime create-if-absent semantics. Runtime inspection derives one authoritative plan status from durable task states rather than persisting a second mutable status copy. `AgentPlanExecutionState` exposes that status plus stable `created_at` and derived `updated_at` timestamps.

## Durable Agent Tasks

Plans and task records use the existing project `tasks/` root through `ProjectTaskRecordStore`.

Task lifecycle is strict and durable:

```text
planned -> ready -> running -> succeeded
   |         |          |-> failed
   |         |-> cancelled
   |-> cancelled
```

A dependent task becomes ready only after every dependency succeeds. Failed work never silently unlocks downstream tasks. Mixed terminal plans become terminal rather than remaining falsely active, and cancellation propagates to planned descendants made impossible by a cancelled dependency.

Task mutation uses storage-level compare-and-swap under one project-scoped cross-runtime task-root lock. The canonical lock order is `ProjectStore -> project task lock`; Windows contention waits until the live lease is released rather than using the old bounded `LK_LOCK` retry behavior. Direct task-record writes cannot bypass validated transitions.

Partial plan/task initialization is reopen-recoverable: missing initial task records are reconstructed from the immutable Plan without resetting surviving state or replaying canonical work.

## Execution evidence and restart recovery

Foreground execution records `running` before dispatch and holds the same project task lease through terminal durable state.

Before any canonical or cost-bearing effect, Stage 16 durably binds:

- an opaque typed plan/task/Skill correlation identity;
- the exact execution-time context digest;
- a bounded execution-policy snapshot containing the policy facts actually used for dispatch.

The policy snapshot is a small append-only execution-evidence record under the existing project `tasks/` authority. It contains only safe policy/context/correlation facts; it does not contain prompts, authorization tokens, provider secrets or provider-private runtime state.

Restart/reopen reconciliation is evidence-driven:

1. an already persisted correlated Stage-15 trace is authoritative;
2. otherwise a correlated **committed** `ProjectUnitOfWork` transaction can reconstruct a Production/Timeline success trace;
3. `generation.submit` can reconstruct success only from the exact durable Generation Job bound to the planned idempotency key, request digest and execution mapping evidence;
4. if no durable completion evidence exists, the abandoned `running` task fails closed as interrupted and is never automatically replayed.

This also covers ordinary success-trace persistence failures. If a canonical mutation/Generation Job is already durable but success-trace append raises an exception such as `OSError`, the coordinator does **not** write a false `FAILED` terminal task. It leaves the task `running`, so reopen can reconstruct the missing Stage-15 success trace from committed evidence without replaying the effect.

Recovered traces use the exact execution-time context and execution-time policy snapshot rather than older Plan-time values. Terminal task writes accept only exact typed-correlated durable trace evidence matching project, action, planned input digest, execution window and requested terminal status.

For Timeline/Production mutations, recovery derives affected identities from validated `ProjectUnitOfWork` before/after snapshots. This includes authority-generated `track_id` / `clip_id` values for Timeline commands and the Shot/track/clip identities affected by `production.accept_take`.

## Skills

`AgentSkillCatalog` is a bounded reusable-procedure catalog over existing Agent actions. Its public description carries `schema_version=1` together with stable Skill ID, purpose, bounded input fields, allowed action IDs, derived effects/policy envelope, Job Manager routing, possible D-017 requirement and underlying authorities.

The proof Skill `production.scene_with_shot` expands to:

1. `production.create_scene`;
2. dependent `production.create_shot`.

Skills cannot introduce shell, Python, arbitrary filesystem access, arbitrary provider calls or actions absent from the Agent catalog.

## Trace correlation

Stage 16 keeps the Stage-15 `AgentTraceStore` as the sole execution-trace authority. Correlation enriches the same `AgentTraceRecord` with opaque orchestration identity plus canonical inputs/results.

Trace reconciliation checks typed correlation, action identity, exact normalized input digest and execution start window. Preparation failures retain safe planned-input correlation without persisting rejected values. Caller-selected plan/task IDs therefore cannot collide with ordinary Scene/Shot/etc. identities and accidentally consume an unrelated trace.

The durable task record points back to the resulting `trace_id`, making plan -> task/Skill -> action -> policy/effects -> canonical result linkage inspectable without another trace store or hidden reasoning log.

## Generation and D-017

Generation continues to use the existing Model Registry, Generation Service, Job Manager and D-017 authority.

- unavailable/configuration-required offers fail before runnable task creation;
- remote/non-free work keeps its exact one-shot D-017 requirement;
- authorization tokens are execution-only and never enter Plans, Tasks or execution evidence;
- failed authorization creates no generation Job;
- Agent Task success does not replace Job/Attempt provenance;
- a succeeded or recovered generation task cannot silently replay and create another Job;
- one verified `GenerationSubmissionPreparation` is checked against the frozen Agent policy before D-017/Job commit and reused by submit;
- append-only preparation evidence binds model, request digest and capability/offer/adapter execution mapping for recovery;
- Job idempotency remains owned by `GenerationJobManager`.

## Final verification

The final reviewed PR head was `3478bb17e21fb0f02b4a456a61baf4c0ad941c22`.

- exact-head CI #3442 (`33065539562`) completed successfully across all five permanent jobs;
- Ubuntu and Windows bootstrap/unit suites passed;
- Ubuntu and Windows app-baseline browser E2E suites passed;
- all inline review threads were resolved;
- the fresh Codex exact-head review reported no major issues;
- PR #70 merged as `bd258b7564f864c7f5fe636cb1336515f0dacce2`.

Stage-16 tests cover bounded Skill expansion, dependency ordering, restart/reopen, partial initialization recovery, exact canonical prerequisite validation, task CAS/locking, execution-time context/policy evidence, typed trace correlation, post-commit recovery, Generation mapping/idempotency/D-017 protection and the canonical Scene/Shot/Take/track/clip/media edge cases found during review.

## Next D-066 layer

After lifecycle closure, the next separate slice is `studio-v2-agent-functional-subagents`: bounded `explore / plan / media / critic` roles consuming the merged Context / Planner / Task / Skill contracts. Functional specialization must not introduce private mutation/tool/permission authority.

Background Agent work remains layer 4; evaluate/repair remains layer 5; human takeover/edit/resume remains layer 6; long-form autonomy remains layer 7.

## Known limitations

This is internal bounded Agent infrastructure, not a user-visible autonomous-production claim. Functional subagents, background Agent work, evaluate/repair, human takeover/edit/resume and long-form autonomy remain later D-066 layers. The unrelated desktop updater and real continuation-provider UI are also outside Stage 16.
