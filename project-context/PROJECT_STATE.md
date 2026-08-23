# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: product-recovery-general-video-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

General Video recovery is in **Review** in PR #53 on `fix/product-recovery-general-video-orchestration`, based on idle `main` closure `85ccc3b795df6cf255ebf5f22c870919ff17e367` after Narrated PR #52.

The slice recovers `general_video` as the seventh authoritative Product Orchestrator journey without adding a second workflow store or reopening generic editor ownership. Canonical inputs remain the existing Stage 8 workspace and Project Store media bindings.

## Current General Video boundary

- Stage 8 stores the required brief, optional script and ordered SHA-bound project-owned image/video/audio sources;
- the first deterministic path requires at least one image/video and allows zero or one explicit audio source;
- `video.render_general` normalizes visuals to H.264 1280×720/30fps, uses images for a fixed 2 seconds and video clips whole;
- embedded audio in source video is deliberately not mixed into the master; an explicit workspace audio source is the only soundtrack for this bounded path;
- Product Orchestrator owns readiness, prerequisites, current outcome and the `render_general` semantic action while Capability Registry remains the execution boundary;
- current outcome fails closed on stale workspace/source identity or substituted output bytes.

## Verification evidence

Exact Draft head `a7f6b56921d85cdbc66f0a2c596b93b06574e5f6` passed CI run `32649030821` (#2555), all five permanent checks green. The complete app-baseline jobs passed on Ubuntu and Windows, including the real General Video visible-UI -> ordered image/video -> FFmpeg master browser outcome.

Review requires the exact Review lifecycle head to pass the same five permanent checks before merge.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

`product-recovery-story-orchestration`, as defined by `project-context/NEXT_TASK.md`.
