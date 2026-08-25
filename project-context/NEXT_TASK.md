# Next Task

<!-- uv-next-slice: studio-v2-application-transactions -->

## Goal

After `architecture-authority-cleanup` is reviewed, merged and lifecycle-closed, harden the **modern Studio application boundary** and add one atomic transaction/undo authority before rich Production Direction state or long-running AI integration grows on top of it.

The slice must not be interpreted narrowly as “timeline undo”. The current audit found several recipe-era seams inside otherwise-modern Studio code; they must be corrected as part of establishing the application transaction boundary.

## Entry prerequisites — modern Studio boundary

Before building cross-document undo/redo, make the modern project identity and dependency direction trustworthy:

1. **Protect Production Direction identity.** Introduce a typed/validated Studio project metadata boundary (or equivalent) for `product_model=production_directions` + known `direction_id`. Modern Studio loads/commands must fail closed on malformed/unknown Studio identity rather than accepting arbitrary `extensions.studio` JSON.
2. **Prevent arbitrary generic mutation of Studio identity.** The generic project PATCH/import compatibility path must not silently replace/corrupt modern direction identity. A future direction change, if supported, is an explicit semantic migration command, not an arbitrary extensions patch.
3. **Decouple modern Studio API from recipe/orchestrator imports.** `studio_timeline.py` currently imports neutral payload/store helpers from `api/projects.py`, whose import graph pulls Recipe Registry and `orchestration.catalog`. Extract neutral project API schemas/dependencies or otherwise make modern Studio modules recipe-free.
4. **Remove legacy creation defaults from the core foundation.** `ProjectStore.create_project()` must not silently default to `general_video`; compatibility callers should pass legacy identity explicitly. The generic recipe-create API/client should be clearly isolated as compatibility so new Agent/scripts/UI code cannot accidentally adopt it as the modern contract.
5. Preserve old projects/imports and legacy workflow routes until caller/dependency proof permits removal. This is boundary isolation, not a destructive rewrite.

## Project Unit of Work / undo-redo

After the boundary above is explicit:

- introduce a file-first `ProjectUnitOfWork` or equivalent UV-owned transaction boundary for coordinated project, production-document, asset/reference, generation/take and timeline mutations;
- give Studio application/domain commands durable transaction identity suitable for undo/redo without making MLT state canonical;
- prove at least one representative cross-document transaction, not only isolated timeline edits;
- keep GUI, Agent, scripts and MCP on the same semantic command handlers;
- replace growing command/API `if/elif` dispatch with explicit handlers/registries where this slice touches the boundary;
- preserve Project Store path/integrity/portable-state rules;
- keep Production Direction identity separate from execution/provider/model selection;
- keep recipe/Product Orchestrator/Stage 8 paths compatibility-only and do not grow them;
- do not add cloud/provider integration or hide model choice in transaction infrastructure.

## Required proof

The slice is complete when all of the following are true:

- a valid Studio project has one parseable known Production Direction identity across create/load/archive round-trip;
- malformed/unknown/tampered Studio identity fails closed on modern Studio operations;
- modern Studio API/application modules no longer require recipe/Product-Orchestrator imports merely to access neutral project services;
- core Project Store creation cannot accidentally choose `general_video` through an implicit default;
- a representative semantic production operation coordinates multiple canonical project-owned documents atomically;
- injected failure/validation failure leaves no split state;
- undo/redo uses the same UV-owned application authority as programmatic callers;
- MLT remains a derived engine representation.

A suitable transaction proof may use a small bounded production record plus asset/reference and timeline mutation, modeling the later operation:

```text
AcceptTake(shot_12_3, take_4)
 -> accepted take / Shot state
 -> project asset/reference
 -> Timeline clip
 -> undo transaction
```

## Following direction

After this foundation is green, establish the first real direction-domain vertical: **micro-drama** with bounded Story / Characters / Locations / Scenes / Shots / Takes state and continuity hooks. Then add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the same Studio commands/transactions.

## Entry gate

Begin only from idle `main` after PR #64 `architecture-authority-cleanup` is merged and lifecycle-closed. Do not start from archived PR #59, merged PR #61/#63 branches, or a recipe/Product-Orchestrator compatibility branch.
