# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Repair the confirmed P2 in Draft PR #95 without restoring the retired Product Orchestrator Music mutation envelope.

## Confirmed review finding

The review head `cd5bea656ef2e7612bda46f9c324d933103860ae` had clean exact-head CI, but a live review thread identified a semantic regression in render prerequisites. Independent validation confirmed it:

- BASE `render_music_master` was enabled only when `assembly is not None`, `rhythm_aligned` and render capability availability were all true;
- the new direct `video.render_music_video` handler validates current Map/Direction/Assembly revisions and source bytes but does not run `MusicDirectionStore.rhythm_audit()`;
- therefore a caller can render an unaligned current Music Director state that the retired action path previously blocked.

## Bounded repair plan

1. Keep PR #95 in Draft.
2. Expand write scope only to `uv_studio/capabilities/adapters/music_video_render.py` and `tests_real_media/test_music_video_render_real_media.py`.
3. Require exact-head `development-context` success before editing those paths.
4. At the canonical direct render boundary, compute the current direction rhythm audit and fail closed unless `summary.all_aligned is true`, before FFmpeg materialization.
5. Add focused acceptance proving an unaligned current direction/assembly is rejected while the existing aligned render path remains green.
6. Do not change Music UI components, add a new endpoint, restore Product Workflow Music actions, or widen into broader Product Orchestrator/Stage8 retirement.
7. After repair require exact Draft-head permanent CI 5/5, context-only review refreeze, Ready, exact review-head 5/5 and a new fresh ordinary-ChatGPT semantic review on the new HEAD.

The unresolved review thread remains blocking until this repair is proven and the exact finding is answered/resolved.
