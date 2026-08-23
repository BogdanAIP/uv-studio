# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-recovery-music-orchestration -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **draft** on `product-recovery-music-orchestration`, branched from idle `main` after completion of Dubbing PR #47.

The slice projects the existing `music_video` production chain through Product Orchestrator. It must reuse the canonical Music Map, Music Direction, Music Assembly and Music Video Review state plus existing capability execution and artifact provenance. Product Orchestrator remains a read projection plus semantic action boundary and must not introduce a second durable music workflow store.

Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Completed Product Recovery journeys

The permanent Product Orchestrator has authoritative Class A/B journeys for:

- `photo_to_video -> photo_composition`;
- `visualizer -> audio_visualizer`;
- `free_project -> targeted_edit`;
- `dubbing -> dubbing`.

These journeys keep Project Store/domain stores canonical and use Product Orchestrator only as current-state projection plus allowed semantic actions.

## Music — active recovery slice

The canonical legacy Music chain already exists and is being projected rather than rewritten:

`verified master song -> Music Map -> Music Direction -> Music Assembly -> local render -> deterministic rhythm/evidence review -> approved current outcome`

`MusicMapStore` binds the map to exact project-owned song bytes. `MusicDirectionStore` binds direction to one exact Music Map revision and performs the deterministic rhythm audit. `MusicAssemblyStore` binds every current shot to verified project-owned video bytes. `MusicVideoReviewStore` validates the render artifact against the exact Map/Direction/Assembly revisions, master-song bytes, duration, rhythm alignment and render provenance before approval.

The entry contract mentioned a separate `MusicAuditStore`/`music_audit.py`, but the as-built code keeps rhythm audit as `MusicDirectionStore.rhythm_audit()` and final persisted evidence in `MusicVideoReviewStore`. This slice will preserve that canonical structure instead of creating an unnecessary second audit store.

## Verification target

Before Review, the exact Draft head must prove through focused API/browser evidence and all permanent CI checks that the visible Music journey can:

- use verified project-owned audio/video sources;
- create or regenerate the Music Map;
- create Music Direction;
- create/replace Music Assembly against current source bytes;
- execute the existing local/free music-video render capability;
- expose deterministic rhythm audit and evidence-bound final Review;
- reject stale/tampered song, visual sources and render artifacts;
- surface the accepted/current music outcome through Product Orchestrator;
- preserve the already recovered Dubbing browser path.

This slice does **not** claim Class C cold-start product usability, installed Windows human acceptance or release readiness.

## Remaining recovery work after Music

1. Narrated orchestration;
2. General orchestration;
3. Class C cold-start validation;
4. installed Windows human acceptance;
5. only then resumption of Stage 9 packaging/release work.

## Next authorized slice

`product-recovery-music-orchestration` is currently active. `project-context/NEXT_TASK.md` remains the entry/exit contract until this slice reaches Review and merges.
