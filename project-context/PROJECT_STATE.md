# Project State

<!-- uv-context-state: idle -->
<!-- uv-active-slice: none -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **idle** after completion of `product-recovery-music-orchestration` in PR #48.

PR #48 merged as `55b87839f79fa639906c409c9e763d650eaf7c03` after exact Review head `f81c9931ee9974607aa5e003f8b06dd72b13682e` passed all five permanent Ubuntu/Windows checks in CI run `32631393026`. The final merge gate also confirmed `main` had not moved and there were no review submissions or unresolved review threads.

Stage 9 PR #38 remains closed **without merge** and is retained only as an engineering reference. Product Truth Recovery remains release-blocking.

## Completed Product Recovery journeys

The permanent Product Orchestrator now has authoritative Class A/B journeys for:

- `photo_to_video -> photo_composition`;
- `visualizer -> audio_visualizer`;
- `free_project -> targeted_edit`;
- `dubbing -> dubbing`;
- `music_video -> music_video`.

These journeys keep Project Store/domain stores canonical and use Product Orchestrator only as current-state projection plus allowed semantic actions.

## Music — completed in PR #48

The authoritative Music chain is now:

`verified master song -> Music Map -> Music Direction -> Music Assembly -> local render -> deterministic rhythm/evidence review -> approved current outcome`

`MusicMapStore`, `MusicDirectionStore`, `MusicAssemblyStore` and `MusicVideoReviewStore` remain canonical. Product Orchestrator projects readiness/prerequisites/workspace/diagnostics/current outcome and exposes semantic actions for saving Map, Direction and Assembly, rendering the master and saving final Review. Rhythm audit remains deterministic in `MusicDirectionStore.rhythm_audit()`; no duplicate Music workflow or audit store was introduced.

The completed flow fails closed on stale or tampered project-owned media and binds final Review/current outcome to exact current source bytes, Map/Direction/Assembly revisions and render SHA. Browser evidence also proves the visible UI uses all five semantic Product Orchestrator actions and completes the approved 20-second release path on both Ubuntu and Windows.

## Verification completed

The final Draft and exact Review heads passed the permanent Ubuntu/Windows gates. Evidence includes:

- development-context lifecycle validation;
- Ubuntu and Windows bootstrap/unit suites;
- API integration and real HTTP probes;
- real-media golden suites;
- frontend dependency audit, lint and build;
- Ubuntu and Windows browser user-outcome suites;
- stale/tampered source rejection and current-outcome binding through focused Music API tests.

This remains Class A/API plus Class B informed browser evidence. It does **not** claim Class C cold-start product usability, installed Windows human acceptance or release readiness.

## Repository hygiene before the next product route

A repository audit identified contract/documentation debt that should be closed before Narrated recovery:

- synchronize Product Truth and Product Orchestrator architecture docs with completed Dubbing and Music recovery;
- remove or redirect legacy frontend routes that still expose old VideoClaw workspaces;
- fix the Dubbing `accepted_id` Product Orchestrator action-schema mismatch;
- remove dead Music projector code without changing its canonical behavior;
- define the next hardening slice for strict JSON/non-finite-number rejection and per-project corruption quarantine;
- keep missing `main` branch protection recorded as an external repository-setting P0 until it can be enabled manually or by an authorized GitHub operation.

## Remaining recovery work

UV Studio is not release-ready. The planned order is now:

1. repository hygiene / contract hardening;
2. Narrated orchestration;
3. General orchestration;
4. Class C cold-start validation;
5. installed Windows human acceptance;
6. only then resumption of Stage 9 packaging/release work.

## Next authorized slice

`product-recovery-repository-hygiene`

Use `project-context/NEXT_TASK.md` as the entry contract. Keep this slice narrow: reconcile repository truth and semantic contracts before starting Narrated; do not reopen Stage 9 packaging.
