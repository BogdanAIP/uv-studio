# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47` after accepted `execution-plan-retirement` PR #93 and D-038 closure PR #94. Draft PR #95 is the bounded D-070 slice `legacy-music-action-envelope-retirement` on branch `chore/legacy-music-action-envelope-retirement`.

The initial PR-bound Draft context passed `development-context` on exact head `71de50b5dfbe31b43e22455c1f2df3897f690bda`. Material head `cfee9e04109cd91ee21daf83e21d24ab133e913d` removed the five Product Workflow Music actions and Music-specific backend dispatch glue while preserving the read projection.

## Fresh caller and acceptance evidence

Browser CI #4858 exposed a hidden live client seam: the Music panels use specialized facades, but `frontend/lib/musicVideoApi.ts` and `frontend/lib/musicVideoReviewApi.ts` still tunneled supported mutations through `executeProjectWorkflowAction()`. After expanding scope and passing `development-context`, head `698b9e5c5350c735dc687044c455b8a08b58949c` migrated those facades onto the already-existing direct Music Map, Direction, Assembly, capability-render and Review APIs without changing Music components.

CI #4862 then supplied the next exact finding: all 213 API tests, all 22 real-media tests, frontend lint/build and 14 of 15 browser outcomes passed. The Music browser scenario itself reached the final rendered artifact, approved Review and ready Product Workflow state, but its final assertion still required observing the five retired `/workflow/actions/...` POSTs and failed because `observed=[]`.

That failure is stale acceptance instrumentation, not a product regression. The desired post-retirement browser contract is now stronger and explicit:

- no Music POST may use `/workflow/actions/`;
- Music Map must POST `/music-map/commands`;
- Music Director must POST `/music-direction/commands`;
- Music Assembly must POST `/music-assembly/commands`;
- render must POST `/capabilities/video.render_music_video/execute`;
- final Review must POST `/music-video-review`;
- the same visible journey must still produce the current rendered artifact, approved Review and `workflow.readiness == ready`.

The write scope is therefore expanded only by `e2e/test_music_video_outcome.py`. This acceptance file may be updated only after `development-context` succeeds on the exact scope-expanded Draft head.

## Bounded retirement target

Retire only the duplicate Music mutation/action envelope end to end while preserving read compatibility and user-visible behavior:

- keep `GET /api/uv/projects/{id}/workflow` for Music readiness/prerequisites/workspace/current-outcome compatibility;
- keep Music `next_actions` retired;
- keep Music-specific Product Orchestrator mutation request/dispatch glue removed;
- keep specialized Music clients on the established direct domain/capability/review endpoints;
- update the browser acceptance to positively prove that direct transport and the absence of Product Orchestrator Music mutation calls;
- preserve all project-owned Music state, revisions, validation and fail-closed behavior.

## Guardrails

Do not change Music UI components, Photo Composer or Visualizer Product Workflow actions. Do not retire Product Orchestrator GET/read projection, internal Recipe Registry, the legacy project route, Stage8, other directions, or Music domain services. Do not introduce another recipe-like action planner or new mutation endpoint.

## Verification plan

Require `development-context` success on the exact 12-path scope-expanded Draft head before editing the E2E file. Then require all five permanent CI jobs on the exact frozen Draft head. Before merge, perform the normal context-only `draft -> review` refreeze, exact review-head 5/5 and fresh ordinary-ChatGPT semantic review on the frozen BASE/HEAD.
