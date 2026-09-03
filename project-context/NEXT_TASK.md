# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. The mandatory fresh ordinary-ChatGPT review of frozen head `16f597ff5a1bea7e0353c64e824712b69829b235` returned `CURRENT / FINDINGS / 1 P1 / 21 rejected candidates`.

The P1 is confirmed and materially repaired while the PR/lifecycle are Draft. Regression-first commit `75aed8ea5326dd2891007632ef42dbf20fc60ba0` adds the direct `GenerationService.run()` retry path to the redo-only terminal-split regression. Runtime commit `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` moves the missing Redo-aware durable-materialization check to the shared `GenerationJobManager.start_execution()` boundary before a failed Job can create another attempt.

Synchronized Draft repair head `9b3fd0ce5814ead7b36579b073c11f13f9f315de` passed canonical CI #4619 (`33761623377`) **5/5 SUCCESS**: development-context, both Ubuntu/Windows full unit suites including the new direct-retry regression, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs all succeeded.

## Immediate continuation

1. Keep PR #89 Draft while synchronizing this context and PR body with the successful P1 repair evidence.
2. Require one final exact-head synchronized Draft CI **5/5 SUCCESS** after those context-only commits.
3. Re-resolve live PR identity, mergeability and unresolved inline review threads.
4. Refreeze lifecycle `draft -> review` without runtime/test/schema/product changes.
5. Synchronize review context/body with the exact frozen HEAD, mark PR #89 Ready, and require a distinct post-Ready exact-head CI **5/5 SUCCESS**.
6. Re-resolve live BASE/HEAD/mergeability/threads and launch another genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.
7. Merge only if the new review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and final live exact-head evidence remains clean.
8. After merge, perform mandatory D-038 lifecycle closure to `idle` before initializing the next declared handoff.

## Repair invariant to preserve

A Generation output reachable only through the current durable Redo suffix may be a recovery-compatible incomplete legacy materialization. Exact Job/Attempt/request/provenance/path/size/SHA authority can preserve those bytes without claiming success or recreating current Project/Take state. **Every failed-job execution entry point, including direct `GenerationService.run()` and explicit HTTP retry, must remain blocked before new attempt/provider execution while that validated redo-owned materialization is reachable.** Explicit Redo may restore the exact validated reference, after which ordinary local recovery may complete the owning attempt without provider replay. Portable archive authority remains stricter and requires completed successful attempt/output-reference/Take authority.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review/merge cycle.
