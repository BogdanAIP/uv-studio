# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89 and is refrozen in `review` after repair of the fresh-review P2 concerning reserved Generation ProjectReference root authority.

Regression-first CI #4726 (`33855530439`) proved the wrong-root defect on the unpatched runtime. Runtime repair `b7f50f751ebf301c11986f178fe6c0aa62031d60` made the direct canonical `artifacts/generated_<attempt_id>[.<ext>]` shape mandatory for every reserved `metadata.generation` reference; test-only follow-ups aligned older expectations with that stronger persistence boundary.

Synchronized Draft head `bbe8aaf55714d0a0ac62c3a5ba1e51af864beb6c` completed CI #4735 (`33856985717`) **5/5 SUCCESS**. The only first-attempt failure was a transient npm-registry HTTP 503 in Windows `npm audit`; rerunning only that job on the same HEAD succeeded. All inline review threads were rechecked and are resolved.

## Immediate continuation

1. Mark PR #89 Ready without changing runtime/test/schema/product behavior.
2. Freeze the resulting exact BASE/HEAD identity.
3. Obtain the permanent exact-head CI required for the Ready frozen HEAD if GitHub creates a new run from the lifecycle/Ready transition; do not change the HEAD merely to trigger CI.
4. Launch a genuinely fresh ordinary-ChatGPT read-only semantic review using immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 and a neutral `REVIEW_REQUEST_V1` against that exact frozen HEAD.
5. If the review returns `CURRENT / FINDINGS`, validate independently and return PR/lifecycle to Draft before any material repair.
6. If the review returns `CURRENT / PASS / 0 findings`, obtain a new final exact-head permanent CI after the review on the same reviewed HEAD, then re-resolve live BASE/HEAD/mergeability and unresolved threads before merge with the reviewed expected HEAD.
7. After merge, perform mandatory D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

Every ProjectReference carrying reserved `metadata.generation` authority must have a direct canonical `artifacts/generated_<attempt_id>[.<ext>]` path. Canonical persistence and downstream Generation materialization authority must accept exactly the same root/name shape.

Managed-publication recovery must continue to reject lexical leaf symlinks before resolution, preserve filesystem-equivalent reservation/correlation, require exact reference-ID ownership and keep persisted Project paths portable. Generation archive/Redo/recovery must continue to use canonical durable Job/Attempt provenance and exact output size/SHA-256 authority. All previous Stage-19 publication, recovery, schema-v1/v2, Undo/Redo, root-staging and Product Truth invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this review cycle.
