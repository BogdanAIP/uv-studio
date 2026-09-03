# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `6603e46e932432e52e409a4a9656f5625bd9b540` returned `CURRENT / FINDINGS / 1 P1 / 15 rejected candidates`. The finding was independently **CONFIRMED**, so PR #89 and lifecycle returned to Draft before material repair; that review is stale for merge authority.

Regression-first commit `6a45e4b5a548d9eb37fe8f36875118cb697f51e2` covers the exact old-marker/no-bytes state: one durable managed-publication marker reserves a caller-selected path while the canonical file is absent, and a second same-path reservation must fail before another marker can be created. It also proves recovery of the first no-byte marker clears the reservation without quarantine and allows a later reservation.

Runtime repair `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef` moves that invariant into the shared `begin_managed_publication()` authority. Marker validation, same-canonical-path conflict detection and marker creation now execute atomically under the same re-entrant cross-runtime project lock. A second already-running publisher can no longer reuse a path still reserved by a crash-left marker merely because the canonical file is absent.

## Repaired invariant

A canonical managed arbitrary-publication path has at most one unresolved durable reservation at a time. Reservation validation + marker creation is atomic under the project OS lock. An interrupted marker with no materialized bytes blocks later publishers until recovery clears it; therefore recovery of an older marker cannot quarantine bytes from a newer successful publication at the same path.

The earlier Generation redo-only retry invariant remains unchanged: every failed-job execution entry point stays blocked before provider replay while validated redo-owned materialization is reachable.

## Verification

- frozen pre-repair review head `6603e46e932432e52e409a4a9656f5625bd9b540`: CI #4636 (`33771183215`) **5/5 SUCCESS**, fresh review `CURRENT / FINDINGS / 1 P1 / 15 rejected candidates`;
- regression-first commit `6a45e4b5a548d9eb37fe8f36875118cb697f51e2`;
- material repair head `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef`: CI #4643 (`33772892896`) **5/5 SUCCESS** — development-context, both Ubuntu/Windows full unit suites including the new regression, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs all passed.

No other runtime, test, schema or product behavior changed in this repair cycle.

## Final Draft gate before refreeze

This context and the PR body must now be synchronized with the confirmed P1 repair. The resulting exact Draft head must pass all five permanent checks. Only then may lifecycle transition `draft -> review`, PR #89 become Ready, and a new genuinely fresh ordinary-ChatGPT semantic review be launched on the new immutable BASE/HEAD.

After a future `CURRENT / PASS / 0 findings` review, obtain the final exact-head permanent CI/browser/real-media acceptance confirmation on that same reviewed HEAD, verify live BASE/HEAD/mergeability and unresolved review threads, then merge with expected HEAD SHA. After merge, perform mandatory D-038 lifecycle closure to `idle`.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
