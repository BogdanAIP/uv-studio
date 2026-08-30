# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in implementation/draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The entry gate remains satisfied: fresh exact-tree CI run #4018 passed all five required checks before the branch was created. The previously frozen head `f401f68567f5968592aa33e88681448b6f3087e6` also passed all five required checks in CI run #4093, but the fresh ordinary-ChatGPT semantic review on exact `52be1939eca51d7147990288cfc6258b023c2cd2..f401f68567f5968592aa33e88681448b6f3087e6` returned two surviving P2 findings, so that review is no longer a merge approval and the slice is reopened.

The two current confirmed findings are:

- archive export must hold the same cross-runtime project mutation fence across raw schema sampling, enumeration, hashing and ZIP capture so a legacy schema-v1 project cannot be persisted as schema v2 halfway through one backup/export;
- `docs/architecture/LEGACY_SURFACE_INVENTORY.md` is active D-070 caller/migration evidence and must be synchronized with the schema-v2 compatibility boundary and the five direct recipe-identity readers already migrated by this slice.

The earlier schema-v1 ProjectUnitOfWork undo/redo defect and stale `docs/PROJECT_STORE.md` finding remain fixed and covered.

## Implementation boundary

This slice still implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips;
- preserve durable ProjectUnitOfWork undo/redo when a legacy schema-v1 project is first migrated by a canonical transaction;
- preserve a stable project-level recovery snapshot while archive export is concurrent with canonical project mutation.

Recipe endpoint retirement, execution-plan changes, Product Orchestrator redesign, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters now read legacy identity through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration, allowing a schema-v1 archive to load as a current schema-v2 document without falsely comparing the old manifest version to the migrated in-memory version. Modern schema-v2 and legacy schema-v1 round trips are covered directly in Project Store/identity/archive/API tests. The reopened work adds stable export fencing so the manifest and exact archived project bytes come from one canonical snapshot.

ProjectUnitOfWork validation uses the same migration boundary for staged historical `project.json` snapshots. Validation sees the current in-memory schema while undo/redo still writes the exact recorded bytes, preserving durable history across the schema transition.

## Acceptance synchronization

The implementation-head CI exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Exact-head CI runs #4069, #4074, #4087 and final pre-review run #4093 all passed their applicable five required checks. Because the fresh semantic review found two material issues, the next implementation head must pass all five checks again before another review freeze.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility/recovery work and is no longer frozen while the two confirmed P2 findings are addressed. After the fixes, the branch must return to `review`, the new final exact `BASE_SHA..HEAD_SHA` must pass all five required CI checks, review threads must be resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` must report zero surviving findings. Any later material change invalidates that review and requires another fresh review.
