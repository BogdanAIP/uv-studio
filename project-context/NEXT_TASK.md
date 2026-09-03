# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. The confirmed P1 from the previous fresh review is materially repaired. Runtime repair `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` closes the direct failed-job retry divergence at the shared `GenerationJobManager.start_execution()` boundary.

Final synchronized Draft head `5b59495e9b733f4af790c16bc8b4e869089214aa` passed CI #4624 (`33762251065`) **5/5 SUCCESS**: development-context, both Ubuntu/Windows full unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs all succeeded. The lifecycle is now refrozen `draft -> review`; runtime/test/schema/product behavior must remain unchanged unless a new material finding requires returning to Draft.

## Immediate continuation

1. Synchronize the PR body with the exact frozen review HEAD.
2. Mark PR #89 Ready without material changes.
3. Require a distinct post-Ready exact-head CI **5/5 SUCCESS**.
4. Re-resolve live repository/PR identity, exact BASE/HEAD, mergeability and unresolved inline review threads.
5. Launch another genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.
6. Merge only if the new review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and final live exact-head evidence remains clean.
7. After merge, perform mandatory D-038 lifecycle closure to `idle` before initializing the next declared handoff.

## Repair invariant to preserve

A Generation output reachable only through the current durable Redo suffix may be a recovery-compatible incomplete legacy materialization. Exact Job/Attempt/request/provenance/path/size/SHA authority can preserve those bytes without claiming success or recreating current Project/Take state. **Every failed-job execution entry point, including direct `GenerationService.run()` and explicit HTTP retry, must remain blocked before new attempt/provider execution while that validated redo-owned materialization is reachable.** Explicit Redo may restore the exact validated reference, after which ordinary local recovery may complete the owning attempt without provider replay. Portable archive authority remains stricter and requires completed successful attempt/output-reference/Take authority.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review/merge cycle.
