# Next Task

<!-- uv-next-slice: studio-v2-model-registry-job-manager-generation -->

## Goal

After `studio-v2-micro-drama-production-semantics` is reviewed, merged and lifecycle-closed, add the backend-owned user-visible model and long-running generation layer without bypassing the shared production commands or Stage-12 transaction authority.

## Required direction

- add a user-visible Model Registry whose canonical model identity is separate from capability/provider transport;
- add a project-scoped Job Manager for queued/running/succeeded/failed/cancelled long-running work and durable provenance;
- implement the first named AI generation path against an existing shared Shot/Take workflow rather than a provider-private project model;
- preserve meaningful model choice in GUI/Agent/script/MCP callers;
- materialize generated media as project-owned references before it can become an accepted Take;
- keep acceptance and Timeline projection on the existing `ProductionSemanticService` / `ProjectUnitOfWork` path;
- do not turn Capability Registry, provider names, RecipeDefinition, Product Orchestrator or frontend state into product authority.

## Required proof

At minimum prove one bounded flow such as:

```text
modern Studio project + shared Shot
 -> choose named model
 -> create project-scoped generation Job
 -> execute through capability/provider adapter
 -> persist result + model/provider provenance
 -> register generated media as project-owned Take candidate
 -> accept through shared production command
 -> project to canonical Timeline
 -> undo acceptance without corrupting Job/provenance history
```

The first implementation may use one local or test adapter; model/provider abstraction must remain explicit enough for later local and optional remote models.

## Entry gate

Begin only after PR #66 `studio-v2-micro-drama-production-semantics` is merged and lifecycle-closed on idle `main`.
