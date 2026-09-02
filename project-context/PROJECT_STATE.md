# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-02

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The ninth repair itself passed material CI #4445 and synchronized Draft CI #4452, and all inline review threads were resolved. Before marking Ready again, a development-context prefinal adversarial audit was deliberately run across the cumulative BASE..HEAD authority/recovery surface to avoid another Ready -> fresh-review -> Draft loop.

## Prefinal adversarial findings

Four concrete gaps survived falsification and are being repaired together:

1. **Partial Redo Generation byte gap.** `ProjectUnitOfWork.redo()` validates Generation bytes only when the specific Redo operation restores `project.json`. A valid sequence can Redo `generation.register_output` while bytes are intact, mutate the file, then Redo `production.register_take` (Production Semantics only) and restore the historical Take around corrupted media.
2. **Valid reference metadata evolution is misclassified as ambiguous.** `production.accept_take` legitimately annotates the same ProjectReference with `production_acceptances`. If Undo moves far enough back that both the original Generation reference and the later accepted-reference variant are reachable through Redo, archive/restart reference merging currently treats the same ID/path with changed metadata as ambiguous and can reject a valid project.
3. **Redo authority does not prove the full snapshot chain is actually reachable.** `redo_project_documents()` validates transaction identity and after-snapshots but does not verify each redo transaction's `before` snapshots against the simulated current state. A damaged committed transaction can therefore contribute media authority to archive/startup even though direct Redo would reject it as an exact-snapshot conflict.
4. **Archive Generation structural path authority is incomplete.** Shared Generation authority checks the attempt-derived basename but not the canonical `artifacts/` root. Archive uses that structural authority without `validate_generation_reference_bytes()`, so a Generation reference moved to another managed root with the same filename/digest can be archived despite no longer matching the publication path contract.

These are pre-Ready development findings, not independent-review results. The required fresh ordinary-ChatGPT review remains pending until this repair is green and refrozen.

## Accepted evidence before this preflight repair

- ninth material/test head `3eb78fc25a6fd65ce55cac837e4c1816c4eb67d9`: CI #4445 (`33630725870`) **5/5 SUCCESS**;
- synchronized Draft head `892db28ca4abee56a64dfe211b28b02af8f2fde4`: CI #4452 (`33631575224`) **5/5 SUCCESS**;
- P1 thread `PRRT_kwDOT0Lyms6edmby` resolved with exact evidence;
- live review-thread recheck before this audit: zero unresolved inline threads;
- previous review freeze head `056a35bab13adaa9cbd5b159f8bbbc8fbf00ea09` changed only project context after #4452 and was intentionally not marked Ready once this preflight audit was requested.

All earlier Stage-19 repairs remain intended to stay in force: schema-v1/v2 exact historical identity, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity and immediate-next-action Product Truth behavior.

## Next required action

1. add deterministic regressions for the four prefinal findings;
2. repair Redo validation, reachable-history simulation, reference-variant merging and canonical Generation output-root authority without creating binary snapshot history;
3. run exact material-head CI 5/5;
4. synchronize docs/context/PR body and run a final Draft exact-head CI 5/5;
5. perform one more read-only cumulative preflight for the repaired authority matrix;
6. only then refreeze to `review`, mark Ready once, require post-Ready exact-head CI 5/5 and run the mandatory fresh ordinary-ChatGPT review;
7. merge only on `CURRENT PASS` with zero findings and clean final live identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
