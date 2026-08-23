# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-story-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Story Video recovery is active in **Draft** on `fix/product-recovery-story-orchestration`, based on validated idle `main` `1a82db63c95b85b2eeb0838066b3f74be267bf72` after General Video PR #53.

PR #54 is the active review surface. The slice is recovering `story_video` through Product Orchestrator without introducing a story-specific workflow database, reopening editor ownership, or claiming a final Story render that is not yet audited end to end.

## As-built boundary under recovery

- Stage 8 already owns the required brief, optional script and ordered SHA-bound Story image/video/audio bindings;
- Product Orchestrator now projects that verified Stage 8 state as the authoritative preparation outcome: invalid or stale project-owned bytes fail closed instead of advertising readiness;
- existing `sequence_continuity` state is reused only as optional continuity evidence, and accepted takes are exposed only after their current media bytes validate;
- the Story recipe declares `timeline.assemble`, but this slice does **not** treat that declaration as proof of an audited Story-specific final render/export path;
- provider-backed text/image/video/speech generation remains optional and setup-dependent and is not exposed as local/free Story execution;
- the visible Story project surface is the Stage 8 Story workspace plus Sequence Continuity, driven by the same Product Orchestrator readiness shown elsewhere in UV Studio;
- no `render_story` action, provider bypass, hidden seed state, generic NLE authority or parallel Story workflow store is introduced.

## Verification status

Draft implementation now includes focused Product Orchestrator unit tests, API projection tests and a visible browser outcome that saves Story brief/script/media through production UI and verifies that readiness becomes preparation-ready without advertising a final render action.

CI run #2575 on Draft head `9d8855954f6d31b72d4df9a71d6355064933dbe5` exposed a context-only failure because PR #54 initially lacked the required `uv-active-slice` marker; the PR body has been corrected. Ubuntu bootstrap, including unit tests, passed on that run. A fresh exact-head CI run is required before transition to Review.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

`product-recovery-commercial-product-orchestration`, as defined by `project-context/NEXT_TASK.md`.
