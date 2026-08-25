# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: studio-v2-application-transactions -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository development state is idle on `main` after completion of:

- slice `studio-v2-application-transactions`;
- PR #65;
- merge commit `3b87aa0f0d0636bd7d410c8a9212aded8ec7c7be`.

No feature branch is currently active. The single authorized handoff remains `studio-v2-micro-drama-production-semantics`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-033** — MLT/editor foundation; canonical Timeline remains UV-owned.

Stage 12 deliberately did not add rich Scene/Shot/AI features. It made the Project/Studio boundary safe enough for those features.

## Stage 12 implementation state

The completed slice contains the application-foundation path:

1. typed backend-owned Production Direction identity;
2. backend projection of `modern_direction` / `legacy_compatibility` / `invalid_recovery`;
3. protected Studio identity across generic PATCH/save/import boundaries;
4. recipe-free modern Studio/media API helpers and no implicit `general_video` core creation;
5. bounded `production/` canonical storage for future D-065 documents;
6. file-first `ProjectUnitOfWork` with prepared journals, exact rollback, restart recovery and portable durable history;
7. project-level undo/redo across production documents, `project.json` references/assets and `timeline/main.json`;
8. timeline commands, media registration and Studio export registration routed through the shared transaction authority;
9. HTTP history/undo/redo plus Studio UI controls backed by canonical project history rather than browser-local state.

The exact merged review head passed 436 core tests, 228 API tests, frontend lint/build, high-severity dependency audit and all five permanent Ubuntu/Windows CI jobs. Three review findings covering command concurrency, PR-63 identity compatibility and stale export UI state were fixed and resolved before merge.

## Compatibility rule

Legacy recipe projects and pre-D-064 `studio_first` projects remain readable as explicit compatibility projects. They do not receive a fake Production Direction. Invalid/tampered Studio identity is surfaced as recovery state rather than guessed by the frontend.

Recipe/Product Orchestrator/Stage routes remain compatibility code; new Studio modules must not depend on them merely to access neutral project services.

## Next handoff

From idle `main`, `studio-v2-micro-drama-production-semantics` may now prove the shared Scene/Shot/Take contracts plus micro-drama Story/Characters/Locations/continuity extensions.
