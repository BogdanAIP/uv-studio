# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-08-31

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in implementation/draft in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Implementation head `6890ad79f0598d701881ebe264674d5d5c606891` passed required CI runs #4161 and #4162 **5/5**. Context-only frozen head `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` then passed exact-head post-Ready CI #4165, but its required fresh ordinary-ChatGPT semantic review returned `FINDINGS` with two surviving P2 findings. The development context independently classified both findings **CONFIRMED**. That review/head are therefore not merge-valid after the required material repair.

Confirmed finding 1: archive recovery hardening recognizes incomplete UV-managed publication only from `src_` / `art_` / `aud_` UUID-style basenames. `timeline.assemble` is a supported counterexample: callers may choose an arbitrary canonical output such as `artifacts/joined.mp4`; FFmpeg writes that path before the adapter creates a separate `art_<uuid>` ProjectReference and before `update_project()` acquires the shared project fence. Export can therefore freeze old metadata while capturing the newly written arbitrary-named artifact. The recovery boundary must cover this publisher without making ordinary unregistered project files non-portable.

Confirmed finding 2: the permanent browser user-outcome tests in `e2e/test_micro_drama_production_outcome.py` and `e2e/test_named_generation_outcome.py` were changed only on the test side to capture the old Shot-intent DOM element and wait until it disconnects after Scene creation. No production frontend fix accompanies those changes. That internal stale-element wait deliberately advances past the known production-form remount window that can discard a user's next Shot intent, weakening the acceptance gate rather than proving the user-visible race fixed. The waits must not remain as the permanent acceptance solution.

No runtime/material files may change while lifecycle state is `review`; this context-only transition returns durable state to `draft`. PR #89 must also be converted back to GitHub Draft before material repairs begin. The GitHub connector's draft mutation currently fails on the known `Repository.fullDatabaseId` GraphQL schema error, so that UI transition may require the repository owner.

## Implementation boundary

This slice remains bounded to the D-070 Project identity/schema compatibility and recovery boundary:

- canonical Project schema v2 with schema-v1 project/archive readability;
- explicit legacy recipe compatibility identity rather than fake modern Production Direction identity;
- stable project/source/artifact/media/Timeline identities across migration and archive round trips;
- durable schema-v1 ProjectUnitOfWork undo/redo;
- one recoverable archive state under concurrent Project mutation and media publication;
- fail-closed archive symlink safety with only the ordinary technical task-record lock excluded from portable payload.

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement and later D-070 compression work remain outside this slice.

## Implemented compatibility and recovery boundary

`ProjectStore` routes loaded JSON through `migrate_project_data`; schema v2 keeps legacy recipe information in compatibility state. Current direct compatibility readers use the explicit accessor, while historical v1 bytes remain readable and exact transaction snapshots remain authoritative for undo/redo.

Archive import validates the manifest against the raw archived Project schema before migration. Export holds `ProjectTaskRecordStore.project_lock` while freezing Project metadata and enumerating the project tree. The technical `tasks/.uv-task-records.lock` remains non-portable only when it is an ordinary file; symlink occupancy still fails closed.

Source upload proactively stages incomplete request bytes outside every canonical project directory and publishes final source bytes plus metadata under the shared project fence.

The current archive guard rejects unregistered UUID-style UV-owned managed publication names and streams accepted files once into ZIP while computing manifest size/SHA-256 from the same bytes. That mechanism remains useful but is insufficient for supported arbitrary-named outputs such as `timeline.assemble`; the next repair must close that concrete gap without silently dropping ordinary portable files.

## Repair plan

1. Preserve `timeline.assemble`'s caller-visible canonical `output_path`, but prevent incomplete bytes from becoming visible inside the canonical project tree before the matching ProjectReference can participate in the shared project fence. Add focused concurrency coverage for archive export versus arbitrary-named assembly publication.
2. Remove the stale-DOM remount waits from the two permanent browser user-outcome tests. The gate must again exercise the immediate next-user-action sequence; if the production remount still loses input, fix the product behavior rather than synchronizing the acceptance test around it.
3. Run focused tests, then all five required hosted CI checks on the new implementation head.
4. Only after green implementation CI, return context to `review`, make the PR Ready, require exact frozen-head CI and a new fresh ordinary-ChatGPT semantic review. Any material change invalidates the review on `d93391d9f2fbbd2be41237b662c0bcf6d40abecc`.

## Review and verification

Lifecycle is `draft`. Both findings from the fresh review at `d93391d9f2fbbd2be41237b662c0bcf6d40abecc` are CONFIRMED and must be repaired before the next freeze. The old semantic review is evidence for the defects only; it cannot be reused for merge after any fix.
