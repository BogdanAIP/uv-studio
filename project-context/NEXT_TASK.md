# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Complete review and merge of PR #95 for `legacy-music-action-envelope-retirement` from lifecycle-closed BASE `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47`.

## Frozen material result

Final material Draft head `bf11b97f9a6ef4c3d57e15831cf3b855cabf4dd2` has the bounded retirement complete:

- the five duplicate Music Product Workflow mutation actions are retired;
- specialized Music client facades use the existing direct Map, Direction, Assembly, capability-render and Review authorities;
- Product Workflow remains read-only compatibility state for the legacy Music page;
- browser acceptance proves zero Music `/workflow/actions/` POSTs and positively observes all five direct mutation paths;
- the visible Music journey still reaches the current rendered master, approved Review and `workflow.readiness == ready`.

CI #4872 on that exact material head completed SUCCESS for all five permanent jobs, including browser outcomes on Ubuntu and Windows. Duplicate exact-head CI #4871 also completed SUCCESS.

## Current review refreeze

This transition is context-only: no product/runtime/frontend/test bytes change from the green material head. The next exact HEAD is the review identity.

## Gate

1. Mark PR #95 Ready for review.
2. Require all five permanent CI jobs SUCCESS on the exact context-only review head.
3. Run a genuinely fresh ordinary-ChatGPT semantic review using BASE `.agents/skills/code-review/SKILL.md` v1.0 and the exact BASE/HEAD pair.
4. Validate any reported finding against that exact head; material fixes require returning to Draft before changes.
5. Merge only if the fresh result is `PASS`, `review_validity=CURRENT`, `reported_findings=0`, exact-head CI remains green and no unresolved review thread blocks acceptance.
6. Immediately create and merge the separate D-038 lifecycle closure, restoring `idle` and selecting the next D-070 slice from accepted repository authority rather than guessing it.
