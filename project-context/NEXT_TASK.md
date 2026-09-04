# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Execute the first bounded D-070 legacy direction/tool migration slice from lifecycle-closed `main` `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`: retire the duplicate Product Orchestrator mutation/action envelope for legacy `music_video` projects without removing the Music workflow read projection or direct Music domain authorities.

## Caller proof

The legacy `/projects/{id}` page still reads Product Workflow state for `music_video`, but its Music panels already save Music Map, visual direction, Assembly/render and Review through dedicated Music APIs. Therefore no supported UI caller requires Product Workflow Music mutation actions.

`project_workflow_state()` currently exposes live Product Workflow projections only for `photo_to_video`, `visualizer` and `music_video`; historical dubbing/targeted/general/narrated workflow action handlers are not the live first-migration target.

GitHub Code Search is not absence proof in this repository. Use exact-head file inspection, focused regression tests and permanent CI.

## Planned bounded changes

1. Keep Music goal/readiness/prerequisites/relevant workspaces in `music_workflow_state()` for legacy read compatibility.
2. Remove the five duplicate Music Product Workflow `next_actions`: map, direction, assembly, render and final review.
3. Remove Music-specific Product Orchestrator request/dispatch glue from `uv_studio/api/project_workflow.py`.
4. Rework `tests_api/test_music_workflow_api.py` to prove the read projection survives while retired Music workflow actions are unavailable/fail closed.
5. Rely on existing direct Music API suites for canonical Music Map, Direction, Assembly, render/review semantics.
6. Synchronize D-070 architecture/inventory docs to the bounded candidate state.

## Required preservation

- direct Music Map, Direction, Assembly, render and Review APIs;
- all project-owned Music state and revision/fail-closed behavior;
- legacy Music workflow goal/readiness/prerequisites/workspaces needed by `/projects/{id}`;
- Photo Composer and Visualizer Product Workflow actions;
- modern `Production Direction -> Studio Project` and canonical Project/Production/Timeline/Generation/Capability authorities;
- internal Recipe Registry, Stage8 and broader Product Orchestrator retirement for later slices.

## Gate

Record the actual Draft PR number in `ACTIVE_SLICE.json`, obtain a successful `development-context` run on that exact head, then make product changes only within the declared write scope. Before Ready, require exact-head 5/5 permanent CI and fresh semantic review on the frozen review head.
