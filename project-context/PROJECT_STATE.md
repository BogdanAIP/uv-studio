# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `71006f09aa0db73991b7014fa1d2242db163ea83` returned `CURRENT / FINDINGS / 2 P2 / 14 rejected candidates`. Both findings were independently confirmed, PR/lifecycle returned to Draft before material changes, regression-first evidence proved both defects on the unpatched runtime, and the two runtime repairs were completed.

## Repaired findings

Managed-publication recovery now rejects the marker's lexical leaf symlink before general project-file resolution can follow it. A crash-left marker can therefore never quarantine the target of an in-root symlink. Existing containment checks, host-filesystem case-alias identity, exact reference-ID ownership and regular-file quarantine semantics remain unchanged.

Shared Generation materialization authority now parses the complete durable Job through canonical `GenerationJob.from_dict()` validation and explicitly requires parsed `project_id`/`job_id` to match the physical project/task identity before historical attempt authority is trusted. Historical successful-attempt semantics remain supported even when a later attempt is failed.

Regression-only CI #4689 (`33791042300`) failed both Ubuntu and Windows unit jobs at the two new tests before the fixes. Material repair CI #4693 subsequently passed both Ubuntu and Windows full-unit suites with the new regressions green.

## Draft gate

After Draft context and PR-body synchronization, authoritative exact-head CI #4717 (`33792871334`) completed **5/5 SUCCESS** on repaired Draft head `7977834f0df204dd07ffbc8fd7e94a7dd145ea9f`: development-context, both Ubuntu/Windows bootstrap full-unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs all succeeded. All inline PR review threads were re-resolved live and remain resolved.

No runtime, test, schema or product behavior changed after runtime repair `8555303655a1acc6adaa4196cefecd3fa4489641`; subsequent changes only synchronized durable development context and PR metadata.

## Review authority

The slice is now refrozen for a new independent semantic review. The next mandatory step is to mark PR #89 Ready and launch a genuinely fresh ordinary-ChatGPT read-only review against the resulting exact BASE/HEAD under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.

A future `CURRENT / PASS / 0 findings` is necessary but not sufficient for merge. Only after that review may the final exact-head permanent CI/browser/real-media acceptance be obtained on the same reviewed HEAD. Then live BASE/HEAD/mergeability and unresolved threads must be rechecked before merge. Any material finding returns the PR to Draft and invalidates the previous review identity.

After merge, mandatory D-038 lifecycle closure to `idle` remains required before another slice starts.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
