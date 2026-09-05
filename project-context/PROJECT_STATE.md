# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-05

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` remains `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`. PR #95 has returned to Draft after a new review finding on superseded review head `9c55b852175dd882ccde85c3e39e2395d9af04f1`.

The previous confirmed P2 is repaired: direct `video.render_music_video` now requires `MusicDirectionStore.rhythm_audit(project_id)` to report `summary.all_aligned == true` before media execution. Material Draft head `cb9852c6ee8b59020d00c0adc8c1b309705cced2` passed exact-head CI #4888 with all five permanent jobs SUCCESS, and the context-only review refreeze `9c55b852175dd882ccde85c3e39e2395d9af04f1` had a successful push CI #4889.

## New confirmed P2

The review on `9c55b852175dd882ccde85c3e39e2395d9af04f1` identified a revision-consistency race in the repaired rhythm gate. `render_music_video_state()` first loads and validates Assembly A1 and Direction D1, then calls `MusicDirectionStore.rhythm_audit(project_id)`. That audit independently reloads the latest Direction and Music Map and returns their revision hashes. The adapter currently checks only `summary.all_aligned` and ignores those revision hashes.

Therefore a concurrent Direction update between the first reads and the audit can make an aligned D2 audit authorize rendering an older A1/D1 assembly. The finding is material and blocking.

## Bounded repair

Keep the repair at the existing canonical direct execution boundary and inside the already-authorized 14-path write scope:

- require the rhythm audit's `music_direction_revision_sha256` to equal both the loaded Direction revision and `assembly.music_direction_revision_sha256`;
- require the audit's `music_map_revision_sha256` to equal the loaded current Music Map revision;
- reject any revision mismatch before source probing or FFmpeg/FFprobe execution;
- add focused regression coverage proving an aligned audit from a different Direction revision cannot authorize the loaded Assembly;
- preserve the existing unaligned rejection and aligned real-media success cases;
- do not add locks around long-running FFmpeg execution, restore Product Workflow mutation actions, or add a new UI gate or endpoint.

The old review identity is superseded. Before material edits, require `development-context` SUCCESS on this exact Draft context head. After repair, require exact Draft-head permanent CI 5/5, then a context-only review refreeze, Ready state, exact review-head 5/5, no unresolved findings, and a new genuinely fresh ordinary-ChatGPT semantic review.
