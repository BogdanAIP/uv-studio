# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for independent review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The entry gate remains satisfied: the repository-level full-SHA GitHub Actions policy was enabled and fresh exact-tree CI run #4018 passed all five required checks before the branch was created.

The first frozen review head `5789681110c7b957ef0fa401b1f5d8d8593d6d6e` passed all five required CI checks. Codex review then reported two concrete findings; both were classified **CONFIRMED**, fixed, replied to and resolved before this refreeze:

- P1: ProjectUnitOfWork now migrates historical schema-v1 `project.json` snapshots only for current-schema validation before undo/redo, while exact recorded snapshot bytes remain authoritative for restoration;
- P2: `docs/PROJECT_STORE.md` now describes canonical Project schema v2 and persisted `compatibility.recipe_id` instead of the superseded schema-v1 persistence contract.

`tests/test_project_transactions_v1_compat.py` proves the first v1→v2 canonical transaction, exact-byte undo back to the original v1 `project.json`, and exact-byte redo to the committed v2 bytes. Draft-head CI run #4087 on `e63786ff1f2371c25a901292d5611f5b10cabc24` passed all five required checks on Ubuntu and Windows, including unit, API, real-media and browser suites.

## Frozen implementation boundary

This slice implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips;
- preserve durable ProjectUnitOfWork undo/redo when a legacy schema-v1 project is first migrated by a canonical transaction.

Recipe endpoint retirement, execution-plan changes, Product Orchestrator redesign, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters now read the legacy value through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration, allowing a schema-v1 archive to load as a current schema-v2 document without falsely comparing the old manifest version to the migrated in-memory version. Modern schema-v2 and legacy schema-v1 round trips are covered directly in Project Store/identity/archive/API tests.

ProjectUnitOfWork validation now uses the same migration boundary for staged historical `project.json` snapshots. Validation sees the current in-memory schema while undo/redo still writes the exact recorded bytes, preserving durable history across the schema transition.

## Acceptance synchronization

The implementation-head CI exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Exact-head CI run #4069 on `0775971302c46d493275f880d5c844cde14bcbaa`, the first frozen review run #4074 on `5789681110c7b957ef0fa401b1f5d8d8593d6d6e`, and post-fix draft-head run #4087 on `e63786ff1f2371c25a901292d5611f5b10cabc24` all passed the applicable five required checks. This lifecycle freeze advances the head once more, so the final frozen head must pass the five checks again.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility work and is frozen again. Merge requires the final exact `BASE_SHA..HEAD_SHA` to pass all five required CI checks, all review threads to remain resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` to report zero surviving findings. Any later material change invalidates that review and requires another fresh review.
