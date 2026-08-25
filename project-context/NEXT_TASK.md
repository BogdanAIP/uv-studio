# Next Task

<!-- uv-next-slice: studio-v2-model-registry-job-manager-generation -->

## Goal

After the JarvisHub donor-architecture documentation slice is merged and lifecycle-closed, add the backend-owned user-visible model and long-running generation layer without bypassing the shared production commands or Stage-12 transaction authority.

This slice is also the first implementation consumer of D-066. It must establish the reliability/provenance contracts that the later Agent Harness will depend on, but it must **not** implement the full Agent runtime yet.

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

## Required proof

At minimum prove one bounded flow such as:

```text
modern Studio project + shared Shot
 -> choose named model
 -> construct GenerationContract
 -> create idempotent project-scoped generation Job/Attempt
 -> execute through capability/provider adapter
 -> persist result + model/provider/adapter/contract provenance
 -> register generated media as project-owned Take candidate
 -> accept through shared production command
 -> project to canonical Timeline
 -> undo acceptance without corrupting Job/Attempt/provenance history
```

Also prove a duplicate/replayed generation request cannot create a second expensive execution, and that reusing the same idempotency key for materially different inputs is rejected.

The first implementation may use one local or test adapter; model/provider abstraction must remain explicit enough for later local and optional remote models.

## JarvisHub boundary

D-066 designates JarvisHub as the reference donor for the future Agent Harness. In this slice borrow only the foundations needed now: idempotency, generation constraints, action/effect visibility and traceable Job provenance.

Do **not** vendor JarvisHub, introduce its Canvas-as-source-of-truth, PostgreSQL/Hono application shape, generic node project model, Planner, Memory, Skills or Subagents in this slice. Those Agent Harness layers come after the Job/generation foundation is proven.

## Entry gate

Begin only after `chore/jarvishub-agent-donor-architecture` is merged and lifecycle-closed on idle `main`.
