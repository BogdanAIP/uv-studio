# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-story-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Story Video recovery is active in **Draft** on `fix/product-recovery-story-orchestration`, based on validated idle `main` `1a82db63c95b85b2eeb0838066b3f74be267bf72` after General Video PR #53.

The slice is recovering `story_video` through Product Orchestrator without introducing a story-specific workflow database or reopening editor ownership.

## As-built boundary under recovery

- Stage 8 already owns the required brief, optional script and ordered SHA-bound story image/video/audio bindings;
- the existing `sequence_continuity` and review primitives are durable continuity tools, not a replacement story-plan authority, and should be projected only where linked-scene continuity is actually relevant;
- Story already declares `timeline.assemble` as its deterministic assembly requirement, while provider-backed text/image/video generation remains optional/setup-dependent and must not be disguised as local execution;
- General Video proved a bounded normalized local assembly pattern that can be reused internally, but Story needs its own semantic capability/current-outcome contract rather than silently invoking the General recipe.

## Verification status

Focused implementation and tests are still being developed. Exact Draft-head verification requires all five permanent Ubuntu/Windows CI jobs plus a visible Story UI outcome before transition to Review.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

`product-recovery-commercial-product-orchestration`, as defined by `project-context/NEXT_TASK.md`.
