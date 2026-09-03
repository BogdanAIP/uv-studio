# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235` passed post-Ready CI #4609 (`33746380980`) **5/5 SUCCESS** and then the mandatory genuinely fresh ordinary-ChatGPT `code-review` v1.0 returned `review_validity=CURRENT`, `status=FINDINGS`, `reported_findings=1`, `rejected_candidates=21`. The single P1 was confirmed, so that review head is permanently stale/merge-blocked and the lifecycle was returned to Draft before material repair.

Lifecycle commit `ca202726ecfb05472fcf0ab817f30c4f153fb5b3` changed `ACTIVE_SLICE.json` from `review` to `draft`. Regression-first commit `75aed8ea5326dd2891007632ef42dbf20fc60ba0` extends the existing terminal-split test with the direct `GenerationService.run()` retry path. Runtime repair commit `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` makes the shared `GenerationJobManager.start_execution()` retry/terminal guard consult and validate the same current Redo-owned Generation authority used by explicit requeue before it may create another attempt.

## Confirmed fresh-review P1: direct retry bypassed redo-owned materialization

The supported legacy terminal split can contain exact durable Generation bytes and ProjectReference provenance while the owning attempt/job remains `FAILED`. If the user Undo-es `generation.register_output`, the reference becomes reachable only through the durable ProjectUnitOfWork Redo suffix while its bytes remain present.

Startup correctly preserves that redo-only materialization and the explicit HTTP retry path already called `requeue_failed_generation_job()`, which validates Redo authority and rejects replay. However, `GenerationService.run()` also supports direct failed-job retry and calls `GenerationJobManager.start_execution()` directly. Before this repair, `start_execution()` used `_has_unreconciled_durable_artifact()` that inspected only live `Project.artifacts`; therefore a direct service/script retry could create a second RUNNING attempt and invoke the provider again even though the first attempt's exact materialization remained durably owned by Redo.

The repair places the missing authority check at the shared Job-manager boundary before attempt creation. `_has_unreconciled_durable_artifact()` now loads current Redo ProjectReferences through the existing recovery authority, validates redo-owned Generation bytes/provenance, and evaluates live plus Redo-owned references against every historical attempt. Direct `GenerationService.run()`, explicit requeue, failure and cancellation therefore converge on the same fail-closed durable-materialization rule.

Regression `tests/test_stage19_redo_terminal_split_recovery.py` covers the exact chain: post-artifact local failure -> legacy `FAILED` attempt -> Undo `generation.register_output` -> restart -> **direct `GenerationService.run()` rejection** -> explicit requeue rejection -> explicit Redo -> local reconciliation. It asserts the Job remains FAILED after the direct retry attempt, the attempt count remains one, Redo remains available, and `executor.calls` remains exactly one.

## Verification

Accepted evidence now includes:

- prior synchronized Draft head `106b7396b9e8681550cb59b411b8cb0935f88066`, CI #4602 (`33741327112`): **5/5 SUCCESS**;
- prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235`, post-Ready CI #4609 (`33746380980`): **5/5 SUCCESS**;
- synchronized P1 repair head `9b3fd0ce5814ead7b36579b073c11f13f9f315de`, canonical Draft CI #4619 (`33761623377`): **5/5 SUCCESS**.

CI #4619 passed:

- `development-context` — SUCCESS;
- Ubuntu full unit suite — SUCCESS, including the direct redo-only failed-job retry regression;
- Windows full unit suite — SUCCESS, including the same regression;
- Ubuntu app-baseline — SUCCESS through API integration, real-media, frontend lint/audit/build and browser Product Truth;
- Windows app-baseline — SUCCESS through API integration, pinned media toolchain, real-media, frontend lint/audit/build and browser Product Truth.

The earlier CI #4616 on runtime head `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` is non-authoritative only because `development-context` correctly detected the transient lifecycle-marker mismatch before context synchronization; it is not evidence of a runtime/test defect.

Context-only commit `02edf56c4b3e535a5913d81ad57598c08d84e3b7` synchronizes `NEXT_TASK.md` with the P1 repair and successful #4619 gate. This `PROJECT_STATE.md` commit is the second and final Draft context synchronization step; no runtime, test, schema or product behavior has changed after `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09`.

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, ProjectUnitOfWork exact-byte v1/v2 Undo/Redo, prepared-UOW archive recovery, archive snapshot locking, source/WebVTT/Generation publication fences, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation and byte validation, publication-marker reference identity, Generation digest/provenance/path/lineage authority, direct Redo binary validation, leased root staging with cross-runtime allocation/recovery serialization, and immediate-next-action Product Truth behavior.

## Final Draft gate before refreeze

PR #89 must remain Draft until this exact synchronized context head passes one final CI **5/5 SUCCESS**. That final run is context-only relative to the already-green material head and must still include all five permanent jobs.

After that gate:

1. re-resolve PR #89 as open, Draft, mergeable, BASE `52be1939eca51d7147990288cfc6258b023c2cd2`, exact current HEAD, and zero unresolved inline review threads;
2. refreeze lifecycle `draft -> review` without runtime/test/schema/product changes;
3. synchronize review context/body with the exact frozen HEAD;
4. mark PR Ready without material changes;
5. require a new distinct post-Ready exact-head CI **5/5 SUCCESS**;
6. re-resolve live BASE/HEAD/mergeability/threads;
7. perform another genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until that new review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and all exact-head gates remain clean. After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
