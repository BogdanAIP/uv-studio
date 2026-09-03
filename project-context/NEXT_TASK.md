# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. Fresh review of frozen head `6006c85e78af84643ae942d2db87f47ec9976280` returned `CURRENT / FINDINGS / 1 P2 / 10 rejected candidates`; the Windows case-alias publication finding is independently confirmed and PR/lifecycle are back in Draft.

## Immediate continuation

1. Add a regression for filesystem-equivalent case aliases (`Clip.mp4` / `clip.mp4`) at the managed-publication boundary.
2. Repair reservation and recovery to use one shared filesystem-equivalent path identity while preserving the persisted canonical lexical path.
3. Run exact material-head CI across all five permanent checks, including Windows unit/browser Product Truth.
4. Synchronize Draft context and PR body; require one authoritative exact synchronized-head Draft CI 5/5.
5. Refreeze lifecycle `draft -> review`, mark PR #89 Ready, and launch another genuinely fresh ordinary-ChatGPT semantic review on the new exact HEAD.
6. Merge only after a future `CURRENT / PASS / 0 findings` plus final exact-head permanent CI and clean live identity/threads.
7. After merge, perform D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

A physical arbitrary publication path may have only one unresolved durable managed-publication reservation, including case-only aliases on case-insensitive filesystems. Reservation conflict detection and recovery reference correlation must use the same path identity. Persisted `ProjectReference.path` values remain canonical relative strings and are not silently rewritten solely to enforce coordination identity.

Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication semantics and all previously repaired Stage-19 invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this repair cycle.
