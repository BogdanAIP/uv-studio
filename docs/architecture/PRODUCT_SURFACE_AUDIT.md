# UV Studio Product Surface Audit

## Purpose

This document separates the D-062 Stage 8 failure baseline from current Product Truth Recovery behavior. Historical findings remain evidence for why the installed application felt broken, but they are not current supported-product truth after the recovery slices.

## Current supported shell

The supported root `AppShell` is UV-owned and exposes Projects and Settings. It no longer imports or polls the old VideoClaw session/task/sandbox runtime and no longer places `/pipelines/*` in normal navigation.

Legacy `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and old `/pipelines/*` routes remain compiled migration debt. Their historical backend contracts are intentionally not remounted.

**Status:** normal-shell split repaired; legacy route source remains isolated debt.

## Current workflow isolation

The Stage 8 baseline mounted generic Editor, Sequence Continuity and three Dubbing panels for nearly every project and then appended recipe-specific panels. That violated the product promise that a selected task should expose only relevant stages.

The two deterministic Product Orchestrator journeys are now isolated:

- Photo -> Video projects project only `photo_composition`;
- Visualizer projects project only `audio_visualizer`.

For both, the project page uses `workflow.relevant_workspaces` as the workspace authority and does not additionally mount generic Editor/Continuity/Dubbing panels.

Non-migrated recipes still retain their existing domain panels because their Orchestrator projection has not yet declared an authoritative workspace set.

**Status:** repaired for the two migrated deterministic journeys; application-wide migration remains incomplete.

## Visualizer surface truth

Visualizer is no longer merely a recipe-specific panel over a direct capability helper.

Current path:

```text
verified master audio
 + optional verified artwork
 -> Product Orchestrator readiness/prerequisites
 -> audio_visualizer workspace
 -> render_visualizer semantic action
 -> audio.visualize capability
 -> local/free FFmpeg
 -> project artifact
```

The panel receives allowed source IDs from the action schema. Tampered audio is removed from the usable set, disables the primary action and requires a new verified copy. `suggested_input` is a valid action payload rather than a hidden option-list channel.

## Recipe selection remains readiness-blind

`/projects` still presents recipe cards before the user can see product-level `ready | setup_required | partial | unavailable` truth.

Current examples:

- Photo -> Video: `working_orchestrated`;
- Visualizer: `working_orchestrated`;
- Performance/Lip-sync: real optional runtime path with setup requirements;
- Music Video and Dubbing: substantial real domains with UX/setup orchestration debt;
- Story/Commercial: preparation state, incomplete production journey;
- General/Narrated/Action Transfer: no complete current user journey.

**Status:** current product defect. Readiness needs a pre-project/catalog projection in a later bounded slice.

## Targeted edit surface

Targeted edit is real functionality. Source import, preview, exact range selection, replacement planning/candidates/review, acceptance and render are current UV-owned paths.

The product problem is presentation. Durable internal state such as Brief -> Plan -> Candidate -> Review -> Accepted is useful for correctness and recoverability, but ordinary users should primarily see outcome-oriented progression:

```text
Choose fragment -> Describe change -> Prepare result -> Preview -> Accept/Reject -> Export
```

The next recovery slice should project that journey through Product Orchestrator without deleting the underlying domain rigor.

## D-033 editor conformance

D-033 remains the accepted editor foundation:

- Project Store/domain state is canonical;
- meaningful editor mutations use UV-owned semantic/domain command boundaries;
- MLT is a bounded editing/timeline engine representation, not another project authority;
- OpenCut Classic is a selective MIT editor UX/component donor;
- FFmpeg remains authoritative accepted-edit export until parity evidence promotes another renderer.

PR #44 repaired the concrete accepted-edit removal bypass by moving mutation to semantic `remove_accepted_edit` under `/editor/commands` and leaving `/edits` read-only.

## Historical defects already repaired

The following D-062 baseline findings must not be described as current supported-shell behavior:

- legacy Video-Claw navigation/session/task polling in root AppShell;
- the `Производственный интерфейс -> / -> /projects` navigation loop;
- base recipe execution metadata falsely advertising unmounted narrated/action-transfer pipeline targets;
- Photo-to-Video receiving generic Editor/Continuity/Dubbing panels;
- Visualizer receiving generic Editor/Continuity/Dubbing panels;
- Visualizer product UI invoking `audio.visualize` through a direct capability helper instead of Product Orchestrator.

They remain regression evidence.

## Current acceptance rules

1. Supported navigation must not expose runtime surfaces whose backend contracts are absent.
2. Stage 3.5 security must not be reversed to satisfy old frontend callers.
3. Recipe selection must eventually expose truthful readiness before project creation.
4. Product Orchestrator `relevant_workspaces` is authoritative for migrated recipes.
5. Disabled primary actions need visible structured prerequisites.
6. Internal domain vocabulary is progressive detail, not the default product mental model.
7. Visible execution actions must reach current UV semantic/domain/capability paths.
8. Meaningful canonical editor mutations must not bypass D-033 command/domain boundaries.
9. Photo-to-Video and Visualizer are the two deterministic orchestrated reference flows.
10. `suggested_input` must remain executable according to the action input contract; available choices belong in the bounded schema/projection.
11. Class C cold-start tests and installed Windows human acceptance remain release gates in addition to lower-layer regression tests.
