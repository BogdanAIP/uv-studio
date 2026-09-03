# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89 and is back in `draft` after fresh review of frozen head `71006f09aa0db73991b7014fa1d2242db163ea83` returned `CURRENT / FINDINGS / 2 P2 / 14 rejected candidates`.

Both findings were independently confirmed and regression-first evidence was added before runtime repair. `f3bf657480ebb7d0da0bb4d10e58df8f48a1d17e` covers recovery of a crash-left managed-publication marker whose lexical output is an in-root symlink; `ad16553a34482bdf0b2008e3dd5ae05ece0be998` covers archive authority accepting durable Generation Job JSON that the canonical Job parser rejects. Regression-only CI #4689 (`33791042300`) failed both Ubuntu and Windows full-unit jobs on the new tests while both app-baseline Product Truth jobs remained green.

Runtime repair `efcf6dc6c7dd01def6bc7b77a309ac071ded068f` rejects publication marker leaf symlinks before general path resolution can follow them. Runtime repair `8555303655a1acc6adaa4196cefecd3fa4489641` routes durable Generation Job records through canonical `GenerationJob.from_dict()` validation and binds parsed project/job identity to the physical project/task identity before historical attempt authority is trusted. Preliminary material CI #4693 has both Ubuntu and Windows full-unit suites green on these repairs; its development-context failure predates this synchronization and is not an acceptance result.

## Immediate continuation

1. Synchronize this repaired Draft state and PR body; make no further runtime/test/schema/product changes unless new evidence requires them.
2. Require one authoritative exact-head Draft CI **5/5 SUCCESS** after synchronization.
3. Re-resolve live PR identity/mergeability and unresolved inline review threads.
4. Refreeze lifecycle `draft -> review`, mark PR #89 Ready, and freeze the new exact BASE/HEAD.
5. Launch another genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 and neutral `REVIEW_REQUEST_V1` launcher instructions.
6. After a future `CURRENT / PASS / 0 findings` review, obtain/confirm the final exact-head permanent CI/browser/real-media acceptance required by the accepted protocol, verify live identity/threads, and merge with expected HEAD SHA.
7. After merge, perform mandatory D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

Managed-publication recovery must treat the marker's lexical leaf as authority for filesystem type: a symlink leaf fails closed and must never cause its target to be quarantined. Existing filesystem-equivalent path reservation/correlation, exact reference-ID ownership and portable persisted lexical paths remain unchanged.

Generation archive/Redo/recovery authority must first accept the complete durable Job through canonical `GenerationJob.from_dict()` validation and require parsed `project_id`/`job_id` to match the physical project/task identity before trusting any historical attempt. Historical successful-attempt semantics remain valid even when a later attempt is failed.

All previous Stage-19 Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication, schema-v1/v2 compatibility, Undo/Redo, root-staging and Product Truth invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this repair cycle.
