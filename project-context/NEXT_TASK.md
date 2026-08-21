# Next Task

<!-- uv-next-slice: product-recovery-workspace-routing -->

## Goal

Make Product Orchestrator workspace projection authoritative for a second real deterministic journey by migrating `visualizer` and removing recipe-specific frontend reconstruction from the orchestrated path.

## Required direction

- keep Project Store, Recipe Registry, Capability Registry and D-017 as the existing authorities;
- add truthful `visualizer` readiness, prerequisites, relevant workspace and semantic action without introducing orchestration persistence;
- render orchestrated workspaces from `ProjectWorkflowState.relevant_workspaces` rather than from a parallel `recipe_id` decision tree;
- keep `photo_to_video` as the first reference and prove both deterministic workflows use the same product contract;
- do not expose generic editor, continuity, dubbing or music workspaces unless the Product Orchestrator explicitly declares them relevant;
- keep non-migrated recipes fail-closed as `partial` at the Product Orchestrator boundary rather than inventing readiness from legacy execution metadata;
- preserve the D-033 editor foundation and do not add generic NLE primitives in this slice.

## Completion proof

The slice is complete when Photo-to-Video and Visualizer both reach real local artifacts through Product Orchestrator semantic actions, their project pages are driven by projected workspaces instead of a duplicate recipe switch, irrelevant specialist panels are absent from both journeys, and focused API/browser tests prove blocked/setup/ready/result states.

## Entry gate

Do not begin until the D-033 conformance audit is reviewed and merged, its lifecycle is closed to `idle`, and any editor-foundation deviations discovered there are either corrected or explicitly recorded as bounded follow-up work.
