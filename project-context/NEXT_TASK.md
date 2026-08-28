# Next Task

<!-- uv-next-slice: architecture-compression-inventory -->

## Goal

Perform a **behavior-preserving architecture-compression inventory** immediately after `studio-v2-agent-background-execution` is reviewed, merged and lifecycle-closed.

This slice changes the development order before D-066 layer 5. It must identify the exact live callers, compatibility-only paths, canonical replacements and safe retirement criteria for the overlapping legacy product architecture before any further Agent-autonomy layer is added.

## Required direction

- do not add new Agent capabilities, schedulers, repair loops, providers or product surfaces in this slice;
- inventory `uv_studio/recipes/**`, `uv_studio/orchestration/**`, `api/recipes.py`, `api/execution.py` / `/execution-plan`, Stage 6/8 workspace/API/frontend surfaces, server compatibility routes and schema-v1 `recipe_id` usage;
- map backend, API, frontend, tests, docs and persisted-project compatibility callers for every legacy path;
- classify each path using the existing architecture vocabulary: **KEEP**, **ADAPT**, **MOVE**, **LEGACY**, or **DELETE LATER**;
- for every **MOVE**, **LEGACY** or **DELETE LATER** item, name the canonical replacement authority and the proof required before removal;
- distinguish canonical project/domain state from legacy workflow/orchestration code in dubbing, targeted edit, continuity and music paths so useful state is not deleted with obsolete composition logic;
- make Production Directions + Shared Production Semantic Core + Studio/Application Commands + Generation/Capability authorities the destination for modern callers;
- keep contextual operations such as dubbing, targeted edit, continuity and music assistance as tools/capabilities rather than separate product engines;
- record an explicit no-new-caller rule for Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 6/8 workspace composition and other superseded product identities;
- preserve the accepted Stage-18 cross-runtime mutation fence, Generation idempotency and background recovery guarantees while inventory work proceeds;
- prefer reducing or merging documentation/process machinery over adding another parallel architecture-description system.

## Required proof

At minimum produce:

- an exact caller/migration table for every targeted legacy path;
- a canonical replacement for every modern caller that still depends on legacy product composition;
- explicit persisted-project migration/compatibility requirements for schema-v1 `recipe_id` and any other durable legacy identity;
- deletion gates that prevent removal while a supported runtime/frontend/project-migration caller remains;
- a proposed PR sequence for retirement/extraction with disjoint responsibilities and no big-bang rewrite;
- a named first user-visible golden vertical: `New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`;
- confirmation that Agent execution for that vertical uses the same application/domain commands and Generation authority as GUI/scripts/MCP rather than a private Agent path;
- no production behavior change from the inventory slice itself;
- all permanent repository checks still green.

## Product gate before further D-066 autonomy

D-066 remains the target Agent architecture, and accepted Stage 18 remains useful infrastructure. However, layers 5-7 are deferred until both gates below are satisfied:

1. **Architecture compression gate:** the legacy/modern overlap has an accepted caller map and migration sequence, no new callers are added to superseded product composition, and high-risk duplicate authorities have an executable retirement path.
2. **Golden vertical gate:** one real Studio workflow proves the canonical product path through GUI from project creation to export, with Agent using the same commands/models/jobs when invoked.

Passing the inventory slice does not by itself satisfy either gate; it defines the exact work and evidence needed to satisfy them.

## Explicitly deferred

- actual deletion of Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 6/8 UI/API or donor-era runtime paths;
- semantic refactoring/renaming of `stage16_*` / `stage17_*` Agent modules;
- contextual-tool extraction for dubbing, targeted edit, continuity and music;
- Product Truth validator/process simplification;
- implementation of the `micro_drama` golden vertical where missing;
- D-066 layer 5 evaluation/repair;
- D-066 layer 6 takeover/edit/resume;
- D-066 layer 7 long-form autonomy;
- unrelated desktop updater work.

## Entry gate

Begin only from lifecycle-closed `main` after PR #75 Stage 18 is accepted. Stage-18 guarantees remain part of the baseline; this reprioritization does not discard or bypass its review findings, CI requirements or recovery/concurrency protections.
