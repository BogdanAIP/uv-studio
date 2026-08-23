# Project State

<!-- uv-context-state: idle -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **idle** on `main` after General Video recovery PR #53 merged at `733ead42d19d0d0af54cd3046b3b357f7ea8fbce`.

Product Orchestrator now owns seven authoritative Class A/B journeys:
- Photo -> Video
- Visualizer
- Targeted Edit
- Dubbing
- Music Video
- Narrated Video
- General Video

General Video reuses the existing Stage 8 workspace for required brief, optional script and ordered SHA-bound project-owned image/video/audio inputs. The bounded local/free `video.render_general` path requires at least one visual, allows zero or one explicit audio source, gives images a fixed two-second duration, uses verified video clips whole, normalizes visuals to H.264 1280x720/30fps and deliberately ignores embedded clip audio. Product Orchestrator owns readiness, exact semantic action input and current-outcome truth; stale/tampered workspace sources or output bytes fail closed.

## Verification evidence

- exact Draft head `a7f6b56921d85cdbc66f0a2c596b93b06574e5f6`: CI `32649030821` (#2555), all five permanent checks green;
- exact Review head `6a4c4bfef7615f3ffd25da2a3abb81f3b5085398`: CI `32650520289` (#2558), all five permanent checks green;
- real General Video visible-UI -> ordered image/video workspace -> local FFmpeg master browser outcome passed on Ubuntu and Windows in both final gates.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-story-orchestration`, as defined by `project-context/NEXT_TASK.md`.
