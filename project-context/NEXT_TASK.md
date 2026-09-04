# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Continue Draft PR #95 from lifecycle-closed `main` `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`: retire the duplicate Product Orchestrator mutation/action envelope for legacy `music_video` projects while keeping its temporary read projection and all direct Music authorities.

## Confirmed implementation state

The backend no longer projects or dispatches the five duplicate Music Product Workflow mutation actions. The specialized Music client facades now use established direct authorities:

- Music Map → `/music-map/commands`;
- Music Director → `/music-direction/commands`;
- Music Assembly → `/music-assembly/commands`;
- render → `/capabilities/video.render_music_video/execute` with `local_free_first`;
- final Review → `/music-video-review`.

No Music UI component changed.

## Latest acceptance finding

CI #4862 on frontend-repair head `698b9e5c5350c735dc687044c455b8a08b58949c` passed all 213 API tests, all 22 real-media tests, frontend lint/build and 14 of 15 browser outcomes. The Music browser journey itself completed through render, approved Review and ready Product Workflow state. It failed only because `e2e/test_music_video_outcome.py` still asserted that the UI must emit all five retired `/workflow/actions/...` POSTs; the actual observed old-action set was correctly empty.

The browser acceptance is therefore stale and must be migrated rather than removed.

## Planned bounded repair

1. Add only `e2e/test_music_video_outcome.py` to write scope and require exact-head `development-context` success before editing it.
2. Preserve the complete visible Music journey and artifact/Review/readiness assertions.
3. Replace the obsolete Product Orchestrator requirement with positive request evidence that:
   - no Music mutation POST uses `/workflow/actions/`;
   - Map posts `/music-map/commands`;
   - Direction posts `/music-direction/commands`;
   - Assembly posts `/music-assembly/commands`;
   - render posts `/capabilities/video.render_music_video/execute`;
   - final Review posts `/music-video-review`.
4. Do not broaden runtime scope or change Music UI components.
5. Require all five permanent CI jobs on the exact frozen Draft head after the acceptance repair.

## Required preservation

- all project-owned Music state, revisions, validation and fail-closed behavior;
- legacy Music Product Workflow read projection;
- direct Music domain/capability/review endpoints;
- Photo Composer and Visualizer Product Workflow actions;
- modern `Production Direction -> Studio Project` and canonical Project/Production/Timeline/Generation/Capability authorities;
- internal Recipe Registry, Stage8 and broader Product Orchestrator retirement for later bounded slices.

## Gate

The write scope will contain exactly 12 paths after adding the focused browser acceptance file. Require a successful `development-context` run on that exact scope-expanded Draft head before changing the E2E assertion. Then require exact-head permanent CI 5/5 before the normal review refreeze and fresh semantic review.
