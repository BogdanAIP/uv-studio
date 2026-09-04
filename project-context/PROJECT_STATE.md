# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `ed14b91b01892c6888406f836c1c9bc5a50e011e` returned `CURRENT / FINDINGS / 1 P2 / 9 rejected candidates`. The finding was independently confirmed before material repair: canonical Project persistence could accept a reserved `metadata.generation` ProjectReference outside the direct `artifacts/` root, while shared Generation materialization authority rejected the same durable state.

## Repaired finding

The persistence boundary now requires every ProjectReference carrying reserved `metadata.generation` authority to use a direct canonical `artifacts/generated_<attempt_id>[.<ext>]` path. This makes canonical Project acceptance agree with archive, Redo and recovery Generation authority.

Regression-first head `01401beb97d02032139ade287633441d1cf43ca5` proved the defect in CI #4726 (`33855530439`) with the two new non-`artifacts/` cases failing on the unpatched runtime. Runtime repair `b7f50f751ebf301c11986f178fe6c0aa62031d60` made the canonical root requirement unconditional. Test-only follow-ups `1ef208087370e25f740293c4bad2b28f5b571721` and `df5fbe6b6e420c74bbe0b625db895ae0336eafa3` aligned older expectations with the stronger early fail-closed persistence boundary.

## Draft gate

The synchronized Draft head `bbe8aaf55714d0a0ac62c3a5ba1e51af864beb6c` completed authoritative CI #4735 (`33856985717`) **5/5 SUCCESS**. Development-context, both Ubuntu/Windows bootstrap full-unit suites and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs succeeded. The first Windows app-baseline attempt failed only because `npm audit` received HTTP 503 from the npm registry; rerunning that one failed job on the same exact HEAD succeeded through audit, build and browser Product Truth. No repository content changed for the rerun.

All inline PR review threads were rechecked live before refreeze and are resolved. PR #89 was open, Draft, unmerged and mergeable with exact BASE `52be1939eca51d7147990288cfc6258b023c2cd2` and exact Draft HEAD `bbe8aaf55714d0a0ac62c3a5ba1e51af864beb6c`.

## Invariants

Any ProjectReference with reserved `metadata.generation` authority must be a direct file under the canonical `artifacts/` root and its basename must match `generated_<attempt_id>` with an optional extension. Persistence, Generation archive authority, Redo authority and restart recovery must agree on this shape.

Managed-publication recovery must continue to reject lexical leaf symlinks before resolution, preserve filesystem-equivalent reservation/correlation, require exact reference-ID ownership and keep persisted Project paths portable. Generation archive/Redo/recovery must continue to use canonical durable Job/Attempt provenance and exact output size/SHA-256 authority. All previous Stage-19 publication, recovery, schema-v1/v2, Undo/Redo, root-staging and Product Truth invariants remain unchanged.

## Review authority

This refreeze changes only durable development context; it does not change runtime, tests, schemas or product behavior. PR #89 may now return to Ready. The resulting exact HEAD must remain frozen for a genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0.

A future `CURRENT / PASS / 0 findings` is necessary but not sufficient for merge. The final merge-authoritative exact-head permanent CI must be obtained after that review on the same reviewed HEAD, followed by live BASE/HEAD/mergeability and unresolved-thread verification. Any material finding returns the PR and lifecycle to Draft before repair.

After merge, mandatory D-038 lifecycle closure to `idle` remains required before another slice starts.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
