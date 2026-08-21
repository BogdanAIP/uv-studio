# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: product-recovery-editor-ownership-resolution -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-editor-ownership-resolution` completed in PR #44. The repository is back in explicit `idle` state and the next authorized handoff is `product-recovery-workspace-routing`.

PR #44 reaffirmed D-033 as the accepted editor foundation, synchronized recovery documentation with the live implementation, and repaired the accepted-edit mutation bypass without changing UV Studio product identity.

Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference for Windows packaging/native-shell work. Product Truth Recovery remains release-blocking.

## Product definition

UV Studio remains the product described by `README.md` and `ROADMAP.md`: a desktop/local-first video **production and editing workspace** with task-specific workflows. It is intentionally hybrid:

- guided task workflows and manual editing coexist over one project;
- Project Store/domain state is canonical;
- Product Orchestrator explains readiness, prerequisites, relevant workspaces and next actions;
- UV semantic/domain commands own mutations;
- Capability Registry owns provider/runtime offers and D-017 authorization;
- FFmpeg, MLT, local ML, MCP and remote providers are bounded implementations behind those contracts.

The recovery does not redefine UV Studio as either a generic NLE clone or a workflow-only AI application.

## Accepted editor foundation — D-033

D-033 remains binding:

- **UV Studio owns** Project Store, portable identity, canonical edit/domain contracts, semantic Command API, validation, acceptance/review invariants, provenance and security;
- **MLT owns behind a UV adapter** reusable timeline/editing mechanics and engine representation where mapped by UV contracts;
- **OpenCut Classic** is a selective MIT editor-UX/component donor, not a second application shell or canonical store;
- **FFmpeg accepted-edit export** remains authoritative until preview/render parity evidence explicitly promotes another renderer;
- GUI, scripts, AI and MCP converge incrementally on the same UV-owned semantic/domain mutation contracts rather than receiving raw-state bypasses.

The 2026-08-21 clarification distinguishes conforming transient UI state, incomplete implementation, concrete conformance defects and evidence-backed amendment candidates. A fundamental ownership change still requires reproducible evidence and separate approval.

## Current Product Truth state

### Product Orchestrator

PR #43 implemented the first real Product Orchestrator journey for **Photo → Video only**:

- `ProjectWorkflowState` is a read projection; it creates no second workflow store;
- readiness is derived from canonical project/source state plus executable capability availability;
- `compose_photos` delegates to the existing `video.compose_photos` D-017 capability path;
- only the `photo_composition` workspace is mounted for that orchestrated project;
- damaged/unverified image references do not falsely satisfy readiness.

**Visualizer is not yet migrated to Product Orchestrator.** Its local deterministic `audio.visualize` capability path is real, but `project_workflow_state()` currently returns the generic `partial/workflow_not_migrated` projection for it. Older documentation that described Visualizer as already equivalent to the Photo orchestration flow has been corrected.

### Frontend shell

The normal `AppShell` is UV-owned and exposes Projects and Settings. It no longer imports/polls the old VideoClaw session/task/sandbox runtime or advertises `/pipelines/*` in normal navigation.

Legacy `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and `/pipelines/*` source remain compiled migration debt. Their historical backend contracts are intentionally not remounted.

### Remaining cross-workflow leakage

Photo → Video is isolated, but the generic project page still mounts `ProjectEditor`, Sequence Continuity and all three dubbing panels for every **non-photo** recipe. Recipe-specific workspaces are then appended. Task isolation is therefore not solved application-wide yet.

Recipe cards on `/projects` also remain readiness-blind before project creation.

## D-033 conformance result

### Conforming / valuable

- `uv_studio/editor/commands.py` is a real product-owned semantic editor command service;
- range selection creates canonical `RangeContinuityBrief` state instead of frontend-only JSON;
- `RangeTimeline.tsx` and `timelineMath.ts` explicitly reuse/adapt pinned OpenCut Classic interaction/ruler ideas while keeping UV integer-microsecond identity;
- `MLTTimelineAdapter` creates an ephemeral derived MLT representation from canonical accepted edits; raw MLT XML is not a public mutation channel;
- browser playhead/selection/form state is transient UI state and is not itself canonical timeline ownership;
- accepted edit/replacement/review state remains durable and project-owned;
- current bounded FFmpeg accepted-edit export remains consistent with D-033 until parity evidence promotes another renderer.

### Concrete bounded deviation — repaired in PR #44

The historical `uv_studio/api/edit_state.py` exposed:

`DELETE /api/uv/projects/{project_id}/edits/{edit_id}`

which mutated canonical `RangeEditStateStore` directly. Accepted range edits are D-028 non-destructive timeline state, so this was a genuine D-033 command-boundary bypass.

The maintained implementation now:

- provides typed `RemoveAcceptedEditCommand` / result contracts through `EditorCommandService`;
- exposes semantic `remove_accepted_edit` through `/editor/commands`;
- validates edit identity and preserves project/edit not-found semantics;
- leaves `/edits` as a read-only HTTP surface;
- has domain and API conformance tests for the semantic mutation path;
- has no production frontend caller depending on the removed direct DELETE route.

### Explicit incomplete work, not a reason to replace D-033

- MLT currently serves mainly as a derived accepted-edit projection/render seam rather than owning every potential generic timeline primitive;
- OpenCut reuse is selective, as D-033 permits, and should expand only for concrete reusable primitives;
- product-level transaction/undo-redo semantics are not yet proven as a complete shared feature;
- GUI/scripts/AI/MCP convergence is real for selected paths but not yet proven for every meaningful editor/domain mutation;
- MLT preview/render parity has not promoted it over the current authoritative export path.

These are bounded follow-up concerns. Generic NLE growth must not outrun them, but the current evidence does not justify a new editor foundation.

## Documentation truth repaired by PR #44

- `PRODUCT_RECOVERY_PLAN.md` treats Phase 4 as D-033 conformance/clarification rather than product/editor re-selection;
- `PRODUCT_TRUTH_MATRIX.md` separates historical Stage 8 findings from current Photo-only orchestration truth;
- `PRODUCT_SURFACE_AUDIT.md` no longer claims Photo still receives generic specialist panels;
- `FRONTEND_BACKEND_INTERACTION_MAP.md` records Product Orchestrator as the current product next-action owner where migrated and Visualizer as still unmigrated;
- `EDITOR_FOUNDATION_CONFORMANCE.md` records the current ownership map and repaired mutation bypass;
- D-033 itself contains the accepted 2026-08-21 clarification.

## Strong foundations to preserve

- Project Store, archives, migrations, path and media-integrity boundaries;
- D-017 authorization and provider-neutral Capability Registry;
- provenance, cancellation and deterministic media adapters;
- accepted edit, dubbing, music and continuity durable state;
- MLT adapter and OpenCut provenance/reuse evidence;
- Product Orchestrator as a projection rather than another canonical state engine;
- archived Stage 9 packaging/native-shell engineering.

## Verification policy

Existing unit/API/real-media/browser suites remain required. They are strong engineering and informed-regression evidence, but they do not replace Class C cold-start journeys or installed Windows human acceptance.

Every review head must pass the repository-required Ubuntu/Windows checks and have no unresolved review threads before merge. Exact active-head SHAs and check conclusions remain live GitHub facts rather than durable project-state content.

## Release status

Release/signing remains downstream of Product Truth Recovery. Stage 9 may resume only after truthful workflows, orchestrated user journeys, cold-start evidence and installed-app human acceptance are restored.

## Next handoff

`product-recovery-workspace-routing` is the single next slice from `project-context/NEXT_TASK.md`: migrate Visualizer as the second deterministic Product Orchestrator journey and make projected relevant workspaces authoritative for the migrated project pages without adding generic NLE primitives.
