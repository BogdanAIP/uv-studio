# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen review head `dff66391cdf9101695dbac8ec72c0a31c86f1051` passed exact-head CI run #4141 **5/5**, but its required fresh ordinary-ChatGPT semantic review reported one surviving P2 source-upload/archive snapshot race. The development context independently confirmed that finding, returned the PR and durable context to draft, and corrected the race without broadening Stage 19 into later D-070 retirement work.

The corrected implementation head is `c1499d571531a5463e80d01275725869a296fce7`. Exact-head CI run #4146 completed **5/5 SUCCESS**, including both bootstrap jobs and both full app-baseline jobs on Ubuntu and Windows. This context-only transition now freezes that implementation for a new exact-head review cycle; no further runtime changes are permitted unless review finds another concrete defect and the lifecycle returns to draft first.

The earlier schema-v1 ProjectUnitOfWork undo/redo defect, Project Store documentation drift, archive schema-snapshot race, active D-070 inventory drift, technical-lock symlink defect and archive portability-documentation drift remain fixed. Current inline review threads remain resolved.

## Implementation boundary

This slice implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips;
- preserve durable ProjectUnitOfWork undo/redo when a legacy schema-v1 project is first migrated by a canonical transaction;
- preserve one stable project-level recovery snapshot while archive export is concurrent with canonical project mutation, including source-media publication;
- preserve the archive's fail-closed symlink safety while excluding only the ordinary technical task-record lock file from portable backups;
- keep the current archive documentation synchronized with that exact portability/recovery contract.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters read legacy identity through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration. Archive export holds the canonical project mutation fence for the whole snapshot so the manifest and archived bytes cannot straddle a concurrent canonical project mutation. The technical task-record lock is non-portable only when it is an ordinary file; symlink occupancy at that lexical path fails closed before lock acquisition and before transient filtering.

Source upload now streams incomplete request bytes into an exclusive staging file at the Project Store root, outside every canonical project directory. Only completed bytes enter the canonical project under `ProjectTaskRecordStore.project_lock`; final `os.replace`, media probing, source-reference registration and failure cleanup are serialized with archive export. The deterministic concurrency regression test proves an export holding the snapshot fence sees the complete pre-publication Project, while source publication waits and becomes fully registered only after export releases the fence.

ProjectUnitOfWork validation uses the same migration boundary for staged historical `project.json` snapshots. Validation sees the current in-memory schema while undo/redo still writes the exact recorded bytes, preserving durable history across the schema transition.

## Acceptance synchronization

The implementation-head CI previously exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Corrected implementation head `c1499d571531a5463e80d01275725869a296fce7` passed CI run #4146 **5/5**, including API integration, real-media golden coverage, frontend lint/audit/build and Stage 4C + Stage 5 browser user-outcome suites on the applicable platforms.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility/recovery/concurrency work and is now frozen again for review. The new exact frozen `BASE_SHA..HEAD_SHA` must pass all five required CI checks with PR #89 non-draft, every inline review thread must remain resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0 must report zero surviving findings. The earlier review on `dff66391cdf9101695dbac8ec72c0a31c86f1051` is stale by construction. Any material change after this freeze invalidates the new review and requires returning to draft before editing runtime code.
