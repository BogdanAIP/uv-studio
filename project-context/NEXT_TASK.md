# Next Task

<!-- uv-next-slice: studio-v2-first-real-image-ai -->

## Goal

After `studio-v2-model-registry-job-manager-generation` is reviewed, merged and lifecycle-closed, replace the Stage-14 demo generation binding with the first real named Image AI vertical while preserving the same backend-owned model identity, Job lifecycle, project-media ownership and capability/adapter authorization boundaries.

## Required direction

- choose one real named image model with a supportable local or optional remote execution path;
- register its stable user-visible model identity in the backend Model Registry separately from provider/transport identity;
- expose only the modes/options the selected model actually supports;
- keep connection/runtime configuration in Settings/adapter configuration rather than hiding creative model choice;
- execute through the Stage-14 project-scoped Job Manager and existing Capability/Adapter authorization boundary;
- persist exact selected model, resolved provider/offer, bounded inputs/options and output provenance;
- materialize generated image bytes as a project-owned reference before any production/timeline use;
- expose the generated asset in the shared Studio Media/Inspector flow without provider-specific frontend routing;
- retain explicit user model choice; `Auto` may be additive later but must not replace named-model selection.

## Required proof

At minimum prove:

```text
modern Studio project
 -> choose one real named image model
 -> submit bounded image generation input/options
 -> create and run project-scoped Job
 -> persist resolved model/provider provenance
 -> materialize project-owned image
 -> expose it in shared Studio media state
 -> preserve Job/provenance across reload/archive boundaries
```

If the selected provider is remote or potentially paid, existing one-shot consent/authorization requirements remain mandatory and must not be bypassed by the Job Manager.

## Non-goals

- no second Model Registry in frontend state;
- no provider-specific project schema;
- no new RecipeDefinition/Product-Orchestrator product path;
- no broad multi-provider matrix in this slice;
- no video-model expansion until the image vertical proves the common path.

## Entry gate

Begin only after Stage 14 `studio-v2-model-registry-job-manager-generation` is merged and lifecycle-closed on idle `main`.
