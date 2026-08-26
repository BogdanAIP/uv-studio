# Next Task

<!-- uv-next-slice: studio-v2-agent-context-command-catalog-trace -->

## Goal

Build the **first bounded UV Agent Harness foundation** now that Stage 14 has proven Models, Jobs, generation provenance, effects metadata and Product Truth.

The slice is `studio-v2-agent-context-command-catalog-trace`. It implements D-066 layer 1 only:

```text
Context Builder
 + canonical command/tool catalog
 + effects/policy inspection
 + inspectable Agent trace
```

It must prove that a future autonomous runtime can observe UV Studio and invoke existing product capabilities without gaining a private project-write path. It must **not** implement Planner/Tasks/Skills/Subagents yet.

## Required direction

- add a UV-owned **Context Builder** that derives bounded Agent context from existing canonical Project/Production/Timeline/Model/Job state rather than copying the whole project/chat;
- reference canonical Project / Scene / Shot / Take / asset / Timeline identities instead of creating a second Agent graph;
- expose one deterministic **command/tool catalog** assembled from existing Studio/Application Commands and approved model/job/capability entry points;
- do not create a JarvisHub-style parallel Protocol Bridge or a second tool registry that competes with Capability Registry/application commands;
- carry existing `CapabilityEffects`, locality/cost/availability and D-017 facts into a small Agent policy projection so the runtime can distinguish read-only, mutating, destructive, long-running, reversible and cost-bearing work;
- keep authorization enforcement in the existing D-017/capability boundary; Agent policy may explain/route a requirement but cannot silently authorize it;
- add an append-only, project-scoped **Agent Trace** that records observations, selected catalog entry, policy decision, command/model/job invocation/result/failure and canonical entity references;
- trace is execution/history evidence, not canonical production truth and not Undo/Redo state;
- prove at least one bounded Agent-harness execution uses the **same existing command/service path** as GUI/script/MCP rather than writing project JSON directly;
- keep Stage-14 Job/Attempt provenance authoritative for long-running generation; trace references Job/Attempt IDs instead of duplicating provider execution history;
- keep context/trace payloads bounded, strict portable JSON and project-relative where applicable;
- preserve restart/reopen readability for persisted trace records;
- use a machine-readable internal contract/test registry where useful instead of heuristic documentation parsing.

## Context Builder contract

The first context projection should be deliberately bounded and reconstructible. At minimum it should be able to expose selected facts such as:

- project identity and Production Direction;
- relevant Scene/Shot/Take identities and current accepted state;
- canonical Timeline revision/summary rather than a full duplicate timeline;
- project-owned media/reference identities relevant to the current target;
- named Model availability and selected capability/offer effects where requested;
- Job/Attempt status/provenance references needed to reason about current work.

Do not persist the whole context snapshot as a second source of truth. Durable trace may record a bounded observation/digest plus explicit canonical references needed for audit/replay reasoning.

## Command/tool catalog contract

Each catalog entry must point to an existing UV-owned execution authority. The catalog should expose stable metadata such as:

- stable action/command identity;
- human-readable purpose;
- input schema or bounded argument contract;
- read-only versus canonical mutation behavior;
- relevant effects/policy facts;
- whether execution may create/use a Job;
- whether D-017 authorization can be required;
- canonical service/command boundary actually invoked.

The catalog itself does not become a new mutation engine.

## Policy boundary

Policy consumes existing facts; it does not invent a second permission system.

At minimum prove:

- safe read-only observation can proceed without mutation authority;
- canonical mutation is routed only through the existing application/domain command;
- unavailable execution remains unavailable;
- remote/non-free execution still reaches D-017 and cannot be self-approved by the Agent;
- destructive/long-running/cost-bearing effects remain inspectable in the trace/policy decision.

## Trace contract

Trace should be project-scoped, append-only and inspectable. A first record model may include:

- trace/run/step identity;
- timestamp;
- bounded observation/context digest;
- canonical entity references;
- catalog action identity;
- policy/effects snapshot;
- command/model/job/capability references;
- result/failure summary;
- links to generated Job/Attempt/asset/Take identities when relevant.

Do not copy complete provider prompts, secrets, host paths or provider-private caches into trace.

## Required proof

Prove a bounded flow such as:

```text
existing modern Studio project
 -> build context for one existing Shot
 -> list/resolve an allowed existing action
 -> inspect effects/policy
 -> invoke one canonical command/service through the Agent Harness seam
 -> canonical project state changes through the normal authority
 -> trace records what happened and references the resulting canonical identities
 -> reopen/reload and read the same trace
```

Also prove negative cases:

- an unknown/unregistered action fails closed;
- the harness cannot request a direct project-file mutation path;
- unavailable capability/model execution is not promoted to available;
- D-017-required work cannot execute without the existing exact authorization;
- trace/context cannot smuggle secrets, absolute host paths or arbitrary non-portable state;
- a failed action leaves an inspectable failure trace without fabricating canonical success.

## Product Truth boundary

Most of this slice is internal infrastructure. Do not invent a user-facing Agent product claim merely to satisfy D-067.

If the slice adds a user-visible trace/context surface, give that surface an appropriate Product Truth record and browser proof. Otherwise mark the infrastructure explicitly internal/not-ready for user-visible Agent autonomy and prove it through deterministic unit/API/integration tests.

## JarvisHub boundary

Use JarvisHub only as a method donor for context/policy/trace structure. UV Studio keeps its existing authorities:

- Project Store;
- Production Semantic Core;
- canonical Timeline;
- Studio/Application Commands;
- ProjectUnitOfWork;
- Model Registry;
- Job Manager;
- Capability Registry and D-017.

Do not vendor JarvisHub or adopt Canvas-as-source-of-truth, generic node project state, PostgreSQL/Hono application authority or a duplicate Protocol Bridge.

## Explicitly deferred

The following are **not** part of this slice:

1. Planner + durable Task graph + Skills;
2. functional subagents (`explore`, `plan`, `media`, `critic`);
3. automatic dependency-aware evaluate/repair loops;
4. human takeover/edit/resume orchestration;
5. long-form autonomous production;
6. D-068 desktop updater implementation;
7. a real InfinityEdit/Helios continuation adapter/UI.

Those begin only after the Context Builder/catalog/policy/trace foundation is merged and lifecycle-closed.

## Entry gate

Begin only from lifecycle-closed idle `main` after PR #68 merge commit `daa9381f45e136f7e406ac29888f8ac597da3f79` is recorded as `last_completed`.
