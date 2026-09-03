# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. Fresh review of `6603e46e932432e52e409a4a9656f5625bd9b540` returned `CURRENT / FINDINGS / 1 P1 / 15 rejected candidates`; that P1 is confirmed and materially repaired while the PR/lifecycle are Draft.

Regression `6a45e4b5a548d9eb37fe8f36875118cb697f51e2` covers the crash-left marker with absent canonical bytes followed by an attempted second same-path reservation. Runtime repair `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef` makes `begin_managed_publication()` atomically reject any pending marker that already reserves the same canonical `relative_path` under the shared cross-runtime project lock. Material CI #4643 (`33772892896`) passed **5/5 SUCCESS** on Ubuntu/Windows including full unit suites and browser Product Truth.

## Immediate continuation

1. Synchronize this Draft repair state and PR body; make no further runtime/test/schema/product changes unless new evidence requires them.
2. Require one authoritative exact-head Draft CI **5/5 SUCCESS** after synchronization.
3. Re-resolve live PR identity/mergeability and unresolved inline review threads.
4. Refreeze lifecycle `draft -> review`, mark PR #89 Ready, and freeze the new exact BASE/HEAD.
5. Launch another genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 and only neutral `REVIEW_REQUEST_V1` launcher instructions.
6. If that review is `CURRENT / PASS / 0 findings`, obtain the final exact-head permanent CI/browser/real-media acceptance confirmation on the same reviewed HEAD, then verify live identity/threads and merge with expected HEAD SHA.
7. After merge, perform D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

A canonical arbitrary publication path may have only one unresolved durable managed-publication reservation. The path-reservation check and marker creation are one project-lock critical section; an absent target file does not permit reuse while an older marker exists. Recovery of a no-byte interrupted marker clears only that reservation and cannot invalidate a later successful publication.

Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication semantics and all previously repaired Stage-19 invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this repair cycle.
