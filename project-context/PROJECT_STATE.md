# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `ed14b91b01892c6888406f836c1c9bc5a50e011e` returned `CURRENT / FINDINGS / 1 P2 / 9 rejected candidates`. The finding was independently confirmed before material repair: canonical Project persistence could accept a reserved `metadata.generation` ProjectReference outside the direct `artifacts/` root, while shared Generation materialization authority rejected the same durable state.

PR #89 and lifecycle were returned to Draft before runtime/test changes.

## Current repair

The persistence boundary now requires every ProjectReference carrying reserved `metadata.generation` authority to use a direct canonical `artifacts/generated_<attempt_id>[.<ext>]` path. This makes canonical Project acceptance agree with the archive/Redo/recovery Generation authority boundary instead of allowing a durable state that later fail-closes only downstream.

Regression-first head `01401beb97d02032139ade287633441d1cf43ca5` added explicit `exports/...` and `assets/...` Generation-path cases. CI #4726 (`33855530439`) ran the unpatched Ubuntu unit suite and failed exactly those two new subcases with `ProjectValidationError not raised`; the remaining tests passed.

Runtime repair `b7f50f751ebf301c11986f178fe6c0aa62031d60` removes the conditional root check and enforces the direct canonical `artifacts/` root for every reserved Generation reference. Test-only commits `1ef208087370e25f740293c4bad2b28f5b571721` and `df5fbe6b6e420c74bbe0b625db895ae0336eafa3` align two older tests with the stronger early fail-closed persistence contract; no runtime behavior changed in those follow-ups.

Material/test CI #4732 (`33856115358`) on `df5fbe6b6e420c74bbe0b625db895ae0336eafa3` has both Ubuntu and Windows full-unit suites green with the repaired contract. Its `development-context` failure is expected because this durable context still described the previous review cycle before this synchronization; the clean synchronized Draft 5/5 gate is the next authority.

## Invariants

Any ProjectReference with reserved `metadata.generation` authority must be a direct file under the canonical `artifacts/` root and its basename must match `generated_<attempt_id>` with an optional extension. Persistence, Generation archive authority, Redo authority and restart recovery must agree on this shape.

All earlier Stage-19 schema-v1/v2 compatibility, historical identity, Undo/Redo, archive, Generation retry/recovery/idempotency, exact byte-digest authority, source/WebVTT/arbitrary publication, managed-publication symlink/case/reference ownership, leased root staging and Product Truth repairs remain unchanged.

## Next gate

Synchronize the PR body to this Draft repair without changing runtime/test/schema/product behavior, then require one exact-head post-body-sync CI with all five permanent jobs successful: `development-context`, both Ubuntu/Windows full-unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs.

Only after that clean Draft gate may lifecycle move `draft -> review`, PR #89 return to Ready and a new exact frozen HEAD be sent to a genuinely fresh ordinary-ChatGPT semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.

A future `CURRENT / PASS / 0 findings` is necessary but not sufficient for merge. The final merge-authoritative exact-head CI must be obtained after that review on the same reviewed HEAD, followed by live BASE/HEAD/mergeability and unresolved-thread verification. After merge, mandatory D-038 lifecycle closure to `idle` remains required before another slice starts.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
