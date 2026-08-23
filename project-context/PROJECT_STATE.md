# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: product-recovery-narrated-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **review** on `fix/product-recovery-narrated-orchestration` in PR #52, branched from idle `main` commit `971ff3c1ce5bba7ad82e09531a5152f1dffbdc25` after Project Store hardening PR #50 merged and closed.

The exact Draft head `a374c6411bbcf35b7f21b6598d417143ef7c6239` passed all five permanent checks in CI run `32644620113` (#2518), including the real Ubuntu and Windows browser suites. The slice is therefore transitioning to Review without broadening scope.

This slice recovers the existing `narrated_video` intent through Product Orchestrator. It reuses UV-owned project state rather than introducing a Narrated workflow database or reviving legacy VideoClaw pipelines.

## As-built Narrated boundary

The recovered implementation uses these existing canonical pieces:

- Stage 8 recipe workspace stores Narrated brief, required product-level script and SHA-bound project-owned visual inputs;
- ProjectPreparedAudioStore owns imported/recorded/TTS-promoted prepared speech under project assets and verifies current bytes;
- ProjectSourceMediaStore owns visual input identity and current-byte verification;
- `speech.synthesize` remains an optional route behind Capability Registry/D-017 through the Edge TTS compatibility offer;
- the generic `timeline.assemble` offer remains concat-copy only and is not falsely used for Narrated audio-over-visual composition;
- the narrow local/free `video.render_narrated` capability renders the exact current Narrated workspace revision plus one verified PreparedAudio narration track;
- Product Orchestrator projects `narrated_video`, prerequisites, diagnostics, the exact `render_narrated` action contract and current-outcome validity;
- the project page renders the Narrated Stage 8 workspace plus a PreparedAudio/render panel selected by `relevant_workspaces` rather than a parallel frontend recipe state machine.

The first bounded render path is intentionally image-led: verified workspace images are timed across one verified narration track. Video bindings may remain in the input workspace but are explicitly described as preserved/not rendered by this capability.

## Verification evidence

The Draft gate proved on the exact Draft head:

- Narrated brief/script and visual bindings persist through the existing Stage 8 workspace and fail closed when bound source bytes change;
- prepared narration bytes are verified before readiness/render;
- Narrated render binds the exact workspace revision, image hashes and prepared-audio hash into artifact metadata;
- a current master disappears from Product Orchestrator projection when workspace, narration, image or output bytes become stale/tampered;
- the project page exposes the Narrated workspace and PreparedAudio/render action through Product Orchestrator;
- real browser evidence reaches a local FFmpeg Narrated master from project UI inputs on Ubuntu and Windows without hidden workflow-state seeding after project creation;
- the five previously recovered journeys and strict Project Store behavior remain intact;
- all five permanent Ubuntu/Windows CI checks passed in Draft run `32644620113` (#2518).

Review must now pass the same five permanent checks on the exact Review head before merge.

This slice does not claim full mixed video-source Narrated assembly, General Video recovery, Class C cold-start acceptance, installed Windows human acceptance or Stage 9 release readiness. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-narrated-orchestration` is in Review in PR #52. After it is merged and lifecycle returns to idle, the next authorized slice is `product-recovery-general-video-orchestration` as defined by `project-context/NEXT_TASK.md`.
