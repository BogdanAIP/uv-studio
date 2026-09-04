# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` remains `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`. PR #95 has returned from review to Draft after validation of an unresolved P2 review finding on review head `cd5bea656ef2e7612bda46f9c324d933103860ae`.

The previously frozen implementation passed exact review-head CI 5/5, but review identified a semantic regression in the direct Music render boundary. BASE Product Workflow enabled `render_music_master` only when `assembly is not None and rhythm_aligned and render_ready`. After the action-envelope migration, `frontend/lib/musicVideoApi.ts` calls `video.render_music_video` directly, while `uv_studio/capabilities/adapters/music_video_render.py::render_music_video_state()` validates current Map/Direction/Assembly revisions and media bytes but does not execute `MusicDirectionStore.rhythm_audit()` or reject an unaligned current direction.

This finding is confirmed and material: a direct render can now create a master for an unaligned Music Director state that the retired Product Workflow action previously blocked.

## Bounded repair

The canonical fix belongs at the direct execution boundary, not in the UI or a replacement workflow layer:

- require the current `MusicDirectionStore.rhythm_audit(project_id)` result to report `summary.all_aligned == true` before any FFmpeg render is started;
- reject an unaligned current direction as invalid capability input, preserving fail-closed semantics for all direct callers;
- extend the existing focused real-media render acceptance to prove an unaligned assembly is rejected before render and the aligned path still succeeds;
- keep the five Product Workflow Music mutation actions retired and keep the specialized clients on direct domain/capability endpoints.

The write scope is expanded only by `uv_studio/capabilities/adapters/music_video_render.py` and `tests_real_media/test_music_video_render_real_media.py`. No Music UI component, Product Workflow action, Stage8 surface or new endpoint is added.

## Gate

PR #95 is Draft before any material repair. Require `development-context` success on the exact scope-expanded Draft head before editing the two newly added paths. Then require exact-head permanent CI 5/5, re-freeze context to review, mark Ready, require exact review-head 5/5, and obtain a new genuinely fresh ordinary-ChatGPT semantic review. The old review identity is superseded once material bytes change.
