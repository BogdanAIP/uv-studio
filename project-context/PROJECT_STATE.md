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

The draft now contains the first complete rich-direction vertical path:

1. strict shared `Scene`, `Shot`, `Take` and accepted-take contracts in `production/semantics.json`;
2. micro-drama-only Story, Characters, Locations and per-scene continuity/canon in `production/micro_drama.json`;
3. one serialized `ProductionSemanticService` command boundary for shared semantic mutations, holding the shared Project Store lock across read/modify/commit so concurrent GUI/Agent callers cannot lose updates;
4. explicit HTTP command-handler registry over the same service rather than a direction-private pipeline or growing conditional dispatcher;
5. shared Scene/Shot/Take reuse proven from the commercial direction rather than hidden inside micro-drama;
6. `accept_take` atomically updates accepted Shot state, the accepted project-owned media reference and `timeline/main.json` through Stage-12 `ProjectUnitOfWork`;
7. accepted media provenance supports multiple Shot/Take/Timeline bindings for one reusable project media reference and survives undo/redo exactly;
8. accepted Shot state stores Timeline clip binding without making production state a second timeline;
9. the existing common Studio page now exposes the rich Production panel only for `micro_drama`; other directions keep the shared Studio Core without receiving premature direction UI;
10. Production and the existing Timeline/Undo/Redo UI synchronize through project-level change notifications instead of maintaining independent canonical browser state;
11. core and API proof covers Scene -> Shot -> multiple Takes -> micro-drama context -> accepted Take -> canonical Timeline, durable undo/redo, shared commercial reuse and concurrent semantic commands;
12. a Playwright user-outcome test drives the visible `/projects` and shared Studio UI through direction selection, real-media import, Scene -> Shot -> Take, Story/Character/Location/continuity, acceptance into Timeline, Undo and Redo without using API calls to perform the workflow.

The previous backend/API matrix was green on Ubuntu and Windows before the rich UI was connected. The current exact-head CI is the remaining merge gate; the earlier frontend lint finding was corrected structurally by replacing effect-driven form synchronization with explicit continuity draft hydration.

## Compatibility rule

Recipe/Product Orchestrator/Stage routes remain compatibility code. Stage 13 does not add a RecipeDefinition, Product-Orchestrator graph, numbered Stage workspace, direction-private editor engine or provider-specific domain identity.

Legacy/compatibility projects cannot execute modern direction production commands until they have valid modern Production Direction identity.

## Known intentional limit

Replacing an already accepted Take with another candidate remains an explicit future semantic operation. Stage 13 requires Undo before choosing another accepted Take rather than silently mutating acceptance history.

Model Registry, project-scoped Job Manager and real AI generation are intentionally not part of Stage 13.

## Next handoff

After shared production semantics are green, reviewed, merged and lifecycle-closed, `studio-v2-model-registry-job-manager-generation` should add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the same application-command and transaction authority.
