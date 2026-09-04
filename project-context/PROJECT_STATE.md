# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47` after accepted `execution-plan-retirement` PR #93 and D-038 closure PR #94. Draft PR #95 is the bounded D-070 slice `legacy-music-action-envelope-retirement` on branch `chore/legacy-music-action-envelope-retirement`.

The initial write scope was recorded before any product change. Product implementation remains blocked until `development-context` succeeds on an exact Draft head that is bound to PR #95.

## Fresh caller evidence

Current Product Workflow projection has live read/workspace paths only for `photo_to_video`, `visualizer` and `music_video`; other historical recipe handlers are not exposed by `project_workflow_state()` and therefore are not valid first migration targets.

For `music_video`, the legacy `/projects/{id}` page still consumes Product Workflow only as a read-only journey/workspace projection. Its rendered Music panels already mutate state directly through dedicated Music domain APIs:

- Music Map via `/music-map/commands`;
- Music Director via `/music-direction/commands`;
- Music Assembly and render via dedicated Music APIs;
- clip/final review via dedicated Music review APIs.

The remaining duplicate authority is the Product Orchestrator action envelope that projects and dispatches `save_music_map`, `save_music_direction`, `save_music_assembly`, `render_music_master` and `review_music_master`.

## Bounded retirement target

Retire only that duplicate Music mutation/action envelope:

- preserve `GET /api/uv/projects/{id}/workflow` for Music goal/readiness/prerequisites/workspaces while the legacy page still needs it;
- stop projecting Music `next_actions` through Product Workflow;
- remove Music mutation request/dispatch glue from `uv_studio/api/project_workflow.py`;
- preserve direct Music Map/Direction/Assembly/Render/Review APIs and all project-owned Music state;
- convert the dedicated Music Product Workflow API test into proof that the read projection remains and the retired mutation actions fail closed, while existing direct Music API suites remain authoritative for mutation semantics.

## Guardrails

Do not change Photo Composer or Visualizer Product Workflow actions. Do not retire Product Orchestrator GET/read projection, internal Recipe Registry, the legacy project route, Stage8, other directions, or the Music domain services themselves. Do not introduce another recipe-like action planner.

## Verification plan

Require `development-context` success on PR #95 exact Draft head before changing product/test/docs paths inside the declared write scope. Before review, require all five permanent CI checks and a fresh ordinary-ChatGPT semantic review on the frozen exact BASE/HEAD.
