# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: product-recovery-workspace-routing -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-workspace-routing` completed in PR #45. The repository is back in explicit `idle` state and the next authorized handoff is `product-recovery-targeted-edit-orchestration`.

PR #45 migrated Visualizer to Product Orchestrator, made projected workspaces authoritative for both deterministic reference journeys, enforced projected source choices before capability dispatch, and preserved the existing Project Store/Capability Registry/D-017 authority boundaries.

PR #44 remains the completed D-033 conformance baseline. Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Product definition

UV Studio remains a desktop/local-first video **production and editing workspace** with task-specific workflows:

- Project Store/domain state is canonical;
- Product Orchestrator projects readiness, prerequisites, relevant workspaces and semantic next actions;
- UV semantic/domain commands own mutations;
- Capability Registry owns provider/runtime offers and D-017 authorization;
- FFmpeg, MLT, local ML, MCP and remote providers remain bounded implementations behind those contracts.

## Accepted editor foundation — D-033

D-033 remains binding:

- UV Studio owns canonical project/edit/domain state and semantic mutations;
- MLT remains the bounded timeline/editing engine representation where mapped;
- OpenCut Classic remains a selective MIT editor-UX/component donor;
- current FFmpeg accepted-edit export remains authoritative until parity evidence promotes another renderer;
- meaningful editor mutations converge on UV-owned semantic/domain command boundaries.

## Product Orchestrator — current migrated journeys

### Photo -> Video

Photo -> Video is the first deterministic reference journey:

- verified project-owned images satisfy the source prerequisite;
- local/free `video.compose_photos` availability determines executable readiness;
- `compose_photos` delegates through the existing capability execution boundary;
- `photo_composition` is projected through `relevant_workspaces`;
- damaged or substituted source bytes fail closed.

### Visualizer

Visualizer is the second deterministic Product Orchestrator journey:

- verified project-owned master audio is required;
- verified project-owned artwork is optional;
- local/free `audio.visualize` availability determines executable readiness;
- `audio_visualizer` is projected through `relevant_workspaces`;
- semantic action `render_visualizer` delegates through the existing capability/D-017 execution boundary;
- the product panel does not call the raw capability execution endpoint directly;
- the action input schema exposes only verified project-owned source choices;
- the HTTP Product Orchestrator boundary revalidates submitted source IDs against the fresh projected action contract before dispatch;
- `suggested_input` remains executable action input rather than a UI-only side channel;
- missing, damaged or substituted audio fails closed and blocks execution.

## Authoritative workspace routing

For Photo -> Video and Visualizer, the project page renders the workspace declared by `workflow.relevant_workspaces` instead of reconstructing the choice from `recipe_id`.

When a dedicated migrated workspace is present, the page does not also mount unrelated `ProjectEditor`, Sequence Continuity or Dubbing panels.

Non-migrated recipes remain fail-closed as `partial` at the Product Orchestrator boundary and preserve their existing domain implementations until later bounded migrations.

## Verification evidence

The maintained regression suite covers:

- Visualizer `setup_required` without verified master audio;
- `ready` state with verified audio and projected `audio_visualizer` workspace;
- strict action input and local/free `audio.visualize` dispatch;
- executable `suggested_input` semantics;
- rejection of source IDs excluded by the freshly projected action schema before capability execution;
- source-integrity failure after audio tampering;
- browser execution through `/workflow/actions/render_visualizer`;
- real `audio_visualizer_render` artifact creation;
- absence of unrelated Editor/Continuity/Dubbing panels for both deterministic migrated journeys;
- non-migrated recipe projection remaining `partial` with no fabricated actions/workspaces.

Existing browser suites remain Class B informed-regression evidence, not Class C cold-start proof.

## Remaining product gaps

- targeted existing-video edit, dubbing and music video still need product-level Orchestrator journeys that progressively disclose their existing durable domain state;
- Narrated and General Video do not yet have complete current user journeys;
- recipe selection on `/projects` remains readiness-blind before creation;
- legacy pipeline/workflow source remains compiled migration debt even though normal navigation no longer exposes it;
- Class C cold-start UI-only evidence and installed Windows human acceptance remain Product Truth Gate requirements.

## Next handoff

Continue with `product-recovery-targeted-edit-orchestration` from `project-context/NEXT_TASK.md`: project the existing targeted-edit domain chain into understandable prerequisites and next actions without replacing the accepted Brief -> Plan -> Candidate -> Review -> Accept invariants or creating a second workflow engine.
