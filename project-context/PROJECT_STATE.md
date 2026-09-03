# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `6006c85e78af84643ae942d2db87f47ec9976280` returned `CURRENT / FINDINGS / 1 P2 / 10 rejected candidates`. The Windows case-alias managed-publication defect was independently confirmed, PR/lifecycle returned to Draft before material changes, regression-first evidence was added, and the runtime repair was completed without changing persisted lexical path values.

Regression-first commit `bfd85892037ad25e5389aa2c3c26faef99c64ec6` failed CI #4662 at the new case-alias reservation test on the unpatched runtime, proving the regression detects the defect. Runtime repair `969142b4adb92104a77041c02ae3f9081965999b` applies one shared host-filesystem identity to both unresolved reservation conflicts and recovery reference correlation. Material CI #4665 (`33782870284`) passed **5/5 SUCCESS**, including the Windows-only real-filesystem recovery regression and both browser Product Truth jobs.

The synchronized Draft head `ea9a7dcd559fabc96b04f08b478e70159a7bafa0` then passed authoritative post-body-sync CI #4678 (`33784319416`) **5/5 SUCCESS**: development-context, both Ubuntu/Windows full unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs all succeeded. No runtime, test, schema, or product behavior changed after `969142b4adb92104a77041c02ae3f9081965999b`.

## Repaired invariant

A physical managed arbitrary-publication path has at most one unresolved durable reservation, including case-only aliases on case-insensitive Windows filesystems. Reservation conflict detection and recovery reference correlation use the same host-filesystem identity, while exact expected `reference_id` ownership remains required. Persisted `ProjectReference.path` and marker `relative_path` values remain canonical portable lexical strings.

All earlier Stage-19 Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication, historical identity, Undo/Redo, leased root staging and Product Truth invariants remain unchanged.

## Review authority

This refreeze changes only lifecycle/context state. The next mandatory step is to mark PR #89 Ready, freeze the resulting exact BASE/HEAD, obtain a distinct exact-head post-Ready permanent CI result, and launch a genuinely fresh ordinary-ChatGPT semantic review governed by immutable BASE `.agents/skills/code-review/SKILL.md` v1.0. Merge remains forbidden unless that review returns `CURRENT / PASS / 0 findings` and final live identity, CI and review threads remain clean.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
