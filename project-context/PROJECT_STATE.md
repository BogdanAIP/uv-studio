# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of the prior frozen head `6603e46e932432e52e409a4a9656f5625bd9b540` returned `CURRENT / FINDINGS / 1 P1 / 15 rejected candidates`. The finding was independently confirmed, PR/lifecycle returned to Draft before material repair, and that old review is permanently stale for merge authority.

Regression-first commit `6a45e4b5a548d9eb37fe8f36875118cb697f51e2` covers the old-marker/no-bytes same-path reservation race. Runtime repair `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef` makes marker validation, same-canonical-path conflict detection and marker creation one atomic critical section under the shared re-entrant cross-runtime project lock.

## Repaired invariant

A canonical managed arbitrary-publication path has at most one unresolved durable reservation at a time. An interrupted marker with no materialized bytes blocks later publishers until recovery clears it; recovery of an older marker therefore cannot quarantine bytes from a newer successful publication at the same path.

The earlier Generation redo-only retry invariant remains unchanged: every failed-job execution entry point stays blocked before provider replay while validated redo-owned materialization is reachable.

## Verification

- material repair head `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef`: CI #4643 (`33772892896`) **5/5 SUCCESS**;
- synchronized Draft head `9d0fa344e2f8b35f283dba7f3b533228d8e7f42c`: latest authoritative Draft CI #4646 (`33773714906`) **5/5 SUCCESS** — development-context, both Ubuntu/Windows full unit suites including the new regression, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs all passed.

No runtime, test, schema or product behavior changed after `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef`.

## Review freeze

The corrected repair has completed its Draft gates and lifecycle is refrozen `draft -> review`. Runtime/test/schema/product changes are prohibited unless a new supported material finding requires returning PR #89 to Draft.

Next required gates:

1. synchronize PR body with the exact refrozen review HEAD and mark PR #89 Ready without material changes;
2. freeze exact live BASE/HEAD and perform another genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
3. treat any refreeze/Ready-triggered CI before that review as preliminary evidence only;
4. if the new review is `CURRENT / PASS / 0 findings`, obtain a final exact-head permanent CI/browser/real-media acceptance confirmation on that same reviewed HEAD;
5. verify live BASE/HEAD/mergeability and zero unresolved review threads, then merge with expected HEAD SHA;
6. after merge, perform mandatory D-038 lifecycle closure to `idle` before the next slice.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
