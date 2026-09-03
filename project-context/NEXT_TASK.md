# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. Fresh review of frozen head `6006c85e78af84643ae942d2db87f47ec9976280` returned `CURRENT / FINDINGS / 1 P2 / 10 rejected candidates`. The Windows case-alias publication defect is confirmed and repaired while PR/lifecycle remain Draft.

Regression-first commit `bfd85892037ad25e5389aa2c3c26faef99c64ec6` added portable and Windows-real-filesystem case-alias tests; regression-only CI #4662 failed at the new reservation test on the unpatched runtime. Runtime repair `969142b4adb92104a77041c02ae3f9081965999b` applies one shared host-filesystem identity to both reservation conflicts and recovery reference correlation while preserving persisted lexical paths. Material CI #4665 (`33782870284`) passed **5/5 SUCCESS**, including both new tests on Windows and both browser Product Truth jobs.

## Immediate continuation

1. Synchronize this repaired Draft state and PR body; make no further runtime/test/schema/product changes unless new evidence requires them.
2. Require one authoritative exact-head Draft CI **5/5 SUCCESS** after synchronization.
3. Re-resolve live PR identity/mergeability and unresolved inline review threads.
4. Refreeze lifecycle `draft -> review`, mark PR #89 Ready, and freeze the new exact BASE/HEAD.
5. Launch another genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 and only neutral `REVIEW_REQUEST_V1` launcher instructions.
6. If that review is `CURRENT / PASS / 0 findings`, obtain the final exact-head permanent CI/browser/real-media acceptance confirmation on the same reviewed HEAD, then verify live identity/threads and merge with expected HEAD SHA.
7. After merge, perform D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

A physical arbitrary publication path may have only one unresolved durable managed-publication reservation, including case-only aliases on case-insensitive filesystems. Reservation conflict detection and recovery reference correlation use the same host-filesystem identity. Exact marker `reference_id` ownership remains required. Persisted `ProjectReference.path` and marker `relative_path` values remain canonical relative strings and are not silently case-folded or rewritten.

Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication semantics and all previously repaired Stage-19 invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this repair cycle.
