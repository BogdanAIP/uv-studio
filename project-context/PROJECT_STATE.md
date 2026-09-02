# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-02

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The ninth repair itself passed material CI #4445 and synchronized Draft CI #4452, and all inline review threads were resolved. Before marking Ready again, a development-context prefinal adversarial audit was deliberately run across the cumulative BASE..HEAD authority/recovery surface to avoid another Ready -> fresh-review -> Draft loop.

## Prefinal adversarial findings and repair

Four concrete gaps survived falsification and are being repaired together:

1. **Partial Redo Generation byte gap.** `ProjectUnitOfWork.redo()` validated Generation bytes only when the specific Redo operation restored `project.json`. A valid sequence could Redo `generation.register_output` while bytes were intact, mutate the file, then Redo `production.register_take` (Production Semantics only) and restore the historical Take around corrupted media. Runtime `6e16b5bcd42d887b14b22c36173bb77f4b78dc14` now validates every Generation ProjectReference that remains live after any Redo, even when that Redo changes only Production/Timeline JSON.
2. **Valid reference metadata evolution was misclassified as ambiguous.** `production.accept_take` legitimately annotates the same ProjectReference with `production_acceptances`. Shared authority `07253a6e8646b7caeb12bc92de5e89530f2b8847`, archive `553b240dc8c1f4f06d25ee0b9dfdacd3a8bc2a27`, and startup recovery `abed09f7780159e2a6e16905993ca6b2383033f9` now allow metadata evolution only while stable reference ID/path/kind and immutable Generation Job/Attempt/size/SHA authority remain identical; path reuse, identity drift, Generation classification drift or provenance drift still fail closed.
3. **Redo authority did not prove the full snapshot chain was reachable.** `redo_project_documents()` previously validated transaction identity and after-snapshots but not every transaction's `before` snapshot against simulated current state. Runtime `6e16b5bcd42d887b14b22c36173bb77f4b78dc14` now simulates the entire redo suffix across all changed canonical documents and requires exact before -> after reachability before any historical ProjectReference can become archive/restart authority.
4. **Archive Generation structural path authority was incomplete.** Shared Generation authority checked attempt-derived basename but not the canonical `artifacts/` root. `07253a6e8646b7caeb12bc92de5e89530f2b8847` now requires the exact direct `artifacts/generated_<attempt>...` publication shape and also reconnects persisted continuation lineage to the durable Generation contract.

Regression-first commit `f0ea9f54854895646776572edf0602dffc5c1309` extends the real Generation harness with four cases: corruption between first and second Redo; accepted-reference metadata evolution surviving restart/export/import/three Redos; a structurally valid but unreachable damaged redo transaction being rejected by archive and startup; and a Generation reference moved outside the canonical artifacts root being rejected.

The current material head is `abed09f7780159e2a6e16905993ca6b2383033f9`. CI #4471 (`33639266506`) is running. Its first `development-context` attempt failed only because the PR body still lacked the required single `## Changes` heading while this Draft preflight was being synchronized; runtime/unit/app jobs continue and the PR body is being corrected without changing material code.

## Accepted evidence before this preflight repair

- ninth material/test head `3eb78fc25a6fd65ce55cac837e4c1816c4eb67d9`: CI #4445 (`33630725870`) **5/5 SUCCESS**;
- synchronized Draft head `892db28ca4abee56a64dfe211b28b02af8f2fde4`: CI #4452 (`33631575224`) **5/5 SUCCESS**;
- P1 thread `PRRT_kwDOT0Lyms6edmby` resolved with exact evidence;
- live review-thread recheck before this audit: zero unresolved inline threads;
- previous review freeze head `056a35bab13adaa9cbd5b159f8bbbc8fbf00ea09` changed only project context after #4452 and was intentionally not marked Ready once this preflight audit was requested.

All earlier Stage-19 repairs remain intended to stay in force: schema-v1/v2 exact historical identity, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity and immediate-next-action Product Truth behavior.

## Next required action

1. finish exact material-head CI and repair only concrete failures;
2. synchronize archive/store docs with the repaired preflight authority contract;
3. run a final synchronized Draft exact-head CI 5/5;
4. perform one more read-only cumulative preflight for the repaired authority matrix;
5. only then refreeze to `review`, mark Ready once, require post-Ready exact-head CI 5/5 and run the mandatory fresh ordinary-ChatGPT review;
6. merge only on `CURRENT PASS` with zero findings and clean final live identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
