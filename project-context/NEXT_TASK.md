# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. The latest confirmed publication P1 is materially repaired: regression `6a45e4b5a548d9eb37fe8f36875118cb697f51e2` covers the same-path crash reservation race and runtime repair `5279df39fc7f7ca80cda22d9a8dd3ed237a28fef` closes it at the shared `begin_managed_publication()` boundary.

Synchronized Draft head `9d0fa344e2f8b35f283dba7f3b533228d8e7f42c` passed latest authoritative CI #4646 (`33773714906`) **5/5 SUCCESS** across development-context, both full unit suites and both app-baseline API/real-media/frontend/browser Product Truth jobs. Lifecycle is now refrozen `draft -> review`; no runtime/test/schema/product changes are allowed unless new review evidence requires a Draft repair cycle.

## Immediate continuation

1. Synchronize the PR body with the exact refrozen review HEAD and mark PR #89 Ready without material changes.
2. Freeze exact live BASE/HEAD and launch another genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 and only neutral `REVIEW_REQUEST_V1` launcher instructions.
3. Treat CI triggered by refreeze/Ready before the fresh review as preliminary evidence only.
4. If review returns `CURRENT / PASS / 0 findings`, obtain final exact-head permanent CI/browser/real-media acceptance on the same reviewed HEAD, then verify live BASE/HEAD/mergeability and unresolved threads and merge with expected HEAD SHA.
5. If review returns a supported material finding, return PR/lifecycle to Draft before any material change and repeat the governed repair cycle.
6. After merge, perform D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

A canonical arbitrary publication path may have only one unresolved durable managed-publication reservation. The path-reservation check and marker creation are one project-lock critical section; an absent target file does not permit reuse while an older marker exists. Recovery of a no-byte interrupted marker clears only that reservation and cannot invalidate a later successful publication.

Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication semantics and all previously repaired Stage-19 invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review/merge cycle.
