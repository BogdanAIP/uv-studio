# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235` passed post-Ready CI #4609 (`33746380980`) **5/5 SUCCESS** and then the mandatory genuinely fresh ordinary-ChatGPT `code-review` v1.0 returned `CURRENT / FINDINGS / 1 P1 / 21 rejected candidates`. That single P1 was confirmed, the PR/lifecycle returned to Draft before material repair, and the old review head is permanently stale for merge authority.

Regression-first commit `75aed8ea5326dd2891007632ef42dbf20fc60ba0` adds the direct `GenerationService.run()` retry path to the redo-only terminal-split scenario. Runtime repair commit `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` moves the missing Redo-aware durable-materialization check to the shared `GenerationJobManager.start_execution()` boundary before a failed Job can create another attempt.

## Repaired invariant

A validated Generation materialization reachable only through the current durable ProjectUnitOfWork Redo suffix blocks every failed-job execution entry point before new attempt/provider execution. Direct `GenerationService.run()`, explicit HTTP retry and Job terminal transitions now converge on the same fail-closed authority. Explicit Redo may restore the exact validated reference, after which local recovery may complete the owning attempt without provider replay.

Regression `tests/test_stage19_redo_terminal_split_recovery.py` covers post-artifact local failure -> legacy `FAILED` attempt -> Undo `generation.register_output` -> restart -> direct `GenerationService.run()` rejection -> explicit requeue rejection -> explicit Redo -> local reconciliation. It asserts the Job remains FAILED after the direct retry attempt, the attempt count remains one, Redo remains available, and `executor.calls` remains exactly one.

## Verification

Accepted evidence includes:

- synchronized Draft head `106b7396b9e8681550cb59b411b8cb0935f88066`, CI #4602 (`33741327112`): **5/5 SUCCESS**;
- prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235`, post-Ready CI #4609 (`33746380980`): **5/5 SUCCESS**;
- P1 material/context repair head `9b3fd0ce5814ead7b36579b073c11f13f9f315de`, CI #4619 (`33761623377`): **5/5 SUCCESS**;
- final synchronized Draft head `5b59495e9b733f4af790c16bc8b4e869089214aa`, CI #4624 (`33762251065`): **5/5 SUCCESS**.

CI #4624 passed all five permanent jobs: development-context, both Ubuntu/Windows full unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs. No runtime, test, schema or product behavior changed after runtime repair `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09`.

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, ProjectUnitOfWork exact-byte v1/v2 Undo/Redo, prepared-UOW archive recovery, archive snapshot locking, source/WebVTT/Generation publication fences, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation and byte validation, publication-marker reference identity, Generation digest/provenance/path/lineage authority, direct Redo binary validation, leased root staging with cross-runtime allocation/recovery serialization, and immediate-next-action Product Truth behavior.

## Review freeze

The final Draft gate is complete and lifecycle is now refrozen `draft -> review`. Runtime/test/schema/product changes are prohibited unless a new supported material finding requires returning PR #89 to Draft.

Next required gates:

1. synchronize the PR body with the exact frozen review HEAD;
2. mark PR #89 Ready without material changes;
3. require a distinct post-Ready exact-head CI **5/5 SUCCESS**;
4. re-resolve live repository/PR identity, exact BASE/HEAD, mergeability and unresolved inline review threads;
5. launch another genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
6. merge only if that review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and final live exact-head evidence remains clean.

After merge, mandatory D-038 lifecycle closure to `idle` must happen before starting the next declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
