# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. The confirmed redo-only legacy Generation terminal-split finding is materially repaired and the synchronized Draft head `106b7396b9e8681550cb59b411b8cb0935f88066` passed CI #4602 **5/5 SUCCESS**.

The slice is now refrozen for review. Do not change runtime, tests, schema or product behavior unless a new supported material finding requires returning the PR to Draft.

## Immediate continuation

1. Synchronize the PR body with the repaired review freeze and exact current HEAD.
2. Mark PR #89 Ready without material changes.
3. Require a distinct post-Ready exact-head CI **5/5 SUCCESS**.
4. Re-resolve live repository/PR identity, exact BASE/HEAD, mergeability and unresolved inline threads.
5. Launch a new genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0. The earlier review on `4f8f1e55c9bfd3ef8289a3964fa94707ee4b1f1c` is stale after repair.
6. Merge only if that new review is `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and final live exact-head evidence remains clean.
7. After merge, perform D-038 lifecycle closure to `idle` before initializing the next declared handoff.

## Repair invariant to preserve

A Generation output reachable only through the current durable Redo suffix may be a recovery-compatible incomplete legacy materialization. Exact Job/Attempt/request/provenance/path/size/SHA authority can preserve those bytes without claiming success or recreating current Project/Take state. Retry must remain blocked while that redo-owned materialization is reachable. Explicit Redo may restore the exact validated reference, after which ordinary local recovery may complete the owning attempt without provider replay. Portable archive authority remains stricter and requires completed successful attempt/output-reference/Take authority.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review/merge cycle.
