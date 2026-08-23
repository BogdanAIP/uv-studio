# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: product-recovery-general-video-orchestration -->

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

General Video reuses the existing Stage 8 workspace and Project Store for ordered SHA-bound image/video/audio inputs. The bounded local/free `video.render_general` capability normalizes visuals into an H.264 master and accepts at most one explicit project-owned soundtrack. It intentionally does not claim provider generation, arbitrary timing, transitions, multitrack mixing or generic NLE behavior.

## Verification evidence

- exact Draft head `a7f6b56921d85cdbc66f0a2c596b93b06574e5f6`: CI `32649030821` (#2555), all five permanent checks green;
- exact Review head `6a4c4bfef7615f3ffd25da2a3abb81f3b5085398`: CI `32650573026` (#2559), all five permanent checks green;
- the complete app-baseline browser suite passed on Ubuntu and Windows, including the visible General Video workspace -> ordered image/video import -> local FFmpeg master outcome;
- stale/tampered workspace inputs and substituted output bytes invalidate the current outcome as designed.

Stage 9 remains blocked until remaining Product Truth, Class C cold-start and installed Windows human-acceptance gates are complete. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-recovery-story-orchestration`, as defined by `project-context/NEXT_TASK.md`.
