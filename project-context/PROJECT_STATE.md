# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-workspace-routing -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-workspace-routing` is the active Draft slice on branch `fix/product-recovery-workspace-routing`, created from the explicit idle `main` after PR #44.

The implementation is now functionally complete enough to prepare for review: Visualizer is migrated to the existing Product Orchestrator contract, and `relevant_workspaces` is authoritative for both deterministic reference journeys. The slice adds no second workflow store, does not remount legacy VideoClaw runtime and does not grow generic NLE functionality.

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

## Product Orchestrator — current migrated journeys

### Photo -> Video

Photo -> Video remains the first deterministic reference journey:

- verified project-owned images satisfy the source prerequisite;
- local/free `video.compose_photos` availability determines executable readiness;
- `compose_photos` delegates through the existing capability execution boundary;
- `photo_composition` is projected through `relevant_workspaces`;
- damaged or substituted source bytes fail closed.

### Visualizer

Visualizer is now the second deterministic Product Orchestrator journey:

- verified project-owned master audio is the required source prerequisite;
- verified project-owned artwork is optional and only verified images are offered as choices;
- local/free `audio.visualize` availability determines executable readiness;
- `audio_visualizer` is projected through `relevant_workspaces`;
- semantic action `render_visualizer` delegates through the existing capability/D-017 execution boundary;
- the product panel no longer calls the raw capability execution endpoint directly;
- the action input schema bounds usable source IDs to verified project-owned media;
- `suggested_input` is executable action input, while option lists remain in the schema;
- missing, damaged or substituted audio fails closed and blocks execution.

## Authoritative workspace routing

For Photo -> Video and Visualizer, the project page renders the workspace declared by `workflow.relevant_workspaces` instead of reconstructing the choice from `recipe_id`.

When a dedicated migrated workspace is present, the page does not also mount unrelated `ProjectEditor`, Sequence Continuity or Dubbing panels. This removes the duplicate frontend workspace authority for the migrated deterministic paths.

Non-migrated recipes remain fail-closed as `partial` at the Product Orchestrator boundary and preserve their existing domain implementations until later bounded migrations.

## Verification evidence required for review

Focused API/browser coverage now exercises:

- Visualizer `setup_required` without verified master audio;
- `ready` state with verified audio and projected `audio_visualizer` workspace;
- strict action input and local/free `audio.visualize` dispatch;
- executable `suggested_input` semantics;
- source-integrity failure after audio tampering;
- browser execution through `/workflow/actions/render_visualizer`;
- real `audio_visualizer_render` artifact creation;
- absence of unrelated Editor/Continuity/Dubbing panels for both deterministic migrated journeys;
- non-migrated recipe projection remaining `partial` with no fabricated actions/workspaces.

The final review head must pass every repository-required Ubuntu/Windows check and have no unresolved review threads before merge. Exact active-head SHAs and check conclusions remain live GitHub facts rather than durable project-state content.

Existing Stage 8 browser tests remain Class B informed-regression evidence, not Class C cold-start proof.

## Remaining product gaps outside this slice

- targeted existing-video edit, dubbing and music video still need product-level Orchestrator journeys that progressively disclose their existing durable domain state;
- Narrated and General Video do not yet have complete current user journeys;
- recipe selection on `/projects` remains readiness-blind before creation;
- legacy pipeline/workflow source remains compiled migration debt even though normal navigation no longer exposes it;
- Class C cold-start UI-only evidence and installed Windows human acceptance remain Product Truth Gate requirements.

## Next handoff

After this slice is reviewed, merged and closed to `idle`, `product-recovery-targeted-edit-orchestration` is the next planned slice: project the existing targeted-edit domain chain into understandable prerequisites and next actions without replacing the accepted Brief -> Plan -> Candidate -> Review -> Accept invariants.
