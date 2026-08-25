# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-micro-drama-production-semantics -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Active Stage 13 rich-production slice:

- slice `studio-v2-micro-drama-production-semantics`;
- branch `stage-13/studio-v2-micro-drama-production-semantics`;
- draft PR #66;
- base idle `main` at `84dca67a0db261f84343e18a52762bfc230d0167`;
- last completed Stage 12 / PR #65, merge `3b87aa0f0d0636bd7d410c8a9212aded8ec7c7be`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-033** — canonical Timeline remains UV-owned; MLT remains derived.

A Shot is production meaning, not a Timeline Clip. Direction-specific data may reference shared production identities but must not fork Scene/Shot/Take infrastructure.

## Stage 13 implementation state

The draft now contains the first complete backend vertical path:

1. strict shared `Scene`, `Shot`, `Take` and accepted-take contracts in `production/semantics.json`;
2. micro-drama-only Story, Characters, Locations and per-scene continuity/canon in `production/micro_drama.json`;
3. one `ProductionSemanticService` command boundary for shared semantic mutations;
4. shared Scene/Shot/Take reuse proven from the commercial direction rather than hidden inside micro-drama;
5. `accept_take` atomically updates accepted Shot state, the accepted project-owned media reference and `timeline/main.json` through Stage-12 `ProjectUnitOfWork`;
6. accepted Shot state stores Timeline clip binding without making production state a second timeline;
7. recipe-neutral Studio HTTP routes expose the same semantic handlers;
8. core and API proof covers Scene -> Shot -> multiple Takes -> micro-drama context -> accepted Take -> canonical Timeline plus durable undo/redo.

CI and review hardening are still required before this slice can move from draft to review.

## Compatibility rule

Recipe/Product Orchestrator/Stage routes remain compatibility code. Stage 13 does not add a RecipeDefinition, Product-Orchestrator graph, numbered Stage workspace, direction-private editor engine or provider-specific domain identity.

Legacy/compatibility projects cannot execute modern direction production commands until they have valid modern Production Direction identity.

## Next handoff

After shared production semantics are green and merged, `studio-v2-model-registry-job-manager-generation` should add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the same application-command and transaction authority.
