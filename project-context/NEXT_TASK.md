# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89 and is refrozen in `review` after repair of the two P2 findings from the prior fresh review.

Regression-first CI #4689 proved both defects on the unpatched runtime. Runtime repairs reject lexical managed-publication leaf symlinks before resolution and require canonical `GenerationJob.from_dict()` plus physical project/job identity binding before Generation materialization authority is trusted.

Authoritative synchronized Draft CI #4717 (`33792871334`) on repaired Draft head `7977834f0df204dd07ffbc8fd7e94a7dd145ea9f` completed **5/5 SUCCESS**, including both full Ubuntu/Windows unit suites and both app-baseline API/real-media/frontend/browser Product Truth jobs. All inline PR review threads were rechecked live and are resolved.

## Immediate continuation

1. Mark PR #89 Ready without runtime/test/schema/product changes.
2. Freeze the resulting exact BASE/HEAD identity.
3. Launch a genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 and a neutral `REVIEW_REQUEST_V1` launcher.
4. If the review returns `CURRENT / FINDINGS`, validate the findings, return PR/lifecycle to Draft before material repair, add regression-first evidence where applicable, repair, re-gate and obtain another fresh review on the new HEAD.
5. If the review returns `CURRENT / PASS / 0 findings`, obtain the final exact-head permanent CI/browser/real-media acceptance **after the review** on that same reviewed HEAD.
6. Re-resolve live PR state, exact BASE/HEAD, mergeability and unresolved inline review threads; merge only with the reviewed expected HEAD.
7. After merge, perform mandatory D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

Managed-publication recovery treats the marker's lexical leaf as authority for filesystem type: a symlink leaf fails closed and must never cause its target to be quarantined. Existing filesystem-equivalent reservation/correlation, exact reference-ID ownership and portable persisted lexical paths remain unchanged.

Generation archive/Redo/recovery authority first accepts the complete durable Job through canonical `GenerationJob.from_dict()` validation and requires parsed `project_id`/`job_id` to match physical project/task identity before trusting historical attempt provenance. Historical successful-attempt semantics remain valid when a later attempt is failed.

All previous Stage-19 Generation retry/recovery, archive authority, source/WebVTT/Generation publication, schema-v1/v2 compatibility, Undo/Redo, root-staging and Product Truth invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review cycle.
