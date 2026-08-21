# UV Studio Product Surface Audit

## Purpose

This document separates the D-062 Stage 8 failure baseline from the current recovery state. Historical findings remain evidence for why the installed application felt broken, but they are not allowed to masquerade as current behavior after PR #42/#43.

## Current supported shell

The supported root `AppShell` is UV-owned and exposes Projects and Settings. It no longer imports or polls the old VideoClaw session/task/sandbox runtime and no longer places `/pipelines/*` in normal navigation.

Legacy `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and the old `/pipelines/*` routes still exist as compiled migration debt. They depend on historical backend contracts that Stage 3.5 intentionally stopped mounting. Their correct disposition is dependency-proven migration/removal, not restoration of the complete VideoClaw backend.

**Status:** normal-shell split repaired; legacy route source remains isolated debt.

## Current workflow isolation

The Stage 8 baseline mounted generic Editor, Sequence Continuity and three Dubbing panels for every project and then appended recipe-specific panels. That violated the product promise that a selected task should expose only relevant stages.

PR #43 repaired this for **Photo -> Video only**. Its page is driven by Product Orchestrator `relevant_workspaces`, mounts `photo_composition`, and does not mount the unrelated editor/continuity/dubbing panels.

Every non-photo recipe still follows the older composition pattern. Visualizer, Music, Story/Commercial/Free and Performance projects therefore still inherit unrelated generic editor/continuity/dubbing workspaces before or alongside their specialist panels.

**Status:** partially repaired. Product Orchestrator workspace projection must become authoritative as each recipe is migrated.

## Recipe selection remains readiness-blind

`/projects` still presents recipe cards before the user can see product-level `ready | setup_required | partial | unavailable` truth.

Current examples:

- Photo -> Video: `working_orchestrated`;
- Visualizer: real local deterministic execution, but not yet Product-Orchestrator-migrated;
- Performance/Lip-sync: real optional runtime path with setup requirements;
- Music Video and Dubbing: substantial real domains with UX/setup orchestration debt;
- Story/Commercial: preparation state, incomplete production journey;
- General/Narrated/Action Transfer: no complete current user journey.

**Status:** current product defect. Readiness needs a pre-project/catalog projection in a later bounded slice.

## Targeted edit surface

Targeted edit is not fake functionality. Source import, preview, exact range selection, replacement planning/candidates/review, acceptance and render are real UV-owned paths.

The remaining product problem is presentation. Durable internal state such as Brief -> Plan -> Candidate -> Review -> Accepted is useful for safety and recoverability, but the ordinary user should primarily see the next outcome-oriented action:

```text
Choose fragment -> Describe change -> Prepare result -> Preview -> Accept/Reject -> Export
```

Product Orchestrator should eventually project that journey without deleting the underlying domain rigor.

## D-033 editor conformance

D-033 remains the accepted editor foundation:

- Project Store/domain state is canonical;
- meaningful editor mutations use UV-owned semantic/domain command boundaries;
- MLT is a bounded editing/timeline engine representation, not another project authority;
- OpenCut Classic is a selective MIT editor UX/component donor;
- FFmpeg remains authoritative accepted-edit export until parity evidence promotes another renderer.

The current audit found one concrete bounded violation: the historical `DELETE /api/uv/projects/{project_id}/edits/{edit_id}` route mutated canonical accepted-edit state directly through `RangeEditStateStore`.

PR #44 moves that mutation to semantic command `remove_accepted_edit` under `/editor/commands` and leaves `/edits` as a read-only inspection surface. See `EDITOR_FOUNDATION_CONFORMANCE.md`.

## Historical defects already repaired

The following D-062 baseline findings should no longer be described as current supported-shell behavior:

- legacy Video-Claw navigation/session/task polling in root AppShell;
- the `Производственный интерфейс -> / -> /projects` navigation loop;
- base recipe execution metadata falsely advertising unmounted narrated/action-transfer pipeline targets;
- Photo-to-Video receiving generic Editor/Continuity/Dubbing panels.

They remain useful historical evidence and regression targets.

## Current acceptance rules

1. Supported navigation must not expose runtime surfaces whose backend contracts are absent.
2. Stage 3.5 security must not be reversed to satisfy old frontend callers.
3. Recipe selection must eventually expose truthful readiness before project creation.
4. Product Orchestrator `relevant_workspaces` becomes authoritative for migrated recipes.
5. Disabled primary actions need visible structured prerequisites.
6. Internal domain vocabulary is progressive detail, not the default product mental model.
7. Visible execution actions must reach current UV semantic/domain/capability paths.
8. Meaningful canonical editor mutations must not bypass D-033 command/domain boundaries.
9. Photo-to-Video remains the first orchestrated reference flow; Visualizer is the next deterministic reference candidate.
10. Class C cold-start tests and installed Windows human acceptance remain release gates in addition to lower-layer regression tests.
