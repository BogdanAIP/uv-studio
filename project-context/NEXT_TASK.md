# Next Task

<!-- uv-next-slice: studio-v2-agent-planner-durable-tasks-skills -->

## Goal

Build **D-066 Agent Harness layer 2** on top of the merged Stage-15 Context Builder / action catalog / policy / trace foundation.

The slice is `studio-v2-agent-planner-durable-tasks-skills`:

```text
Planner
 + durable Agent Tasks
 + Skills
```

The goal is not long-form autonomy yet. It is to prove that UV Studio can convert a bounded production goal into an inspectable dependency-aware task plan, persist/reopen that plan safely, reuse bounded Skills, and execute approved tasks only through the existing Stage-15 Agent Harness and UV application authorities.

## Required direction

- add a UV-owned **Planner contract** that consumes bounded Stage-15 context plus the existing deterministic action catalog;
- a plan must reference stable canonical Project/Scene/Shot/Take/asset/Timeline identities and stable Agent catalog action IDs rather than raw project files or a second Agent graph;
- planning output must be strict, bounded, deterministic/validatable structured data even when a future model proposes it;
- persist **durable Agent Tasks** project-scoped under existing bounded project task storage, without replacing Generation Job/Attempt provenance or ProjectUnitOfWork history;
- tasks must expose explicit dependency/state semantics and survive restart/reopen;
- add **Skills** as reusable bounded procedures/templates/policies that expand only into allowed plan/task/catalog contracts; Skills are not arbitrary shell/Python/provider execution and do not gain a private project-write path;
- task execution must call the existing `AgentHarness` / `AgentActionCatalog` path, which in turn delegates to existing Production/Timeline/Generation authorities;
- preserve Stage-15 policy facts and D-017: planning or a Skill may explain that authorization is required but cannot mint or bypass authorization;
- link plan/task/skill identities into inspectable Agent trace without copying raw provider prompts, secrets, authorization tokens, absolute host paths or provider-private runtime state;
- keep execution bounded and foreground/synchronous enough for this slice to be independently testable; **background Agent workers belong to D-066 layer 4**, not this slice;
- keep functional subagents out of this slice; they are D-066 layer 3 and must consume the Planner/Task/Skill contracts built here.

## Planner contract

The first Planner should produce a bounded structured plan rather than free-form hidden reasoning.

At minimum a plan should carry stable facts such as:

- plan identity and schema version;
- project identity and bounded context digest/reference set;
- bounded user/production goal summary;
- ordered/dependency-aware task identities;
- action ID or Skill ID selected for each executable task;
- canonical target references needed by the task;
- bounded task arguments/inputs or references to reconstruct them;
- explicit dependencies;
- policy/effects facts needed to know whether execution is local/mutating/destructive/long-running/cost-bearing or may require D-017;
- plan status and timestamps needed for durable inspection.

Planner validation must fail closed on:

- unknown action or Skill IDs;
- dependency cycles;
- missing dependencies;
- duplicate task identities;
- non-portable/secret/path-bearing plan payloads;
- a task that attempts to request an authority outside the Stage-15 catalog/Skill boundary.

A future model-backed planner may propose the structured plan, but schema/policy validation remains UV-owned and deterministic.

## Durable Agent Task contract

Agent Tasks are orchestration state, not Generation Jobs and not canonical production truth.

Use a small explicit lifecycle suitable for restart/reopen, for example bounded states equivalent to:

```text
planned -> ready -> running -> succeeded
                   |-> failed
planned/ready ---->|-> cancelled
```

Exact names may be refined in implementation, but transitions must be validated and impossible states rejected.

Required properties:

- project-scoped stable task identity;
- parent plan identity;
- explicit dependency identities;
- action/Skill identity;
- canonical target references;
- durable state/timestamps;
- result references to existing transaction/Job/Attempt/asset/Take/Timeline identities where execution creates them;
- sanitized failure facts;
- restart/reopen readability;
- no hidden retry of external/cost-bearing work: underlying Generation Job idempotency and D-017 remain authoritative.

Do not turn `tasks/` into a second project graph. Task records coordinate work and point back to canonical authorities.

## Skills contract

A Skill is a reusable bounded procedure over known UV actions/tasks, not a plugin with arbitrary execution rights.

The first Skill model should expose stable metadata such as:

- Skill ID and version/schema;
- purpose;
- bounded input contract;
- allowed catalog action IDs and/or validated task templates;
- declared effects/policy envelope derived from its underlying actions rather than invented independently;
- deterministic expansion/validation rules;
- explicit canonical authorities ultimately invoked.

A Skill must not:

- call shell/Python/arbitrary filesystem writes;
- invoke an action absent from the Agent catalog;
- widen D-017 permissions;
- hide remote/non-free execution from policy/trace;
- persist provider secrets/prompts/private caches as Skill state.

Prefer a small built-in Skill set needed to prove the architecture over a large catalog of job-title automations.

## Required proof

Prove at least one bounded multi-step flow such as:

```text
existing modern Studio project
 -> build Stage-15 context for a production target
 -> Planner creates a validated plan with 2+ dependent tasks
 -> persist plan/tasks
 -> reopen from a fresh ProjectStore/Agent runtime instance
 -> determine which task is runnable from dependency state
 -> execute through AgentHarness / existing command authority
 -> mark durable task result with canonical transaction/entity references
 -> unlock and execute the dependent task
 -> trace remains inspectable and linked to plan/task/skill/canonical identities
```

At least one proof should execute a Skill that expands into approved catalog-backed work rather than bypassing the Planner/Task authority.

Also prove negative cases:

- dependency cycles fail closed;
- unknown action/Skill IDs fail closed;
- a blocked task cannot run before dependencies succeed;
- invalid task-state transitions fail;
- planner/Skill cannot request `project.write_file`, shell, Python or arbitrary provider execution;
- unavailable model/capability remains unavailable;
- D-017-required execution still fails without the existing exact one-shot authorization;
- remote/non-free task replay cannot silently duplicate an already-created Generation Job;
- plan/task/Skill records reject secrets, authorization tokens, absolute host paths and arbitrary non-portable state;
- a failed task records failure without marking dependencies or the parent plan falsely successful;
- restart/reopen preserves plan/task state and result references.

## Trace integration

Extend the Stage-15 trace only as needed to reference stable plan/task/Skill identities and task transitions. Do not create a second competing trace store.

The trace should make it possible to answer:

- which plan/task/Skill caused an action;
- what bounded context digest/canonical target it used;
- which catalog action and policy/effects applied;
- which canonical transaction/Job/Attempt/entity resulted;
- why a task failed or remained blocked.

Do not persist hidden model reasoning or complete planner prompts.

## Product Truth boundary

This is still primarily internal Agent infrastructure. Do not claim user-visible autonomous production readiness unless this slice deliberately adds a real Studio surface and D-067 Product Truth/browser proof for that surface.

## JarvisHub boundary

JarvisHub remains a method donor for Planner/Task/Skill factoring only. UV keeps these existing authorities:

- Project Store;
- Production Semantic Core;
- canonical Timeline;
- Studio/Application Commands;
- ProjectUnitOfWork;
- Stage-15 Agent Context / Action Catalog / Policy / Trace;
- Model Registry;
- Job Manager;
- Capability Registry and D-017.

Do not adopt JarvisHub Canvas/node/PostgreSQL/Hono application authority or a parallel Protocol Bridge/tool/permission system.

## Explicitly deferred

The following are **not** part of this slice:

1. functional subagents (`explore`, `plan`, `media`, `critic`) — D-066 layer 3;
2. background Agent work through Job Manager — layer 4;
3. critic/evaluation + dependency-aware local repair — layer 5;
4. human takeover/edit/resume orchestration — layer 6;
5. long-form autonomous production — layer 7;
6. unrelated D-068 desktop updater implementation;
7. a real InfinityEdit/Helios continuation adapter/UI.

## Entry gate

Begin only from lifecycle-closed idle `main` after Stage 15 / PR #69 merge commit `273b5ea8f979cf759cfbf6510e1215a55e98d9c9` is recorded as `last_completed` and `development-context` passes on the closure head.
