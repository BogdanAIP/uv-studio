# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen again for independent review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The entry gate remains satisfied: fresh exact-tree CI run #4018 passed all five required checks before the branch was created.

The prior fresh ordinary-ChatGPT semantic review on exact `52be1939eca51d7147990288cfc6258b023c2cd2..f401f68567f5968592aa33e88681448b6f3087e6` reported two P2 findings. Both are now addressed before this refreeze:

- archive export holds the same cross-runtime project mutation fence used by canonical transactions across raw schema sampling, file enumeration, hashing and ZIP capture; the technical `tasks/.uv-task-records.lock` is excluded from portable archives;
- `docs/architecture/LEGACY_SURFACE_INVENTORY.md` is synchronized with the schema-v2 compatibility boundary and the five direct recipe-identity runtime readers already migrated by Stage 19.

A deterministic archive concurrency regression test pauses a schema-v1 export after raw schema sampling, proves a concurrent `ProjectUnitOfWork` waits for the fence, verifies that the ZIP remains an internally consistent schema-v1 snapshot, verifies the transient lock file is absent, and proves the archive still imports after the source project has been canonically persisted as schema v2. The test passed on both Ubuntu and Windows in draft-head CI run #4105 on `5ce3b6776eb2f8e09463e20da3e4f2fb8d2eda9e`.

The earlier schema-v1 ProjectUnitOfWork undo/redo defect and stale `docs/PROJECT_STORE.md` finding remain fixed and covered.

## Frozen implementation boundary

This slice implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips;
- preserve durable ProjectUnitOfWork undo/redo when a legacy schema-v1 project is first migrated by a canonical transaction;
- preserve one stable project-level recovery snapshot while archive export is concurrent with canonical project mutation.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters read legacy identity through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration, allowing a schema-v1 archive to load as a current schema-v2 document without falsely comparing the old manifest version to the migrated in-memory version. Archive export now holds the canonical project mutation fence for the whole snapshot, so the manifest and archived bytes cannot straddle a concurrent canonical project mutation.

ProjectUnitOfWork validation uses the same migration boundary for staged historical `project.json` snapshots. Validation sees the current in-memory schema while undo/redo still writes the exact recorded bytes, preserving durable history across the schema transition.

## Acceptance synchronization

The implementation-head CI previously exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Exact-head CI runs #4069, #4074, #4087, #4093 and post-review draft-head run #4105 all passed their applicable five required checks. This lifecycle refreeze advances the branch head again, so the new frozen exact head must pass all five required checks before independent review is accepted for merge.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility/recovery work and is frozen again. Merge requires the final exact `BASE_SHA..HEAD_SHA` to pass all five required CI checks, all review threads to remain resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` to report zero surviving findings. Any later material change invalidates that review and requires another fresh review.
