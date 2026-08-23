# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-narrated-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **draft** on `feat/product-recovery-narrated-orchestration` in PR #51, branched from idle `main` commit `971ff3c1ce5bba7ad82e09531a5152f1dffbdc25` after Project Store hardening PR #50 merged and closed.

This slice recovers the existing `narrated_video` intent through Product Orchestrator. It reuses UV-owned project state rather than introducing a Narrated workflow database or reviving legacy VideoClaw pipelines.

## As-built Narrated boundary

The recovered implementation now uses these existing canonical pieces:

- Stage 8 recipe workspace stores Narrated brief, required product-level script and SHA-bound project-owned visual inputs;
- ProjectPreparedAudioStore owns imported/recorded/TTS-promoted prepared speech under project assets and verifies current bytes;
- ProjectSourceMediaStore owns visual input identity and current-byte verification;
- `speech.synthesize` remains an optional route behind Capability Registry/D-017 through the Edge TTS compatibility offer;
- the generic `timeline.assemble` offer remains concat-copy only and is not falsely used for Narrated audio-over-visual composition;
- the narrow local/free `video.render_narrated` capability renders the exact current Narrated workspace revision plus one verified PreparedAudio narration track;
- Product Orchestrator projects `narrated_video`, prerequisites, diagnostics, the exact `render_narrated` action contract and current-outcome validity;
- the project page renders the Narrated Stage 8 workspace plus a PreparedAudio/render panel selected by `relevant_workspaces` rather than a parallel frontend recipe state machine.

The first bounded render path is intentionally image-led: verified workspace images are timed across one verified narration track. Video bindings may remain in the input workspace but are explicitly described as preserved/not rendered by this capability.

## Verification target

Before Review, the exact Draft head must prove:

- Narrated brief/script and visual bindings persist through the existing Stage 8 workspace and fail closed when bound source bytes change;
- prepared narration bytes are verified before readiness/render;
- Narrated render binds the exact workspace revision, image hashes and prepared-audio hash into its artifact metadata;
- a current master disappears from Product Orchestrator projection when workspace, narration, image or output bytes become stale/tampered;
- the project page exposes the Narrated workspace and PreparedAudio/render action through Product Orchestrator;
- real browser evidence reaches a local FFmpeg Narrated master from project UI inputs without hidden workflow-state seeding;
- the five previously recovered journeys and strict Project Store behavior remain intact;
- all five permanent Ubuntu/Windows CI checks pass on the exact Draft head.

This slice does not claim full mixed video-source Narrated assembly, General Video recovery, Class C cold-start acceptance, installed Windows human acceptance or Stage 9 release readiness. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-narrated-orchestration` is active in PR #51. After it is reviewed, merged and lifecycle returns to idle, the next authorized slice is `product-recovery-general-video-orchestration` as defined by `project-context/NEXT_TASK.md`.
