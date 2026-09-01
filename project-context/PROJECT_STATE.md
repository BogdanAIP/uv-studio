# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen in `review` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `a6324ec9f4113f62e82e19004a1ab82b276f8b3a` passed authoritative post-Ready CI #4298 **5/5**, but a completely fresh ordinary-ChatGPT semantic review returned two new `CURRENT` P1 findings. Both were independently confirmed, PR #89 returned to Draft, and that review/freeze evidence became stale for merge authority.

The second repair is now complete. Material/test head `e037d20c773a141dc24f35369179a581d4081e9c` passed CI #4311 (`33510352252`) **5/5**. Final Draft docs/context head `4ef9f2f75497467f4b6ac68fb4b0961deef4fa99` then passed authoritative post-body-sync CI #4318 (`33511031438`) **5/5**: `development-context`, both Ubuntu/Windows bootstrap jobs and both Ubuntu/Windows app-baseline jobs all succeeded, including full unit suites, API integration, pinned real-media verification, frontend lint/audit/build and browser Product Truth. The one fresh unresolved inline review thread was answered with exact repair/test/CI evidence and resolved before this context-only `draft -> review` freeze.

## Second fresh-review repair now frozen

### P1 — historical older-attempt Generation artifacts

Generation recovery and archive authority are attempt-specific instead of assuming every durable artifact belongs to `attempts[-1]`.

A Generation ProjectReference names its own `attempt_id`. Recovery groups Job artifacts by that identity, validates the exact artifact/attempt bytes and provenance, and can repair a historical failed/cancelled artifact-owning attempt in place even when a later retry already exists. Repairing an older attempt does not overwrite the newer attempt or falsely make the Job overall `SUCCEEDED`; current execution state remains governed by the newest attempt.

Retry/fail/cancel transitions are blocked while any Job attempt has a durable artifact that has not yet been reconciled as that attempt's success. Archive export validates every Generation artifact against the exact matching durable attempt rather than requiring it to equal the final attempt.

### P1 — current Production Take vs immutable Job provenance after Undo

Generation Job records intentionally remain outside user Undo/Redo. A successful attempt's `take_id` is immutable historical provenance; it is not treated as proof that the Take still exists in current Production Semantics.

Archive export resolves current Production Semantics for every Generation artifact. If the named Take exists, it must belong to the Job's exact `shot_id` and point to that exact artifact. If it is absent, export accepts that absence only when durable ProjectUnitOfWork transaction/operation journals prove that `production.register_take` created the exact Take and a committed user Undo later removed it. That proof survives a later user command truncating the stale redo branch.

An out-of-band missing Take, wrong Shot/reference, malformed or ambiguous history, or a later Redo remains fail-closed. Startup does not silently recreate a Take for an already-SUCCEEDED attempt merely because the user intentionally undid it.

## Deterministic regression evidence

`tests/test_stage19_fresh_review_repairs.py` additionally proves:

1. a BASE-compatible `attempt0` durable artifact followed by later failed `attempt1` blocks another retry before recovery, then startup repairs `attempt0` by its own identity without replaying the provider, keeps `attempt1`/Job current status intact and makes the historical artifact archiveable;
2. successful Generation followed by real global `ProjectUnitOfWork.undo()` removes the current Production Take while preserving the SUCCEEDED Job; a later user command truncates redo history, yet archive remains valid because durable Undo evidence proves the Take's intentional absence;
3. removing that same Take outside UOW history causes archive to fail closed because no durable Undo authority exists.

The prior seven fresh-review regressions remain active, covering post-artifact Take failure, legacy current-attempt terminal split, cross-runtime cancel, changed Generation bytes, provenance mismatch, succeeded-artifact archive corruption and source crash-orphan recovery.

## Previously repaired Stage-19 behavior retained

The frozen repair preserves:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejection of raw schema-v1 `project.json`, while historical schema-v1 undo/redo migrates only for validation and restores exact recorded bytes;
- coherent cross-runtime Generation Job/publication fencing;
- exact Generation byte/digest/provenance verification;
- source `src_<uuid>` crash-orphan quarantine;
- arbitrary-path `timeline.assemble` durable publication markers;
- WebVTT `sub_<uuid>` orphan quarantine;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exclusion and symlink fail-closed behavior;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair;
- no automatic provider replay during recovery.

## Verification history

- Frozen `e31f42afe652d7238be99388084a81684626fe08`: post-Ready CI #4265 **5/5**, then three confirmed findings.
- Draft repair `1ad82d4c0475eb4fc05ad79ab45ede375601538d`: CI #4293 **5/5**.
- Frozen `a6324ec9f4113f62e82e19004a1ab82b276f8b3a`: post-Ready CI #4298 **5/5**, then two new confirmed P1 findings.
- `c71f7f7ae03f9ecff616bef64e1fd30cb3a15721`: attempt-specific historical Generation reconciliation.
- `af661b794301b6135f61ec2e63a04b03d399f1d2`: retry/fail/cancel guards across all unreconciled Job artifacts.
- `a2ae900db2eaff044b5fa9fe46eebe730c71afd3`: archive validation by artifact-owning attempt plus current Take / durable Undo authority.
- `e037d20c773a141dc24f35369179a581d4081e9c`: three focused second-review regressions; CI #4311 **5/5 SUCCESS**.
- `4ef9f2f75497467f4b6ac68fb4b0961deef4fa99`: final Draft docs/context head; authoritative post-body-sync CI #4318 (`33511031438`) **5/5 SUCCESS**.
- All inline review threads resolved before refreeze.

## Current review gate

Lifecycle is now `review`; no further material/runtime/test edits are authorized on this frozen branch unless a later confirmed finding first returns the slice to `draft`.

Next required sequence:

1. return PR #89 from Draft to Ready without changing this frozen head;
2. require authoritative post-Ready exact-head CI **5/5**;
3. re-resolve live base/head identity and verify zero unresolved review threads;
4. run a completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved. Lifecycle closure remains a separate follow-up after merge.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
