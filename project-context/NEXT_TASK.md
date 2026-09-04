# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89 and is in `draft` after the fresh review of frozen head `ed14b91b01892c6888406f836c1c9bc5a50e011e` returned `CURRENT / FINDINGS / 1 P2 / 9 rejected candidates`.

The confirmed P2 was an acceptance-authority mismatch: canonical Project persistence could accept a reserved `metadata.generation` reference outside `artifacts/`, while Generation archive/Redo/recovery authority required the direct canonical `artifacts/` root.

Regression-first head `01401beb97d02032139ade287633441d1cf43ca5` proved the defect in CI #4726 (`33855530439`): the two new `exports/...` and `assets/...` cases failed on the unpatched runtime while the rest of the Ubuntu unit suite passed. Runtime repair `b7f50f751ebf301c11986f178fe6c0aa62031d60` makes the canonical root requirement unconditional. Test-only follow-ups `1ef208087370e25f740293c4bad2b28f5b571721` and `df5fbe6b6e420c74bbe0b625db895ae0336eafa3` move two older expectations to the stronger early persistence boundary.

Both Ubuntu and Windows full-unit suites are green on material/test CI #4732 (`33856115358`) for `df5fbe6b6e420c74bbe0b625db895ae0336eafa3`. The old `development-context` failure on that run is expected because durable context had not yet been synchronized.

## Immediate continuation

1. Synchronize the PR body to the current Draft repair, preserving the exact `## Changes` heading required by development-context validation.
2. Treat only a CI created after that final PR-body synchronization as the authoritative synchronized Draft gate.
3. Require all five permanent jobs to pass: development-context, Ubuntu full-unit, Windows full-unit, Ubuntu app-baseline and Windows app-baseline including API, real-media, frontend and browser Product Truth.
4. If a failure is clearly transient external infrastructure, rerun only the failed job on the same HEAD; do not create no-op commits.
5. After 5/5, re-resolve PR #89 and inline review threads, then refreeze lifecycle `draft -> review` in one context-only commit and mark the PR Ready.
6. Freeze the resulting exact BASE/HEAD and launch a genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 with a neutral `REVIEW_REQUEST_V1`.
7. If that review returns `CURRENT / FINDINGS`, validate independently and return PR/lifecycle to Draft before any material change.
8. If it returns `CURRENT / PASS / 0 findings`, obtain a new final exact-head permanent CI after the review, re-resolve live BASE/HEAD/mergeability and unresolved threads, then merge only with the reviewed expected HEAD.
9. After merge, perform mandatory D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

Every ProjectReference carrying reserved `metadata.generation` authority must have a direct canonical `artifacts/generated_<attempt_id>[.<ext>]` path. Canonical persistence and downstream Generation materialization authority must accept exactly the same root/name shape.

Managed-publication recovery must continue to reject lexical leaf symlinks before resolution, preserve filesystem-equivalent reservation/correlation, require exact reference-ID ownership and keep persisted Project paths portable. Generation archive/Redo/recovery must continue to use canonical durable Job/Attempt provenance and exact output size/SHA-256 authority. All previous Stage-19 publication, recovery, schema-v1/v2, Undo/Redo, root-staging and Product Truth invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this repair cycle.
