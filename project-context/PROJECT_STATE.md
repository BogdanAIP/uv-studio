# Project State

<!-- uv-context-state: idle -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository context is **idle** after Commercial Product recovery PR #55 merged as `614cf26f5d45d5e2feb5d627d559ea87bf095ee3`.

Commercial Product now has a truthful preparation-only Product Orchestrator journey over the existing Stage 8 workspace and Project Store media references. It does not claim unsupported advertising generation, final assembly or approval gates.

## Completed Product Truth recovery

The permanent Product Orchestrator now owns the recovered product journeys for Photo to Video, Visualizer, Targeted Edit (`free_project`), Dubbing, Music Video, Narrated Video, General Video, Story Video preparation and Commercial Product preparation. Canonical state remains in Project Store and the existing domain stores; execution/provider boundaries remain governed by Capability Registry/D-017 and editor mutation ownership by D-033.

Commercial Product specifically:

- stores brief/script and media bindings in the existing Stage 8 workspace;
- requires a saved workspace plus at least one verified image/video product reference before preparation is ready;
- verifies SHA-bound current bytes and fails closed when product media is stale or tampered;
- exposes no `render_commercial`, hidden approval completion, provider bypass or parallel advertising workflow store;
- keeps recipe-declared source-review, direction, sample-first, plan and final-review gates non-authoritative until a real audited state contract exists.

## Verification status

Commercial Draft exact head `3d520d5cf972f1988112b248abfcd6b41b65bf12` passed all five permanent checks in run `32655859437`; an isolated Ubuntu browser-suite failure passed on a same-SHA rerun without code changes.

Commercial Review exact head `3d63b5cad8acfc23ba11a0108d59a8ad34c57e52` independently passed all five permanent checks in post-ready run `32657250155` (#2626), including the full browser user-outcome suite on both Ubuntu and Windows, before merge.

Stage 9 remains blocked until the remaining Product Truth reconciliation, Class C cold-start evidence and installed Windows human acceptance are complete. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-recipe-workspace-reconciliation`, defined by `project-context/NEXT_TASK.md`.

The next slice must inventory every creatable recipe against its Product Orchestrator projection and visible workspace routing, remove irrelevant fallback editor/dubbing/continuity leakage for unsupported recipes, keep `free_project` aligned with Targeted Edit, fail closed where no authoritative workflow exists, and synchronize the stale engineering backlog with the actual recovered state.
