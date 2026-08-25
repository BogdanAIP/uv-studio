# Project State

<!-- uv-context-state: draft -->
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

## Stage 12 implementation order

1. typed backend-owned Production Direction identity;
2. backend projection of `modern_direction` / `legacy_compatibility` / `invalid_recovery`;
3. protect Studio identity against generic PATCH/save/import corruption;
4. decouple modern Studio/media API helpers from Recipe Registry/Product Orchestrator imports;
5. remove implicit `general_video` creation from the Project Store/core compatibility surfaces;
6. establish bounded `production/` canonical storage for future D-065 documents;
7. after those P0 boundaries are green, establish Project Unit of Work + transaction/undo authority across production documents, project references/assets and Timeline state.

## Compatibility rule

Legacy recipe projects and pre-D-064 `studio_first` projects remain readable as explicit compatibility projects. They do not receive a fake Production Direction. Invalid/tampered Studio identity is surfaced as recovery state rather than guessed by the frontend.

Recipe/Product Orchestrator/Stage routes remain compatibility code; new Studio modules must not depend on them merely to access neutral project services.

## Next handoff

After this transaction foundation is complete, `studio-v2-micro-drama-production-semantics` will prove the shared Scene/Shot/Take contracts plus micro-drama Story/Characters/Locations/continuity extensions.
