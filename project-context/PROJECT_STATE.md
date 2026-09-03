# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235` passed post-Ready CI #4609 (`33746380980`) **5/5 SUCCESS** and then the mandatory genuinely fresh ordinary-ChatGPT `code-review` v1.0 returned `review_validity=CURRENT`, `status=FINDINGS`, `reported_findings=1`, `rejected_candidates=21`. The single P1 was confirmed, so that review head is merge-blocked and the lifecycle was returned to Draft before material repair.

Lifecycle commit `ca202726ecfb05472fcf0ab817f30c4f153fb5b3` changes `ACTIVE_SLICE.json` from `review` to `draft`. Regression-first commit `75aed8ea5326dd2891007632ef42dbf20fc60ba0` extends the existing terminal-split test with the direct `GenerationService.run()` retry path. Runtime repair commit `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` makes the shared `GenerationJobManager.start_execution()` retry/terminal guard consult and validate the same current Redo-owned Generation authority used by explicit requeue before it may create another attempt.

## Confirmed fresh-review P1: direct retry bypassed redo-owned materialization

The supported legacy terminal split can contain exact durable Generation bytes and ProjectReference provenance while the owning attempt/job remains `FAILED`. If the user Undo-es `generation.register_output`, the reference becomes reachable only through the durable ProjectUnitOfWork Redo suffix while its bytes remain present.

Startup correctly preserves that redo-only materialization and the explicit HTTP retry path already called `requeue_failed_generation_job()`, which validates Redo authority and rejects replay. However, `GenerationService.run()` also supports direct failed-job retry and calls `GenerationJobManager.start_execution()` directly. Before this repair, `start_execution()` used `_has_unreconciled_durable_artifact()` that inspected only live `Project.artifacts`; therefore a direct service/script retry could create a second RUNNING attempt and invoke the provider again even though the first attempt's exact materialization remained durably owned by Redo.

The repair places the missing authority check at the shared Job-manager boundary before attempt creation. `_has_unreconciled_durable_artifact()` now loads the current Redo ProjectReferences through the existing recovery authority, validates redo-owned Generation bytes/provenance, and evaluates live plus Redo-owned references against every historical attempt. Direct `GenerationService.run()`, explicit requeue, failure and cancellation therefore converge on the same fail-closed durable-materialization rule.

Regression `tests/test_stage19_redo_terminal_split_recovery.py` now covers the exact chain: post-artifact local failure -> legacy `FAILED` attempt -> Undo `generation.register_output` -> restart -> **direct `GenerationService.run()` rejection** -> explicit requeue rejection -> explicit Redo -> local reconciliation. It asserts the Job remains FAILED after the direct retry attempt, the attempt count remains one, Redo remains available, and `executor.calls` remains exactly one.

## Verification

Previous accepted evidence remains:

- prior synchronized Draft head `106b7396b9e8681550cb59b411b8cb0935f88066`, CI #4602 (`33741327112`): **5/5 SUCCESS**;
- prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235`, post-Ready CI #4609 (`33746380980`): **5/5 SUCCESS**.

Current P1 repair evidence is pending a clean exact-head Draft CI after this context synchronization. The earlier CI #4616 on runtime head `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` is not authoritative because `development-context` correctly detected that `PROJECT_STATE.md` still carried the pre-repair `review` marker while `ACTIVE_SLICE.json` was already Draft.

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, ProjectUnitOfWork exact-byte v1/v2 Undo/Redo, prepared-UOW archive recovery, archive snapshot locking, source/WebVTT/Generation publication fences, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation and byte validation, publication-marker reference identity, Generation digest/provenance/path/lineage authority, direct Redo binary validation, leased root staging with cross-runtime allocation/recovery serialization, and immediate-next-action Product Truth behavior.

## Draft repair gate

Material/runtime repair is allowed only while PR #89 and this lifecycle remain Draft. Before refreeze:

1. require exact-head Draft CI **5/5 SUCCESS** including both full unit suites and both app-baseline Product Truth jobs;
2. keep the direct redo-only failed-job retry regression green on Ubuntu and Windows;
3. synchronize PR body and context with the exact repair head/evidence;
4. verify PR #89 remains open, Draft, mergeable, BASE `52be1939eca51d7147990288cfc6258b023c2cd2`, and has zero unresolved inline review threads;
5. refreeze lifecycle `draft -> review` only after the authoritative Draft gate is green.

After refreeze, mark PR Ready without material changes, require a new post-Ready exact-head CI 5/5, re-resolve live identity/threads, and perform another genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0. Merge remains prohibited until that new review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and all exact-head gates remain clean.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
