# Next Task

<!-- uv-next-slice: studio-v2-model-registry-job-manager-generation -->

## Goal

After the current architecture documentation slice is merged and lifecycle-closed, add the backend-owned user-visible model and long-running generation layer without bypassing the shared production commands or Stage-12 transaction authority.

This slice is the first implementation consumer of D-066 and D-067. It must establish the reliability/provenance contracts that the later Agent Harness will depend on **and** prove the user-visible path across backend, frontend and E2E. It must **not** implement the full Agent runtime yet.

## Required direction

- add a user-visible Model Registry whose canonical model identity is separate from capability/provider transport;
- add a project-scoped Job Manager for queued/running/succeeded/failed/cancelled long-running work and durable generation-attempt provenance;
- make long-running/cost-bearing/external generation retry-safe through a UV-native idempotency contract derived from the JarvisHub reference pattern;
- add a bounded provider-neutral `GenerationContract` for semantic constraints that must survive provider-specific prompt/option rendering;
- implement the first named AI generation path against an existing shared Shot/Take workflow rather than a provider-private project model;
- preserve meaningful model choice in GUI/Agent/script/MCP callers;
- materialize generated media as project-owned references before it can become a Take candidate or accepted material;
- keep acceptance and Timeline projection on the existing `ProductionSemanticService` / `ProjectUnitOfWork` path;
- expose enough capability/application-command effects metadata for later Agent policy/trace use without creating a second JarvisHub-style tool registry;
- keep generation Job/Attempt history separate from semantic Take acceptance so Undo of acceptance does not erase generation provenance;
- add the first machine-readable D-067 Product Truth Contract for the named-model generation feature, binding canonical command/API, Studio UI entry, state/dependencies and E2E proof;
- expose truthful UI states for model choice, queued/running/succeeded/failed/cancelled generation and generated Take-candidate result;
- ensure the feature is not marked ready if backend/API exists without the declared Studio surface or if the frontend advertises a path that is not wired to canonical backend behavior;
- do not turn Capability Registry, provider names, RecipeDefinition, Product Orchestrator, frontend state or a JarvisHub Canvas/node model into product authority.

## Required contracts

### Model identity

A named model is a user-visible creative/execution choice owned by the backend Model Registry. Provider/adapter/capability offers are execution mappings beneath it.

### Job + attempt identity

A Job is project-scoped durable long-running work. A generation Attempt records the exact named model, provider/adapter mapping, normalized inputs, Generation Contract, status, output/failure and provenance.

Retrying infrastructure must not accidentally become a new creative Attempt.

### Idempotency

For the first generation path prove at minimum:

- an idempotency key is bound to a stable normalized request/context digest;
- the digest includes project/semantic target, named model, selected execution mapping and generation inputs/contract;
- same key + different normalized request fails closed as a conflict;
- an equivalent request already running is not executed twice;
- a succeeded equivalent request returns/reuses the recorded result instead of launching duplicate expensive work;
- failure/retry history remains inspectable and distinct from deliberately starting a new creative attempt.

Idempotency does not replace D-017 authorization. A retry/replay must not silently widen remote/cost permission.

### Generation Contract

The first bounded schema should support provider-neutral equivalents of:

- fixed constraints that must remain stable;
- one or more explicitly editable variables;
- forbidden semantic changes;
- approved project reference/keyframe identity where applicable.

The contract references canonical UV project/production identities where possible; adapters render it into provider-specific prompts/options. Do not store provider prompt text as the semantic source of truth.

### Effects metadata

Reuse/extend the current capability/application-command metadata rather than introduce a parallel Protocol Bridge. Make relevant effects inspectable where applicable, including project mutation, Timeline mutation, media generation, destructive behavior, long-running behavior, reversibility and cost-bearing execution.

### Product Truth Contract

The first contract should identify at minimum:

- stable generation `feature_id` and readiness;
- canonical application/domain command/query;
- backend/API surface;
- Studio frontend entry point and named-model control;
- Job/Attempt/generated-asset/Take-candidate state involved;
- capability/model/authorization dependencies;
- visible progress/failure/result semantics;
- browser E2E proof identifier.

The contract is verification metadata only; it does not become another runtime feature registry or state authority.

## Required proof

At minimum prove one bounded flow such as:

```text
modern Studio project + shared Shot
 -> choose named model in Studio UI
 -> construct GenerationContract
 -> create idempotent project-scoped generation Job/Attempt
 -> expose queued/running state
 -> execute through capability/provider adapter
 -> persist result + model/provider/adapter/contract provenance
 -> register generated media as project-owned Take candidate
 -> show candidate/result in Studio UI
 -> accept through shared production command
 -> project to canonical Timeline
 -> undo acceptance without corrupting Job/Attempt/provenance history
```

Also prove:

- a duplicate/replayed generation request cannot create a second expensive execution;
- reusing the same idempotency key for materially different inputs is rejected;
- the Product Truth Contract resolves to real backend/frontend/test references;
- the browser E2E begins from the visible Studio surface rather than manual API calls or test-only state seeding.

The first implementation may use one local or test adapter; model/provider abstraction must remain explicit enough for later local and optional remote models.

## JarvisHub boundary

D-066 designates JarvisHub as the reference donor for the future Agent Harness. In this slice borrow only the foundations needed now: idempotency, generation constraints, action/effect visibility and traceable Job provenance.

Do **not** vendor JarvisHub, introduce its Canvas-as-source-of-truth, PostgreSQL/Hono application shape, generic node project model, Planner, Memory, Skills or Subagents in this slice. Those Agent Harness layers come after the Job/generation foundation is proven.

## Product Truth boundary

D-067 requires this new user-visible generation feature to land as one coherent product capability. Backend-first or frontend-first intermediate commits are acceptable while the slice is draft, but the review/merge state must not contain a declared-ready backend/frontend parity gap.

The architecture/documentation for the slice must describe as-built behavior accurately at review time rather than leave completed work phrased as future target work.

## Desktop update boundary

D-068 is accepted architecture but is **not** implementation scope for this generation slice. Update UI/Service, in-place installer replacement and N-1 -> N packaged upgrade proof remain Stage-9 desktop productization work.

## Entry gate

Begin only after `chore/jarvishub-agent-donor-architecture` is merged and lifecycle-closed on idle `main`.
