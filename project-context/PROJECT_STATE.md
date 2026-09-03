# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `6006c85e78af84643ae942d2db87f47ec9976280` returned `CURRENT / FINDINGS / 1 P2 / 10 rejected candidates`. The finding was independently confirmed before material repair: managed-publication reservation/recovery compares `relative_path` using case-sensitive lexical identity, while supported Windows filesystems can resolve case variants such as `artifacts/Clip.mp4` and `artifacts/clip.mp4` to the same physical file.

PR #89 returned to Draft before any runtime/test repair. The prior review is now stale for merge authority.

## Repair target

Preserve the existing single-owner arbitrary-path publication invariant across filesystem-equivalent case aliases on Windows. A crash-left marker reserving one case variant must block another publisher using a case-only alias, and recovery must correlate registered references using the same path identity so an older marker cannot quarantine a newer valid output.

## Prior verified state

- material identical-string reservation repair head `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef`: CI #4643 **5/5 SUCCESS**;
- synchronized Draft head `9d0fa344e2f8b35f283dba7f3b533228d8e7f42c`: CI #4646 **5/5 SUCCESS**;
- frozen review head `6006c85e78af84643ae942d2db87f47ec9976280`: preliminary Ready CI #4650 **5/5 SUCCESS**, but fresh review found the Windows case-alias P2.

All earlier Stage-19 invariants remain in force. Material changes now require regression-first repair, exact-head Draft CI, context synchronization, refreeze, Ready transition and another fresh ordinary-ChatGPT review.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
