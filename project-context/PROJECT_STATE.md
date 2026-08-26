# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-agent-context-command-catalog-trace -->

**Updated:** 2026-08-26

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Stage 15 is active in review on branch `stage-15/agent-context-command-catalog-trace`, created from lifecycle-closed `main` commit `ff644f3bfc9cbf27b13d6742207951dfb0470cf2`, with PR #69 ready for review.

Goal: deliver only the first bounded Agent Harness layer from D-066 — canonical Context Builder, catalog over existing UV command/model/job/capability authorities, effects/policy projection, append-only inspectable trace and one bounded execution seam through the existing application authority.

Stage 14 / PR #68 merged as `daa9381f45e136f7e406ac29888f8ac597da3f79` and was lifecycle-closed to idle before this branch was created. Planner, durable Tasks, Skills, subagents, background Agent orchestration, evaluation/repair and long-form autonomy remain out of scope.

Implementation/refinement head `6cf999203e17d458914ec1b248c29bc097bf45c0` passed all five permanent CI jobs, including browser E2E on Ubuntu and Windows. The review-state head must independently pass the same exact-head gate before merge, with no unresolved review threads.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-066** — JarvisHub is the Agent Harness architecture/method donor; UV retains canonical project/application authority.
- **D-067** — Product Truth Contract/current-document consistency.
- **D-068** — desktop in-place updates remain accepted Stage-9 release work.
- **D-069** — sequential generative continuation persists provider-neutral media lineage while provider cache/latent/session state remains adapter-private.
- **D-033** — canonical Timeline/editor foundation.
- **D-017** — exact one-shot authorization for remote/non-free execution.

## As-built foundation through Stage 14

Stages 12–14 provide the lower production and generation spine consumed by this slice:

1. typed Production Direction identity and bounded project/production storage;
2. shared `Scene`, `Shot`, `Take` and accepted-Take semantics across directions;
3. `ProductionSemanticService` as the shared production mutation boundary;
4. canonical Timeline plus `ProjectUnitOfWork` prepared journal, rollback/recovery and durable project Undo/Redo;
5. transactional accepted-Take projection into Timeline while preserving project media provenance;
6. backend-owned user-visible Model Registry above capability/provider transport;
7. project-scoped durable generation Job/Attempt records under the existing `tasks/` authority;
8. exact idempotency and durable retry/failure history;
9. D-017 exact authorization for remote/non-free execution;
10. provider-neutral `GenerationContract`, including feature-gated D-069 continuation parent lineage;
11. generated output becomes project-owned media and a shared Take candidate before semantic acceptance;
12. resolved `CapabilityEffects` are available through the existing Capability Registry for Agent policy/trace projection;
13. the first machine-readable Product Truth record binds the named-generation domain/API/frontend/state/evidence path;
14. cross-platform browser proof covers named generation -> Take candidate -> acceptance -> canonical Timeline -> Undo while Job provenance remains durable.

## Stage-15 as-built bounded contracts

This slice does not create another project, command, tool, model or permission authority.

### Context Builder

A compact deterministic observation is built from canonical Project, Production, Timeline, Model Registry and Job Manager state. Context references canonical identities and bounded summaries rather than copying arbitrary project files, provider prompts, secrets, absolute host paths or provider-private runtime state.

### Existing-command/tool catalog

Stable Agent-facing action metadata resolves only to existing UV-owned services. Production and Timeline mutations continue through their existing command services; named generation continues through the existing generation/model/job/capability stack. Catalog metadata includes the canonical authority, bounded input fields, effects, whether a model is required, whether the action uses Job Manager and whether D-017 authorization may be required. Unknown actions fail closed.

### Effects / policy

Policy consumes existing `CapabilityEffects`, offer availability/locality/cost and D-017 authorization facts. It projects those facts for inspection but does not create a second permission system or allow the Agent to self-authorize remote/non-free work.

### Inspectable trace

Append-only project-scoped trace records are persisted under existing bounded project task storage. Trace links context/input digests, canonical identities, action/policy/effects, invocation outcome and Job/Attempt/transaction references. Trace is execution history rather than canonical production state and rejects authorization tokens, secret material, absolute host paths and arbitrary non-portable state.

### Bounded execution proof

Agent Harness execution uses the same existing semantic command/service boundaries as other callers. Successful canonical mutations return the existing transaction/Job identity into trace; failed existing commands and unknown actions leave inspectable failure trace without fabricating canonical success. Unavailable generation remains unavailable before Job creation, and remote/non-free generation still requires exact D-017 authorization.

## Explicit non-goals still in force

- no Planner or durable Agent Task graph;
- no Skills runtime;
- no functional subagents (`explore`, `plan`, `media`, `critic`) yet;
- no Agent-only project write path;
- no duplicate JarvisHub-style tool registry or protocol bridge;
- no automatic background Agent replay through Job Manager;
- no evaluation/repair loop or long-form autonomy;
- no provider-private cache/latent/session state in Project Store;
- no desktop Update Service/UI implementation;
- no claim that a real continuation-capable provider is integrated;
- no new user-facing Agent readiness claim unless a real Studio surface and D-067 evidence are added.

## Active slice

`studio-v2-agent-context-command-catalog-trace`

```text
canonical Project / Production / Timeline / Model / Job observation
 -> UV-owned Context Builder
 -> deterministic catalog over existing UV authorities
 -> effects / policy projection
 -> bounded execution through existing service
 -> append-only inspectable project trace
```

The current `project-context/NEXT_TASK.md` remains the exact scope contract for this active review until the slice is merged and lifecycle-closed.
