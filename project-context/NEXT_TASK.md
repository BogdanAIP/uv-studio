# Next Task

<!-- uv-next-slice: studio-v2-application-transactions -->

## Goal

After `architecture-authority-cleanup` is reviewed, merged and lifecycle-closed, harden the **modern Studio application boundary** and add one atomic transaction/undo authority before rich Production Direction state or long-running AI integration grows on top of it.

The slice must not be interpreted narrowly as “timeline undo”. The architecture audit found recipe-era seams inside otherwise-modern Studio code; they must be corrected before Project Unit of Work is made authoritative.

## Entry prerequisites — modern Studio boundary

1. **Protect Production Direction identity.** Introduce a typed/validated Studio metadata contract for `product_model=production_directions` + known `direction_id`. Its schema version must version that metadata contract itself; do not use a version number merely because the product is called “Studio v2”.
2. **Distinguish modern identity from legacy compatibility.** A modern Studio project must have valid direction identity. A legacy recipe or pre-D-064 Studio project may remain readable/editable through an explicit compatibility classification, but direction-specific domain commands must not silently treat it as a modern direction project. Any later upgrade/direction change is an explicit semantic migration operation.
3. **Make identity classification backend-owned.** Current `/projects` UI infers “Studio” from `recipe_id == studio_v2` or the mere presence of an `extensions.studio` object. Replace that guess with a validated server/application projection such as modern-direction / legacy-compatibility / invalid-recovery status. Frontend code must not decide canonical product identity by reparsing arbitrary extensions JSON.
4. **Prevent arbitrary generic mutation of Studio identity.** Generic project PATCH/import compatibility paths must not silently replace/corrupt modern direction identity.
5. **Decouple modern Studio API from recipe/orchestrator imports.** `studio_timeline.py` and `project_media.py` currently import neutral payload/store helpers from `api/projects.py`, whose import graph pulls Recipe Registry and `orchestration.catalog`. Extract neutral project API schemas/dependencies or otherwise make modern Studio/media modules recipe-free.
6. **Remove legacy creation defaults from the core foundation.** `ProjectStore.create_project()` must not silently default to `general_video`; compatibility callers pass legacy identity explicitly. Generic recipe-create/execution-plan client/server surfaces are explicitly compatibility-only so new GUI/Agent/scripts/MCP code cannot accidentally adopt them.
7. **Reserve a bounded production-state layout.** Establish a deliberate project-owned production/domain root or equivalent storage contract suitable for D-065 shared Scene/Shot/Take documents and direction extensions; do not misuse `tasks/`, Timeline files or generic `project.json.extensions` as the long-term semantic store.
8. Preserve old projects/imports and legacy workflow routes until caller/dependency proof permits removal. This is boundary isolation, not a destructive rewrite.

## Project Unit of Work / undo-redo

After the boundary above is explicit:

- introduce a file-first `ProjectUnitOfWork` or equivalent UV-owned transaction boundary for coordinated project metadata, shared production-semantic documents, direction extensions, asset/reference, generation/take and Timeline mutations;
- give application/domain commands durable transaction identity suitable for undo/redo without making MLT state canonical;
- prove at least one representative cross-document transaction, not only isolated timeline edits;
- keep GUI, Agent, scripts and MCP on the same semantic command handlers;
- replace growing command/API `if/elif` dispatch with explicit handlers/registries where this slice touches the boundary;
- preserve Project Store path/integrity/archive/portable-state rules;
- keep Production Direction identity separate from execution/provider/model selection;
- keep recipe/Product Orchestrator/Stage 8 paths compatibility-only and do not grow them;
- do not add cloud/provider integration or hide model choice in transaction infrastructure.

## Required proof

The slice is complete when all of the following are true:

- a valid modern Studio project has one parseable known Production Direction identity across create/load/archive round-trip;
- malformed/unknown/tampered modern Studio identity fails closed and is not mislabeled by the frontend;
- an explicit legacy compatibility project can remain readable without being assigned a fake direction, while direction-specific commands reject/require migration;
- modern Studio/media API modules no longer require recipe/Product-Orchestrator imports merely to access neutral project services;
- core Project Store creation cannot accidentally choose `general_video` through an implicit default;
- shared production/domain storage has a bounded, versionable Project Store home suitable for D-065 semantics;
- a representative semantic production operation coordinates multiple canonical project-owned documents atomically;
- injected failure/validation failure leaves no split state;
- undo/redo uses the same UV-owned application authority as programmatic callers;
- MLT remains a derived engine representation.

A suitable transaction proof should model the later shared semantic operation:

```text
AcceptTake(shot_12_3, take_4)
 -> accepted Take
 -> shared Shot state
 -> project asset/reference
 -> canonical Timeline clip/projection
 -> undo transaction
```

## Following direction

After this foundation is green, use **micro-drama** as the first rich Production Direction to prove D-065 shared production primitives: Scene/Shot/Take plus direction extensions for Story/Characters/Locations/continuity. Micro-drama must not own a private Shot/Take system; later commercial/music/dub-battle directions reuse the common contracts.

Then add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the same Studio commands/transactions.

## Entry gate

Begin only from idle `main` after PR #64 `architecture-authority-cleanup` is merged and lifecycle-closed. Do not start from archived PR #59, merged PR #61/#63 branches, or a recipe/Product-Orchestrator compatibility branch.
