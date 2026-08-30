# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in implementation/draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The latest frozen head `a900c770f527956a709ec4523b1f23292d368a44` passed exact-head CI run #4131 **5/5**, but a new automated review thread then found one surviving P2 documentation-contract inconsistency. That head is therefore no longer a merge candidate and the slice is reopened.

The confirmed finding is documentation-specific but contract-relevant: archive export intentionally excludes the ordinary technical file `tasks/.uv-task-records.lock` from portable backups while holding the shared project mutation fence, but `docs/PROJECT_ARCHIVES.md` still states that a portable archive is one complete canonical project directory and that every regular project file is declared and hashed. The archive document must explicitly define this technical transient-file exception and the stable-snapshot behavior under the project fence without weakening the existing symlink/special-entry fail-closed contract.

The earlier schema-v1 ProjectUnitOfWork undo/redo defect, Project Store documentation drift, archive schema-snapshot race, active D-070 inventory drift and technical-lock symlink defect remain fixed and covered.

## Implementation boundary

This slice still implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips;
- preserve durable ProjectUnitOfWork undo/redo when a legacy schema-v1 project is first migrated by a canonical transaction;
- preserve one stable project-level recovery snapshot while archive export is concurrent with canonical project mutation;
- preserve the archive's fail-closed symlink safety while excluding only the ordinary technical task-record lock file from portable backups;
- keep the current archive documentation synchronized with that exact portability/recovery contract.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters read legacy identity through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration. Archive export holds the canonical project mutation fence for the whole snapshot so the manifest and archived bytes cannot straddle a concurrent canonical project mutation. The technical task-record lock is non-portable only when it is an ordinary file; symlink occupancy at that lexical path fails closed before lock acquisition and before transient filtering.

ProjectUnitOfWork validation uses the same migration boundary for staged historical `project.json` snapshots. Validation sees the current in-memory schema while undo/redo still writes the exact recorded bytes, preserving durable history across the schema transition.

## Acceptance synchronization

The implementation-head CI previously exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Exact-head CI runs #4069, #4074, #4087, #4093, #4105, #4111, #4112, #4127 and #4131 passed their applicable five required checks. Because the new confirmed P2 requires a branch change, the next implementation head must pass all five checks again before another review freeze.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility/recovery/security work and is no longer frozen while the confirmed archive-documentation contract drift is corrected. After the fix, the branch must return to `review`, the new exact `BASE_SHA..HEAD_SHA` must pass all five required CI checks, every inline review thread must be resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` must report zero surviving findings. Any later material change invalidates that review and requires another fresh review.
