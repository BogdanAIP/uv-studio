# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Continue Draft PR #95 from lifecycle-closed `main` `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`: retire the duplicate Product Orchestrator mutation/action envelope for legacy `music_video` projects while keeping its temporary read projection and all direct Music authorities.

## Corrected caller proof

The legacy `/projects/{id}` page reads Product Workflow state for Music readiness/workspace projection and renders specialized Music panels. The panels themselves call `musicVideoApi.ts` / `musicVideoReviewApi.ts`, but CI #4858 proved those two client facades still hid the retired Product Workflow mutation seam:

- `musicVideoApi.ts` routed set Map, set Direction, set Assembly and render through `executeProjectWorkflowAction()`;
- `musicVideoReviewApi.ts` routed final Review through `executeProjectWorkflowAction()`.

The first browser Music outcome failed at `save_music_map` after backend retirement, while API integration and frontend build were otherwise green. GitHub Code Search returned false zero results for these known symbols, so exact-head file inspection and browser evidence remain authoritative.

## Planned bounded repair

1. Keep Music goal/readiness/prerequisites/relevant workspaces in `music_workflow_state()` for legacy read compatibility and keep Music `next_actions` retired.
2. Keep Music-specific Product Orchestrator request/dispatch glue removed.
3. Change only `frontend/lib/musicVideoApi.ts` so set Map/Direction/Assembly call their existing `/commands` endpoints and render calls the existing `video.render_music_video` capability execution endpoint directly.
4. Change only `frontend/lib/musicVideoReviewApi.ts` so final Review calls the existing `/music-video-review` endpoint directly.
5. Preserve the current exported client functions and browser-visible panel behavior so Music components need no edits.
6. Synchronize D-070 architecture/inventory docs with accepted PR #93/#94 history and current PR #95 evidence.

## Required preservation

- all project-owned Music state, revisions, validation and fail-closed behavior;
- existing Music Map, Direction, Assembly, capability render and Review endpoints;
- legacy Music Product Workflow read projection;
- Photo Composer and Visualizer Product Workflow actions;
- modern `Production Direction -> Studio Project` and canonical Project/Production/Timeline/Generation/Capability authorities;
- internal Recipe Registry, Stage8 and broader Product Orchestrator retirement for later bounded slices.

## Gate

The write scope now includes exactly two additional frontend client files. Require a successful `development-context` run on the exact scope-expanded Draft head before editing them. After the repair and doc synchronization, require all five permanent CI jobs on the exact frozen Draft head before the normal review refreeze and fresh semantic review.
