# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `71006f09aa0db73991b7014fa1d2242db163ea83` returned `CURRENT / FINDINGS / 2 P2 / 14 rejected candidates`. Both findings were independently confirmed before material repair, and PR #89 was converted back to Draft before runtime/test changes. Lifecycle `review -> draft` was persisted in `552367f7a95848af640f768b61f535c76a474c6a`.

The first P2 was a managed-publication recovery leaf-symlink bug: `resolve_project_file()` followed an existing in-root leaf symlink before recovery checked `is_symlink()`, so a crash-left marker could cause recovery to quarantine the symlink target rather than fail closed on the marker's lexical entry. The second P2 was a Generation authority validation gap: `generation_materialization_authority()` cherry-picked raw durable Job JSON without first applying canonical `GenerationJob.from_dict()` validation or binding parsed Job identity to the physical project/task identity.

## Regression-first evidence

Regression commit `f3bf657480ebb7d0da0bb4d10e58df8f48a1d17e` adds a publication recovery test proving that a marker leaf symlink must be rejected without touching its legitimate registered target. Regression commit `ad16553a34482bdf0b2008e3dd5ae05ece0be998` adds a Generation archive-authority test that first proves `GenerationJobManager` rejects an unsupported durable Job schema and then requires archive authority to reject the same record.

Exact regression-only CI #4689 (`33791042300`) on `ad16553a34482bdf0b2008e3dd5ae05ece0be998` failed both Ubuntu and Windows full-unit jobs at the new regressions on the unpatched runtime. The existing Ubuntu/Windows app-baseline API/real-media/frontend/browser jobs still passed. `development-context` also failed only because lifecycle had already returned to Draft while this file and `NEXT_TASK.md` still described the superseded review state.

## Runtime repair

`efcf6dc6c7dd01def6bc7b77a309ac071ded068f` makes managed-publication recovery inspect and reject the marker's lexical leaf symlink before the general resolver can follow it. The existing containment/root validation, exact/case-alias reservation identity, reference-ID ownership and ordinary regular-file quarantine behavior remain unchanged.

`8555303655a1acc6adaa4196cefecd3fa4489641` makes shared Generation materialization authority parse durable Job JSON through canonical `GenerationJob.from_dict()`, fail closed on parser/validation errors, and explicitly require parsed `project_id`/`job_id` to match the physical project and task-file identity before selecting the historical attempt. Historical successful-attempt semantics remain supported; overall Job success is not newly required for incomplete materialization authority.

Preliminary material CI #4693 (`33791585364`) on `8555303655a1acc6adaa4196cefecd3fa4489641` has both Ubuntu and Windows full-unit suites green, including both new regressions. Its `development-context` result is intentionally obsolete because the Draft context synchronization had not yet been committed; the authoritative gate is the post-synchronization exact-head Draft CI.

## Repaired invariants

Managed publication recovery must preserve lexical leaf identity: a crash-left marker whose output entry is a symlink fails closed and can never quarantine the symlink target. Physical publication path reservation/recovery still uses the shared host-filesystem identity for case aliases while persisted lexical Project paths remain unchanged.

Every Generation ProjectReference trusted by archive/Redo/recovery authority must resolve through one canonically parsed durable `GenerationJob`, whose parsed project/job identity matches the physical project/task identity, before historical attempt provenance or output bytes can be trusted.

All earlier Stage-19 schema-v1/v2, historical identity, Undo/Redo, archive, Generation retry/recovery/idempotency, publication, leased root staging and Product Truth invariants remain unchanged.

## Next gate

Draft lifecycle and continuation context are synchronized. Synchronize the PR body without further runtime/test/schema/product changes, then require one authoritative exact-head Draft CI **5/5 SUCCESS** created after that body synchronization. Only after that may lifecycle refreeze `draft -> review`, PR #89 return to Ready, and another genuinely fresh ordinary-ChatGPT semantic review be launched against the new frozen exact HEAD.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
