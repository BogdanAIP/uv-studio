# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for independent review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The entry gate is satisfied: the repository-level full-SHA GitHub Actions policy was enabled and fresh exact-tree CI run #4018 passed all five required checks before the branch was created.

## Frozen implementation boundary

This slice implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips.

Recipe endpoint retirement, execution-plan changes, Product Orchestrator redesign, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters now read the legacy value through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration, allowing a schema-v1 archive to load as a current schema-v2 document without falsely comparing the old manifest version to the migrated in-memory version. Modern schema-v2 and legacy schema-v1 round trips are covered directly in Project Store/identity/archive/API tests.

## Acceptance synchronization

The implementation-head CI exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests now wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Exact-head CI run #4069 on `0775971302c46d493275f880d5c844cde14bcbaa` passed all five required checks, including the Windows browser suite. The lifecycle freeze changes the head, so the final review head must pass the five checks again.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility work and is now frozen. Merge requires the final exact `BASE_SHA..HEAD_SHA` to pass all five required CI checks and receive a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` with zero surviving findings. Any material post-review fix makes that review stale and returns the slice to implementation work before a new review.
