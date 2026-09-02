# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-02

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The cumulative Stage-19 implementation and all prior fresh-review repairs remain in force. Before the next Ready transition, a final development-context adversarial preflight was run across Project schema-v1/v2 compatibility, ProjectUnitOfWork history, archive/recovery authority, Generation Job/Attempt/Take identity, binary digest authority, publication recovery and browser Product Truth.

## Final preflight findings and repairs

The preflight found and repaired these additional concrete gaps before Ready:

1. **Partial Redo Generation byte validation.** `ProjectUnitOfWork.redo()` now validates every Generation ProjectReference remaining live after any Redo, including a Production-only Redo after the artifact Redo. This prevents a Take from being restored around bytes changed between Redos.
2. **Valid ProjectReference metadata evolution.** Shared redo authority now allows canonical metadata evolution such as `production.accept_take` only while stable reference ID/path/kind and immutable Generation Job/Attempt/size/SHA authority stay identical. Path reuse, classification drift and provenance drift fail closed.
3. **Full Redo reachability.** Redo authority simulates the complete current redo suffix and requires each canonical `before -> after` snapshot transition to be reachable before historical ProjectReferences become archive/recovery authority.
4. **Generation structural authority.** Generation authority requires the canonical attempt-derived publication shape, reconnects continuation lineage to the durable contract, and prevents nested `artifacts/.../...` Generation paths.
5. **Reserved Generation namespace.** A ProjectReference carrying the `generation` key must carry a JSON-object authority payload. `job_id` and `attempt_id` are validated identifiers before task-record path use; malformed/downgraded Generation metadata fails closed at the Project boundary.
6. **Generation container role.** A Generation ProjectReference is an artifact and cannot be placed in `Project.sources`, preventing archive ownership classification from bypassing Generation Job/digest validation.
7. **Existing Generation authority immutability under generic writes.** While a reference ID remains present, generic canonical mutation cannot change its path/kind or strip/rebind `metadata.generation`. Full removal through Undo remains valid, and unrelated canonical metadata such as `production_acceptances` may still evolve.
8. **Regression layering after stronger guards.** Two older negative tests previously used canonical `update_project()` to construct intentionally corrupt Generation state. The stronger transition guard now rejects those mutations earlier, so commits `61acf52bf15568dd76ff082509fb5c332e1383d5` and `ae95ad0d83d240dcbb29d51b0038f95eaa8b1fb1` preserve the original recovery/archive checks by simulating out-of-band durable `project.json` corruption directly instead of weakening production validation.

Key implementation/test commits in this final preflight include `f0ea9f54854895646776572edf0602dffc5c1309`, `07253a6e8646b7caeb12bc92de5e89530f2b8847`, `6e16b5bcd42d887b14b22c36173bb77f4b78dc14`, `553b240dc8c1f4f06d25ee0b9dfdacd3a8bc2a27`, `abed09f7780159e2a6e16905993ca6b2383033f9`, `7e31b75b1aee9ba92a7e4043a5359195ed12d07e`, `8a3bc170a43a8f766635e6b5b23399e9452d3f7d`, `2eacf0ba055baf5e716ac1222aa7cec34fd2b5a7`, and `808cf64f1c14484e6268e28412bbf937ac2e9d42`.

`docs/PROJECT_STORE.md` and `docs/PROJECT_ARCHIVES.md` are synchronized with the resulting Generation/Redo/archive authority contract.

## Verification

Exact material/test head `ae95ad0d83d240dcbb29d51b0038f95eaa8b1fb1` passed CI #4507 (`33646746316`) **5/5 SUCCESS**:

- `development-context` — SUCCESS;
- `bootstrap (ubuntu-latest, 3.11)` — SUCCESS, full unit suite;
- `bootstrap (windows-latest, 3.11)` — SUCCESS, full unit suite;
- `app-baseline (ubuntu-latest)` — SUCCESS, API integration, real-media, frontend lint/audit/build and browser Product Truth;
- `app-baseline (windows-latest)` — SUCCESS, API integration, pinned media toolchain, real-media, frontend lint/audit/build and browser Product Truth.

A live PR-thread recheck after the material repair found zero unresolved inline review threads. The final read-only falsification pass found no additional supported defect across the repaired Generation classification, pending/succeeded recovery, redo variant aggregation, archive digest authority, schema-v1 compatibility and generic public Project-update boundaries.

All earlier Stage-19 repairs remain intended to stay in force: exact historical schema-v1/v2 identity, prepared-UOW recovery before archive sampling, project-fenced archive snapshots, staged/fenced WebVTT and Generation publication, exact Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, arbitrary-path publication fail-closed behavior and immediate-next-action Product Truth behavior.

## Next required action

1. synchronize the PR body with this final Draft evidence and current context head;
2. require one synchronized exact-head Draft CI **5/5**;
3. recheck exact BASE/HEAD and zero unresolved inline threads;
4. if still clean, make only context lifecycle changes from `draft` to `review` and freeze the resulting HEAD;
5. mark PR #89 Ready once and require post-Ready exact-head CI **5/5**;
6. run the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
7. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with exact final BASE/HEAD/CI/thread identity still clean.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
