# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-workspace-routing -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-workspace-routing` is the active Draft slice on branch `fix/product-recovery-workspace-routing`, created from the explicit idle `main` after PR #44.

The slice is intentionally narrow: migrate Visualizer to the existing Product Orchestrator contract and make `relevant_workspaces` authoritative for Photo → Video and Visualizer project pages. It does not add a second workflow store, does not remount legacy VideoClaw runtime, and does not grow generic NLE functionality.

PR #44 completed the D-033 conformance audit, reaffirmed the accepted editor foundation and repaired the accepted-edit mutation bypass. Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Product definition

UV Studio remains a desktop/local-first video **production and editing workspace** with task-specific workflows:

- Project Store/domain state is canonical;
- Product Orchestrator projects readiness, prerequisites, relevant workspaces and semantic next actions;
- UV semantic/domain commands own mutations;
- Capability Registry owns provider/runtime offers and D-017 authorization;
- FFmpeg, MLT, local ML, MCP and remote providers remain bounded implementations behind those contracts.

## Accepted editor foundation — D-033

D-033 remains binding and is not reopened by this slice:

- UV Studio owns canonical project/edit/domain state and semantic mutations;
- MLT remains the bounded timeline/editing engine representation where mapped;
- OpenCut Classic remains a selective MIT editor-UX/component donor;
- current FFmpeg accepted-edit export remains authoritative until parity evidence promotes another renderer;
- meaningful editor mutations converge on UV-owned semantic/domain command boundaries.

## Product Orchestrator state before this slice

### Photo → Video

Photo → Video is the first migrated deterministic journey:

- verified project-owned images satisfy the source prerequisite;
- local/free `video.compose_photos` availability determines executable readiness;
- `compose_photos` delegates through the existing capability execution boundary;
- `photo_composition` is projected through `relevant_workspaces`;
- damaged or substituted source bytes fail closed.

### Visualizer

Visualizer has a real deterministic local `audio.visualize` capability and produces `audio_visualizer_render` artifacts, but it is not yet a Product Orchestrator journey:

- `project_workflow_state()` returns generic `partial/workflow_not_migrated`;
- `Stage8MediaPanel` invokes the visualizer capability through a direct frontend helper instead of a workflow action;
- the project page chooses the Visualizer panel by `recipe_id` rather than projected workspace;
- because every non-photo project receives generic panels, Visualizer also exposes Project Editor, Continuity and Dubbing surfaces that are irrelevant to its task.

This is the concrete product-routing defect addressed by the active slice.

## Active slice target

The maintained direction is:

1. project Visualizer readiness from verified project-owned audio plus local/free `audio.visualize` availability;
2. expose structured audio/capability prerequisites, an `audio_visualizer` relevant workspace and one semantic render action;
3. execute that action through the existing capability/D-017 boundary rather than calling the adapter directly from product UI;
4. make the project page mount both deterministic migrated workspaces from `workflow.relevant_workspaces`;
5. suppress generic editor/continuity/dubbing panels for any project whose Product Orchestrator declares its dedicated workspace;
6. leave all non-migrated recipes `partial` at the Orchestrator boundary and preserve their existing domain code until later slices;
7. prove source-integrity blocking, setup/unavailable state, successful local result and absence of irrelevant specialist panels with focused API/browser tests.

No new orchestration persistence is permitted. `ProjectWorkflowState` remains a projection over canonical project/domain/capability state.

## Remaining product gaps outside this slice

- targeted existing-video edit, dubbing and music video still need product-level Orchestrator journeys that progressively disclose their existing durable domain state;
- Narrated and General Video do not yet have complete current user journeys;
- recipe selection on `/projects` remains readiness-blind before creation;
- legacy pipeline/workflow source remains compiled migration debt even though normal navigation no longer exposes it;
- Class C cold-start UI-only evidence and installed Windows human acceptance remain future Product Truth Gate requirements.

## Verification policy

The slice must preserve the existing full CI matrix on Ubuntu and Windows. Focused proof must cover Visualizer readiness/prerequisites, strict action input, local-free capability dispatch, verified source bindings and browser workspace isolation. Existing Stage 8 browser coverage remains informed regression evidence and must not be mislabelled as Class C cold-start proof.

Exact active-head SHAs and CI conclusions remain live GitHub facts rather than durable project-state content.

## Next handoff

After this slice is reviewed, merged and closed to `idle`, `product-recovery-targeted-edit-orchestration` is the next planned slice: project the existing targeted-edit domain chain into understandable prerequisites/next actions without replacing its accepted Brief → Plan → Candidate → Review → Accept invariants.
