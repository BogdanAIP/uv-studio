# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: legacy-music-action-envelope-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47` after accepted `execution-plan-retirement` PR #93 and D-038 closure PR #94. PR #95 is now frozen for review as bounded D-070 slice `legacy-music-action-envelope-retirement` on branch `chore/legacy-music-action-envelope-retirement`.

The final material Draft head is `bf11b97f9a6ef4c3d57e15831cf3b855cabf4dd2`. CI #4872 completed SUCCESS with all five permanent jobs green, including the Stage 4C + Stage 5 browser user-outcome suite on Ubuntu and Windows. Duplicate exact-head CI #4871 also completed SUCCESS.

## Accepted implementation boundary for review

The slice retires only the duplicate Music mutation/action envelope:

- Product Workflow no longer projects or dispatches the five Music mutation actions;
- `GET /api/uv/projects/{id}/workflow` remains as temporary read compatibility for Music readiness/prerequisites/workspace/current-outcome state;
- specialized Music clients preserve their public UI-facing functions but now call the established direct Music Map, Direction, Assembly, capability-render and Review endpoints;
- browser acceptance requires zero Music POSTs to `/workflow/actions/` and positively observes all five direct mutation paths while preserving the same rendered artifact, approved Review and ready workflow state;
- Photo Composer and Visualizer Product Workflow actions remain unchanged.

## Evidence chain

CI #4858 exposed the hidden live frontend caller seam after backend retirement. After scope expansion and a successful `development-context`, the specialized clients were migrated to direct authorities. CI #4862 then showed the Music user journey itself was healthy but the final browser assertion still required retired workflow-action POSTs. After a second scoped `development-context`, the E2E network assertion was migrated to the post-retirement direct-transport contract. Exact final material head `bf11b97f9a6ef4c3d57e15831cf3b855cabf4dd2` then passed permanent CI 5/5.

## Review freeze

The transition from Draft to review changes project context only. Product/runtime/frontend/E2E implementation remains frozen at the exact bytes already proven on `bf11b97f9a6ef4c3d57e15831cf3b855cabf4dd2`.

## Guardrails

Do not change Music UI components, Photo Composer or Visualizer Product Workflow actions. Do not retire Product Orchestrator GET/read projection, internal Recipe Registry, the legacy project route, Stage8, other directions, or Music domain services. Do not introduce another recipe-like action planner or new mutation endpoint.

## Review gate

Mark PR #95 Ready, require all five permanent CI jobs on the exact context-only review head, then obtain a genuinely fresh ordinary-ChatGPT semantic review governed by BASE `.agents/skills/code-review/SKILL.md`. Merge only an exact reviewed head with `PASS`, `review_validity=CURRENT`, zero findings and clean exact-head CI, then perform the mandatory separate D-038 lifecycle closure.
