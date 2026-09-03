# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89.

The implementation is materially complete after the confirmed fresh-review repair for the redo-only legacy Generation terminal split. Do not start Recipe endpoint retirement, execution-plan retirement, Product Orchestrator retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work inside this PR.

## Immediate continuation

1. Require the synchronized Draft HEAD to pass all five declared CI checks.
2. Re-resolve live PR #89 BASE/HEAD, mergeability and unresolved review threads.
3. Freeze the exact repair HEAD by moving lifecycle from `draft` to `review` with context-only commits; do not change runtime/test/schema/product behavior after the successful Draft gate.
4. Mark PR #89 Ready and require a distinct post-Ready exact-head CI 5/5.
5. Launch a new genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0. The earlier review of `4f8f1e55c9bfd3ef8289a3964fa94707ee4b1f1c` is stale after the confirmed P2 repair.
6. Merge only if the new review returns `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` and the final live BASE/HEAD/CI/thread identity remains clean.
7. After merge, perform D-038 lifecycle closure to `idle` before initializing the next declared handoff.

## Repair invariant to preserve

A Generation output reachable only through the current durable Redo suffix can represent a recovery-compatible incomplete legacy materialization. Its exact Job/Attempt/request/provenance/path/size/SHA authority may be validated and its bytes preserved without claiming that the attempt is already successful or recreating current Project/Take state. Explicit retry must remain blocked while that redo-owned materialization is reachable. An explicit user Redo may restore the exact reference after binary validation; ordinary local recovery may then complete the attempt without provider replay. Portable archive authority remains stricter and requires completed successful attempt/output-reference/Take authority.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this bounded repair/refreeze cycle.
