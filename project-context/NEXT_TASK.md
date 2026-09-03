# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. The confirmed P1 from the previous fresh review is materially repaired by runtime commit `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09`; no runtime/test/schema/product behavior is changing in this context-only correction.

The prior refrozen head `5bc3943f188c0c96958c2480b5a22d4f02b30b34` passed Ready-triggered CI #4628 (`33763695643`) **5/5 SUCCESS**. That run remains useful preliminary exact-head evidence, but the accepted governing protocol requires the mandatory fresh semantic review to precede the final exact-head CI/acceptance confirmation used for merge.

## Immediate continuation

1. Keep PR #89 Draft while this process-context correction is synchronized and the permanent checks validate the Draft state.
2. Refreeze lifecycle `draft -> review` without runtime/test/schema/product changes and mark PR #89 Ready.
3. Freeze exact BASE/HEAD and launch a genuinely fresh ordinary-ChatGPT read-only review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0. The launcher contains `REVIEW_REQUEST_V1` plus only a neutral direct instruction to perform the skill.
4. If the review is `FINDINGS`, validate each finding; any confirmed material repair requires returning to Draft and a later fresh review.
5. If the review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0`, require the final exact-head permanent CI/browser/real-media acceptance confirmation on that same reviewed HEAD.
6. Re-resolve live BASE/HEAD/mergeability and unresolved GitHub review threads, then merge with expected HEAD SHA only if all final gates remain clean.
7. After merge, perform mandatory D-038 lifecycle closure to `idle` before initializing the next declared handoff.

## Repair invariant to preserve

A Generation output reachable only through the current durable Redo suffix may be a recovery-compatible incomplete legacy materialization. Exact Job/Attempt/request/provenance/path/size/SHA authority can preserve those bytes without claiming success or recreating current Project/Take state. **Every failed-job execution entry point, including direct `GenerationService.run()` and explicit HTTP retry, must remain blocked before new attempt/provider execution while that validated redo-owned materialization is reachable.** Explicit Redo may restore the exact validated reference, after which ordinary local recovery may complete the owning attempt without provider replay. Portable archive authority remains stricter and requires completed successful attempt/output-reference/Take authority.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review/merge cycle.
