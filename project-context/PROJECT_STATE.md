# Project State

<!-- uv-context-state: draft -->
<!-- uv-last-completed: product-recovery-orchestrator-foundation -->

**Updated:** 2026-08-21

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`product-recovery-editor-ownership-resolution` is active in Draft PR #44 on branch `research/product-recovery-editor-ownership-resolution`, based on `main@f7ba7e8d4a9e41294ba8f4104c4330d24e80a93f`.

This is a **D-033 implementation conformance slice**, not a product-identity redesign and not a new choice between UV Studio, OpenCut and MLT. D-033 remains the accepted baseline unless reproducible evidence proves one of its ownership boundaries technically invalid.

The previous slice `product-recovery-orchestrator-foundation` completed in PR #43 and merged as `297556a76484e3445feb93e6f22f512e212d8360`; its lifecycle was then closed to `idle` by `f7ba7e8d4a9e41294ba8f4104c4330d24e80a93f`.

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
- GUI, scripts, AI and MCP must converge on the same product-owned mutation contracts rather than receiving raw-state bypasses.

The current slice audits implementation against this map. It may clarify D-033 or record bounded incomplete work. A fundamental ownership change requires separate reproducible evidence and explicit approval.

## Current Product Truth state

### Product Orchestrator

PR #43 implemented the first real Product Orchestrator journey for **Photo → Video only**:

- `ProjectWorkflowState` is a read projection; it creates no second workflow store;
- readiness is derived from canonical project/source state plus executable capability availability;
- `compose_photos` delegates to the existing `video.compose_photos` D-017 capability path;
- only the `photo_composition` workspace is mounted for that orchestrated project;
- damaged/unverified image references do not falsely satisfy readiness.

**Visualizer is not yet migrated to Product Orchestrator.** Its local deterministic `audio.visualize` capability path is real, but `project_workflow_state()` currently returns the generic `partial/workflow_not_migrated` projection for it. Any older documentation saying Visualizer is “the same” as the Photo orchestration flow is stale.

### Frontend shell

The normal `AppShell` is now UV-owned and exposes Projects and Settings. It no longer imports/polls the old VideoClaw session/task/sandbox runtime or advertises `/pipelines/*` in normal navigation.

Legacy `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and `/pipelines/*` source remain compiled migration debt. Their historical backend contracts are intentionally not remounted.

### Remaining cross-workflow leakage

Photo → Video is isolated, but the generic project page still mounts `ProjectEditor`, Sequence Continuity and all three dubbing panels for every **non-photo** recipe. Recipe-specific workspaces are then appended. Therefore task isolation is not solved application-wide yet.

Recipe cards on `/projects` also remain readiness-blind before project creation.

## D-033 conformance audit findings so far

### Conforming / valuable

- `uv_studio/editor/commands.py` provides a real product-owned semantic editor command service;
- range selection creates canonical `RangeContinuityBrief` state instead of frontend-only JSON;
- `RangeTimeline.tsx` and `timelineMath.ts` explicitly reuse/adapt pinned OpenCut Classic interaction/ruler ideas while keeping UV integer-microsecond identity;
- `MLTTimelineAdapter` creates an ephemeral derived MLT representation from canonical accepted edits; raw MLT XML is not a public mutation channel;
- browser playhead/selection/form state is transient UI state and is not itself canonical timeline ownership;
- accepted edit/replacement/review state remains durable and project-owned.

### Concrete bounded deviation

`uv_studio/api/edit_state.py` exposes a direct mutating route:

`DELETE /api/uv/projects/{project_id}/edits/{edit_id}`

which calls `RangeEditStateStore.remove(...)` directly. Because accepted range edits are canonical non-destructive timeline state under D-028, this bypasses the D-033 requirement that meaningful editor mutations pass through the product-owned Command API.

PR #44 will migrate accepted-edit removal to `EditorCommandService`/`/editor/commands`, keep edit-state reads read-only, update API/domain tests, and remove the privileged direct mutation route if call-site evidence confirms no required external dependency.

### Incomplete, not yet a reason to replace D-033

- MLT currently serves mainly as a derived accepted-edit projection/render seam rather than owning every potential generic timeline primitive;
- OpenCut reuse is selective, as D-033 permits, and should not be expanded merely to increase code reuse percentage;
- generic transaction/undo-redo semantics are not yet proven as a complete shared product feature;
- GUI/scripts/AI/MCP convergence is real for selected semantic paths but not yet proven for every editor/domain mutation.

These are conformance/remediation items. They do not by themselves justify reopening product identity or selecting a different editor foundation.

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

The final PR #44 review head must pass the repository-required checks on Ubuntu and Windows. The D-033 conformance claim must be backed by code/call-site tests, not documentation alone.

## Release status

Release/signing remains downstream of Product Truth Recovery. Stage 9 may resume only after truthful workflows, orchestrated user journeys, cold-start evidence and installed-app human acceptance are restored.

## Next handoff

After PR #44 is reviewed, merged and lifecycle returns to `idle`, continue with `product-recovery-workspace-routing` from `project-context/NEXT_TASK.md`: migrate Visualizer as the second deterministic Product Orchestrator journey and make projected relevant workspaces authoritative for those orchestrated project pages without adding generic NLE primitives.
