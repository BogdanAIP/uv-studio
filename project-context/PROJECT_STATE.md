# Project State

<!-- uv-context-state: idle -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **idle** on `main` after Narrated recovery PR #52 merged at `e926bd97d9a5e644bd316f79ec9b9d7ff0f79853`.

Product Orchestrator now owns six authoritative Class A/B journeys:
- Photo -> Video
- Visualizer
- Targeted Edit
- Dubbing
- Music Video
- Narrated Video

Narrated reuses the existing Stage 8 workspace for brief/script/SHA-bound visual inputs, ProjectPreparedAudioStore for verified narration, ProjectSourceMediaStore for visual identity and a narrow local/free `video.render_narrated` capability. The first render path is intentionally image-led; workspace video bindings are preserved but not falsely claimed as rendered.

## Verification evidence

- exact Draft head `a374c6411bbcf35b7f21b6598d417143ef7c6239`: CI `32644620113` (#2518), all five permanent checks green;
- exact Review head `603c61f7e1dad28e610469043e8c1e74238cd75f`: CI `32644996053` (#2521), all five permanent checks green;
- real Narrated UI -> PreparedAudio -> FFmpeg master browser outcome passed on Ubuntu and Windows in both final gates;
- stale/tampered workspace, visual, narration and output bytes invalidate readiness/current outcome as designed.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-general-video-orchestration`, as defined by `project-context/NEXT_TASK.md`.
