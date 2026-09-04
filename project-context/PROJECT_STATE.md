# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47` after accepted `execution-plan-retirement` PR #93 and D-038 closure PR #94. Draft PR #95 is the bounded D-070 slice `legacy-music-action-envelope-retirement` on branch `chore/legacy-music-action-envelope-retirement`.

The initial PR-bound Draft context passed `development-context` on exact head `71de50b5dfbe31b43e22455c1f2df3897f690bda`. Material head `cfee9e04109cd91ee21daf83e21d24ab133e913d` then removed the five Product Workflow Music actions and Music-specific backend dispatch glue while preserving the read projection.

## Fresh caller evidence and scope correction

Initial file inspection correctly found that the rendered Music panels import specialized Music clients rather than calling Product Workflow directly. However, exact-head browser acceptance CI #4858 exposed a hidden client seam: `frontend/lib/musicVideoApi.ts` still routed Music Map, Direction, Assembly and render mutations through `executeProjectWorkflowAction()`, and `frontend/lib/musicVideoReviewApi.ts` still routed final Review through the same Product Orchestrator action endpoint.

This is a real supported caller, not a flaky browser failure. Ubuntu and Windows API integration, server probe and frontend build progressed successfully; the Stage 4C/5 Music browser outcome failed when `save_music_map` reached the retired `/workflow/actions/...` contract.

Direct domain/execution authorities already exist and remain the canonical destination:

- Music Map: `POST /api/uv/projects/{id}/music-map/commands`;
- Music Director: `POST /api/uv/projects/{id}/music-direction/commands`;
- Music Assembly: `POST /api/uv/projects/{id}/music-assembly/commands`;
- Music render: `POST /api/uv/projects/{id}/capabilities/video.render_music_video/execute` with `local_free_first`;
- final Review: `POST /api/uv/projects/{id}/music-video-review`.

The write scope is therefore expanded only by `frontend/lib/musicVideoApi.ts` and `frontend/lib/musicVideoReviewApi.ts`. Music UI components themselves do not require changes.

## Bounded retirement target

Retire only the duplicate Music mutation/action envelope end to end:

- preserve `GET /api/uv/projects/{id}/workflow` for Music goal/readiness/prerequisites/workspaces while the legacy page still needs it;
- stop projecting Music `next_actions` through Product Workflow;
- remove Music mutation request/dispatch glue from `uv_studio/api/project_workflow.py`;
- move the two specialized Music client facades from Product Workflow action calls onto the already-established direct Music/capability/review APIs;
- preserve all project-owned Music state and existing browser-visible behavior;
- keep the focused Product Workflow test as retirement/read-compatibility proof and rely on direct Music API suites plus browser acceptance for mutation semantics.

## Guardrails

Do not change Music UI components, Photo Composer or Visualizer Product Workflow actions. Do not retire Product Orchestrator GET/read projection, internal Recipe Registry, the legacy project route, Stage8, other directions, or the Music domain services themselves. Do not introduce another recipe-like action planner or new mutation endpoint.

## Verification plan

Before modifying the newly added frontend paths, require `development-context` success on this exact scope-expanded Draft head. Then require exact-head permanent CI 5/5. Before merge, perform the normal context-only `draft -> review` refreeze, exact review-head 5/5 and fresh ordinary-ChatGPT semantic review on the frozen BASE/HEAD.
