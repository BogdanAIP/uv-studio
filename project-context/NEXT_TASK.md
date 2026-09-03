# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89 and is refrozen in `review` after repair of the Windows case-alias managed-publication defect.

Regression-first head `bfd85892037ad25e5389aa2c3c26faef99c64ec6` proved the defect on the unpatched runtime via CI #4662. Runtime repair `969142b4adb92104a77041c02ae3f9081965999b` passed material CI #4665 **5/5 SUCCESS**. Synchronized Draft head `ea9a7dcd559fabc96b04f08b478e70159a7bafa0` passed authoritative post-body-sync CI #4678 (`33784319416`) **5/5 SUCCESS**, including both full unit suites and both app-baseline browser Product Truth jobs.

## Immediate continuation

1. Mark PR #89 Ready without runtime/test/schema/product changes.
2. Freeze the resulting exact BASE/HEAD and require a distinct exact-head post-Ready permanent CI **5/5 SUCCESS**.
3. Launch another genuinely fresh ordinary-ChatGPT read-only semantic review using only immutable `REVIEW_REQUEST_V1` identity and `.agents/skills/code-review/SKILL.md` v1.0 governed by BASE_SHA.
4. If that review returns `CURRENT / PASS / 0 findings`, re-resolve exact live identity, permanent CI and unresolved inline threads, then merge with expected HEAD SHA.
5. After merge, perform mandatory D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

A physical arbitrary publication path may have only one unresolved durable managed-publication reservation, including case-only aliases on case-insensitive filesystems. Reservation conflict detection and recovery reference correlation use the same host-filesystem identity. Exact marker `reference_id` ownership remains required. Persisted Project paths remain canonical relative lexical strings and are not silently case-folded or rewritten.

Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication semantics and all previously repaired Stage-19 invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review cycle.
