# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Repair the confirmed revision-consistency P2 in Draft PR #95 without restoring the retired Product Orchestrator Music mutation envelope.

## Confirmed review finding

The superseded review head `9c55b852175dd882ccde85c3e39e2395d9af04f1` repaired the original missing rhythm prerequisite, but its guard is not bound to the loaded Assembly/Direction snapshot:

- `render_music_video_state()` loads current Assembly A1 and Direction D1 and verifies `assembly.music_direction_revision_sha256 == direction.revision_sha256`;
- `MusicDirectionStore.rhythm_audit(project_id)` then reloads the latest Direction and Music Map independently;
- the audit returns exact `music_direction_revision_sha256` and `music_map_revision_sha256`, but the adapter checks only `summary.all_aligned`;
- a concurrent aligned D2 can therefore authorize rendering older A1/D1 bytes even when D1 itself is unaligned.

## Bounded repair plan

1. Keep PR #95 in Draft.
2. Keep the existing 14-path write scope unchanged; the canonical adapter and its focused real-media test are already authorized paths.
3. Require exact-head `development-context` SUCCESS before material edits.
4. At the direct render boundary, fail closed unless the rhythm audit Direction revision equals both the loaded Direction revision and the Assembly-bound Direction revision, and the audit Map revision equals the loaded current Music Map revision.
5. Add a focused race regression where an apparently aligned audit reports a different Direction revision; require rejection before FFmpeg/FFprobe execution and no render artifact.
6. Preserve the existing valid misalignment rejection, aligned real-media render success, direct Music clients and read-only Product Workflow projection.
7. After repair require exact Draft-head permanent CI 5/5, context-only review refreeze, Ready, exact new review-head 5/5, resolved review threads and a new genuinely fresh ordinary-ChatGPT semantic review.

The old review identity is superseded and must not be reused.
