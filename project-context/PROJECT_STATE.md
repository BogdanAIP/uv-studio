# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: studio-v2-micro-drama-production-semantics -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository is idle on `main` after completion of Stage 13:

- completed slice `studio-v2-micro-drama-production-semantics`;
- PR #66 merged as `16409d2d01ce4ca2be3eab61a02a06655650f444`;
- no feature branch is currently active;
- next authorized handoff is `studio-v2-model-registry-job-manager-generation` from `project-context/NEXT_TASK.md`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-033** — canonical Timeline remains UV-owned; MLT remains derived.

A Shot is production meaning, not a Timeline Clip. Direction-specific data may reference shared production identities but must not fork Scene/Shot/Take infrastructure.

## Stage 13 completed

Stage 13 establishes the first complete rich-direction vertical path:

1. strict shared `Scene`, `Shot`, `Take` and accepted-take contracts in `production/semantics.json`;
2. micro-drama Story, Characters, Locations and per-scene continuity/canon extensions in `production/micro_drama.json`;
3. one serialized `ProductionSemanticService` command boundary for shared semantic mutations with shared Project Store locking across read/modify/commit;
4. explicit HTTP semantic command handlers over the same service rather than a direction-private pipeline;
5. cross-direction reuse of shared Scene/Shot/Take contracts proven from the commercial direction;
6. transactional `accept_take` spanning accepted production state, project-owned media provenance and canonical `timeline/main.json` through Stage-12 `ProjectUnitOfWork`;
7. exact project-level Undo/Redo of accepted Take projection without splitting production and Timeline state;
8. support for multiple Shot/Take/Timeline provenance bindings when one project media reference is reused;
9. rich micro-drama Production UI inside the shared Studio page, while other directions keep the common Studio Core without premature direction-specific UI;
10. shared project-change synchronization between Production, Timeline and Undo/Redo controls;
11. core/API coverage for Scene -> Shot -> multiple Takes -> micro-drama context -> accepted Take -> canonical Timeline, concurrency and cross-direction reuse;
12. cross-platform Playwright proof from visible direction selection and real-media import through Scene/Shot/Take, Story/Characters/Locations/continuity, acceptance, Timeline, Undo and Redo.

Final review head `7bf776e4a58cade4706e6a5256e5fc2dcc2f91d0` passed all five permanent CI jobs. Ubuntu and Windows app-baseline both passed frontend lint/build, real-media evidence and the full browser user-outcome suite. A pre-merge Windows-only Music Video test race was traced to an assertion on transient local notification state; the E2E now verifies durable Assembly readiness instead, and the exact review head is green on both platforms.

## Compatibility rule

Recipe/Product Orchestrator/Stage routes remain compatibility code. New Studio modules must not depend on them merely to access neutral project or production services.

Legacy/compatibility projects cannot execute modern direction production commands until they have valid modern Production Direction identity.

Stage 13 adds no RecipeDefinition, Product-Orchestrator graph, numbered Stage workspace, direction-private editor engine, second timeline or provider-specific production identity.

## Known intentional limit

Replacing an already accepted Take with another candidate remains a future semantic operation. Current callers Undo the acceptance before choosing another Take rather than silently rewriting acceptance history.

## Next handoff

`studio-v2-model-registry-job-manager-generation` should add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the same shared Shot/Take application-command and transaction boundaries. Generated output must become project-owned media with explicit model/provider provenance before it can become a Take candidate and later project to the canonical Timeline.
