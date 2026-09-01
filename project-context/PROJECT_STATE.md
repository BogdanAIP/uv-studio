# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `a6324ec9f4113f62e82e19004a1ab82b276f8b3a` passed authoritative post-Ready CI #4298 **5/5**, but a completely fresh ordinary-ChatGPT semantic review returned two new `CURRENT` P1 findings. Both were independently confirmed. PR #89 returned to Draft and that review/freeze evidence is stale for merge authority.

The two findings are now materially repaired. Material/test head `e037d20c773a141dc24f35369179a581d4081e9c` passed diagnostic CI #4311 (`33510352252`) **5/5** on Ubuntu and Windows, including the full unit suite, API integration, pinned real-media verification, frontend lint/audit/build and browser Product Truth. Project Store/archive documentation is synchronized after that material gate; one final exact Draft docs/context head CI remains required before refreeze.

## Second fresh-review repair

### P1 — historical older-attempt Generation artifacts

Generation recovery and archive authority are now attempt-specific instead of assuming every durable artifact belongs to `attempts[-1]`.

A Generation ProjectReference names its own `attempt_id`. Recovery groups Job artifacts by that identity, validates the exact artifact/attempt bytes and provenance, and can repair a historical failed/cancelled artifact-owning attempt in place even when a later retry already exists. Repairing an older attempt does not overwrite the newer attempt or falsely make the Job overall `SUCCEEDED`; current execution state remains governed by the newest attempt.

Current retry/fail/cancel transitions are blocked while any Job attempt has a durable artifact that has not yet been reconciled as that attempt's success. Current code therefore cannot create another older-attempt stranded-artifact state while historical BASE-compatible states remain recoverable without provider replay.

Archive export validates every Generation artifact against the exact matching durable attempt rather than requiring it to equal the final attempt. The artifact-owning attempt must itself be a successful materialization with the same output reference and historical Take identity.

### P1 — current Production Take vs immutable Job provenance after Undo

Generation Job records intentionally remain outside user Undo/Redo. A successful attempt's `take_id` is immutable historical provenance; it is no longer treated as proof that the Take still exists in current Production Semantics.

Archive export resolves current Production Semantics for every Generation artifact. If the named Take exists, it must belong to the Job's exact `shot_id` and point to that exact artifact. If it is absent, export accepts that absence only when durable ProjectUnitOfWork transaction/operation journals prove that `production.register_take` created the exact Take and a committed user Undo later removed it. That proof survives a later command truncating the stale redo branch.

An out-of-band missing Take, wrong Shot/reference, malformed/ambiguous history or a later Redo remains fail-closed. Startup does not silently recreate a Take for an already-SUCCEEDED attempt merely because the user intentionally undid it.

## New deterministic regressions

`tests/test_stage19_fresh_review_repairs.py` now additionally proves:

1. a BASE-compatible `attempt0` durable artifact followed by later failed `attempt1` blocks another retry before recovery, then startup repairs `attempt0` by its own identity without replaying the provider, keeps `attempt1`/Job current status intact and makes the historical artifact archiveable;
2. successful Generation followed by real global `ProjectUnitOfWork.undo()` removes the current Production Take while preserving the SUCCEEDED Job; a later user command truncates redo history, yet archive remains valid because durable Undo evidence proves the Take's intentional absence;
3. removing that same Take outside UOW history causes archive to fail closed because no durable Undo authority exists.

The prior seven fresh-review regressions remain active, covering post-artifact Take failure, legacy current-attempt terminal split, cross-runtime cancel, changed Generation bytes, provenance mismatch, succeeded-artifact archive corruption and source crash-orphan recovery.

## Previously repaired Stage-19 behavior retained

The current repair preserves:

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
- `6a8b8d44bad4852e5d41c71b7a3c78ef22ed1dcc` and `e559a1ad269c15abc74d73759a1a8778bceeb61c`: Project Store/archive contract synchronization after the material gate.

## Current repair gate

Lifecycle remains `draft`. Runtime/test behavior is materially green on CI #4311 and documentation is synchronized. The next authoritative gate is all five permanent CI jobs on the exact final Draft docs/context head, after the canonical PR body is synchronized to this second repair cycle.

After exact Draft-head CI is **5/5**:

1. reply to any new review threads with exact repair/test/CI evidence and resolve only after validation;
2. perform one context-only `draft -> review` freeze;
3. return PR #89 to Ready without changing the frozen head;
4. require authoritative post-Ready exact-head CI **5/5**;
5. verify no unresolved review threads;
6. run another completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved. Lifecycle closure remains a separate follow-up after merge.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
