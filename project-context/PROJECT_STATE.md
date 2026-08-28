# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: architecture-compression-inventory -->

**Updated:** 2026-08-28

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is in draft for `architecture-compression-inventory` on branch `research/architecture-compression-inventory`, starting from lifecycle-closed `main` merge `e6d23e9444023c0c491ae0800d6aac01d415968c`.

Stage 18 `studio-v2-agent-background-execution` remains the last completed product/Agent slice, merged through PR #75 as `c5051b975a1ba8e747f453dd0a485cac1e308ba7` and lifecycle-closed through PR #76.

## Accepted Stage 18 baseline

D-066 layer 4 bounded background Agent execution remains accepted infrastructure. The architecture-compression inventory must not weaken or bypass its cross-runtime project mutation fence, Generation idempotency/D-017 reservation guarantees, exact canonical freshness checks, background-worker ownership, or recovery semantics.

## Active product-first slice

D-070 requires a behavior-preserving inventory before further D-066 Agent-autonomy work.

This slice maps the overlapping legacy and modern product-composition paths across backend, API, frontend, tests, documentation and persisted-project compatibility. It covers at least:

- `uv_studio/recipes/**` and Recipe Registry;
- `uv_studio/orchestration/**` and Product Orchestrator;
- `/api/uv/recipes`;
- `/api/uv/projects/{project_id}/execution-plan`;
- Stage 6/8 workspace/API/frontend compatibility surfaces;
- server compatibility routes, including donor-era metadata where still mounted;
- schema-v1 `recipe_id` and typed Studio identity compatibility;
- dubbing, targeted edit, continuity and music responsibilities that must be separated from obsolete product composition without deleting useful domain state.

The inventory uses the existing **KEEP / ADAPT / MOVE / LEGACY / DELETE LATER** vocabulary. It names the canonical replacement and proof-before-removal gate for every non-KEEP item, records a no-new-caller rule for superseded composition, and proposes bounded retirement/extraction PRs rather than a big-bang rewrite.

## Current canonical destination

Modern product composition is owned by Production Directions over the shared Studio core. Production Directions are not execution pipelines: all directions share Project Store, Studio shell, Scene/Shot/Take semantics, canonical Timeline, Studio/Application Commands, Model/Generation Job authority and Capability/D-017 boundaries.

Reusable operations such as dubbing, targeted edit, continuity and music assistance remain domain tools/capabilities where useful; they are not to survive as parallel product engines merely because legacy orchestration still calls them.

## Golden vertical gate

The first named user-visible proof remains:

`New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`

The inventory does not implement this vertical. It must state the caller/migration work required so GUI and Agent, when Agent is invoked, use the same application/domain commands and Generation authority as scripts/MCP.

## Known implementation risk observed during closure CI

Windows browser E2E exposed a timing-sensitive remount race in the production form: `ProductionWorkspacePanel` keys `ProductionSemanticsPanel` by history cursor, so a post-command history refresh can remount the panel and discard form input entered before the refresh settles. The closure PR did not modify runtime behavior; its final exact SHA passed the permanent checks on the successful rerun. This risk is not part of the inventory write scope and must not be silently fixed in this behavior-preserving slice.

## Handoff

The provisional next bounded slice is `donor-ui-retirement`: remove only donor Workflow/Pipeline/Sandbox/stage UI that the accepted inventory proves has no supported route/import/runtime caller. The inventory must replace this handoff before review if the caller map disproves that it is the safest first retirement.

D-066 layers 5-7 remain deferred until both D-070 gates are satisfied.
