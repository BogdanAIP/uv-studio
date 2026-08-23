# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-general-video-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

General Video recovery is active in Draft PR #53 on `fix/product-recovery-general-video-orchestration`, based on idle `main` closure `85ccc3b795df6cf255ebf5f22c870919ff17e367` after Narrated PR #52.

The slice is recovering `general_video` as the seventh authoritative Product Orchestrator journey without adding a second workflow store or reopening generic editor ownership. Canonical inputs remain the existing Stage 8 workspace and Project Store media bindings.

## Current General Video boundary

- Stage 8 stores the required brief, optional script and ordered SHA-bound project-owned image/video/audio sources;
- the first deterministic path requires at least one image/video and allows zero or one explicit audio source;
- `video.render_general` normalizes visuals to H.264 1280×720/30fps, uses images for a fixed 2 seconds and video clips whole;
- embedded audio in source video is deliberately not mixed into the master; an explicit workspace audio source is the only soundtrack for this bounded path;
- Product Orchestrator owns readiness, prerequisites, current outcome and the `render_general` semantic action while Capability Registry remains the execution boundary;
- current outcome fails closed on stale workspace/source identity or substituted output bytes.

## Draft verification

Focused renderer and Product Orchestrator API integrity tests are present. Exact Draft-head verification still requires all five permanent Ubuntu/Windows CI jobs plus the real browser outcome before transition to Review.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

`product-recovery-story-orchestration`, as defined by `project-context/NEXT_TASK.md`.
