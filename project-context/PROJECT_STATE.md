# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in implementation/draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `87a018abebea1dbcd5959921603b53305b02d5f5` passed exact-head CI run #4150 **5/5**, but its required fresh ordinary-ChatGPT semantic review reported one surviving P2 recovery/concurrency finding. The development context independently validated that finding as **CONFIRMED**: archive export holds the shared project snapshot fence, while existing targeted-edit and local-FFmpeg artifact publishers can still write bytes directly into canonical `artifacts/` outside that fence and register their Project references only afterwards. Export can therefore capture orphan or changing artifact bytes while canonical metadata remains frozen.

The review on `87a018abebea1dbcd5959921603b53305b02d5f5` is stale because this confirmed finding requires a material runtime/concurrency fix. PR #89 is draft again. The active write scope is expanded narrowly to the two affected publishers and their focused tests, plus the existing direct-canonical-store fence test. The fix must preserve long-running copy/render work outside the project fence while moving only canonical publication and metadata registration under the shared snapshot authority.

The earlier schema-v1 ProjectUnitOfWork undo/redo defect, Project Store documentation drift, archive schema-snapshot race, active D-070 inventory drift, technical-lock symlink defect, archive portability-documentation drift and source-upload snapshot race remain fixed. Existing inline review threads remain resolved.

## Implementation boundary

This slice still implements only the D-070 Project identity/schema compatibility boundary:

- advance the canonical Project document to schema v2;
- keep schema-v1 project files and `.uvproj.zip` archives readable through the existing migration boundary;
- preserve exact known, known-but-uncreatable and unknown historical recipe IDs as explicit compatibility state rather than canonical product identity;
- move direct Project runtime reads of legacy recipe identity behind an explicit compatibility accessor;
- keep the compatibility Project HTTP surface working while its `recipe_id` field is derived from compatibility state;
- preserve project/source/artifact/media/Timeline identifiers and paths across migration and archive round trips;
- preserve durable ProjectUnitOfWork undo/redo when a legacy schema-v1 project is first migrated by a canonical transaction;
- preserve one stable project-level recovery snapshot while archive export is concurrent with canonical project mutation, including source and artifact publication;
- preserve the archive's fail-closed symlink safety while excluding only the ordinary technical task-record lock file from portable backups;
- keep the current archive documentation synchronized with that exact portability/recovery contract.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain explicitly outside this slice.

## Implemented compatibility boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`, so schema-v1 compatibility is centralized instead of scattering version checks across runtime code. Schema v2 keeps legacy recipe information in a dedicated compatibility object; current serializers no longer treat top-level `recipe_id` as canonical Project identity. The identity classifier, compatibility API, Stage8 compatibility readers, music-video readers and render adapters read legacy identity through the explicit compatibility accessor.

Archive import validates the manifest against the archive's raw Project schema before migration. Archive export holds the canonical project mutation fence for the whole snapshot so the manifest and archived bytes cannot straddle a concurrent canonical project mutation. The technical task-record lock is non-portable only when it is an ordinary file; symlink occupancy at that lexical path fails closed before lock acquisition and before transient filtering.

Source upload streams incomplete request bytes into an exclusive staging file at the Project Store root, outside every canonical project directory. Only completed bytes enter the canonical project under `ProjectTaskRecordStore.project_lock`; final `os.replace`, media probing, source-reference registration and failure cleanup are serialized with archive export. The deterministic concurrency regression test proves an export holding the snapshot fence sees the complete pre-publication Project, while source publication waits and becomes fully registered only after export releases the fence.

The remaining confirmed defect is the same publication boundary for canonical artifacts. Targeted replacement copy and local FFmpeg range extraction currently create canonical artifact bytes before their Project references participate in the shared project fence. This draft cycle corrects that class without holding the project lock during the expensive copy/render phase.

ProjectUnitOfWork validation uses the same migration boundary for staged historical `project.json` snapshots. Validation sees the current in-memory schema while undo/redo still writes the exact recorded bytes, preserving durable history across the schema transition.

## Acceptance synchronization

The implementation-head CI previously exposed a pre-existing timing race in two Windows browser acceptance scenarios around the intentional Production panel remount after a project transaction. The product frontend was not changed in this slice. Both affected tests wait for the old Production DOM instance to detach before entering the next step; no arbitrary sleep or weaker product assertion was introduced.

Frozen head `87a018abebea1dbcd5959921603b53305b02d5f5` passed CI run #4150 **5/5**, including both bootstrap jobs, API integration, real-media golden coverage, frontend lint/audit/build and Stage 4C + Stage 5 browser user-outcome suites on the applicable platforms. That evidence remains useful but is no longer merge-authoritative once the confirmed artifact-publication fix changes the branch.

## Accepted GitHub Actions security boundary

The previously merged Actions hardening remains unchanged. Maintained workflow Actions are full-SHA pinned, checkout credentials are least-privilege, and the permanent workflow-policy guards remain the accepted supply-chain boundary.

## Review and verification

This is material Project runtime/compatibility/recovery/concurrency work and is no longer frozen while the confirmed artifact-publication/archive snapshot race is corrected. After the fix, the branch must return to `review`, the new exact `BASE_SHA..HEAD_SHA` must pass all five required CI checks, every inline review thread must remain resolved, and a fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0 must report zero surviving findings. Any later material change invalidates that review and requires another fresh review.
