# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-application-transactions -->

**Updated:** 2026-08-25

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Active Stage 12 foundation slice:

- slice `studio-v2-application-transactions`;
- branch `stage-12/studio-v2-application-transactions`;
- PR #65 (draft);
- base idle `main` at `a9c3c38b05e6ed37f8efdad9e28c340fce4a4854`;
- last completed PR #64 `architecture-authority-cleanup`, merge `e213315643bf5d0b724c23bb725f10cda0a96e95`.

## Current architecture authority

- **D-064** — Production Directions over one shared Studio Core.
- **D-065** — shared Production Semantic Core beneath directions.
- **D-033** — MLT/editor foundation; canonical Timeline remains UV-owned.

The current slice does not add rich Scene/Shot/AI features yet. It first makes the Project/Studio boundary safe enough for those features.

## Stage 12 implementation state

The slice now contains the complete application-foundation path under review:

1. typed backend-owned Production Direction identity;
2. backend projection of `modern_direction` / `legacy_compatibility` / `invalid_recovery`;
3. protected Studio identity across generic PATCH/save/import boundaries;
4. recipe-free modern Studio/media API helpers and no implicit `general_video` core creation;
5. bounded `production/` canonical storage for future D-065 documents;
6. file-first `ProjectUnitOfWork` with prepared journals, exact rollback, restart recovery and portable durable history;
7. project-level undo/redo across production documents, `project.json` references/assets and `timeline/main.json`;
8. timeline commands, media registration and Studio export registration routed through the shared transaction authority;
9. HTTP history/undo/redo plus Studio UI controls backed by canonical project history rather than browser-local state.

Local proof currently passes 435 core tests, 228 API tests, frontend lint/build and high-severity dependency audit. Exact-head required checks remain the merge authority.

## Compatibility rule

Legacy recipe projects and pre-D-064 `studio_first` projects remain readable as explicit compatibility projects. They do not receive a fake Production Direction. Invalid/tampered Studio identity is surfaced as recovery state rather than guessed by the frontend.

Recipe/Product Orchestrator/Stage routes remain compatibility code; new Studio modules must not depend on them merely to access neutral project services.

## Next handoff

After this transaction foundation is reviewed, merged and lifecycle-closed, `studio-v2-micro-drama-production-semantics` will prove the shared Scene/Shot/Take contracts plus micro-drama Story/Characters/Locations/continuity extensions.
