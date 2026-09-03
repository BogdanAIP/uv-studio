# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `6006c85e78af84643ae942d2db87f47ec9976280` returned `CURRENT / FINDINGS / 1 P2 / 10 rejected candidates`. The finding was independently confirmed before material repair: managed-publication reservation/recovery used case-sensitive lexical `relative_path` identity, while Windows can resolve case variants such as `artifacts/Clip.mp4` and `artifacts/clip.mp4` to the same physical file. PR #89 and lifecycle returned to Draft before runtime/test changes; that review is stale for merge authority.

Regression-first commit `bfd85892037ad25e5389aa2c3c26faef99c64ec6` adds both a portable filesystem-identity reservation regression and a Windows-only real-filesystem recovery regression. On the regression-only head, CI #4662 (`33782808320`) failed exactly at `test_case_alias_reservation_uses_filesystem_equivalent_identity` because the pre-repair runtime did not raise `ManagedPublicationError`, proving the test detects the defect.

Runtime repair commit `969142b4adb92104a77041c02ae3f9081965999b` introduces one shared host-filesystem path identity for managed-publication coordination using canonical project-relative validation plus `os.path.normcase()` on the host-native relative path. `begin_managed_publication()` uses that identity for unresolved reservation conflicts, and `recover_managed_publications()` uses the same identity when correlating durable registered references. Persisted marker and `ProjectReference.path` strings remain canonical portable lexical paths and are not rewritten solely for coordination.

## Repaired invariant

A physical managed arbitrary-publication path has at most one unresolved durable reservation, including case-only aliases on case-insensitive Windows filesystems. Reservation conflict detection and recovery reference correlation use the same host-filesystem identity; exact expected `reference_id` ownership remains required. Therefore a stale `Clip.mp4` marker cannot be bypassed by a `clip.mp4` publisher and later quarantine that newer valid output.

All earlier Stage-19 Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication, historical identity, Undo/Redo, leased root staging and Product Truth invariants remain unchanged.

## Verification

- frozen pre-repair head `6006c85e78af84643ae942d2db87f47ec9976280`: preliminary Ready CI #4650 **5/5 SUCCESS**, fresh review `CURRENT / FINDINGS / 1 P2 / 10 rejected candidates`;
- regression-first head `bfd85892037ad25e5389aa2c3c26faef99c64ec6`: CI #4662 failed at the new case-alias reservation regression on the unpatched runtime, as intended;
- material repair head `969142b4adb92104a77041c02ae3f9081965999b`: CI #4665 (`33782870284`) **5/5 SUCCESS** — development-context, Ubuntu/Windows full unit suites, and Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth all passed;
- Windows full-unit evidence on #4665 ran 703 tests and passed both `test_case_alias_reservation_uses_filesystem_equivalent_identity` and the Windows-only `test_windows_recovery_matches_registered_case_alias_without_quarantine` on the hosted Windows filesystem.

No runtime/test/schema/product behavior will change after `969142b4adb92104a77041c02ae3f9081965999b` unless new evidence requires it. This Draft context and PR body must now be synchronized, then the resulting exact Draft head must pass all five permanent checks before lifecycle refreeze `draft -> review`.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
